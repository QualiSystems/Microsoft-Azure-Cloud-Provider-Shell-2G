from azure.mgmt.compute.models import OperatingSystemTypes


class VMExtensionActions:
    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def create_linux_vm_script_extension(self, region, resource_group_name, vm_name, script_file_path,
                                         script_config, tags):
        """

        :param region:
        :param resource_group_name:
        :param vm_name:
        :param script_file_path:
        :param script_config:
        :param tags:
        :return:
        """
        return self._azure_client.create_linux_vm_script_extension(
            script_file_path=script_file_path,
            script_config=script_config,
            vm_name=vm_name,
            resource_group_name=resource_group_name,
            region=region,
            tags=tags,
            wait_for_result=False)

    def create_windows_vm_script_extension(self, region, resource_group_name, vm_name, script_file_path,
                                           script_config, tags):
        """

        :param region:
        :param resource_group_name:
        :param vm_name:
        :param script_file_path:
        :param script_config:
        :param tags:
        :return:
        """
        return self._azure_client.create_windows_vm_script_extension(
            script_file_path=script_file_path,
            script_config=script_config,
            vm_name=vm_name,
            resource_group_name=resource_group_name,
            region=region,
            tags=tags,
            wait_for_result=False)
