from azure.mgmt.compute.models import OperatingSystemTypes
from msrestazure.azure_exceptions import CloudError
import ipaddress

from package.cloudshell.cp.azure.actions.network import NetworkActions


class ValidationActions(NetworkActions):
    MAX_VM_DISK_SIZE_GB = 1023

    def register_azure_providers(self):
        """

        :return:
        """
        self._logger.info(f"Registering subscription with Azure providers...")
        for provider in ("Microsoft.Authorization",
                         "Microsoft.Storage",
                         "Microsoft.Network",
                         "Microsoft.Compute"):

            self._logger.info(f"Registering subscription with a {provider} resource provider")
            self._azure_client.register_provider(provider)

    def validate_azure_region(self, region):
        """

        :param str region:
        :return:
        """
        self._logger.info(f"Validating Azure region...")

        if not region:
            raise Exception("Region attribute can not be empty")

        available_regions = [available_region.name for available_region in self._azure_client.get_available_regions()]
        self._logger.debug(f"Available Azure regions: {available_regions}")

        if region not in available_regions:
            raise Exception(f'Region "{region}" is not a valid Azure Geo-location')

    def validate_azure_mgmt_resource_group(self, mgmt_resource_group_name, region):
        """

        :param str mgmt_resource_group_name:
        :param str region:
        :return:
        """
        self._logger.info(f"Validating MGMT resource group {mgmt_resource_group_name}...")

        try:
            resource_group = self._azure_client.get_resource_group(mgmt_resource_group_name)
        except CloudError:
            error_msg = f"Failed to find management resource group '{mgmt_resource_group_name}'"
            self._logger.exception(error_msg)
            raise Exception(error_msg)

        if region != resource_group.location:
            raise Exception(f"Management group '{mgmt_resource_group_name}' is not under the '{region}' region")

    def validate_azure_mgmt_network(self, mgmt_resource_group_name):
        """

        :param str mgmt_resource_group_name:
        :return:
        """
        self._logger.info("Verifying that MGMT vNet exists under the MGMT resource group...")
        self.get_mgmt_virtual_network(resource_group_name=mgmt_resource_group_name)

    def validate_azure_sandbox_network(self, mgmt_resource_group_name):
        """

        :param str mgmt_resource_group_name:
        :return:
        """
        self._logger.info("Verifying that sandbox vNet exists under the MGMT resource group...")
        self.get_sandbox_virtual_network(resource_group_name=mgmt_resource_group_name)

    def validate_azure_vm_size(self, vm_size, region):
        """

        :param str vm_size:
        :param str region:
        :return:
        """
        if vm_size:
            available_vm_sizes = [vm_size.name for vm_size in
                                  self._azure_client.get_virtual_machine_sizes_by_region(region)]

            self._logger.debug(f"Available VM sizes: {available_vm_sizes}")

            if vm_size not in available_vm_sizes:
                raise Exception(f"VM Size {vm_size} is not valid")

    def _is_valid_cidr(self, cidr):
        """Validate that CIDR have a correct format. Example "10.10.10.10/24"

        :param str cidr:
        :rtype: bool
        """
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            self._logger.exception(f"CIDR {cidr} is in invalid format")
            return False

        return "/" in cidr

    def validate_azure_additional_networks(self, mgmt_networks):
        """

        :param list[str] mgmt_networks:
        :return:
        """
        for cidr in mgmt_networks:
            if not self._is_valid_cidr(cidr):
                raise Exception(f"CIDR {cidr} under the 'Additional Mgmt Networks' attribute "
                                f"is not in the valid format")

    def validate_deploy_app_add_public_ip(self, deploy_app, connect_subnets):
        """

        :param deploy_app:
        :param connect_subnets:
        :return:
        """
        all_subnets_are_private = connect_subnets and all([subnet.is_private() for subnet in connect_subnets])

        if all_subnets_are_private and deploy_app.add_public_ip:
            raise Exception("Cannot deploy App with Public IP when connected only to private subnets")

    def validate_deploy_app_inbound_ports(self, deploy_app):
        """

        :param deploy_app:
        :return:
        """
        if deploy_app.inbound_ports and not deploy_app.add_public_ip:
            raise Exception('"Inbound Ports" attribute must be empty when "Add Public IP" is False')

    def validate_deploy_app_script_extension(self, deploy_app, image_os):
        """

        :param deploy_app:
        :param image_os:
        :return:
        """
        if not deploy_app.extension_script_file:
            return

        if image_os == OperatingSystemTypes.windows:
            if not deploy_app.extension_script_file.endswith("ps1"):
                raise Exception("Invalid format for the PowerShell script. It must have a 'ps1' extension")
        else:
            if not deploy_app.extension_script_configurations:
                raise Exception("Linux Custom Script must have a command to execute in "
                                "'Extension Script Configurations' attribute")

    def validate_deploy_app_disk_size(self, deploy_app):
        """

        :param deploy_app:
        :return:
        """
        if not deploy_app.disk_size:
            return

        try:
            disk_size_num = int(deploy_app.disk_size)
        except ValueError:
            error_msg = f"Invalid Virtual Machine Disk size '{deploy_app.disk_size}'"
            self._logger.exception(error_msg)
            raise Exception(error_msg)

        if disk_size_num > self.MAX_VM_DISK_SIZE_GB:
            raise Exception(f"Virtual Machine Disk size cannot be larger than {self.MAX_VM_DISK_SIZE_GB} GB")

    def validate_vm_size(self, deploy_app_vm_size, cloud_provider_vm_size):
        """

        :param str deploy_app_vm_size:
        :param str cloud_provider_vm_size:
        :return:
        """
        return any([deploy_app_vm_size, cloud_provider_vm_size])
