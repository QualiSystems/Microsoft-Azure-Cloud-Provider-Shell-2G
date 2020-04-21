from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class SaveSSHPublicKeyCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, ssh_actions, storage_account_name, resource_group_name,
                 public_key):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param ssh_actions:
        :param storage_account_name:
        :param resource_group_name:
        :param public_key:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._ssh_actions = ssh_actions
        self._storage_account_name = storage_account_name
        self._resource_group_name = resource_group_name
        self._public_key = public_key

    def _execute(self):
        self._ssh_actions.save_ssh_public_key(resource_group_name=self._resource_group_name,
                                              storage_account_name=self._storage_account_name,
                                              public_key=self._public_key)

    def rollback(self):
        pass
