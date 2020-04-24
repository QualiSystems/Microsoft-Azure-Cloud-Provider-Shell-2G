from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateAdditionalMGMTNetworkRuleCommand(RollbackCommand):
    """Create NSG Allow rules for the Additional MGMT Networks

    Allow inbound traffic from additional management networks (can configure on Azure cloud provider resource
    that additional networks are allowed to communicate with subnets and vms)
    """
    NSG_RULE_PRIORITY = 4000
    NSG_RULE_NAME_TPL = "Allow_{mgmt_network}_To_{sandbox_cidr}"

    def __init__(self, rollback_manager, cancellation_manager, nsg_actions, nsg_name, resource_group_name,
                 mgmt_network, sandbox_cidr):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param nsg_actions:
        :param nsg_name:
        :param resource_group_name:
        :param mgmt_network:
        :param sandbox_cidr:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._nsg_actions = nsg_actions
        self._nsg_name = nsg_name
        self._resource_group_name = resource_group_name
        self._mgmt_network = mgmt_network
        self._sandbox_cidr = sandbox_cidr

    def _execute(self):
        self._nsg_actions.create_nsg_allow_rule(
            rule_name=self.NSG_RULE_NAME_TPL.format(mgmt_network=self._mgmt_network,
                                                    sandbox_cidr=self._sandbox_cidr).replace("/", "-"),
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name,
            src_address=self._mgmt_network,
            dst_address=self._sandbox_cidr,
            start_from=self.NSG_RULE_PRIORITY)

    def rollback(self):
        self._nsg_actions.delete_nsg_rule(
            rule_name=self.NSG_RULE_NAME_TPL.format(mgmt_network=self._mgmt_network,
                                                    sandbox_cidr=self._sandbox_cidr).replace("/", "-"),
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name)
