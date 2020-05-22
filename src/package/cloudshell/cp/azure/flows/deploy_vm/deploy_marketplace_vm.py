from azure.mgmt.compute import models

from package.cloudshell.cp.azure.flows.deploy_vm.base_flow import BaseAzureDeployVMFlow
from package.cloudshell.cp.azure.actions.vm_details import VMDetailsActions


class AzureDeployMarketplaceVMFlow(BaseAzureDeployVMFlow):
    def _get_vm_image_os(self, deploy_app, vm_image_actions):
        """

        :param deploy_app:
        :param vm_image_actions:
        :return:
        """
        return vm_image_actions.get_marketplace_image_os(region=self._resource_config.region,
                                                         publisher_name=deploy_app.image_publisher,
                                                         offer=deploy_app.image_offer,
                                                         sku=deploy_app.image_sku)

    def _prepare_storage_profile(self, deploy_app, os_disk):
        """

        :param deploy_app:
        :return:
        """
        return models.StorageProfile(
            os_disk=os_disk,
            image_reference=models.ImageReference(publisher=deploy_app.image_publisher,
                                                  offer=deploy_app.image_offer,
                                                  sku=deploy_app.image_sku,
                                                  version=deploy_app.image_version))

    def _prepare_vm_details_data(self, deployed_vm, resource_group_name):
        """

        :param deployed_vm:
        :param resource_group_name:
        :return:
        """
        vm_details_actions = VMDetailsActions(azure_client=self._azure_client, logger=self._logger)
        vm_details_actions.prepare_marketplace_vm_details(virtual_machine=deployed_vm,
                                                          resource_group_name=resource_group_name)
