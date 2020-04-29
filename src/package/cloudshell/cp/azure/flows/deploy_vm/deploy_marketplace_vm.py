from azure.mgmt.compute import models
from azure.mgmt.compute.models import StorageAccountTypes
from cloudshell.cp.core.models import VmDetailsProperty

from package.cloudshell.cp.azure.flows.deploy_vm.base_flow import BaseAzureDeployVMFlow


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

    def _prepare_vm_instance_data(self, deployed_vm):
        """

        :param deployed_vm:
        :return:
        """
        return [
            VmDetailsProperty(key="Image Publisher", value=deployed_vm.storage_profile.image_reference.publisher),
            VmDetailsProperty(key="Image Offer", value=deployed_vm.storage_profile.image_reference.offer),
            VmDetailsProperty(key="Image SKU", value=deployed_vm.storage_profile.image_reference.sku),
            VmDetailsProperty(key="VM Size", value=deployed_vm.hardware_profile.vm_size),
            VmDetailsProperty(key="Operating System", value=deployed_vm.storage_profile.os_disk.os_type.name),
            VmDetailsProperty(key="Disk Type", value="HDD" if deployed_vm.storage_profile.os_disk.managed_disk
                              .storage_account_type == StorageAccountTypes.standard_lrs else "SSD")
        ]

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

