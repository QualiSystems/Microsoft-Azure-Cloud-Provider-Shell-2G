import time
from datetime import datetime, timedelta

from azure.mgmt.compute.models import OperatingSystemTypes

from package.cloudshell.cp.azure.utils.rollback import RollbackCommand
from package.cloudshell.cp.azure.exceptions import AzureTaskTimeoutException


class CreateVMExtensionCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, vm_extension_actions, script_file_path, script_config,
                 timeout, image_os_type, region, resource_group_name, vm_name, tags):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param vm_extension_actions:
        :param script_file_path:
        :param script_config:
        :param timeout:
        :param image_os_type:
        :param region:
        :param resource_group_name:
        :param vm_name:
        :param tags:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._vm_extension_actions = vm_extension_actions
        self._script_file_path = script_file_path
        self._script_config = script_config
        self._timeout = timeout
        self._image_os_type = image_os_type
        self._region = region
        self._resource_group_name = resource_group_name
        self._vm_name = vm_name
        self._tags = tags

    def _execute(self):
        if self._image_os_type == OperatingSystemTypes.linux:
            operation_poller = self._vm_extension_actions.create_windows_vm_script_extension(
                region=self._region,
                resource_group_name=self._resource_group_name,
                vm_name=self._vm_name,
                script_file_path=self._script_file_path,
                script_config=self._script_config,
                tags=self._tags)
        else:
            operation_poller = self._vm_extension_actions.create_linux_vm_script_extension(
                region=self._region,
                resource_group_name=self._resource_group_name,
                vm_name=self._vm_name,
                script_file_path=self._script_file_path,
                script_config=self._script_config,
                tags=self._tags)

        # todo: check if self._timeout can be None here !!!!
        return self._wait_for_task(operation_poller, timeout=self._timeout)

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
                raise AzureTaskTimeoutException(f"Unable to perform operation within {timeout/60} minute(s)")

        return operation_poller.result()

