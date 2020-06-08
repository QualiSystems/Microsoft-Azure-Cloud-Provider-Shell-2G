from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateAllowMGMTVnetRuleCommand(RollbackCommand):
    """Open traffic to VM from the MGMT vNET"""
    NSG_RULE_PRIORITY = 4070
    NSG_RULE_NAME_TPL = "Allow_Traffic_From_Management_Vnet_To_Any"

    def __init__(self, rollback_manager, cancellation_manager, network_actions, nsg_actions, nsg_name,
                 resource_group_name, mgmt_resource_group_name, rules_priority_generator):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param nsg_actions:
        :param resource_group_name:
        :param nsg_name:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._network_actions = network_actions
        self._nsg_actions = nsg_actions
        self._nsg_name = nsg_name
        self._resource_group_name = resource_group_name
        self._mgmt_resource_group_name = mgmt_resource_group_name
        self._rules_priority_generator = rules_priority_generator

    def _execute(self):
        with self._cancellation_manager:
            mgmt_vnet = self._network_actions.get_mgmt_virtual_network(self._mgmt_resource_group_name)

        mgmt_vnet_cidr = mgmt_vnet.address_space.address_prefixes[0]

        self._nsg_actions.create_nsg_allow_rule(
            rule_name=self.NSG_RULE_NAME_TPL,
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name,
            src_address=mgmt_vnet_cidr,
            rule_priority=self._rules_priority_generator.get_priority(start_from=self.NSG_RULE_PRIORITY))

    def rollback(self):
        self._nsg_actions.delete_nsg_rule(
            rule_name=self.NSG_RULE_NAME_TPL,
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name)

