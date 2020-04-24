from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateSandboxStorageAccountCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, storage_actions, storage_account_name,
                 resource_group_name, region, tags):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param storage_actions:
        :param storage_account_name:
        :param resource_group_name:
        :param region:
        :param tags:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._storage_actions = storage_actions
        self._storage_account_name = storage_account_name
        self._resource_group_name = resource_group_name
        self._region = region
        self._tags = tags

    def _execute(self):
        self._storage_actions.create_storage_account(storage_account_name=self._storage_account_name,
                                                     resource_group_name=self._resource_group_name,
                                                     region=self._region,
                                                     tags=self._tags)

    def rollback(self):
        self._storage_actions.delete_storage_account(storage_account_name=self._storage_account_name,
                                                     resource_group_name=self._resource_group_name)
