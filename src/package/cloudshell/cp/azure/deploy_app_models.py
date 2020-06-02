from cloudshell.cp.core.request_actions import models
from cloudshell.shell.standards.core.resource_config_entities import ResourceAttrRO


class InboundPortsAttrRO(ResourceAttrRO):
    def __get__(self, instance, owner):
        """
        :param GenericResourceConfig instance:
        :rtype: str
        """
        if instance is None:
            return self

        attr = instance.attributes.get(self.get_key(instance), self.default)
        return [port_data.strip() for port_data in attr.split(';') if port_data]


class IntegerAttrRO(ResourceAttrRO):
    def __get__(self, instance, owner):
        """
        :param GenericResourceConfig instance:
        :rtype: str
        """
        if instance is None:
            return self

        attr = instance.attributes.get(self.get_key(instance), self.default)
        return int(attr) if attr else None


class BaseAzureVMDeployApp(models.DeployApp):
    @property
    def app_name(self):
        return self.actionParams.appName.lower().replace(" ", "-")

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

    extension_script_timeout = IntegerAttrRO(
        "Extension Script Timeout", "DEPLOYMENT_PATH"
    )

    public_ip_type = ResourceAttrRO(
        "Public IP Type", "DEPLOYMENT_PATH"
    )

    inbound_ports = InboundPortsAttrRO(
        "Inbound Ports", "DEPLOYMENT_PATH"
    )

    enable_ip_forwarding = ResourceAttrRO(
        "Enable IP Forwarding", "DEPLOYMENT_PATH"
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


class AzureVMFromCustomImageDeployApp(BaseAzureVMDeployApp):
    DEPLOYMENT_PATH = "Microsoft Azure 2G.Azure VM From Custom Image 2G"

    azure_image = ResourceAttrRO(
        "Azure Image", "DEPLOYMENT_PATH"
    )

    azure_resource_group = ResourceAttrRO(
        "Azure Resource Group", "DEPLOYMENT_PATH"
    )
