from functools import partial
from http import HTTPStatus

from package.cloudshell.cp.azure.actions.vm import VMActions
from package.cloudshell.cp.azure.actions.network import NetworkActions
from package.cloudshell.cp.azure.actions.network_security_group import NetworkSecurityGroupActions
from package.cloudshell.cp.azure.utils.azure_name_parser import get_name_from_resource_id
from package.cloudshell.cp.azure.actions.storage_account import StorageAccountActions

from msrestazure.azure_exceptions import CloudError


class AzureDeleteInstanceFlow:
    def __init__(self, resource_config, azure_client, reservation_info, cs_ip_pool_manager, logger):
        """

        :param resource_config:
        :param azure_client:
        :param reservation_info:
        :param cs_ip_pool_manager:
        :param logging.Logger logger:
        """
        self._resource_config = resource_config
        self._azure_client = azure_client
        self._reservation_info = reservation_info
        self._cs_ip_pool_manager = cs_ip_pool_manager
        self._logger = logger

    def _get_public_ip_names(self, network_interfaces):
        """

        :param network_interfaces:
        :return:
        """
        public_ip_names = []
        for interface in network_interfaces:
            public_ip = interface.ip_configurations[0].public_ip_address

            if public_ip is not None:
                public_ip_name = get_name_from_resource_id(public_ip.id)
                public_ip_names.append(public_ip_name)

        return public_ip_names

    def _get_private_ip_names(self, network_interfaces, network_actions):
        """

        :param network_interfaces:
        :return:
        """
        private_ip_names = []
        for interface in network_interfaces:
            ip_config = interface.ip_configurations[0]

            if network_actions.is_static_ip_allocation_type(ip_type=ip_config.private_ip_allocation_method):
                private_ip_names.append(ip_config.private_ip_address)

        return private_ip_names

    def _delete_vm_disk(self, vm, resource_group_name):
        """Delete the VM data disk. Will delete VHD or Managed Disk of the VM.

        :param azure.mgmt.compute.models.VirtualMachine vm:
        :param str resource_group_name:
        :return:
        """
        storage_actions = StorageAccountActions(azure_client=self._azure_client, logger=self._logger)

        if vm.storage_profile.os_disk.vhd:
            storage_actions.delete_vhd_disk(vhd_url=vm.storage_profile.os_disk.vhd.url,
                                            resource_group_name=resource_group_name)

        elif vm.storage_profile.os_disk.managed_disk:
            storage_actions.delete_managed_disk(disk_name=vm.storage_profile.os_disk.name,
                                                resource_group_name=resource_group_name)
        else:
            raise Exception(f"Unable to delete data disk under VM {vm.name}. Unsupported OS data disk type")

    def delete_instance(self, deployed_app):
        """

        :param deployed_app:
        :return:
        """
        resource_group_name = self._reservation_info.get_resource_group_name()
        # nsg_name = self._reservation_info.get_network_security_group_name()

        vm_actions = VMActions(azure_client=self._azure_client, logger=self._logger)
        network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)
        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)

        vm = vm_actions.get_vm(vm_name=deployed_app.name, resource_group_name=resource_group_name)

        network_interface_names = [get_name_from_resource_id(interface.id)
                                   for interface in vm.network_profile.network_interfaces]

        network_interfaces = [network_actions.get_vm_network(interface_name=interface_name,
                                                             resource_group_name=resource_group_name)
                              for interface_name in network_interface_names]

        public_ip_names = self._get_public_ip_names(network_interfaces=network_interfaces)

        private_ips = self._get_private_ip_names(network_interfaces=network_interfaces,
                                                 network_actions=network_actions)

        # todo: add some manager class that will continue deleting resources in case of some exceptions?!!
        delete_commands = [partial(vm_actions.delete_vm,
                                   vm_name=deployed_app.name,
                                   resource_group_name=resource_group_name)]

        for interface_name in network_interface_names:
            delete_commands.append(partial(network_actions.delete_vm_network,
                                           interface_name=interface_name,
                                           resource_group_name=resource_group_name))

        for public_ip_name in public_ip_names:
            delete_commands.append(partial(network_actions.delete_public_ip,
                                           public_ip_name=public_ip_name,
                                           resource_group_name=resource_group_name))

        delete_commands.append(partial(self._delete_vm_disk,
                                       vm=vm,
                                       resource_group_name=resource_group_name))

        delete_commands.append(partial(nsg_actions.delete_vm_network_security_group,
                                       vm_name=vm.name,
                                       resource_group_name=resource_group_name))

        for delete_command in delete_commands:
            try:
                delete_command()
            except CloudError as e:
                if e.status_code == HTTPStatus.NOT_FOUND:
                    self._logger.warning("Unable to find resource on Azure for deleting:", exc_info=True)
                    continue
                raise

        # 6) delete NSG Rules from the sandbox NSG
        # sandbox_nsg = nsg_actions.get_network_security_group(nsg_name=nsg_name,
        #                                                      resource_group_name=resource_group_name)
        # todo: we can have here strange rules created during deploy inbound ports - need to check do we
        #  really need these rules

        if private_ips:
            try:
                self._cs_ip_pool_manager.release_ips(reservation_id=self._reservation_info.reservation_id,
                                                     ips=private_ips)
            except Exception:
                self._logger.warning(f"Unable to release private IPs {private_ips} from the CloudShell:", exc_info=True)

