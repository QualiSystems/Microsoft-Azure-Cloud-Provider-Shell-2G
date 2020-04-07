class NetworkActions:
    NETWORK_TYPE_TAG_NAME = "network_type"
    SANDBOX_NETWORK_TAG_VALUE = "sandbox"
    MGMT_NETWORK_TAG_VALUE = "mgmt"

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
        virtual_networks = self._azure_client.get_virtual_networks_by_resource_group(resource_group_name)
        return self._get_virtual_network_by_tag(virtual_networks=virtual_networks,
                                                tag_key=self.NETWORK_TYPE_TAG_NAME,
                                                tag_value=self.MGMT_NETWORK_TAG_VALUE)

    def get_sandbox_virtual_network(self, resource_group_name):
        """

        :param str resource_group_name:
        :return:
        """
        virtual_networks = self._azure_client.get_virtual_networks_by_resource_group(resource_group_name)
        return self._get_virtual_network_by_tag(virtual_networks=virtual_networks,
                                                tag_key=self.NETWORK_TYPE_TAG_NAME,
                                                tag_value=self.SANDBOX_NETWORK_TAG_VALUE)
