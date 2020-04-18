from cloudshell.cp.core import models
from cloudshell.shell.standards.core.resource_config_entities import ResourceAttrRO


class BaseAzureVMDeployApp(models.DeployApp):
    vm_size = ResourceAttrRO(
        "VM Size", "DEPLOYMENT_PATH"
    )

    disk_type = ResourceAttrRO(
        "Disk Type", "DEPLOYMENT_PATH"
    )

    disk_size = ResourceAttrRO(
        "Disk Size", "DEPLOYMENT_PATH"
    )

    add_public_ip = ResourceAttrRO(
        "Add Public IP", "DEPLOYMENT_PATH"
    )

    wait_for_ip = ResourceAttrRO(
        "Wait for IP", "DEPLOYMENT_PATH"
    )

    extension_script_file = ResourceAttrRO(
        "Extension Script file", "DEPLOYMENT_PATH"
    )

    extension_script_configurations = ResourceAttrRO(
        "Extension Script Configurations", "DEPLOYMENT_PATH"
    )

    extension_script_timeout = ResourceAttrRO(
        "Extension Script Timeout", "DEPLOYMENT_PATH"
    )

    public_ip_type = ResourceAttrRO(
        "Public IP Type", "DEPLOYMENT_PATH"
    )

    inbound_ports = ResourceAttrRO(
        "Inbound Ports", "DEPLOYMENT_PATH"  # todo: needs to be parsed !!!
    )

    allow_all_sandbox_traffic = ResourceAttrRO(
        "Allow all Sandbox Traffic", "DEPLOYMENT_PATH"
    )


class AzureVMFromMarketplaceDeployApp(BaseAzureVMDeployApp):
    DEPLOYMENT_PATH = "Microsoft Azure 2G.Azure VM From Marketplace 2G"

    image_publisher = ResourceAttrRO(
        "Image Publisher", "DEPLOYMENT_PATH"
    )

    image_offer = ResourceAttrRO(
        "Image Offer", "DEPLOYMENT_PATH"
    )

    image_sku = ResourceAttrRO(
        "Image SKU", "DEPLOYMENT_PATH"
    )

    image_version = ResourceAttrRO(
        "Image Version", "DEPLOYMENT_PATH"
    )


class AzureVMFromCustomImageDeployApp(models.DeployApp):
    DEPLOYMENT_PATH = "Microsoft Azure 2G.Azure VM From Custom Image 2G"

    azure_image = ResourceAttrRO(
        "Azure Image", "DEPLOYMENT_PATH"
    )

    azure_resource_group = ResourceAttrRO(
        "Azure Resource Group", "DEPLOYMENT_PATH"
    )
