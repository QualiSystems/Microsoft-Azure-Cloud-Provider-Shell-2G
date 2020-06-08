from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateAllowSandboxTrafficToSubnetRuleCommand(RollbackCommand):
    """Enable access from sandbox traffic for all subnets

    Specific VMs can block sandbox traffic using the VM network security group, which is created per VM
    """
    NSG_RULE_PRIORITY = 2000
    NSG_RULE_NAME_TPL = "Allow_Sandbox_Traffic_To_{subnet_cidr}"

    def __init__(self, rollback_manager, cancellation_manager, nsg_actions, nsg_name, resource_group_name,
                 sandbox_cidr, subnet_cidr, rules_priority_generator):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param nsg_actions:
        :param nsg_name:
        :param resource_group_name:
        :param sandbox_cidr:
        :param subnet_cidr:
        :param rules_priority_generator:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._nsg_actions = nsg_actions
        self._nsg_name = nsg_name
        self._resource_group_name = resource_group_name
        self._sandbox_cidr = sandbox_cidr
        self._subnet_cidr = subnet_cidr
        self._rules_priority_generator = rules_priority_generator

    def _execute(self):
        self._nsg_actions.create_nsg_allow_rule(
            rule_name=self.NSG_RULE_NAME_TPL.format(subnet_cidr=self._subnet_cidr).replace('/', '-'),
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name,
            src_address=self._sandbox_cidr,
            dst_address=self._subnet_cidr,
            rule_priority=self._rules_priority_generator.get_priority(start_from=self.NSG_RULE_PRIORITY))

    def rollback(self):
        self._nsg_actions.delete_nsg_rule(
            rule_name=self.NSG_RULE_NAME_TPL.format(subnet_cidr=self._subnet_cidr).replace('/', '-'),
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name)
