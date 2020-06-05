from cloudshell.cp.core.request_actions import models

from package.cloudshell.cp.azure import constants


class BaseAzureVMDeployedApp(models.DeployedApp):
    pass


class AzureVMFromMarketplaceDeployedApp(BaseAzureVMDeployedApp):
    DEPLOYMENT_PATH = constants.AZURE_VM_FROM_MARKETPLACE_DEPLOYMENT_PATH


class AzureVMFromCustomImageDeployedApp(BaseAzureVMDeployedApp):
    DEPLOYMENT_PATH = constants.AZURE_VM_FROM_CUSTOM_IMAGE_DEPLOYMENT_PATH
