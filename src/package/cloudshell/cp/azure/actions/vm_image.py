class VMImageActions:
    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def get_marketplace_image_os(self, region, publisher_name, offer, sku):
        """

        :param region:
        :param publisher_name:
        :param offer:
        :param sku:
        :return:
        """
        image = self._azure_client.get_latest_virtual_machine_image(region=region,
                                                                    publisher_name=publisher_name,
                                                                    offer=offer,
                                                                    sku=sku)
        return image.os_disk_image.operating_system

    def get_custom_image_os(self, image_resource_group_name, image_name):
        """

        :param image_resource_group_name:
        :param image_name:
        :return:
        """
        image = self._azure_client.get_custom_virtual_machine_image(image_name=image_name,
                                                                    resource_group_name=image_resource_group_name)
        return image.storage_profile.os_disk.os_type

    def get_custom_image_id(self, image_resource_group_name, image_name):
        """

        :param image_resource_group_name:
        :param image_name:
        :return:
        """
        image = self._azure_client.get_custom_virtual_machine_image(image_name=image_name,
                                                                    resource_group_name=image_resource_group_name)
        return image.id
