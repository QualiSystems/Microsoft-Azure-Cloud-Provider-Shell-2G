from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateVMNSGCommand(RollbackCommand):
    NSG_NAME_TPL = "NSG_{vm_name}"

    def __init__(self, rollback_manager, cancellation_manager, nsg_actions, vm_name, resource_group_name,
                 region, tags):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param nsg_actions:
        :param vm_name:
        :param resource_group_name:
        :param region:
        :param tags:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._nsg_actions = nsg_actions
        self._vm_name = vm_name
        self._resource_group_name = resource_group_name
        self._region = region
        self._tags = tags

    def _execute(self):
        return self._nsg_actions.create_network_security_group(
            nsg_name=self.NSG_NAME_TPL.format(vm_name=self._vm_name),
            resource_group_name=self._resource_group_name,
            region=self._region,
            tags=self._tags)

    def rollback(self):
        return self._nsg_actions.delete_network_security_group(
            nsg_name=self.NSG_NAME_TPL.format(vm_name=self._vm_name),
            resource_group_name=self._resource_group_name)
