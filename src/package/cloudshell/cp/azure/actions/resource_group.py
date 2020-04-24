class ResourceGroupActions:
    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def create_resource_group(self, resource_group_name, region, tags):
        """

        :param str resource_group_name:
        :param str region:
        :param dict tags:
        :return:
        """
        self._logger.info(f"Creating resource group: {resource_group_name}")
        self._azure_client.create_resource_group(group_name=resource_group_name,
                                                 region=region,
                                                 tags=tags)

    def delete_resource_group(self, resource_group_name):
        """

        :param str resource_group_name:
        :return:
        """
        self._logger.info(f"Deleting resource group: {resource_group_name}")
        self._azure_client.delete_resource_group(group_name=resource_group_name)
