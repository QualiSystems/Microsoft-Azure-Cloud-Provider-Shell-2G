from cloudshell.cp.core.flows.deploy import AbstractDeployFlow
from cloudshell.cp.core.request_actions.models import DeployAppResult, Attribute

from azure.mgmt.compute import models as compute_models
from package.cloudshell.cp.azure.actions.network import NetworkActions
from package.cloudshell.cp.azure.actions.network_security_group import NetworkSecurityGroupActions
from package.cloudshell.cp.azure.actions.vm import VMActions
from package.cloudshell.cp.azure.actions.validation import ValidationActions
from package.cloudshell.cp.azure.actions.vm_credentials import VMCredentialsActions
from package.cloudshell.cp.azure.actions.vm_extension import VMExtensionActions
from package.cloudshell.cp.azure.exceptions import AzureTaskTimeoutException
from package.cloudshell.cp.azure.flows.deploy_vm import commands
from package.cloudshell.cp.azure.utils import name_generator
from package.cloudshell.cp.azure.utils.nsg_rules_priority_generator import NSGRulesPriorityGenerator
from package.cloudshell.cp.azure.utils.rollback import RollbackCommandsManager
from package.cloudshell.cp.azure.utils.cs_reservation_output import CloudShellReservationOutput
from package.cloudshell.cp.azure.utils.tags import AzureTagsManager


class BaseAzureDeployVMFlow(AbstractDeployFlow):
    def __init__(self, resource_config, azure_client, cs_api, reservation_info, cancellation_manager, cs_ip_pool_manager,
                 lock_manager, logger):
        """

        :param resource_config:
        :param azure_client:
        :param cs_api:
        :param reservation_info:
        :param cancellation_manager:
        :param cs_ip_pool_manager:
        :param lock_manager:
        :param logger:
        """
        super().__init__(logger=logger)
        self._resource_config = resource_config
        self._azure_client = azure_client
        self._cs_api = cs_api
        self._reservation_info = reservation_info
        self._cancellation_manager = cancellation_manager
        self._cs_ip_pool_manager = cs_ip_pool_manager
        self._rollback_manager = RollbackCommandsManager(logger=self._logger)
        self._tags_manager = AzureTagsManager(reservation_info=self._reservation_info)
        self._cs_reservation_output = CloudShellReservationOutput(cs_api=self._cs_api,
                                                                  reservation_id=self._reservation_info.reservation_id,
                                                                  logger=self._logger)
        self._lock_manager = lock_manager

    def _get_vm_image_os(self, deploy_app):
        """

        :param deploy_app:
        :return:
        """
        raise NotImplementedError(f"Class {type(self)} must implement method '_get_vm_image_os'")

    def _prepare_storage_profile(self, deploy_app, os_disk):
        """

        :param deploy_app:
        :param os_disk
        :return:
        """
        raise NotImplementedError(f"Class {type(self)} must implement method '_prepare_storage_profile'")

    def _prepare_vm_details_data(self, deployed_vm, resource_group_name):
        """

        :param deployed_vm:
        :return:
        """
        raise NotImplementedError(f"Class {type(self)} must implement method '_prepare_vm_details_data'")

    def _validate_deploy_app_request(self, deploy_app, connect_subnets, image_os):
        """

        :param deploy_app:
        :param connect_subnets:
        :param image_os:
        :return:
        """
        validation_actions = ValidationActions(azure_client=self._azure_client, logger=self._logger)

        validation_actions.validate_deploy_app_add_public_ip(deploy_app=deploy_app, connect_subnets=connect_subnets)
        validation_actions.validate_deploy_app_inbound_ports(deploy_app=deploy_app)
        validation_actions.validate_deploy_app_disk_size(deploy_app=deploy_app)
        validation_actions.validate_deploy_app_script_file(deploy_app=deploy_app)
        validation_actions.validate_deploy_app_script_extension(deploy_app=deploy_app, image_os=image_os)
        validation_actions.validate_vm_size(deploy_app_vm_size=deploy_app.vm_size,
                                            cloud_provider_vm_size=self._resource_config.vm_size)

    def _create_vm_nsg(self, resource_group_name, vm_name, tags):
        """

        :param resource_group_name:
        :param vm_name:
        :param tags:
        :return:
        """
        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)

        return commands.CreateVMNSGCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            nsg_actions=nsg_actions,
            vm_name=vm_name,
            resource_group_name=resource_group_name,
            region=self._resource_config.region,
            tags=tags,
        ).execute()

    def _create_vm_nsg_inbound_ports_rules(self, deploy_app, vm_name, vm_nsg, resource_group_name,
                                           rules_priority_generator):
        """

        :param deploy_app:
        :param vm_name:
        :param vm_nsg:
        :param resource_group_name:
        :param rules_priority_generator:
        :return:
        """
        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)

        for inbound_port in deploy_app.inbound_ports:
            commands.CreateAllowVMInboundPortRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                nsg_name=vm_nsg.name,
                vm_name=vm_name,
                inbound_port=inbound_port,
                resource_group_name=resource_group_name,
                rules_priority_generator=rules_priority_generator,
            ).execute()

    def _create_vm_nsg_additional_mgmt_networks_rules(self, vm_name, vm_nsg, resource_group_name,
                                                      rules_priority_generator):
        """

        :param vm_nsg:
        :param resource_group_name:
        :param rules_priority_generator:
        :return:
        """
        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)

        for mgmt_network in self._resource_config.additional_mgmt_networks:
            commands.CreateAllowAdditionalMGMTNetworkRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                nsg_name=vm_nsg.name,
                resource_group_name=resource_group_name,
                vm_name=vm_name,
                mgmt_network=mgmt_network,
                rules_priority_generator=rules_priority_generator,
            ).execute()

    def _create_vm_nsg_mgmt_vnet_rule(self, vm_nsg, resource_group_name, rules_priority_generator):
        """

        :param vm_nsg:
        :param resource_group_name:
        :param rules_priority_generator:
        :return:
        """
        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)
        network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)

        commands.CreateAllowMGMTVnetRuleCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            network_actions=network_actions,
            nsg_actions=nsg_actions,
            nsg_name=vm_nsg.name,
            resource_group_name=resource_group_name,
            mgmt_resource_group_name=self._resource_config.management_group_name,
            rules_priority_generator=rules_priority_generator,
        ).execute()

    def _create_vm_nsg_sandbox_traffic_rules(self, deploy_app, vm_nsg, resource_group_name, rules_priority_generator):
        """

        :param deploy_app:
        :param vm_nsg:
        :param resource_group_name:
        :param rules_priority_generator:
        :return:
        """
        if not deploy_app.allow_all_sandbox_traffic:
            nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)

            commands.CreateAllowAzureLoadBalancerRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                nsg_name=vm_nsg.name,
                resource_group_name=resource_group_name,
                rules_priority_generator=rules_priority_generator,
            ).execute()

            commands.CreateDenySandoxTrafficRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                nsg_name=vm_nsg.name,
                resource_group_name=resource_group_name,
                rules_priority_generator=rules_priority_generator,
            ).execute()

    def _create_sandbox_nsg_inbound_ports_rules(self, deploy_app, vm_name, resource_group_name, vm_interfaces):
        """
        
        :param deploy_app: 
        :param vm_name: 
        :param resource_group_name: 
        :param vm_interfaces: 
        :return: 
        """
        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)
        nsg_name = self._reservation_info.get_network_security_group_name()

        with self._lock_manager.get_lock(nsg_name):
            rules_priority_generator = NSGRulesPriorityGenerator(nsg_name=nsg_name,
                                                                 resource_group_name=resource_group_name,
                                                                 include_existing_rules=True,
                                                                 nsg_actions=nsg_actions)

            # todo: check behaviour on the old 1st gen shell !!! when Public IP = False
            for interface in vm_interfaces:
                if interface.ip_configurations[0].public_ip_address is not None:
                    private_ip = interface.ip_configurations[0].private_ip_address

                    for inbound_port in deploy_app.inbound_ports:
                        commands.CreateAllowSandboxInboundPortRuleCommand(
                            rollback_manager=self._rollback_manager,
                            cancellation_manager=self._cancellation_manager,
                            nsg_actions=nsg_actions,
                            nsg_name=nsg_name,
                            vm_name=vm_name,
                            private_ip=private_ip,
                            inbound_port=inbound_port,
                            resource_group_name=resource_group_name,
                            rules_priority_generator=rules_priority_generator,
                        ).execute()

    def _create_vm_nsg_rules(self, deploy_app, vm_name, vm_nsg, resource_group_name, vm_interfaces):
        """

        :param deploy_app:
        :param vm_name:
        :param vm_nsg:
        :param resource_group_name:
        :param vm_interfaces:
        :return:
        """
        rules_priority_generator = NSGRulesPriorityGenerator(nsg_name=vm_nsg.name,
                                                             resource_group_name=resource_group_name)

        self._create_vm_nsg_inbound_ports_rules(deploy_app=deploy_app,
                                                vm_name=vm_name,
                                                vm_nsg=vm_nsg,
                                                resource_group_name=resource_group_name,
                                                rules_priority_generator=rules_priority_generator)

        self._create_vm_nsg_additional_mgmt_networks_rules(vm_name=vm_name,
                                                           vm_nsg=vm_nsg,
                                                           resource_group_name=resource_group_name,
                                                           rules_priority_generator=rules_priority_generator)

        self._create_vm_nsg_mgmt_vnet_rule(vm_nsg=vm_nsg,
                                           resource_group_name=resource_group_name,
                                           rules_priority_generator=rules_priority_generator)

        self._create_vm_nsg_sandbox_traffic_rules(deploy_app=deploy_app,
                                                  vm_nsg=vm_nsg,
                                                  resource_group_name=resource_group_name,
                                                  rules_priority_generator=rules_priority_generator)

        self._create_sandbox_nsg_inbound_ports_rules(deploy_app=deploy_app,
                                                     vm_name=vm_name,
                                                     resource_group_name=resource_group_name,
                                                     vm_interfaces=vm_interfaces)

    def _create_vm_interfaces(self, deploy_app, connect_subnets, network_security_group, resource_group_name, vm_name, tags):
        """

        :param deploy_app:
        :param connect_subnets:
        :param resource_group_name:
        :param vm_name:
        :return:
        """
        network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)
        network_interfaces = []

        sandbox_subnets = network_actions.get_sandbox_subnets(
            resource_group_name=resource_group_name,
            mgmt_resource_group_name=self._resource_config.management_group_name)

        if connect_subnets:
            for idx, connect_subnet in enumerate(connect_subnets):
                subnet = next((subnet for subnet in sandbox_subnets if subnet.name == connect_subnet.subnet_id),
                              None)

                # todo: should we raise some Exception if we are unable to find correct Subnet ?
                self._logger.warning(f"Unable to find subnet with subnet ID: {connect_subnet.subnet_id}")
                if subnet:
                    interface = commands.CreateVMNetworkCommand(
                        rollback_manager=self._rollback_manager,
                        cancellation_manager=self._cancellation_manager,
                        network_actions=network_actions,
                        interface_name=f"{vm_name}_{idx}",
                        public_ip_type=deploy_app.public_ip_type,
                        private_ip_allocation_method=self._resource_config.private_ip_allocation_method,
                        cs_ip_pool_manager=self._cs_ip_pool_manager,
                        resource_group_name=resource_group_name,
                        subnet=subnet,
                        network_security_group=network_security_group,
                        add_public_ip=all([deploy_app.add_public_ip, connect_subnet.is_public()]),
                        reservation_id=self._reservation_info.reservation_id,
                        enable_ip_forwarding=deploy_app.enable_ip_forwarding,
                        region=self._resource_config.region,
                        tags=tags,
                    ).execute()

                    network_interfaces.append(interface)

        else:
            for idx, subnet in enumerate(sandbox_subnets):
                interface = commands.CreateVMNetworkCommand(
                    rollback_manager=self._rollback_manager,
                    cancellation_manager=self._cancellation_manager,
                    network_actions=network_actions,
                    interface_name=f"{vm_name}_{idx}",
                    public_ip_type=deploy_app.public_ip_type,
                    private_ip_allocation_method=self._resource_config.private_ip_allocation_method,
                    cs_ip_pool_manager=self._cs_ip_pool_manager,
                    resource_group_name=resource_group_name,
                    subnet=subnet,
                    network_security_group=network_security_group,
                    add_public_ip=deploy_app.add_public_ip,
                    reservation_id=self._reservation_info.reservation_id,
                    enable_ip_forwarding=deploy_app.enable_ip_forwarding,
                    region=self._resource_config.region,
                    tags=tags,
                ).execute()

                network_interfaces.append(interface)

        if not network_interfaces:
            raise Exception(f"Unable to prepare network interfaces for the VM {vm_name}")

        network_interfaces[0].primary = True
        return network_interfaces

    def _find_vm_public_ip(self, vm_interfaces, resource_group_name):
        """

        :param vm_interfaces:
        :param resource_group_name:
        :return:
        """

        for vm_interface in vm_interfaces:
            if vm_interface.ip_configurations[0].public_ip_address is not None:
                network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)
                public_ip = network_actions.get_vm_network_public_ip(interface_name=vm_interface.name,
                                                                     resource_group_name=resource_group_name)
                return public_ip.ip_address

    def _find_vm_private_ip(self, vm_interfaces):
        """

        :param vm_interfaces:
        :return:
        """
        for vm_interface in vm_interfaces:
            if vm_interface.primary:
                return vm_interface.ip_configurations[0].private_ip_address

    def _prepare_deploy_app_result(self, deployed_vm, deploy_app, vm_interfaces, vm_name, resource_group_name):
        """

        :param deployed_vm:
        :param deploy_app:
        :param vm_interfaces:
        :param vm_name:
        :return:
        """
        public_ip = self._find_vm_public_ip(vm_interfaces=vm_interfaces, resource_group_name=resource_group_name)
        private_ip = self._find_vm_private_ip(vm_interfaces=vm_interfaces)

        deployed_app_attrs = [Attribute("Password", deploy_app.password),
                              Attribute("User", deploy_app.user),
                              Attribute("Public IP", public_ip)]

        vm_details_data = self._prepare_vm_details_data(deployed_vm=deployed_vm,
                                                        resource_group_name=resource_group_name)

        deploy_result = DeployAppResult(actionId=deploy_app.actionId,
                                        vmUuid=deployed_vm.vm_id,
                                        vmName=vm_name,
                                        deployedAppAddress=private_ip,
                                        deployedAppAttributes=deployed_app_attrs,
                                        vmDetailsData=vm_details_data)

        return deploy_result

    def _deploy(self, request_actions):
        """

        :param request_actions:
        :return:
        """
        deploy_app = request_actions.deploy_app

        resource_group_name = self._reservation_info.get_resource_group_name()
        storage_account_name = self._reservation_info.get_storage_account_name()

        name_postfix = name_generator.generate_short_unique_string()
        vm_name = name_generator.generate_name(name=deploy_app.app_name,
                                               postfix=name_postfix,
                                               max_length=64)

        tags = self._tags_manager.get_tags(vm_name=vm_name)

        computer_name = vm_name[:15]  # Windows OS username limit

        image_os = self._get_vm_image_os(deploy_app=deploy_app)

        self._validate_deploy_app_request(deploy_app=deploy_app,
                                          connect_subnets=request_actions.connect_subnets,
                                          image_os=image_os)
        with self._rollback_manager:
            vm_nsg = self._create_vm_nsg(resource_group_name=resource_group_name,
                                         vm_name=vm_name,
                                         tags=tags)

            vm_ifaces = self._create_vm_interfaces(deploy_app=deploy_app,
                                                   connect_subnets=request_actions.connect_subnets,
                                                   network_security_group=vm_nsg,
                                                   resource_group_name=resource_group_name,
                                                   vm_name=vm_name,
                                                   tags=tags)

            self._create_vm_nsg_rules(deploy_app=deploy_app,
                                      vm_name=vm_name,
                                      vm_nsg=vm_nsg,
                                      resource_group_name=resource_group_name,
                                      vm_interfaces=vm_ifaces)

            vm = self._prepare_vm(deploy_app=deploy_app,
                                  image_os=image_os,
                                  resource_group_name=resource_group_name,
                                  storage_account_name=storage_account_name,
                                  vm_network_interfaces=vm_ifaces,
                                  computer_name=computer_name,
                                  tags=tags)

            deployed_vm = self._create_vm(vm_name=vm_name,
                                          virtual_machine=vm,
                                          resource_group_name=resource_group_name)

            self._create_vm_script_extension(deploy_app=deploy_app,
                                             image_os_type=image_os,
                                             resource_group_name=resource_group_name,
                                             vm_name=vm_name,
                                             tags=tags)

            return self._prepare_deploy_app_result(deployed_vm=deployed_vm,
                                                   deploy_app=deploy_app,
                                                   vm_interfaces=vm_ifaces,
                                                   vm_name=vm_name,
                                                   resource_group_name=resource_group_name)

    def _create_vm_script_extension(self, deploy_app, image_os_type, resource_group_name, vm_name, tags):
        """

        :param deploy_app:
        :param image_os_type:
        :param resource_group_name:
        :param vm_name:
        :param tags:
        :return:
        """
        if deploy_app.extension_script_file:
            vm_extension_actions = VMExtensionActions(azure_client=self._azure_client, logger=self._logger)

            create_vm_extension_cmd = commands.CreateVMExtensionCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                vm_extension_actions=vm_extension_actions,
                script_file_path=deploy_app.extension_script_file,
                script_config=deploy_app.extension_script_configurations,
                timeout=deploy_app.extension_script_timeout,
                image_os_type=image_os_type,
                region=self._resource_config.region,
                vm_name=vm_name,
                resource_group_name=resource_group_name,
                tags=tags)
            try:
                create_vm_extension_cmd.execute()
            except AzureTaskTimeoutException:
                msg = f"App {deploy_app.app_name} was partially deployed - Custom script extension reached maximum " \
                      f"timeout of {deploy_app.extension_script_timeout/60} minute(s)"

                self._logger.warning(msg, exc_info=True)
                self._cs_reservation_output.write_error_message(message=msg)

    def _create_vm(self, vm_name, virtual_machine, resource_group_name):
        """Create and deploy Azure VM from the given parameters

        :param str vm_name:
        :param azure.mgmt.compute.models.VirtualMachine virtual_machine:
        :param str resource_group_name:
        """
        vm_actions = VMActions(azure_client=self._azure_client, logger=self._logger)

        return commands.CreateVMCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            vm_actions=vm_actions,
            vm_name=vm_name,
            virtual_machine=virtual_machine,
            resource_group_name=resource_group_name
        ).execute()

    def _prepare_hardware_profile(self, deploy_app):
        """

        :param deploy_app:
        :return:
        """
        vm_size = deploy_app.vm_size or self._resource_config.vm_size
        return compute_models.HardwareProfile(vm_size=vm_size)

    def _prepare_network_profile(self, vm_network_interfaces):
        """

        :param vm_network_interfaces:
        :return:
        """
        network_interfaces = [compute_models.NetworkInterfaceReference(id=interface.id, primary=False)
                              for interface in vm_network_interfaces]
        network_interfaces[0].primary = True
        return compute_models.NetworkProfile(network_interfaces=network_interfaces)

    def _prepare_os_disk(self, deploy_app):
        """

        :param deploy_app:
        :return:
        """
        if deploy_app.disk_type == "HDD":
            storage_account_disk_type = compute_models.StorageAccountTypes.standard_lrs
        else:
            storage_account_disk_type = compute_models.StorageAccountTypes.premium_lrs

        disk_size = int(deploy_app.disk_size) if deploy_app.disk_size else None

        return compute_models.OSDisk(create_option=compute_models.DiskCreateOptionTypes.from_image,
                                     disk_size_gb=disk_size,
                                     managed_disk=compute_models.ManagedDiskParameters(
                                         storage_account_type=storage_account_disk_type))

    def _prepare_os_profile(self, image_os, deploy_app, resource_group_name, storage_account_name, computer_name):
        """

        :param image_os:
        :param deploy_app:
        :param resource_group_name:
        :param storage_account_name:
        :param computer_name:
        :return:
        """
        vm_creds_actions = VMCredentialsActions(azure_client=self._azure_client, logger=self._logger)
        linux_configuration = None

        if image_os == compute_models.OperatingSystemTypes.linux:
            username, password = vm_creds_actions.prepare_linux_credentials(username=deploy_app.user,
                                                                            password=deploy_app.password)
            if not password:
                ssh_key_path = vm_creds_actions.prepare_ssh_public_key_path(username=username)
                ssh_public_key = vm_creds_actions.get_ssh_public_key(resource_group_name=resource_group_name,
                                                                     storage_account_name=storage_account_name)

                ssh_public_key = compute_models.SshPublicKey(path=ssh_key_path, key_data=ssh_public_key)
                ssh_config = compute_models.SshConfiguration(public_keys=[ssh_public_key])

                linux_configuration = compute_models.LinuxConfiguration(disable_password_authentication=True,
                                                                        ssh=ssh_config)
        else:
            username, password = vm_creds_actions.prepare_windows_credentials(username=deploy_app.user,
                                                                              password=deploy_app.password)

        return compute_models.OSProfile(admin_username=username,
                                        admin_password=password,
                                        linux_configuration=linux_configuration,
                                        computer_name=computer_name)

    def _prepare_vm(self, deploy_app, image_os, resource_group_name, storage_account_name, vm_network_interfaces,
                    computer_name, tags):
        """

        :param deploy_app:
        :param image_os:
        :param resource_group_name:
        :param storage_account_name:
        :param vm_network_interfaces:
        :param computer_name:
        :param tags:
        :return:
        """
        os_profile = self._prepare_os_profile(image_os=image_os,
                                              deploy_app=deploy_app,
                                              resource_group_name=resource_group_name,
                                              storage_account_name=storage_account_name,
                                              computer_name=computer_name)

        hardware_profile = self._prepare_hardware_profile(deploy_app=deploy_app)
        network_profile = self._prepare_network_profile(vm_network_interfaces=vm_network_interfaces)
        os_disk = self._prepare_os_disk(deploy_app=deploy_app)
        storage_profile = self._prepare_storage_profile(deploy_app=deploy_app, os_disk=os_disk)

        return compute_models.VirtualMachine(location=self._resource_config.region,
                                             tags=tags,
                                             os_profile=os_profile,
                                             hardware_profile=hardware_profile,
                                             network_profile=network_profile,
                                             storage_profile=storage_profile,
                                             diagnostics_profile=compute_models.DiagnosticsProfile(
                                                 boot_diagnostics=compute_models.BootDiagnostics(enabled=False)))
