from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateNSGDenyTrafficFromOtherSandboxesRuleCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, network_actions, nsg_actions, management_group_name,
                 resource_group_name, nsg_name, sandbox_cidr, start_from):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param network_actions:
        :param nsg_actions:
        :param management_group_name:
        :param resource_group_name:
        :param nsg_name:
        :param sandbox_cidr:
        :param start_from:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._nsg_actions = nsg_actions
        self._network_actions = network_actions
        self._management_group_name = management_group_name
        self._resource_group_name = resource_group_name
        self._nsg_name = nsg_name
        self._sandbox_cidr = sandbox_cidr
        self._start_from = start_from

    def execute(self):
        with self._cancellation_manager:
            sandbox_vnet = self._network_actions.get_sandbox_virtual_network(
                resource_group_name=self._management_group_name)

        sandbox_vnet_cidr = sandbox_vnet.address_space.address_prefixes[0]

        with self._cancellation_manager:
            self._nsg_actions.create_nsg_deny_rule(
                rule_name="Deny_Traffic_From_Other_Sandboxes_To_Sandbox_CIDR",
                resource_group_name=self._resource_group_name,
                nsg_name=self._nsg_name,
                src_address=sandbox_vnet_cidr,
                dst_address=self._sandbox_cidr,
                start_from=self._start_from)

    def rollback(self):
        pass
