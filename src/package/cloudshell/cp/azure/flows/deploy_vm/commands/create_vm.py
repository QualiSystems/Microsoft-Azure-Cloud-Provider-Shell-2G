import re

from package.cloudshell.cp.azure.utils.rollback import RollbackCommand

from msrestazure.azure_exceptions import CloudError


class CreateVMCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, task_waiter_manager, vm_actions, vm_name,
                 disk_type, virtual_machine, resource_group_name):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param task_waiter_manager:
        :param vm_name:
        :param disk_type:
        :param virtual_machine:
        :param resource_group_name:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._task_waiter_manager = task_waiter_manager
        self._vm_actions = vm_actions
        self._vm_name = vm_name
        self._disk_type = disk_type
        self._virtual_machine = virtual_machine
        self._resource_group_name = resource_group_name

    def _execute(self):
        try:
            operation_poller = self._vm_actions.start_create_vm_task(vm_name=self._vm_name,
                                                                     virtual_machine=self._virtual_machine,
                                                                     resource_group_name=self._resource_group_name)

            return self._task_waiter_manager.wait_for_task(operation_poller)
        except CloudError as e:
            if re.search("storage account type .+ is not supported for vm size", e.message.lower()):
                e.error.message += f"\nDisk Type attribute value {self._disk_type} " \
                                   f"doesn't support the selected VM size."
            raise

    def rollback(self):
        self._vm_actions.delete_vm(vm_name=self._vm_name, resource_group_name=self._resource_group_name)
