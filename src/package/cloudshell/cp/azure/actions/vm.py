class VMActions:
    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def start_create_vm_task(self, vm_name, virtual_machine, resource_group_name):
        """

        :param vm_name:
        :param virtual_machine:
        :param resource_group_name:
        :return:
        """
        return self._azure_client.create_virtual_machine(vm_name=vm_name,
                                                         virtual_machine=virtual_machine,
                                                         resource_group_name=resource_group_name,
                                                         wait_for_result=False)

    def start_vm(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        return self._azure_client.start_vm(vm_name=vm_name,
                                           resource_group_name=resource_group_name)

    def stop_vm(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        return self._azure_client.stop_vm(vm_name=vm_name,
                                          resource_group_name=resource_group_name)
