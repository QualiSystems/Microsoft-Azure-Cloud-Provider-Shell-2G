from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateAllowAzureLoadBalancerRuleCommand(RollbackCommand):
    """Allow traffic for AzureLoadBalancer"""
    NSG_RULE_PRIORITY = 4080
    NSG_RULE_NAME_TPL = "Allow_Azure_Load_Balancer"
    LOAD_BALANCER_SRC_ADDRESS = "AzureLoadBalancer"

    def __init__(self, rollback_manager, cancellation_manager, nsg_actions, nsg_name, resource_group_name,
                 rules_priority_generator):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param nsg_actions:
        :param resource_group_name:
        :param nsg_name:
        :param rules_priority_generator:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._nsg_actions = nsg_actions
        self._nsg_name = nsg_name
        self._resource_group_name = resource_group_name
        self._rules_priority_generator = rules_priority_generator

    def _execute(self):
        self._nsg_actions.create_nsg_allow_rule(
            rule_name=self.NSG_RULE_NAME_TPL,
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name,
            src_address=self.LOAD_BALANCER_SRC_ADDRESS,
            rule_priority=self._rules_priority_generator.get_priority(start_from=self.NSG_RULE_PRIORITY))

    def rollback(self):
        self._nsg_actions.delete_nsg_rule(
            rule_name=self.NSG_RULE_NAME_TPL,
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name)
