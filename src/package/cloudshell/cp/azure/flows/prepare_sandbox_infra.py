from cloudshell.cp.flows.prepare_sandbox_infra import AbstractPrepareSandboxInfraFlow
from cloudshell.cp.core.models import PrepareCloudInfra, PrepareSubnet

from package.cloudshell.cp.azure.actions.resource_group import ResourceGroupActions
from package.cloudshell.cp.azure.actions.storage_account import StorageAccountActions
from package.cloudshell.cp.azure.actions.ssh_key_pair import SSHKeyPairActions
from package.cloudshell.cp.azure.actions.network_security_group import NetworkSecurityGroupActions
from package.cloudshell.cp.azure.actions.network import NetworkActions

# TODO: run diffenrt commands in threads in the AbstractPrepareSandboxInfraFlow !!!!!!!!!!!!!!!!


class AzurePrepareSandboxInfraFlow(AbstractPrepareSandboxInfraFlow):
    def __init__(self, resource_config, azure_client, reservation_info, logger):
        """

        :param resource_config:
        :param azure_client:
        :param reservation_info:
        :param logger:
        """
        self._resource_config = resource_config
        self._azure_client = azure_client
        self._reservation_info = reservation_info
        self._logger = logger

    def prepare_cloud_infra(self, action):
        """

        :param cloudshell.cp.core.models.PrepareCloudInfra action:
        :return:
        """
        pass

    def _get_private_subnet_actions(self, subnet_actions):
        """

        :param subnet_actions:
        :return:
        """
        # todo: parse all models in normal way, and add correct methods to the model to get private networks
        private_subnet_actions = []
        for subnet_action in subnet_actions:
            try:
                is_private = subnet_action.actionParams.subnetServiceAttributes["Public"] == "False"
            except (AttributeError, TypeError):
                is_private = False

            if is_private:
                private_subnet_actions.append(subnet_action)

        return private_subnet_actions

    def prepare_subnets(self, actions):
        """

        :param list[cloudshell.cp.core.models.PrepareSubnet] actions:
        :return:
        """
        # todo: check that it will create the same subnets as the old Azure shell !!!!!
        # todo: ??? make partial() for all calls, run them in loop and check cancellation context

        resource_group_name = self._reservation_info.get_resource_group_name()
        nsg_name = self._reservation_info.get_network_security_group_name()
        tags = self._reservation_info.get_tags()

        resource_group_actions = ResourceGroupActions(azure_client=self._azure_client,
                                                      logger=self._logger)

        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client,
                                                  logger=self._logger)

        network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)

        resource_group_actions.create_sandbox_resource_group(resource_group_name=resource_group_name,
                                                             region=self._resource_config.region,
                                                             tags=tags)

        nsg_actions.create_sandbox_network_security_group(nsg_name=nsg_name,
                                                          resource_group_name=resource_group_name,
                                                          region=self._resource_config.region,
                                                          tags=tags)

        # todo: fix cancellation context checking - do it in the end of the command !!!

        def action_with_cidr(action):
            # todo: check if we have PrepareCloudInfra there and replace this code !!!!!!!
            #   BUT HERE WE WILL HAVE ONLY PREPATE_SUBNET ACTIONS !!!!!!!!!!!!!!!!!
            return isinstance(action, PrepareCloudInfra) or isinstance(action, PrepareSubnet)

        # Execute prepareNetwork action first
        network_action = next((a for a in actions if action_with_cidr(a)), None)

        if not network_action:
            raise ValueError("Actions list must contain a PrepareNetworkAction.")

        sandbox_cidr = network_action.actionParams.cidr

        # PRIORITY 2xxx:
        # Enable access from sandbox traffic for all subnets. Note that specific VMs can block sandbox traffic using
        # the VM network security group, which is created per VM.
        for action in actions:
            nsg_actions.create_nsg_allow_rule(
                rule_name=f"Allow_Sandbox_Traffic_To_{action.actionParams.cidr.replace('/', '-')}",
                resource_group_name=resource_group_name,
                nsg_name=nsg_name,
                src_address=sandbox_cidr,
                dst_address=action.actionParams.cidr,
                start_from=2000)

        # PRIORITY 2xxx:
        # Block access from internet to private subnets
        for action in self._get_private_subnet_actions(subnet_actions=actions):
            nsg_actions.create_nsg_deny_rule(
                rule_name=f"Deny_Internet_Traffic_To_Private_Subnet_{action.actionParams.cidr.replace('/', '-')}",
                resource_group_name=resource_group_name,
                nsg_name=nsg_name,
                dst_address=action.actionParams.cidr,
                start_from=2000)

        # PRIORITY 4xxx:
        # Allow inbound traffic from additional management networks (can configure on Azure cloud provider resource
        # that additional networks are allowed to communicate with subnets and vms)
        for mgmt_network in self._resource_config.additional_mgmt_networks:
            nsg_actions.create_nsg_allow_rule(
                rule_name=f"Allow_{mgmt_network.replace('/', '-')}_To_{sandbox_cidr.replace('/', '-')}",
                resource_group_name=resource_group_name,
                nsg_name=nsg_name,
                src_address=mgmt_network,
                dst_address=sandbox_cidr,
                start_from=4000)

        mgmt_vnet = network_actions.get_mgmt_virtual_network(
            resource_group_name=self._resource_config.management_group_name)

        sandbox_vnet = network_actions.get_sandbox_virtual_network(
            resource_group_name=self._resource_config.management_group_name)

        mgmt_vnet_cidr = mgmt_vnet.address_space.address_prefixes[0]
        sandbox_vnet_cidr = sandbox_vnet.address_space.address_prefixes[0]

        # PRIORITY 4080:
        # Allow MGMT vNET CIDR inbound traffic. Basically providing access to the infrastructure to manage
        # elements in the sandbox
        nsg_actions.create_nsg_allow_rule(
            rule_name=f"Allow_{mgmt_vnet_cidr.replace('/', '-')}_To_{sandbox_cidr.replace('/', '-')}",
            resource_group_name=resource_group_name,
            nsg_name=nsg_name,
            src_address=mgmt_vnet_cidr,
            dst_address=sandbox_cidr,
            start_from=4080)

        # PRIORITY 4090
        # Deny inbound traffic from Sandbox vNET (the azure account vNET with  which subnets from all sandboxes
        # are associated). The idea is to block traffic from other sandboxes in the account.
        nsg_actions.create_nsg_deny_rule(
            rule_name="Deny_Traffic_From_Other_Sandboxes_To_Sandbox_CIDR",
            resource_group_name=resource_group_name,
            nsg_name=nsg_name,
            src_address=sandbox_vnet_cidr,
            dst_address=sandbox_cidr,
            start_from=4090)

        # Create additional subnets requested by server
        # for action in actions:
        #     logger.warn('creating: ' + subnet.actionParams.cidr)
        #     subnet_name = self.name_provider_service.format_subnet_name(group_name, subnet.actionParams.cidr)
        #     self._create_subnet(cidr=subnet.actionParams.cidr,
        #                         cloud_provider_model=cloud_provider_model,
        #                         logger=logger,
        #                         network_client=network_client,
        #                         resource_client=resource_client,
        #                         network_security_group=sandbox_network_security_group,
        #                         sandbox_vnet=sandbox_vnet,
        #                         subnet_name=subnet_name)
        #     results.append(self._create_result(subnet, subnet_name))

    def create_ssh_keys(self, action):
        """

        :param action:
        :return: SSH Access key
        :rtype: str
        """
        resource_group_name = self._reservation_info.get_resource_group_name()
        storage_account_name = self._reservation_info.get_storage_account_name()
        tags = self._reservation_info.get_tags()

        ssh_actions = SSHKeyPairActions(azure_client=self._azure_client,
                                        logger=self._logger)

        storage_account_actions = StorageAccountActions(azure_client=self._azure_client,
                                                        logger=self._logger)

        storage_account_actions.create_sandbox_storage_account(storage_account_name=storage_account_name,
                                                               resource_group_name=resource_group_name,
                                                               region=self._resource_config.region,
                                                               tags=tags)

        private_key, public_key = ssh_actions.create_ssh_key_pair()

        ssh_actions.save_ssh_public_key(resource_group_name=resource_group_name,
                                        storage_account_name=storage_account_name,
                                        public_key=public_key)

        ssh_actions.save_ssh_private_key(resource_group_name=resource_group_name,
                                         storage_account_name=storage_account_name,
                                         private_key=private_key)

        return private_key

