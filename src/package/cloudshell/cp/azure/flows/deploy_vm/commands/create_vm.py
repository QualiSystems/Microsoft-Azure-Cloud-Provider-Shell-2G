import time
from datetime import datetime, timedelta

from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateVMCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, vm_actions, vm_name, virtual_machine, resource_group_name):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param vm_name:
        :param virtual_machine:
        :param resource_group_name:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._vm_actions = vm_actions
        self._vm_name = vm_name
        self._virtual_machine = virtual_machine
        self._resource_group_name = resource_group_name

    def _execute(self):
        # def _expand_cloud_error_message(self, exc, deployment_model):
        #     """
        #     :param CloudError exc:
        #     :param BaseDeployAzureVMResourceModel deployment_model:
        #     :return:
        #     """
        #     match = re.search('storage account type .+ is not supported for vm size', exc.message.lower())
        #     if match:
        #         exc.error.message += "\nDisk Type attribute value {} doesn't support the selected VM size.".format(
        #             deployment_model.disk_type)


        # except CloudError as exc:
        # self._expand_cloud_error_message(exc, deployment_model)
        # raise

        operation_poller = self._vm_actions.start_create_vm_task(vm_name=self._vm_name,
                                                                 virtual_machine=self._virtual_machine,
                                                                 resource_group_name=self._resource_group_name)

        return self._wait_for_task(operation_poller)

    def rollback(self):
        pass

    # todo: move this function somewhere???
    # todo: move values to constants
    def _wait_for_task(self, operation_poller, wait_time=30, timeout=1800):
        """Wait for Azure operation to be done

        :param timeout:
        :param operation_poller: msrestazure.azure_operation.AzureOperationPoller instance
        :param wait_time: (int) seconds to wait before polling request
        :return: Azure Operation Poller result
        """
        timeout_time = datetime.now() + timedelta(seconds=timeout)

        while not operation_poller.done():
            with self._cancellation_manager:
                # self._logger.info(f"Waiting for operation to complete, current status is {operation_poller.status()}")
                time.sleep(wait_time)

            if datetime.now() > timeout_time:
                raise Exception(f"Unable to perform operation within {timeout/60} minute(s)")

        return operation_poller.result()

