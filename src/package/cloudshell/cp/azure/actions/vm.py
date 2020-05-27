class VMActions:
    SUCCEEDED_PROVISIONING_STATE = "Succeeded"

    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def get_vm(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        self._logger.info(f"Getting VM {vm_name}")
        return self._azure_client.get_vm(vm_name=vm_name, resource_group_name=resource_group_name)

    def get_active_vm(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        vm = self.get_vm(vm_name=vm_name, resource_group_name=resource_group_name)

        if vm.provisioning_state != self.SUCCEEDED_PROVISIONING_STATE:
            raise Exception("Can't perform action. Azure VM instance is not in the active state")

        return vm

    def start_create_vm_task(self, vm_name, virtual_machine, resource_group_name):
        """

        :param vm_name:
        :param virtual_machine:
        :param resource_group_name:
        :return:
        """
        self._logger.info(f"Starting VM {vm_name} create task")
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
        self._logger.info(f"Starting VM {vm_name}")
        return self._azure_client.start_vm(vm_name=vm_name, resource_group_name=resource_group_name)

    def stop_vm(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        self._logger.info(f"Stopping VM {vm_name}")
        return self._azure_client.stop_vm(vm_name=vm_name, resource_group_name=resource_group_name)

    def delete_vm(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        self._logger.info(f"Deleting VM {vm_name}")
        return self._azure_client.delete_vm(vm_name=vm_name, resource_group_name=resource_group_name)
