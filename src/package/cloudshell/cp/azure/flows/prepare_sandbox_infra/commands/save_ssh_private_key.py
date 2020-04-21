from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class SaveSSHPrivateKeyCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, ssh_actions, resource_group_name, storage_account_name,
                 private_key):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param ssh_actions:
        :param resource_group_name:
        :param storage_account_name:
        :param private_key:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._ssh_actions = ssh_actions
        self._resource_group_name = resource_group_name
        self._storage_account_name = storage_account_name
        self._private_key = private_key

    def _execute(self):
        self._ssh_actions.save_ssh_private_key(resource_group_name=self._resource_group_name,
                                               storage_account_name=self._storage_account_name,
                                               private_key=self._private_key)

    def rollback(self):
        pass
