import time
from datetime import datetime, timedelta

from package.cloudshell.cp.azure.exceptions import AzureTaskTimeoutException


class AzureTaskWaiter:
    DEFAULT_WAIT_TIME = 30
    DEFAULT_TIMEOUT = 30 * 60

    def __init__(self, cancellation_manager, logger):
        """

        :param cancellation_manager:
        :param logging.Logger logger:
        """
        self._cancellation_manager = cancellation_manager
        self._logger = logger

    def wait_for_task(self, operation_poller, timeout=None, wait_time=None):
        """

        :param msrestazure.azure_operation.AzureOperationPoller operation_poller:
        :param int timeout:
        :param int wait_time:
        """
        wait_time = wait_time or self.DEFAULT_WAIT_TIME
        timeout = timeout or self.DEFAULT_TIMEOUT
        timeout_time = datetime.now() + timedelta(seconds=timeout)

        while not operation_poller.done():
            with self._cancellation_manager:
                self._logger.info(f"Waiting for operation to complete, current status is {operation_poller.status()}")
                time.sleep(wait_time)

            if datetime.now() > timeout_time:
                raise AzureTaskTimeoutException(f"Unable to perform operation within {timeout / 60} minute(s)")

        return operation_poller.result()
