from package.cloudshell.cp.azure.flows.deploy_vm.commands.create_allow_vm_inbound_port_rule import \
    CreateAllowVMInboundPortRuleCommand


class CreateAllowSandboxInboundPortRuleCommand(CreateAllowVMInboundPortRuleCommand):
    """Open traffic to VM on inbound ports (an attribute on the App) for private IP on the Sandbox NSG"""

    def __init__(self, rollback_manager, cancellation_manager, nsg_actions, nsg_name, vm_name, inbound_port,
                 resource_group_name, rules_priority_generator, private_ip):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param nsg_actions:
        :param nsg_name:
        :param vm_name:
        :param inbound_port:
        :param resource_group_name:
        :param rules_priority_generator:
        :param private_ip:
        """
        super().__init__(rollback_manager, cancellation_manager, nsg_actions, nsg_name, vm_name, inbound_port,
                         resource_group_name, rules_priority_generator)
        self._private_ip = private_ip

    def _execute(self):
        self._nsg_actions.create_nsg_allow_rule(
            rule_name=self.NSG_RULE_NAME_TPL.format(vm_name=self._vm_name,
                                                    port_range=self._port_range,
                                                    protocol=self._protocol),
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name,
            dst_port_range=self._port_range,
            dst_address=self._private_ip,
            protocol=self._protocol,
            rule_priority=self._rules_priority_generator.get_priority(start_from=self.NSG_RULE_PRIORITY))
