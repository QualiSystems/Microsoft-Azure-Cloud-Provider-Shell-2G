from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.request_actions import DeployVMRequestActions, PrepareSandboxInfraRequestActions, \
    GetVMDetailsRequestActions, CleanupSandboxInfraRequestActions, DeployedVMRequestActions
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext

from package.cloudshell.cp.azure import constants
from package.cloudshell.cp.azure.azure_client import AzureAPIClient
from package.cloudshell.cp.azure.flows.autoload import AzureAutoloadFlow
from package.cloudshell.cp.azure.flows.delete_instance import AzureDeleteInstanceFlow
from package.cloudshell.cp.azure.flows.prepare_sandbox_infra import AzurePrepareSandboxInfraFlow
from package.cloudshell.cp.azure.reservation_info import AzureReservationInfo
from package.cloudshell.cp.azure.resource_config import AzureResourceConfig
from package.cloudshell.cp.azure.models.deploy_app import AzureVMFromMarketplaceDeployApp, AzureVMFromCustomImageDeployApp
from package.cloudshell.cp.azure.models.deployed_app import AzureVMFromMarketplaceDeployedApp, \
    AzureVMFromCustomImageDeployedApp
from package.cloudshell.cp.azure.flows.access_key import AzureGetAccessKeyFlow
from package.cloudshell.cp.azure.flows.application_ports import AzureGetApplicationPortsFlow
from package.cloudshell.cp.azure.flows.available_ip import AzureGetAvailablePrivateIPFlow
from package.cloudshell.cp.azure.flows.deploy_vm.deploy_custom_vm import AzureDeployCustomVMFlow
from package.cloudshell.cp.azure.flows.deploy_vm.deploy_marketplace_vm import AzureDeployMarketplaceVMFlow
from package.cloudshell.cp.azure.utils.cs_ip_pool_manager import CSIPPoolManager
from package.cloudshell.cp.azure.flows.power_mgmt import AzurePowerManagementFlow
from package.cloudshell.cp.azure.flows.vm_details import AzureGetVMDetailsFlow
from package.cloudshell.cp.azure.flows.refresh_ip import AzureRefreshIPFlow
from package.cloudshell.cp.azure.flows.cleanup import AzureCleanupSandboxInfraFlow


class AzureDriver(ResourceDriverInterface):
    SHELL_NAME = constants.SHELL_NAME

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        pass

    def initialize(self, context):
        """Called every time a new instance of the driver is created

        This method can be left unimplemented but this is a good place to load and cache the driver configuration,
        initiate sessions etc. Whatever you choose, do not remove it.
        :param InitCommandContext context: the context the command runs on
        """
        pass

    def get_inventory(self, context):
        """Called when the cloud provider resource is created in the inventory.

        Method validates the values of the cloud provider attributes, entered by the user as part of the cloud provider
        resource creation. In addition, this would be the place to assign values programmatically to optional attributes
        that were not given a value by the user. If one of the validations failed, the method should raise an exception
        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Autoload command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            autoload_flow = AzureAutoloadFlow(resource_config=resource_config,
                                              azure_client=azure_client,
                                              logger=logger)

            return autoload_flow.discover()

    def PrepareSandboxInfra(self, context, request, cancellation_context):
        """Called in the beginning of the orchestration flow (preparation stage), even before Deploy is called.

        Prepares all of the required infrastructure needed for a sandbox operating with L3 connectivity.
        For example, creating networking infrastructure like VPC, subnets or routing tables in AWS, storage entities
        such as S3 buckets, or keyPair objects for authentication. In general, any other entities needed on the
        sandbox level should be created here.

        Note:
        PrepareSandboxInfra can be called multiple times in a sandbox.
        Setup can be called multiple times in the sandbox, and every time setup is called, the PrepareSandboxInfra
        method will be called again. Implementation should support this use case and take under consideration that
        the cloud resource might already exist. It's recommended to follow the "get or create" pattern when
        implementing this method.

        When an error is raised or method returns action result with success false
        Cloudshell will fail sandbox creation, so bear that in mind when doing so.
        :param ResourceCommandContext context:
        :param str request:
        :param CancellationContext cancellation_context:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Prepare Sandbox Infra command...")
            logger.debug(f"Request: {request}")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            request_actions = PrepareSandboxInfraRequestActions.from_request(request)
            reservation_info = AzureReservationInfo.from_resource_context(context)
            cancellation_manager = CancellationContextManager(cancellation_context)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            prepare_sandbox_flow = AzurePrepareSandboxInfraFlow(resource_config=resource_config,
                                                                azure_client=azure_client,
                                                                reservation_info=reservation_info,
                                                                cancellation_manager=cancellation_manager,
                                                                logger=logger)

            return prepare_sandbox_flow.prepare(request_actions=request_actions)

    def Deploy(self, context, request, cancellation_context=None):
        """Called when reserving a sandbox during setup, a call for each app in the sandbox.

        Method creates the compute resource in the cloud provider - VM instance or container.
        If App deployment fails, return a "success false" action result.
        :param ResourceCommandContext context:
        :param str request: A JSON string with the list of requested deployment actions
        :param CancellationContext cancellation_context:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Deploy command...")
            logger.debug(f"Request: {request}")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            cancellation_manager = CancellationContextManager(cancellation_context)
            reservation_info = AzureReservationInfo.from_resource_context(context)
            cs_ip_pool_manager = CSIPPoolManager(cs_api=api, logger=logger)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            for deploy_app_cls in (AzureVMFromMarketplaceDeployApp, AzureVMFromCustomImageDeployApp):
                DeployVMRequestActions.register_deployment_path(deploy_app_cls)

            request_actions = DeployVMRequestActions.from_request(request=request, cs_api=api)

            if isinstance(request_actions.deploy_app, AzureVMFromMarketplaceDeployApp):
                deploy_flow_class = AzureDeployMarketplaceVMFlow
            else:
                deploy_flow_class = AzureDeployCustomVMFlow

            deploy_flow = deploy_flow_class(resource_config=resource_config,
                                            azure_client=azure_client,
                                            cs_api=api,
                                            reservation_info=reservation_info,
                                            cancellation_manager=cancellation_manager,
                                            cs_ip_pool_manager=cs_ip_pool_manager,
                                            logger=logger)

            return deploy_flow.deploy(request_actions=request_actions)

    def PowerOn(self, context, ports):
        """Called when reserving a sandbox during setup, a call for each app in the sandbox can also be run manually by

        the sandbox end-user from the deployed App's commands pane. Method spins up the VM If the operation fails,
        method should raise an exception.
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Power On command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            reservation_info = AzureReservationInfo.from_remote_resource_context(context)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMRequestActions.from_remote_resource(resource)

            power_mgmt_flow = AzurePowerManagementFlow(resource_config=resource_config,
                                                       azure_client=azure_client,
                                                       reservation_info=reservation_info,
                                                       logger=logger)

            return power_mgmt_flow.power_on(deployed_app=deployed_vm_actions.deployed_app)

    def PowerOff(self, context, ports):
        """Called during sandbox's teardown can also be run manually by the sandbox end-user from the deployed

        App's commands pane. Method shuts down (or powers off) the VM instance. If the operation fails,
        method should raise an exception.
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Power Off command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            reservation_info = AzureReservationInfo.from_remote_resource_context(context)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMRequestActions.from_remote_resource(resource)

            power_mgmt_flow = AzurePowerManagementFlow(resource_config=resource_config,
                                                       azure_client=azure_client,
                                                       reservation_info=reservation_info,
                                                       logger=logger)

            return power_mgmt_flow.power_off(deployed_app=deployed_vm_actions.deployed_app)

    def PowerCycle(self, context, ports, delay):
        pass

    def remote_refresh_ip(self, context, ports, cancellation_context):
        """Called when reserving a sandbox during setup, a call for each app in the sandbox can also be run manually

        by the sandbox end-user from the deployed App's commands pane. Method retrieves the VM's updated IP address
        from the cloud provider and sets it on the deployed App resource. Both private and public IPs are retrieved,
        as appropriate. If the operation fails, method should raise an exception.
        :param ResourceRemoteCommandContext context:
        :param ports:
        :param CancellationContext cancellation_context:
        :return:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Remote Refresh IP command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            reservation_info = AzureReservationInfo.from_remote_resource_context(context)
            cancellation_manager = CancellationContextManager(cancellation_context)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMRequestActions.from_remote_resource(resource)

            refresh_ip_flow = AzureRefreshIPFlow(resource_config=resource_config,
                                                 azure_client=azure_client,
                                                 cs_api=api,
                                                 reservation_info=reservation_info,
                                                 cancellation_manager=cancellation_manager,
                                                 logger=logger)

            return refresh_ip_flow.refresh_ip(deployed_app=deployed_vm_actions.deployed_app)

    def GetVmDetails(self, context, requests, cancellation_context):
        """Called when reserving a sandbox during setup, a call for each app in the sandbox can also be run manually

        by the sandbox end-user from the deployed App's VM Details pane. Method queries cloud provider for instance
        operating system, specifications and networking information and returns that as a json serialized driver
        response containing a list of VmDetailsData. If the operation fails, method should raise an exception.
        :param ResourceCommandContext context:
        :param str requests:
        :param CancellationContext cancellation_context:
        :return:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get VM Details command...")
            logger.debug(f"Requests: {requests}")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            for deploy_app_cls in (AzureVMFromMarketplaceDeployedApp, AzureVMFromCustomImageDeployedApp):
                GetVMDetailsRequestActions.register_deployment_path(deploy_app_cls)

            request_actions = GetVMDetailsRequestActions.from_request(requests)
            cancellation_manager = CancellationContextManager(cancellation_context)
            reservation_info = AzureReservationInfo.from_resource_context(context)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            vm_details_flow = AzureGetVMDetailsFlow(resource_config=resource_config,
                                                    azure_client=azure_client,
                                                    reservation_info=reservation_info,
                                                    cancellation_manager=cancellation_manager,
                                                    logger=logger)

            return vm_details_flow.get_vm_details(request_actions=request_actions)

    def DeleteInstance(self, context, ports):
        """Called during sandbox's teardown or when removing a deployed App from the sandbox

        Method deletes the VM from the cloud provider. If the operation fails, method should raise an exception.
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Delete Instance command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            reservation_info = AzureReservationInfo.from_remote_resource_context(context)
            cs_ip_pool_manager = CSIPPoolManager(cs_api=api, logger=logger)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMRequestActions.from_remote_resource(resource)

            delete_flow = AzureDeleteInstanceFlow(resource_config=resource_config,
                                                  azure_client=azure_client,
                                                  reservation_info=reservation_info,
                                                  cs_ip_pool_manager=cs_ip_pool_manager,
                                                  logger=logger)

            delete_flow.delete_instance(deployed_app=deployed_vm_actions.deployed_app)

    def CleanupSandboxInfra(self, context, request):
        """Called at the end of reservation teardown

        Cleans all entities (beside VMs) created for sandbox, usually entities created in the
        PrepareSandboxInfra command. Basically all created entities for the sandbox will be deleted by
        calling the methods: DeleteInstance, CleanupSandboxInfra.
        If a failure occurs, return a "success false" action result.
        :param ResourceCommandContext context:
        :param str request:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Cleanup Sandbox Infra command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            request_actions = CleanupSandboxInfraRequestActions.from_request(request)
            reservation_info = AzureReservationInfo.from_resource_context(context)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            cleanup_flow = AzureCleanupSandboxInfraFlow(resource_config=resource_config,
                                                        azure_client=azure_client,
                                                        reservation_info=reservation_info,
                                                        logger=logger)

            return cleanup_flow.cleanup(request_actions=request_actions)

    def CreateRouteTables(self, context, request):
        """

        :param context:
        :param request:
        :return:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Create Route Tables command...")
            logger.debug(f"Request: {request}")
            # return self.azure_shell.create_route_tables(context, request)

    def SetAppSecurityGroups(self, context, request):
        """Called via cloudshell API call

        Programmatically set which ports will be open on each of the apps in the sandbox, and from
        where they can be accessed. This is an optional command that may be implemented.
        Normally, all outbound traffic from a deployed app should be allowed.
        For inbound traffic, we may use this method to specify the allowed traffic.
        An app may have several networking interfaces in the sandbox. For each such interface, this command allows
        to set which ports may be opened, the protocol and the source CIDR. If operation fails,
        return a "success false" action result.
        :param ResourceCommandContext context:
        :param str request:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Set App Security Groups command...")
            logger.debug(f"Request: {request}")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            # todo: need request for this command !!!

            # request_actions = SetAppSecurityGroupsRequestActions.from_request(request)
            # reservation_info = AzureReservationInfo.from_context(context.reservation)
            #
            # azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
            #                               azure_tenant_id=resource_config.azure_tenant_id,
            #                               azure_application_id=resource_config.azure_application_id,
            #                               azure_application_key=resource_config.azure_application_key,
            #                               logger=logger)
            #
            # app_security_groups_flow = AzureAppSecurityGroupsFlow(resource_config=resource_config,
            #                                             azure_client=azure_client,
            #                                             reservation_info=reservation_info,
            #                                             logger=logger)
            #
            # return app_security_groups_flow.set_app_security_groups(request_actions=request_actions)

    def cleanup(self):
        """Destroy the driver session, this function is called every time a driver instance is destroyed

        This is a good place to close any open sessions, finish writing to log files, etc.
        """
        pass

    def GetApplicationPorts(self, context, ports):
        """

        :param context:
        :param ports:
        :return:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get Application Ports command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            reservation_info = AzureReservationInfo.from_remote_resource_context(context)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMRequestActions.from_remote_resource(resource)

            application_ports_flow = AzureGetApplicationPortsFlow(resource_config=resource_config,
                                                                  azure_client=azure_client,
                                                                  reservation_info=reservation_info,
                                                                  logger=logger)

            return application_ports_flow.get_application_ports(deployed_app=deployed_vm_actions.deployed_app)

    def GetAccessKey(self, context, ports):
        """

        :param context:
        :param ports:
        :return:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get Access Key command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            reservation_info = AzureReservationInfo.from_remote_resource_context(context)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            access_key_flow = AzureGetAccessKeyFlow(resource_config=resource_config,
                                                    azure_client=azure_client,
                                                    reservation_info=reservation_info,
                                                    logger=logger)

            return access_key_flow.get_access_key()

    def GetAvailablePrivateIP(self, context, subnet_cidr, owner):
        """

        :param context:
        :param subnet_cidr:
        :param owner:
        :return:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get Available Private IP command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(shell_name=self.SHELL_NAME,
                                                               context=context,
                                                               api=api)

            reservation_info = AzureReservationInfo.from_remote_resource_context(context)
            cs_ip_pool_manager = CSIPPoolManager(cs_api=api, logger=logger)

            azure_client = AzureAPIClient(azure_subscription_id=resource_config.azure_subscription_id,
                                          azure_tenant_id=resource_config.azure_tenant_id,
                                          azure_application_id=resource_config.azure_application_id,
                                          azure_application_key=resource_config.azure_application_key,
                                          logger=logger)

            get_available_ip_flow = AzureGetAvailablePrivateIPFlow(resource_config=resource_config,
                                                                   azure_client=azure_client,
                                                                   cs_ip_pool_manager=cs_ip_pool_manager,
                                                                   reservation_info=reservation_info,
                                                                   logger=logger)

            return get_available_ip_flow.get_available_private_ip(subnet_cidr=subnet_cidr, owner=owner)