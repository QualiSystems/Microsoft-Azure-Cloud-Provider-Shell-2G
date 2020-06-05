from cloudshell.cp.core.flows.vm_details import AbstractVMDetailsFlow

from package.cloudshell.cp.azure.actions.vm import VMActions
from package.cloudshell.cp.azure.actions.vm_details import VMDetailsActions
from package.cloudshell.cp.azure.models.deployed_app import AzureVMFromMarketplaceDeployedApp


class AzureGetVMDetailsFlow(AbstractVMDetailsFlow):
    def __init__(self, resource_config, azure_client, cancellation_manager, reservation_info, logger):
        """

        :param resource_config:
        :param azure_client:
        :param cancellation_manager:
        :param reservation_info:
        :param logging.Logger logger:
        """
        super().__init__(logger=logger)
        self._resource_config = resource_config
        self._azure_client = azure_client
        self._cancellation_manager = cancellation_manager
        self._reservation_info = reservation_info

    def _get_vm_details(self, deployed_app):
        """

        :param deployed_app:
        :return:
        """
        resource_group_name = self._reservation_info.get_resource_group_name()

        vm_actions = VMActions(azure_client=self._azure_client, logger=self._logger)
        vm_details_actions = VMDetailsActions(azure_client=self._azure_client, logger=self._logger)

        with self._cancellation_manager:
            vm = vm_actions.get_vm(vm_name=deployed_app.name, resource_group_name=resource_group_name)

        if isinstance(deployed_app, AzureVMFromMarketplaceDeployedApp):
            return vm_details_actions.prepare_marketplace_vm_details(virtual_machine=vm,
                                                                     resource_group_name=resource_group_name)

        return vm_details_actions.prepare_custom_vm_details(virtual_machine=vm,
                                                            resource_group_name=resource_group_name)
