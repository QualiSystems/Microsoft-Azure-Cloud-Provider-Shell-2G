import re

from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateAllowAdditionalMGMTNetworkRuleCommand(RollbackCommand):
    """Open traffic to VM from Additional MGMT networks"""
    NSG_RULE_PRIORITY = 3000
    NSG_RULE_NAME_TPL = "Allow_{mgmt_network}"

    def __init__(self, rollback_manager, cancellation_manager, nsg_actions, nsg_name, vm_name, mgmt_network,
                 resource_group_name):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param nsg_actions:
        :param nsg_name:
        :param resource_group_name:
        :param mgmt_network:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._nsg_actions = nsg_actions
        self._nsg_name = nsg_name
        self._resource_group_name = resource_group_name
        self._vm_name = vm_name
        self._mgmt_network = mgmt_network

    def _execute(self):
        self._nsg_actions.create_nsg_allow_rule(
            rule_name=self.NSG_RULE_NAME_TPL.format(mgmt_network=self._mgmt_network).replace("/", "-"),
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name,
            start_from=self.NSG_RULE_PRIORITY)

    def rollback(self):
        self._nsg_actions.delete_nsg_rule(
            rule_name=self.NSG_RULE_NAME_TPL.format(mgmt_network=self._mgmt_network).replace("/", "-"),
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name)
