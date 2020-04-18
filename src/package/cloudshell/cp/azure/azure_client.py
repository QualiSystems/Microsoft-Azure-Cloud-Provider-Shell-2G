from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.file import FileService
from azure.mgmt.resource.resources.models import ResourceGroup
from azure.mgmt.storage import models as storage_models
from azure.mgmt.network import models as network_models
from msrestazure.azure_active_directory import ServicePrincipalCredentials
from retrying import retry

from package.cloudshell.cp.azure.utils.retrying import retry_on_connection_error


class AzureAPIClient:
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

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def get_available_regions(self):
        """List all available regions per subscription

        :rtype: list[azure.mgmt.resource.subscriptions.models.Location]
        """
        locations = self._subscription_client.subscriptions.list_locations(self._azure_subscription_id)
        return list(locations)

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def register_provider(self, provider):
        """

        :param str provider:
        :return:
        """
        self._resource_client.providers.register(provider)

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def get_resource_group(self, resource_group_name):
        """

        :param str resource_group_name:
        :return:
        """
        return self._resource_client.resource_groups.get(resource_group_name=resource_group_name)

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def get_virtual_networks_by_resource_group(self, resource_group_name):
        """

        :param str resource_group_name:
        :return: list of vNets in group
        :rtype: list[VirtualNetwork]
        """
        networks_list = self._network_client.virtual_networks.list(resource_group_name)
        return list(networks_list)

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def get_virtual_machine_sizes_by_region(self, region):
        """List available virtual machine sizes within given location

        :param str region: Azure region
        :return: azure.mgmt.compute.models.VirtualMachineSizePaged instance
        """
        return self._compute_client.virtual_machine_sizes.list(location=region)

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
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

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def create_storage_account(self, resource_group_name, region, storage_account_name, tags, wait_until_created=False):
        """

        :param str resource_group_name:
        :param str region:
        :param str storage_account_name:
        :param dict tags:
        :param bool wait_until_created:
        :return:
        """
        kind_storage_value = storage_models.Kind.storage
        sku_name = storage_models.SkuName.standard_lrs
        sku = storage_models.Sku(name=sku_name)

        create_account_task = self._storage_client.storage_accounts.create(
            resource_group_name=resource_group_name,
            account_name=storage_account_name,
            parameters=storage_models.StorageAccountCreateParameters(
                sku=sku,
                kind=kind_storage_value,
                location=region,
                tags=tags),
            raw=False)

        if wait_until_created:
            create_account_task.wait()

        return storage_account_name

    @retry(stop_max_attempt_number=20, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def _get_storage_account_key(self, group_name, storage_name):
        """Get first storage account access key for some storage

        :param str group_name: name of the resource group on Azure
        :param str storage_name: name of the storage on Azure
        :rtype: str
        """
        account_keys = self._storage_client.storage_accounts.list_keys(group_name, storage_name)
        for account_key in account_keys.keys:
            return account_key.value

        raise Exception(f"Unable to find access key for the storage account '{storage_name}' "
                        f"under the '{group_name}' resource group")

    def _get_file_service(self, group_name, storage_name):
        """Get Azure file service for given storage

        :param str group_name: the name of the resource group on Azure
        :param str storage_name: the name of the storage on Azure
        :return: azure.storage.file.FileService instance
        """
        account_key = self._get_storage_account_key(group_name=group_name,
                                                    storage_name=storage_name)

        return FileService(account_name=storage_name, account_key=account_key)

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def create_file(self, group_name, storage_name, share_name,
                    directory_name, file_name, file_content):
        """Create file on the Azure

        :param str group_name: name of the resource group on Azure
        :param str storage_name: name of the storage on Azure
        :param str share_name: share file name on Azure
        :param str directory_name: directory name for share file name on Azure
        :param str file_name: file name within directory
        :param bytes file_content: file content to be saved
        :return:
        """
        file_service = self._get_file_service(
            group_name=group_name,
            storage_name=storage_name)

        file_service.create_share(share_name=share_name, fail_on_exist=False)
        file_service.create_file_from_bytes(share_name=share_name,
                                            directory_name=directory_name,
                                            file_name=file_name,
                                            file=file_content)

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def create_network_security_group(self, network_security_group_name, resource_group_name, region, tags):
        """

        :param str network_security_group_name:
        :param str resource_group_name:
        :param str region:
        :param dict tags:
        :return:
        """
        nsg_model = network_models.NetworkSecurityGroup(location=region, tags=tags)

        create_nsg_task = self._network_client.network_security_groups.create_or_update(
            resource_group_name=resource_group_name,
            network_security_group_name=network_security_group_name,
            parameters=nsg_model)

        return create_nsg_task.result()

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def get_nsg_rules(self, resource_group_name, nsg_name):
        """

        :param str resource_group_name:
        :param str nsg_name:
        :return:
        """
        return list(self._network_client.security_rules.list(resource_group_name=resource_group_name,
                                                             network_security_group_name=nsg_name))

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
    def create_nsg_rule(self, resource_group_name, nsg_name, rule):
        """Create NSG inbound rule on the Azure

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

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
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

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
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

    @retry(stop_max_attempt_number=5, wait_fixed=2000, retry_on_exception=retry_on_connection_error)
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
