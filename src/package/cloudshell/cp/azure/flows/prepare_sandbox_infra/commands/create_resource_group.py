from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateResourceGroupCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, resource_group_actions, resource_group_name,
                 region, tags):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param resource_group_actions:
        :param resource_group_name:
        :param region:
        :param tags:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._resource_group_actions = resource_group_actions
        self._resource_group_name = resource_group_name
        self._region = region
        self._tags = tags

    def _execute(self):
        self._resource_group_actions.create_sandbox_resource_group(resource_group_name=self._resource_group_name,
                                                                   region=self._region,
                                                                   tags=self._tags)

    def rollback(self):
        pass
