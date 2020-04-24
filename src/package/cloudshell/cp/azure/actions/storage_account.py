class StorageAccountActions:
    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def create_storage_account(self, storage_account_name, resource_group_name, region, tags):
        """

        :param str storage_account_name:
        :param str resource_group_name:
        :param str region:
        :param dict tags:
        :return:
        """
        self._logger.info(f"Creating storage account {storage_account_name}")
        self._azure_client.create_storage_account(resource_group_name=resource_group_name,
                                                  region=region,
                                                  storage_account_name=storage_account_name,
                                                  tags=tags,
                                                  wait_for_result=True)

    def delete_storage_account(self, storage_account_name, resource_group_name):
        """

        :param str storage_account_name:
        :param str resource_group_name:
        :return:
        """
        self._logger.info(f"Deleting storage account {storage_account_name}")
        self._azure_client.delete_storage_account(resource_group_name=resource_group_name,
                                                  storage_account_name=storage_account_name)
