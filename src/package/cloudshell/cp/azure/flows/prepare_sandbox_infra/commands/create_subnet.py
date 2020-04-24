from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateSubnetCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, network_actions, vnet, cidr,
                 resource_group_name, mgmt_resource_group_name, network_security_group):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param network_actions:
        :param vnet:
        :param cidr:
        :param resource_group_name:
        :param mgmt_resource_group_name:
        :param network_security_group:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._network_actions = network_actions
        self._vnet = vnet
        self._cidr = cidr
        self._resource_group_name = resource_group_name
        self._mgmt_resource_group_name = mgmt_resource_group_name
        self._network_security_group = network_security_group

    def _prepare_subnet_name(self):
        return f"{self._resource_group_name}_{self._cidr}".replace(' ', '').replace('/', '-')

    def _execute(self):
        self._network_actions.create_subnet(subnet_name=self._prepare_subnet_name(),
                                            cidr=self._cidr,
                                            vnet=self._vnet,
                                            resource_group_name=self._mgmt_resource_group_name,
                                            network_security_group=self._network_security_group)

    def rollback(self):
        self._network_actions.delete_subnet(subnet_name=self._prepare_subnet_name(),
                                            vnet=self._vnet,
                                            resource_group_name=self._mgmt_resource_group_name)
