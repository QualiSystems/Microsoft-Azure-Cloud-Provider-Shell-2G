from azure.mgmt.compute import models

from package.cloudshell.cp.azure.actions.vm_details import VMDetailsActions
from package.cloudshell.cp.azure.actions.vm_image import VMImageActions
from package.cloudshell.cp.azure.flows.deploy_vm.base_flow import BaseAzureDeployVMFlow


class AzureDeployCustomVMFlow(BaseAzureDeployVMFlow):
    def _get_vm_image_os(self, deploy_app, vm_image_actions):
        """

        :param deploy_app:
        :param vm_image_actions:
        :return:
        """
        return vm_image_actions.get_custom_image_os(image_resource_group_name=deploy_app.azure_resource_group,
                                                    image_name=deploy_app.azure_image)

    def _prepare_storage_profile(self, deploy_app, os_disk):
        """

        :param deploy_app:
        :param os_disk:
        :return:
        """
        vm_image_actions = VMImageActions(azure_client=self._azure_client, logger=self._logger)
        image_id = vm_image_actions.get_custom_image_id(image_resource_group_name=deploy_app.azure_resource_group,
                                                        image_name=deploy_app.azure_image)
        return models.StorageProfile(os_disk=os_disk,
                                     image_reference=models.ImageReference(id=image_id))

    def _prepare_vm_details_data(self, deployed_vm, resource_group_name):
        """

        :param deployed_vm:
        :param resource_group_name:
        :return:
        """
        vm_details_actions = VMDetailsActions(azure_client=self._azure_client, logger=self._logger)
        vm_details_actions.prepare_custom_vm_details(virtual_machine=deployed_vm,
                                                     resource_group_name=resource_group_name)
