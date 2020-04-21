from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateNSGDenyRuleCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, nsg_actions, rule_name, nsg_name, resource_group_name,
                 dst_address, start_from):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param nsg_actions:
        :param rule_name:
        :param nsg_name:
        :param resource_group_name:
        :param dst_address:
        :param start_from:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._nsg_actions = nsg_actions
        self._rule_name = rule_name
        self._nsg_name = nsg_name
        self._resource_group_name = resource_group_name
        self._dst_address = dst_address
        self._start_from = start_from

    def _execute(self):
        self._nsg_actions.create_nsg_allow_rule(
            rule_name=self._rule_name,
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name,
            dst_address=self._dst_address,
            start_from=self._start_from)

    def rollback(self):
        pass
