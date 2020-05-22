from urllib.parse import urlparse


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

    def _parse_blob_url(self, blob_url):
        """Parses Blob URL into AzureBlobUrlModel

        :param str blob_url: Azure Blob URL ("https://someaccount.blob.core.windows.net/container/blobname")
        :rtype: tuple[str, str, str]
        """
        parsed_blob_url = urlparse(blob_url)
        splitted_path = parsed_blob_url.path.split('/')
        blob_name = splitted_path[-1]
        container_name = splitted_path[-2]
        storage_account_name = parsed_blob_url.netloc.split('.', 1)[0]

        return blob_name, container_name, storage_account_name

    def delete_vhd_disk(self, vhd_url, resource_group_name):
        """Delete VHD Disk Blob resource on the azure for given VM

        :param str vhd_url: Blob VHD Disk URL
        :param str resource_group_name: The name of the resource group
        :return:
        """
        self._logger.info(f"Deleting VHD Disk {vhd_url}")
        blob_name, container_name, storage_account_name = self._parse_blob_url(blob_url=vhd_url)
        self._azure_client.delete_blob(blob_name=blob_name,
                                       container_name=container_name,
                                       resource_group_name=resource_group_name,
                                       storage_account_name=storage_account_name)

    def delete_managed_disk(self, disk_name, resource_group_name):
        """

        :param disk_name:
        :param resource_group_name:
        :return:
        """
        self._logger.info(f"Deleting Managed Disk {disk_name}")
        self._azure_client.delete_managed_disk(disk_name=disk_name, resource_group_name=resource_group_name)
