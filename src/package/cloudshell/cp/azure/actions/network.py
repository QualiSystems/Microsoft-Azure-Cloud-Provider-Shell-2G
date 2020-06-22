from functools import partial

from msrestazure.azure_exceptions import CloudError
from azure.mgmt.network import models


class NetworkActions:
    NETWORK_TYPE_TAG_NAME = "network_type"
    SANDBOX_NETWORK_TAG_VALUE = "sandbox"
    MGMT_NETWORK_TAG_VALUE = "mgmt"
    EXISTING_SUBNET_ERROR = "NetcfgInvalidSubnet"
    PUBLIC_IP_NAME_TPL = "{interface_name}_PublicIP"
    CLOUDSHELL_STATIC_IP_ALLOCATION_TYPE = "static"
    CLOUDSHELL_DYNAMIC_IP_ALLOCATION_TYPE = "dynamic"
    AZURE_PRIVATE_IP_ALLOCATION_METHOD = "Azure Allocation"
    CLOUDSHELL_PRIVATE_IP_ALLOCATION_METHOD = "Cloudshell Allocation"

    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def _get_virtual_network_by_tag(self, virtual_networks, tag_key, tag_value):
        """

        :param list[VirtualNetwork] virtual_networks:
        :param str tag_key:
        :param str tag_value:
        :return:
        :rtype: VirtualNetwork
        """
        self._logger.info(f"Getting Virtual Network by tag {tag_key}={tag_value}")
        for network in virtual_networks:
            if network.tags.get(tag_key) == tag_value:
                return network

        raise Exception(f"Unable to find virtual network with tag {tag_key}={tag_value}")

    @staticmethod
    def prepare_sandbox_subnet_name(resource_group_name, cidr):
        """

        :param resource_group_name:
        :param cidr:
        :return:
        """
        return f"{resource_group_name}_{cidr}".replace(' ', '').replace('/', '-')

    def get_mgmt_virtual_network(self, resource_group_name):
        """

        :param str resource_group_name:
        :return:
        """
        self._logger.info(f"Getting MGMT subnet by tag "
                          f"{self.NETWORK_TYPE_TAG_NAME}={self.MGMT_NETWORK_TAG_VALUE}")

        virtual_networks = self._azure_client.get_virtual_networks_by_resource_group(resource_group_name)
        return self._get_virtual_network_by_tag(virtual_networks=virtual_networks,
                                                tag_key=self.NETWORK_TYPE_TAG_NAME,
                                                tag_value=self.MGMT_NETWORK_TAG_VALUE)

    def get_sandbox_virtual_network(self, resource_group_name):
        """

        :param str resource_group_name:
        :return:
        """
        self._logger.info(f"Getting sandbox subnet by tag "
                          f"{self.NETWORK_TYPE_TAG_NAME}={self.SANDBOX_NETWORK_TAG_VALUE}")

        virtual_networks = self._azure_client.get_virtual_networks_by_resource_group(resource_group_name)
        return self._get_virtual_network_by_tag(virtual_networks=virtual_networks,
                                                tag_key=self.NETWORK_TYPE_TAG_NAME,
                                                tag_value=self.SANDBOX_NETWORK_TAG_VALUE)

    def get_sandbox_subnets(self, resource_group_name, mgmt_resource_group_name):
        """

        :param resource_group_name:
        :param mgmt_resource_group_name:
        :return:
        """
        # todo: rework this using some special tags ?
        sandbox_vnet = self.get_sandbox_virtual_network(resource_group_name=mgmt_resource_group_name)
        subnets = [subnet for subnet in sandbox_vnet.subnets if resource_group_name in subnet.name]

        if not subnets:
            raise Exception(f"Unable to find subnets under the Sandbox Virtual Network '{sandbox_vnet.name}' in the "
                            f"Management Resource Group '{mgmt_resource_group_name}'")

        return subnets

    def create_subnet(self, subnet_name, cidr, vnet, resource_group_name, network_security_group):
        """

        :param str subnet_name:
        :param str cidr:
        :param vnet:
        :param str resource_group_name:
        :param network_security_group:
        :return:
        """
        # TODO: CHECK THIS !! This method is atomic because we have to sync subnet creation for the entire sandbox vnet
        self._logger.info(f"Creating subnet {subnet_name} under: {resource_group_name}/{vnet.name}...")

        create_subnet_cmd = partial(self._azure_client.create_subnet,
                                    subnet_name=subnet_name,
                                    cidr=cidr,
                                    vnet_name=vnet.name,
                                    resource_group_name=resource_group_name,
                                    network_security_group=network_security_group,
                                    wait_for_result=True)

        try:
            return create_subnet_cmd()
        except CloudError as e:
            self._logger.warning(f"Unable to create subnet {subnet_name}", exc_info=True)

            if self.EXISTING_SUBNET_ERROR not in str(e.error):
                raise

            self._cleanup_stale_subnet(vnet=vnet, subnet_cidr=cidr, resource_group_name=resource_group_name)
            # try to create subnet again
            return create_subnet_cmd()

    def update_subnet(self, subnet_name, vnet_name, resource_group_name, subnet):
        """

        :param str subnet_name:
        :param str vnet_name:
        :param str resource_group_name:
        :param subnet:
        :return:
        """
        self._logger.info(f"Updating subnet {subnet_name} under: {resource_group_name}/{vnet_name}...")
        self._azure_client.update_subnet(subnet_name=subnet_name,
                                         vnet_name=vnet_name,
                                         resource_group_name=resource_group_name,
                                         subnet=subnet,
                                         wait_for_result=True)

    def get_subnet(self, subnet_name, vnet_name, resource_group_name):
        """

        :param str subnet_name:
        :param vnet_name:
        :param str resource_group_name:
        :return:
        """
        self._logger.info(f"Getting subnet {subnet_name} under: {resource_group_name}/{vnet_name}...")
        return self._azure_client.get_subnet(subnet_name=subnet_name,
                                             vnet_name=vnet_name,
                                             resource_group_name=resource_group_name)

    def delete_subnet(self, subnet_name, vnet_name, resource_group_name):
        """

        :param str subnet_name:
        :param vnet_name:
        :param str resource_group_name:
        :return:
        """
        self._logger.info(f"Deleting subnet {subnet_name} under: {resource_group_name}/{vnet_name}...")
        self._azure_client.delete_subnet(subnet_name=subnet_name,
                                         vnet_name=vnet_name,
                                         resource_group_name=resource_group_name)

    def create_sandbox_subnet(self, cidr, vnet, resource_group_name, mgmt_resource_group_name, network_security_group):
        """

        :param cidr:
        :param vnet:
        :param resource_group_name:
        :param mgmt_resource_group_name:
        :param network_security_group:
        :return:
        """
        subnet_name = self.prepare_sandbox_subnet_name(resource_group_name=resource_group_name, cidr=cidr)
        return self.create_subnet(subnet_name=subnet_name,
                                  cidr=cidr,
                                  vnet=vnet,
                                  resource_group_name=mgmt_resource_group_name,
                                  network_security_group=network_security_group)

    def get_sandbox_subnet(self, cidr, vnet_name, resource_group_name, mgmt_resource_group_name):
        """

        :param str cidr:
        :param str vnet_name:
        :param str resource_group_name:
        :param str mgmt_resource_group_name:
        :return:
        """
        subnet_name = self.prepare_sandbox_subnet_name(resource_group_name=resource_group_name, cidr=cidr)
        return self.get_subnet(subnet_name=subnet_name,
                               vnet_name=vnet_name,
                               resource_group_name=mgmt_resource_group_name)

    def delete_sandbox_subnet(self, cidr, vnet_name, resource_group_name, mgmt_resource_group_name):
        """

        :param str cidr:
        :param str vnet_name:
        :param str resource_group_name:
        :param str mgmt_resource_group_name:
        :return:
        """
        subnet_name = self.prepare_sandbox_subnet_name(resource_group_name=resource_group_name, cidr=cidr)
        self.delete_subnet(subnet_name=subnet_name,
                           vnet_name=vnet_name,
                           resource_group_name=mgmt_resource_group_name)

    def _cleanup_stale_subnet(self, vnet, subnet_cidr, resource_group_name):
        """

        :param VirtualNetwork vnet:
        :param str subnet_cidr:
        :return:
        """
        self._logger.info(f"Subnet with CIDR {subnet_cidr} exists in vNET with a different name. "
                          f"Cleaning the stale data...")

        subnet = next(subnet for subnet in vnet.subnets if subnet.address_prefix == subnet_cidr)

        if subnet.network_security_group is not None:
            self._logger.info(f"Detaching NSG from subnet {subnet.id}")
            subnet.network_security_group = None
            self.update_subnet(subnet_name=subnet.name,
                               vnet_name=vnet.name,
                               subnet=subnet,
                               resource_group_name=resource_group_name)

            self._logger.info(f"NSG from subnet {subnet.id} was successfully detached")

        self.delete_subnet(resource_group_name=resource_group_name,
                           vnet_name=vnet.name,
                           subnet_name=subnet.name)

        self._logger.info(f"Subnet {subnet.id} was successfully deleted")

    def _get_azure_ip_allocation_type(self, ip_type):
        """Get corresponding Enum type by string ip_type

        :param str ip_type: IP allocation method for the Public IP (Static/Dynamic)
        """
        types_map = {
            self.CLOUDSHELL_STATIC_IP_ALLOCATION_TYPE: models.IPAllocationMethod.static,
            self.CLOUDSHELL_DYNAMIC_IP_ALLOCATION_TYPE: models.IPAllocationMethod.dynamic,
        }

        allocation_type = types_map.get(ip_type.lower())

        if not allocation_type:
            raise Exception(f"Incorrect allocation type '{ip_type}'. Possible values are {types_map.keys()}")

        return allocation_type

    def is_static_ip_allocation_type(self, ip_type):
        """

        :param ip_type:
        :return:
        """
        return self._get_azure_ip_allocation_type(ip_type) == models.IPAllocationMethod.static

    def convert_cloudshell_private_ip_allocation_type(self, ip_type):
        """

        :param ip_type:
        :return:
        """
        types_map = {
            self.AZURE_PRIVATE_IP_ALLOCATION_METHOD: self.CLOUDSHELL_DYNAMIC_IP_ALLOCATION_TYPE,
            self.CLOUDSHELL_PRIVATE_IP_ALLOCATION_METHOD: self.CLOUDSHELL_STATIC_IP_ALLOCATION_TYPE,
        }

        allocation_type = types_map.get(ip_type)

        if not allocation_type:
            raise Exception(f"Incorrect allocation type '{ip_type}'. Possible values are {list(types_map.keys())}")

        return allocation_type

    def create_vm_network(self, interface_name, subnet, network_security_group, public_ip_type, resource_group_name,
                          region, tags, private_ip_allocation_method, private_ip_address,
                          add_public_ip=False, enable_ip_forwarding=False):
        """

        :param interface_name:
        :param subnet:
        :param network_security_group:
        :param public_ip_type:
        :param resource_group_name:
        :param region:
        :param tags:
        :param private_ip_allocation_method:
        :param private_ip_address:
        :param add_public_ip:
        :param enable_ip_forwarding:
        :return:
        """
        if add_public_ip:
            self._logger.info(f"Creating Public IP for Interface {interface_name}")
            public_ip_address = self._azure_client.create_public_ip(
                public_ip_name=self.PUBLIC_IP_NAME_TPL.format(interface_name=interface_name),
                public_ip_allocation_method=self._get_azure_ip_allocation_type(public_ip_type),
                resource_group_name=resource_group_name,
                region=region,
                tags=tags)
        else:
            public_ip_address = None

        self._logger.info(f"Creating Virtual Machine Interface {interface_name}")

        return self._azure_client.create_network_interface(
            interface_name=interface_name,
            resource_group_name=resource_group_name,
            region=region,
            subnet=subnet,
            private_ip_allocation_method=self._get_azure_ip_allocation_type(private_ip_allocation_method),
            enable_ip_forwarding=enable_ip_forwarding,
            network_security_group=network_security_group,
            private_ip_address=private_ip_address,
            public_ip_address=public_ip_address,
            tags=tags)

    def get_vm_network(self, interface_name, resource_group_name):
        """

        :param interface_name:
        :param resource_group_name:
        :return:
        """
        self._logger.info(f"Getting Virtual Machine Interface {interface_name}")
        return self._azure_client.get_network_interface(interface_name=interface_name,
                                                        resource_group_name=resource_group_name)

    def get_vm_network_public_ip(self, interface_name, resource_group_name):
        """

        :param interface_name:
        :param resource_group_name:
        :return:
        """
        self._logger.info(f"Getting Public IP for Interface {interface_name}")
        return self._azure_client.get_public_ip(
            public_ip_name=self.PUBLIC_IP_NAME_TPL.format(interface_name=interface_name),
            resource_group_name=resource_group_name)

    def delete_vm_network(self, interface_name, resource_group_name):
        """

        :param interface_name:
        :param resource_group_name:
        :return:
        """
        self._logger.info(f"Deleting Virtual Machine Interface {interface_name}")
        return self._azure_client.delete_network_interface(interface_name=interface_name,
                                                           resource_group_name=resource_group_name)

    def delete_public_ip(self, public_ip_name, resource_group_name):
        """

        :param public_ip_name:
        :param resource_group_name:
        :return:
        """
        self._logger.info(f"Deleting Public IP {public_ip_name}")
        return self._azure_client.delete_public_ip(public_ip_name=public_ip_name,
                                                   resource_group_name=resource_group_name)
