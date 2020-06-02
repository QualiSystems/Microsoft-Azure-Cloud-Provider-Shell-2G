import re

from azure.mgmt.compute.models import StorageAccountTypes
from cloudshell.cp.core.request_actions.models import VmDetailsProperty, VmDetailsData, VmDetailsNetworkInterface

from package.cloudshell.cp.azure.actions.network import NetworkActions
from package.cloudshell.cp.azure.utils.azure_name_parser import get_name_from_resource_id


class VMDetailsActions(NetworkActions):
    @staticmethod
    def _parse_image_name(resource_id):
        """Get image name from the Azure image reference id

        :param str resource_id: Azure image reference id
        :return: Azure image name
        :rtype: str
        """
        match_images = re.match(r".*images/(?P<image_name>[^/]*).*", resource_id, flags=re.IGNORECASE)
        return match_images.group("image_name") if match_images else ""

    @staticmethod
    def _parse_resource_group_name(resource_id):
        """Get resource group name from the Azure resource id

        :param str resource_id: Azure resource Id
        :return: Azure resource group name
        :rtype: str
        """
        match_groups = re.match(r".*resourcegroups/(?P<group_name>[^/]*)/.*", resource_id, flags=re.IGNORECASE)
        return match_groups.group("group_name") if match_groups else ""

    @staticmethod
    def _prepare_common_vm_instance_data(virtual_machine):
        """

        :param virtual_machine:
        :return:
        """
        return [
            VmDetailsProperty(key="VM Size", value=virtual_machine.hardware_profile.vm_size),
            VmDetailsProperty(key="Operating System", value=virtual_machine.storage_profile.os_disk.os_type.name),
            VmDetailsProperty(key="Disk Type", value="HDD" if virtual_machine.storage_profile.os_disk.managed_disk
                              .storage_account_type == StorageAccountTypes.standard_lrs else "SSD")]

    def _prepare_vm_network_data(self, virtual_machine, resource_group_name):
        """

        :param virtual_machine:
        :param resource_group_name:
        :return:
        """
        vm_network_interfaces = []
        for network_interface in virtual_machine.network_profile.network_interfaces:
            interface_name = get_name_from_resource_id(network_interface.id)
            interface = self.get_vm_network(interface_name=interface_name, resource_group_name=resource_group_name)

            ip_configuration = interface.ip_configurations[0]
            private_ip_addr = ip_configuration.private_ip_address

            network_data = [
                VmDetailsProperty(key="IP", value=ip_configuration.private_ip_address),
                VmDetailsProperty(key="MAC Address", value=interface.mac_address)]

            subnet_name = ip_configuration.subnet.id.split('/')[-1]

            if ip_configuration.public_ip_address:
                public_ip = self.get_vm_network_public_ip(interface_name=interface_name,
                                                          resource_group_name=resource_group_name)
                network_data.extend([
                    VmDetailsProperty(key="Public IP", value=public_ip.ip_address),
                    VmDetailsProperty(key="Public IP Type", value=public_ip.public_ip_allocation_method)])

                public_ip_addr = public_ip.ip_address
            else:
                public_ip_addr = ""

            vm_network_interface = VmDetailsNetworkInterface(interfaceId=interface.resource_guid,
                                                             networkId=subnet_name,
                                                             isPrimary=interface.primary,
                                                             networkData=network_data,
                                                             privateIpAddress=private_ip_addr,
                                                             publicIpAddress=public_ip_addr)

            vm_network_interfaces.append(vm_network_interface)

        return vm_network_interfaces

    def _prepare_marketplace_vm_instance_data(self, virtual_machine):
        """

        :param virtual_machine:
        :return:
        """
        return [
            VmDetailsProperty(key="Image Publisher", value=virtual_machine.storage_profile.image_reference.publisher),
            VmDetailsProperty(key="Image Offer", value=virtual_machine.storage_profile.image_reference.offer),
            VmDetailsProperty(key="Image SKU", value=virtual_machine.storage_profile.image_reference.sku),
        ] + self._prepare_common_vm_instance_data(virtual_machine=virtual_machine)

    def _prepare_custom_vm_instance_data(self, virtual_machine):
        """

        :param virtual_machine:
        :return:
        """
        image_resource_id = virtual_machine.storage_profile.image_reference.id
        image_name = self._parse_image_name(resource_id=image_resource_id)
        resource_group = self._parse_resource_group_name(resource_id=image_resource_id)

        return [
            VmDetailsProperty(key="Image", value=image_name),
            VmDetailsProperty(key="Image Resource Group", value=resource_group)
        ] + self._prepare_common_vm_instance_data(virtual_machine=virtual_machine)

    def _prepare_vm_details(self, virtual_machine, resource_group_name, prepare_vm_instance_data_function):
        """

        :param virtual_machine:
        :param resource_group_name:
        :param prepare_vm_instance_data_function:
        :return:
        """
        try:
            return VmDetailsData(
                appName=virtual_machine.name,
                vmInstanceData=prepare_vm_instance_data_function(virtual_machine=virtual_machine),
                vmNetworkData=self._prepare_vm_network_data(virtual_machine=virtual_machine,
                                                            resource_group_name=resource_group_name))
        except Exception as e:
            self._logger.exception(f"Error getting VM details for {virtual_machine.name}")
            return VmDetailsData(appName=virtual_machine.name, errorMessage=str(e))

    def prepare_marketplace_vm_details(self, virtual_machine, resource_group_name):
        """

        :param virtual_machine:
        :param resource_group_name:
        :return:
        """
        return self._prepare_vm_details(virtual_machine=virtual_machine,
                                        resource_group_name=resource_group_name,
                                        prepare_vm_instance_data_function=self._prepare_marketplace_vm_instance_data)

    def prepare_custom_vm_details(self, virtual_machine, resource_group_name):
        """

        :param virtual_machine:
        :param resource_group_name:
        :return:
        """
        return self._prepare_vm_details(virtual_machine=virtual_machine,
                                        resource_group_name=resource_group_name,
                                        prepare_vm_instance_data_function=self._prepare_custom_vm_instance_data)
