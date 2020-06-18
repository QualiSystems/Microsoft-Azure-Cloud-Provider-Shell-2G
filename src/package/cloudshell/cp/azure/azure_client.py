from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import VirtualMachineExtension
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import NetworkInterfaceIPConfiguration, NetworkInterface
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlockBlobService
from azure.storage.file import FileService
from azure.mgmt.resource.resources.models import ResourceGroup
from azure.mgmt.storage import models as storage_models
from azure.mgmt.network import models as network_models
from msrestazure.azure_active_directory import ServicePrincipalCredentials
from retrying import retry

from package.cloudshell.cp.azure.utils.retrying import retry_on_connection_error
from package.cloudshell.cp.azure.utils.retrying import retry_on_retryable_error
from package.cloudshell.cp.azure.utils.retrying import RETRYABLE_ERROR_MAX_ATTEMPTS, RETRYABLE_WAIT_TIME


class AzureAPIClient:
    NETWORK_INTERFACE_IP_CONFIG_NAME = "default"

    VM_SCRIPT_WINDOWS_PUBLISHER = "Microsoft.Compute"
    VM_SCRIPT_WINDOWS_EXTENSION_TYPE = "CustomScriptExtension"
    VM_SCRIPT_WINDOWS_HANDLER_VERSION = "1.9"
    VM_SCRIPT_WINDOWS_COMMAND_TPL = "powershell.exe -ExecutionPolicy Unrestricted -File " \
                                    "{file_name} {script_configuration}"

    VM_SCRIPT_LINUX_PUBLISHER = "Microsoft.OSTCExtensions"
    VM_SCRIPT_LINUX_EXTENSION_TYPE = "CustomScriptForLinux"
    VM_SCRIPT_LINUX_HANDLER_VERSION = "1.5"

    CREATE_PUBLIC_IP_TIMEOUT_IN_MINUTES = 4
    RETRYING_STOP_MAX_ATTEMPT_NUMBER = 5
    RETRYING_WAIT_FIXED = 2000

    def __init__(self, azure_subscription_id, azure_tenant_id, azure_application_id, azure_application_key, logger):
        """

        :param str azure_subscription_id:
        :param str azure_tenant_id:
        :param str azure_application_id:
        :param str azure_application_key:
        :param str azure_application_key:
        :param logging.Logger logger:
        """
        self._azure_subscription_id = azure_subscription_id
        self._azure_tenant_id = azure_tenant_id
        self._azure_application_id = azure_application_id
        self._azure_application_key = azure_application_key
        self._logger = logger
        self._cached_storage_account_keys = {}

        self._credentials = ServicePrincipalCredentials(client_id=azure_application_id,
                                                        secret=azure_application_key,
                                                        tenant=azure_tenant_id)

        self._subscription_client = SubscriptionClient(credentials=self._credentials)

        self._resource_client = ResourceManagementClient(credentials=self._credentials,
                                                         subscription_id=self._azure_subscription_id)

        self._compute_client = ComputeManagementClient(credentials=self._credentials,
                                                       subscription_id=self._azure_subscription_id)

        self._storage_client = StorageManagementClient(credentials=self._credentials,
                                                       subscription_id=self._azure_subscription_id)

        self._network_client = NetworkManagementClient(credentials=self._credentials,
                                                       subscription_id=self._azure_subscription_id)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_available_regions(self):
        """List all available regions per subscription

        :rtype: list[azure.mgmt.resource.subscriptions.models.Location]
        """
        locations = self._subscription_client.subscriptions.list_locations(self._azure_subscription_id)
        return list(locations)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def register_provider(self, provider):
        """

        :param str provider:
        :return:
        """
        self._resource_client.providers.register(provider)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_resource_group(self, resource_group_name):
        """

        :param str resource_group_name:
        :return:
        """
        return self._resource_client.resource_groups.get(resource_group_name=resource_group_name)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_virtual_networks_by_resource_group(self, resource_group_name):
        """

        :param str resource_group_name:
        :return: list of vNets in group
        :rtype: list[VirtualNetwork]
        """
        networks_list = self._network_client.virtual_networks.list(resource_group_name)
        return list(networks_list)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_virtual_machine_sizes_by_region(self, region):
        """List available virtual machine sizes within given location

        :param str region: Azure region
        :return: azure.mgmt.compute.models.VirtualMachineSizePaged instance
        """
        return self._compute_client.virtual_machine_sizes.list(location=region)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_resource_group(self, group_name, region, tags):
        """

        :param str group_name:
        :param str region:
        :param dict tags:
        :return:
        """
        return self._resource_client.resource_groups.create_or_update(
            resource_group_name=group_name,
            parameters=ResourceGroup(location=region, tags=tags))

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_resource_group(self, group_name, wait_for_result=False):
        """

        :param str group_name:
        :param str region:
        :return:
        """
        operation_poller = self._resource_client.resource_groups.delete(resource_group_name=group_name)

        if wait_for_result:
            operation_poller.wait()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_storage_account(self, resource_group_name, region, storage_account_name, tags, wait_for_result=False):
        """

        :param str resource_group_name:
        :param str region:
        :param str storage_account_name:
        :param dict tags:
        :param bool wait_for_result:
        :return:
        """
        kind_storage_value = storage_models.Kind.storage
        sku_name = storage_models.SkuName.standard_lrs
        sku = storage_models.Sku(name=sku_name)

        operation_poller = self._storage_client.storage_accounts.create(
            resource_group_name=resource_group_name,
            account_name=storage_account_name,
            parameters=storage_models.StorageAccountCreateParameters(
                sku=sku,
                kind=kind_storage_value,
                location=region,
                tags=tags),
            raw=False)

        if wait_for_result:
            operation_poller.wait()

        return storage_account_name

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_storage_account(self, resource_group_name, storage_account_name, wait_for_result=False):
        """

        :param str resource_group_name:
        :param str storage_account_name:
        :param bool wait_for_result:
        :return:
        """

        operation_poller = self._storage_client.storage_accounts.delete(
            resource_group_name=resource_group_name,
            account_name=storage_account_name)

        if wait_for_result:
            operation_poller.wait()

        return storage_account_name

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def _get_storage_account_key(self, resource_group_name, storage_account_name):
        """Get first storage account access key for some storage

        :param str resource_group_name: name of the resource group on Azure
        :param str storage_account_name: name of the storage on Azure
        :rtype: str
        """
        cache_key = (resource_group_name, storage_account_name)

        if cache_key in self._cached_storage_account_keys:
            return self._cached_storage_account_keys[cache_key]

        account_keys = self._storage_client.storage_accounts.list_keys(resource_group_name, storage_account_name)

        if not account_keys.keys:
            raise Exception(f"Unable to find access key for the storage account '{storage_account_name}' "
                            f"under the '{resource_group_name}' resource group")

        account_key = account_keys.keys[0].value
        self._cached_storage_account_keys[cache_key] = account_key

        return account_key

    def _get_file_service(self, resource_group_name, storage_account_name):
        """Get Azure file service for given storage

        :param str resource_group_name: the name of the resource group on Azure
        :param str storage_account_name: the name of the storage on Azure
        :rtype: azure.storage.file.FileService
        """
        account_key = self._get_storage_account_key(resource_group_name=resource_group_name,
                                                    storage_account_name=storage_account_name)

        return FileService(account_name=storage_account_name, account_key=account_key)

    def _get_blob_service(self, storage_account_name, resource_group_name):
        """Get Azure Blob service for given storage

        :param str resource_group_name: the name of the resource group on Azure
        :param str storage_account_name: the name of the storage on Azure
        :rtype: azure.storage.blob.BlockBlobService
        """
        account_key = self._get_storage_account_key(resource_group_name=resource_group_name,
                                                    storage_account_name=storage_account_name)

        return BlockBlobService(account_name=storage_account_name, account_key=account_key)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_blob(self, blob_name, container_name, resource_group_name, storage_account_name):
        """

        :param blob_name:
        :param container_name:
        :param resource_group_name:
        :param storage_account_name:
        :return:
        """
        blob_service = self._get_blob_service(storage_account_name=storage_account_name,
                                              resource_group_name=resource_group_name)

        blob_service.delete_blob(container_name=container_name, blob_name=blob_name)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_managed_disk(self, disk_name, resource_group_name):
        """

        :param str disk_name:
        :param str resource_group_name:
        :return:
        """
        operation = self._compute_client.disks.delete(resource_group_name=resource_group_name, disk_name=disk_name)
        return operation.wait()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_file(self, resource_group_name, storage_account_name, share_name,
                    directory_name, file_name, file_content):
        """Create file on the Azure

        :param str resource_group_name: name of the resource group on Azure
        :param str storage_account_name: name of the storage on Azure
        :param str share_name: share file name on Azure
        :param str directory_name: directory name for share file name on Azure
        :param str file_name: file name within directory
        :param bytes file_content: file content to be saved
        :return:
        """
        file_service = self._get_file_service(
            resource_group_name=resource_group_name,
            storage_account_name=storage_account_name)

        file_service.create_share(share_name=share_name, fail_on_exist=False)
        file_service.create_file_from_bytes(share_name=share_name,
                                            directory_name=directory_name,
                                            file_name=file_name,
                                            file=file_content)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_file(self, resource_group_name, storage_account_name, share_name, directory_name, file_name):
        """Get file from the Azure

        :param str resource_group_name: name of the resource group on Azure
        :param str storage_account_name: name of the storage on Azure
        :param str share_name: share file name on Azure
        :param str directory_name: directory name for share file name on Azure
        :param str file_name: file name within directory
        :return:
        """
        file_service = self._get_file_service(
            resource_group_name=resource_group_name,
            storage_account_name=storage_account_name)

        return file_service.get_file_to_text(share_name=share_name,
                                             directory_name=directory_name,
                                             file_name=file_name).content

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_network_security_group(self, network_security_group_name, resource_group_name, region, tags):
        """

        :param str network_security_group_name:
        :param str resource_group_name:
        :param str region:
        :param dict tags:
        :return:
        """
        nsg_model = network_models.NetworkSecurityGroup(location=region, tags=tags)

        operation_poller = self._network_client.network_security_groups.create_or_update(
            resource_group_name=resource_group_name,
            network_security_group_name=network_security_group_name,
            parameters=nsg_model)

        return operation_poller.result()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_network_security_group(self, network_security_group_name, resource_group_name):
        """

        :param str network_security_group_name:
        :param str resource_group_name:
        :return:
        """
        return self._network_client.network_security_groups.get(
            resource_group_name=resource_group_name,
            network_security_group_name=network_security_group_name)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_network_security_group(self, network_security_group_name, resource_group_name, wait_for_result=False):
        """

        :param str network_security_group_name:
        :param str resource_group_name:
        :param bool wait_for_result:
        :return:
        """
        operation_poller = self._network_client.network_security_groups.delete(
            resource_group_name=resource_group_name,
            network_security_group_name=network_security_group_name)

        if wait_for_result:
            return operation_poller.wait()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_nsg_rules(self, resource_group_name, nsg_name):
        """

        :param str resource_group_name:
        :param str nsg_name:
        :return:
        """
        return list(self._network_client.security_rules.list(resource_group_name=resource_group_name,
                                                             network_security_group_name=nsg_name))

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_nsg_rule(self, resource_group_name, nsg_name, rule):
        """

        :param str resource_group_name:
        :param str nsg_name: Network Security Group name on the Azure
        :param cloudshell.cp.azure.models.rule_data.RuleData rule:
        :rtype: azure.mgmt.network.models.SecurityRule
        """
        operation_poller = self._network_client.security_rules.create_or_update(
            resource_group_name=resource_group_name,
            network_security_group_name=nsg_name,
            security_rule_name=rule.name,
            security_rule_parameters=rule)

        return operation_poller.result()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_nsg_rule(self, resource_group_name, nsg_name, rule_name, wait_for_result=False):
        """

        :param str resource_group_name:
        :param str nsg_name:
        :param str rule_name:
        :param bool wait_for_result:
        """
        operation_poller = self._network_client.security_rules.delete(
            resource_group_name=resource_group_name,
            network_security_group_name=nsg_name,
            security_rule_name=rule_name)

        if wait_for_result:
            operation_poller.wait()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_subnet(self, subnet_name, cidr, vnet_name, resource_group_name, network_security_group=None,
                      wait_for_result=False):
        """

        :param str subnet_name:
        :param str cidr:
        :param str vnet_name:
        :param str resource_group_name:
        :param network_security_group:
        :param bool wait_for_result:
        """
        operation_poller = self._network_client.subnets.create_or_update(
            resource_group_name=resource_group_name,
            virtual_network_name=vnet_name,
            subnet_name=subnet_name,
            subnet_parameters=network_models.Subnet(
                address_prefix=cidr,
                network_security_group=network_security_group))

        if wait_for_result:
            return operation_poller.result()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_subnet(self, subnet_name, vnet_name, resource_group_name):
        """

        :param str subnet_name:
        :param str vnet_name:
        :param str resource_group_name:
        :return:
        """
        return self._network_client.subnets.get(
            resource_group_name=resource_group_name,
            virtual_network_name=vnet_name,
            subnet_name=subnet_name)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def update_subnet(self, subnet_name, vnet_name, subnet, resource_group_name, wait_for_result=False):
        """

        :param str subnet_name:
        :param str vnet_name:
        :param subnet:
        :param str resource_group_name:
        :param bool wait_for_result:
        :return:
        """
        operation_poller = self._network_client.subnets.create_or_update(
            resource_group_name=resource_group_name,
            virtual_network_name=vnet_name,
            subnet_name=subnet_name,
            subnet_parameters=subnet)

        if wait_for_result:
            return operation_poller.result()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_subnet(self, subnet_name, vnet_name, resource_group_name):
        """

        :param str subnet_name:
        :param str vnet_name:
        :param str resource_group_name:
        :return:
        """
        result = self._network_client.subnets.delete(resource_group_name=resource_group_name,
                                                     virtual_network_name=vnet_name,
                                                     subnet_name=subnet_name)
        result.wait()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def _get_vm_image_latest_version_name(self, region, publisher_name, offer, sku):
        """Get latest version name of the VM image

        :param str region:
        :param str publisher_name:
        :param str offer:
        :param str sku:
        :rtype: str
        """
        image_resources = self._compute_client.virtual_machine_images.list(location=region,
                                                                           publisher_name=publisher_name,
                                                                           offer=offer,
                                                                           skus=sku)
        return image_resources[-1].name

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_latest_virtual_machine_image(self, region, publisher_name, offer, sku):
        """Get latest version of the VM image

        :param str region:
        :param str publisher_name:
        :param str offer:
        :param str sku:
        """
        latest_version = self._get_vm_image_latest_version_name(region=region,
                                                                publisher_name=publisher_name,
                                                                offer=offer,
                                                                sku=sku)

        return self._compute_client.virtual_machine_images.get(location=region,
                                                               publisher_name=publisher_name,
                                                               offer=offer,
                                                               skus=sku,
                                                               version=latest_version)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_custom_virtual_machine_image(self, image_name, resource_group_name):
        """

        :param image_name:
        :param resource_group_name:
        :return:
        """
        return self._compute_client.images.get(resource_group_name=resource_group_name,
                                               image_name=image_name)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_public_ip(self, public_ip_name, resource_group_name, region, public_ip_allocation_method, tags):
        """

        :param public_ip_name:
        :param resource_group_name:
        :param region:
        :param public_ip_allocation_method:
        :param tags:
        :return:
        """
        operation_poller = self._network_client.public_ip_addresses.create_or_update(
            resource_group_name=resource_group_name,
            public_ip_address_name=public_ip_name,
            parameters=network_models.PublicIPAddress(
                location=region,
                public_ip_allocation_method=public_ip_allocation_method,
                idle_timeout_in_minutes=self.CREATE_PUBLIC_IP_TIMEOUT_IN_MINUTES,
                tags=tags
            ),
        )

        return operation_poller.result()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    @retry(stop_max_attempt_number=RETRYABLE_ERROR_MAX_ATTEMPTS, wait_fixed=RETRYABLE_WAIT_TIME,
           retry_on_exception=retry_on_retryable_error)
    def create_network_interface(self, interface_name, resource_group_name, region, subnet,
                                 private_ip_allocation_method, enable_ip_forwarding, network_security_group, tags,
                                 public_ip_address=None, private_ip_address=None):
        """

        :param interface_name:
        :param resource_group_name:
        :param public_ip_address:
        :param region:
        :param subnet:
        :param private_ip_allocation_method:
        :param enable_ip_forwarding:
        :param network_security_group:
        :param tags:
        :param private_ip_address:
        :return:
        """
        ip_config = NetworkInterfaceIPConfiguration(name=self.NETWORK_INTERFACE_IP_CONFIG_NAME,
                                                    private_ip_allocation_method=private_ip_allocation_method,
                                                    subnet=subnet,
                                                    private_ip_address=private_ip_address,
                                                    public_ip_address=public_ip_address)

        network_interface = NetworkInterface(location=region,
                                             network_security_group=network_security_group,
                                             ip_configurations=[ip_config],
                                             enable_ip_forwarding=enable_ip_forwarding,
                                             tags=tags)

        operation_poller = self._network_client.network_interfaces.create_or_update(
            resource_group_name=resource_group_name,
            network_interface_name=interface_name,
            parameters=network_interface)

        return operation_poller.result()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_public_ip(self, public_ip_name, resource_group_name):
        """

        :param public_ip_name:
        :param resource_group_name:
        :return:
        """
        return self._network_client.public_ip_addresses.get(resource_group_name=resource_group_name,
                                                            public_ip_address_name=public_ip_name)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_network_interface(self, interface_name, resource_group_name):
        """

        :param interface_name:
        :param resource_group_name:
        :return:
        """
        return self._network_client.network_interfaces.get(resource_group_name=resource_group_name,
                                                           network_interface_name=interface_name)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_network_interface(self, interface_name, resource_group_name):
        """

        :param interface_name:
        :param resource_group_name:
        :return:
        """
        return self._network_client.network_interfaces.delete(resource_group_name=resource_group_name,
                                                              network_interface_name=interface_name)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    @retry(stop_max_attempt_number=RETRYABLE_ERROR_MAX_ATTEMPTS, wait_fixed=RETRYABLE_WAIT_TIME,
           retry_on_exception=retry_on_retryable_error)
    def create_virtual_machine(self, vm_name, virtual_machine, resource_group_name, wait_for_result=True):
        """

        :param vm_name:
        :param virtual_machine:
        :param resource_group_name:
        :param wait_for_result:
        :return:
        """
        operation_poller = self._compute_client.virtual_machines.create_or_update(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            parameters=virtual_machine)

        if wait_for_result:
            return operation_poller.result()

        return operation_poller

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_linux_vm_script_extension(self, script_file_path, script_config, vm_name, resource_group_name, region,
                                         tags,  wait_for_result=True):
        """

        :param script_file_path:
        :param script_config:
        :param vm_name:
        :param resource_group_name:
        :param region:
        :param tags:
        :param wait_for_result:
        :return:
        """
        file_uris = [file_uri.strip() for file_uri in script_file_path.split(",")]

        vm_extension = VirtualMachineExtension(location=region,
                                               publisher=self.VM_SCRIPT_LINUX_PUBLISHER,
                                               type_handler_version=self.VM_SCRIPT_LINUX_HANDLER_VERSION,
                                               virtual_machine_extension_type=self.VM_SCRIPT_LINUX_EXTENSION_TYPE,
                                               tags=tags,
                                               settings={
                                                   "fileUris": file_uris,
                                                   "commandToExecute": script_config,
                                               })

        operation_poller = self._compute_client.virtual_machine_extensions.create_or_update(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            vm_extension_name=vm_name,
            extension_parameters=vm_extension)

        if wait_for_result:
            return operation_poller.result()

        return operation_poller

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_windows_vm_script_extension(self, script_file_path, script_config, vm_name, resource_group_name, region,
                                           tags,  wait_for_result=True):
        """

        :param script_file_path:
        :param script_config:
        :param vm_name:
        :param resource_group_name:
        :param region:
        :param tags:
        :param wait_for_result:
        :return:
        """
        file_name = script_file_path.split("/")[-1]
        vm_extension = VirtualMachineExtension(location=region,
                                               publisher=self.VM_SCRIPT_WINDOWS_PUBLISHER,
                                               type_handler_version=self.VM_SCRIPT_WINDOWS_HANDLER_VERSION,
                                               virtual_machine_extension_type=self.VM_SCRIPT_WINDOWS_EXTENSION_TYPE,
                                               tags=tags,
                                               settings={
                                                   "fileUris": [script_file_path],
                                                   "commandToExecute": self.VM_SCRIPT_WINDOWS_COMMAND_TPL.format(
                                                       file_name=file_name,
                                                       script_configuration=script_config
                                                   ),
                                               })

        operation_poller = self._compute_client.virtual_machine_extensions.create_or_update(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            vm_extension_name=vm_name,
            extension_parameters=vm_extension)

        if wait_for_result:
            return operation_poller.result()

        return operation_poller

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def get_vm(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        return self._compute_client.virtual_machines.get(vm_name=vm_name, resource_group_name=resource_group_name)

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def start_vm(self, vm_name, resource_group_name, wait_for_result=True):
        """

        :param vm_name:
        :param resource_group_name:
        :param wait_for_result:
        :return:
        """
        operation_poller = self._compute_client.virtual_machines.start(resource_group_name=resource_group_name,
                                                                       vm_name=vm_name)
        if wait_for_result:
            return operation_poller.result()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def stop_vm(self, vm_name, resource_group_name, wait_for_result=True):
        """

        :param vm_name:
        :param resource_group_name:
        :param wait_for_result:
        :return:
        """
        operation_poller = self._compute_client.virtual_machines.deallocate(resource_group_name=resource_group_name,
                                                                            vm_name=vm_name)
        if wait_for_result:
            return operation_poller.result()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_vm(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        result = self._compute_client.virtual_machines.delete(resource_group_name=resource_group_name,
                                                              vm_name=vm_name)
        result.wait()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def delete_public_ip(self, public_ip_name, resource_group_name):
        """

        :param public_ip_name:
        :param resource_group_name:
        :return:
        """
        result = self._network_client.public_ip_addresses.delete(public_ip_address_name=public_ip_name,
                                                                 resource_group_name=resource_group_name)
        result.wait()

    @retry(stop_max_attempt_number=RETRYING_STOP_MAX_ATTEMPT_NUMBER, wait_fixed=RETRYING_WAIT_FIXED,
           retry_on_exception=retry_on_connection_error)
    def create_route_table(self, resource_group_name, route_table_name, route_table):
        """

        :param resource_group_name:
        :param route_table_name:
        :param route_table:
        :return:
        """
        operation_poller = self._network_client.route_tables.create_or_update(resource_group_name=resource_group_name,
                                                                              route_table_name=route_table_name,
                                                                              parameters=route_table)
        return operation_poller.result()
