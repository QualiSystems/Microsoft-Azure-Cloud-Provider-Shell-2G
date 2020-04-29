import re

from azure.mgmt.compute import models
from azure.mgmt.compute.models import StorageAccountTypes
from cloudshell.cp.core.models import VmDetailsProperty

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

    @staticmethod
    def _parse_image_name(resource_id):
        """Get image name from the Azure image reference id

        :param str resource_id: Azure image reference id
        :return: Azure image name
        :rtype: str
        """
        match_images = re.match(r".*images/(?P<image_name>[^/]*).*", resource_id, flags=re.IGNORECASE)
        return match_images.group("image_name") if match_images else ""

    @staticmethod
    def _parse_resource_group_name(resource_id):
        """Get resource group name from the Azure resource id

        :param str resource_id: Azure resource Id
        :return: Azure resource group name
        :rtype: str
        """
        match_groups = re.match(r".*resourcegroups/(?P<group_name>[^/]*)/.*", resource_id, flags=re.IGNORECASE)
        return match_groups.group("group_name") if match_groups else ""

    def _prepare_vm_instance_data(self, deployed_vm):
        """

        :param deployed_vm:
        :return:
        """
        image_resource_id = deployed_vm.storage_profile.image_reference.id
        image_name = self._parse_image_name(resource_id=image_resource_id)
        resource_group = self._parse_resource_group_name(resource_id=image_resource_id)

        return [
            VmDetailsProperty(key="Image", value=image_name),
            VmDetailsProperty(key="Image Resource Group", value=resource_group),
            VmDetailsProperty(key="VM Size", value=deployed_vm.hardware_profile.vm_size),
            VmDetailsProperty(key="Operating System", value=deployed_vm.storage_profile.os_disk.os_type.name),
            VmDetailsProperty(key="Disk Type", value="HDD" if deployed_vm.storage_profile.os_disk.managed_disk
                              .storage_account_type == StorageAccountTypes.standard_lrs else "SSD")
        ]

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
