from functools import partial

from msrestazure.azure_exceptions import CloudError


class NetworkActions:
    NETWORK_TYPE_TAG_NAME = "network_type"
    SANDBOX_NETWORK_TAG_VALUE = "sandbox"
    MGMT_NETWORK_TAG_VALUE = "mgmt"
    EXISTING_SUBNET_ERROR = "NetcfgInvalidSubnet"

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
        for network in virtual_networks:
            for network_tag_key, network_tag_value in network.tags.items():
                if all([network_tag_key == tag_key, network_tag_value == tag_value]):
                    return network

        raise Exception(f"Unable to find virtual network with tag {tag_key}={tag_value}")

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
            create_subnet_cmd()
        except CloudError as e:
            self._logger.warning(f"Unable to create subnet {subnet_name}", exc_info=True)

            if self.EXISTING_SUBNET_ERROR not in str(e.error):
                raise

            self._cleanup_stale_subnet(vnet=vnet, subnet_cidr=cidr, resource_group_name=resource_group_name)
            # try to create subnet again
            create_subnet_cmd()

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
            self._azure_client.update_subnet(subnet_name=subnet.name,
                                             vnet_name=vnet.name,
                                             subnet=subnet,
                                             resource_group_name=resource_group_name)

            self._logger.info(f"NSG from subnet {subnet.id} was successfully detached")

        self._azure_client.delete_subnet(resource_group_name=resource_group_name,
                                         vnet_name=vnet.name,
                                         subnet_name=subnet.name)

        self._logger.info(f"Subnet {subnet.id} was successfully deleted")
