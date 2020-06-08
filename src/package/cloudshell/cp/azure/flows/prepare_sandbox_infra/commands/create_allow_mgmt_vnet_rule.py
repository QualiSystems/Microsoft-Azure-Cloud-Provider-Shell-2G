from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateAllowMGMTVnetRuleCommand(RollbackCommand):
    """Allow MGMT vNET CIDR inbound traffic

    Basically providing access to the infrastructure to manage elements in the sandbox
    """
    NSG_RULE_PRIORITY = 4080
    NSG_RULE_NAME_TPL = "Allow_{mgmt_vnet_cidr}_To_{sandbox_cidr}"

    def __init__(self, rollback_manager, cancellation_manager, network_actions, nsg_actions, mgmt_resource_group_name,
                 resource_group_name, nsg_name, sandbox_cidr, rules_priority_generator):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param network_actions:
        :param nsg_actions:
        :param mgmt_resource_group_name:
        :param resource_group_name:
        :param nsg_name:
        :param sandbox_cidr:
        :param rules_priority_generator:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._nsg_actions = nsg_actions
        self._network_actions = network_actions
        self._mgmt_resource_group_name = mgmt_resource_group_name
        self._resource_group_name = resource_group_name
        self._nsg_name = nsg_name
        self._sandbox_cidr = sandbox_cidr
        self._rules_priority_generator = rules_priority_generator

    def execute(self):
        with self._cancellation_manager:
            mgmt_vnet = self._network_actions.get_mgmt_virtual_network(
                resource_group_name=self._mgmt_resource_group_name)

        mgmt_vnet_cidr = mgmt_vnet.address_space.address_prefixes[0]

        with self._cancellation_manager:
            self._nsg_actions.create_nsg_allow_rule(
                rule_name=self.NSG_RULE_NAME_TPL.format(mgmt_vnet_cidr=mgmt_vnet_cidr,
                                                        sandbox_cidr=self._sandbox_cidr).replace("/", "-"),
                resource_group_name=self._resource_group_name,
                nsg_name=self._nsg_name,
                src_address=mgmt_vnet_cidr,
                dst_address=self._sandbox_cidr,
                rule_priority=self._rules_priority_generator.get_priority(start_from=self.NSG_RULE_PRIORITY))

    def rollback(self):
        mgmt_vnet = self._network_actions.get_mgmt_virtual_network(
            resource_group_name=self._mgmt_resource_group_name)

        mgmt_vnet_cidr = mgmt_vnet.address_space.address_prefixes[0]

        self._nsg_actions.delete_nsg_rule(
            rule_name=self.NSG_RULE_NAME_TPL.format(mgmt_vnet_cidr=mgmt_vnet_cidr,
                                                    sandbox_cidr=self._sandbox_cidr).replace("/", "-"),
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name)
