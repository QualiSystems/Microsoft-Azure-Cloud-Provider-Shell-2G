from cloudshell.cp.flows.prepare_sandbox_infra import AbstractPrepareSandboxInfraFlow

from package.cloudshell.cp.azure.actions.resource_group import ResourceGroupActions
from package.cloudshell.cp.azure.actions.storage_account import StorageAccountActions
from package.cloudshell.cp.azure.actions.ssh_key_pair import SSHKeyPairActions
from package.cloudshell.cp.azure.actions.network_security_group import NetworkSecurityGroupActions
from package.cloudshell.cp.azure.actions.network import NetworkActions
from package.cloudshell.cp.azure.flows.prepare_sandbox_infra import commands
from package.cloudshell.cp.azure.utils.rollback import RollbackCommandsManager


# TODO: run different commands in threads in the AbstractPrepareSandboxInfraFlow !!!!!!!!!!!!!!!!
class AzurePrepareSandboxInfraFlow(AbstractPrepareSandboxInfraFlow):
    def __init__(self, resource_config, azure_client, reservation_info, cancellation_manager, logger):
        """

        :param resource_config:
        :param azure_client:
        :param reservation_info:
        :param cancellation_manager:
        :param logger:
        """
        super().__init__(resource_config=resource_config, logger=logger)
        self._azure_client = azure_client
        self._reservation_info = reservation_info
        self._cancellation_manager = cancellation_manager
        self._rollback_manager = RollbackCommandsManager(logger=self._logger)

    def prepare_cloud_infra(self, request_actions):
        pass

    def _create_default_nsg_allow_rules(self, request_actions, nsg_actions, resource_group_name, nsg_name):
        """Create default NSG allow rules

        PRIORITY 2xxx:
            Enable access from sandbox traffic for all subnets. Note that specific VMs can block sandbox traffic using
            the VM network security group, which is created per VM.
        :param request_actions:
        :param nsg_actions:
        :param resource_group_name:
        :param nsg_name:
        :return:
        """
        for action in request_actions.prepare_subnets:
            commands.CreateNSGAllowRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                rule_name=f"Allow_Sandbox_Traffic_To_{action.actionParams.cidr.replace('/', '-')}",
                resource_group_name=resource_group_name,
                nsg_name=nsg_name,
                src_address=request_actions.sandbox_cidr,
                dst_address=action.get_cidr(),
                # todo: add constants for these values !!!
                start_from=2000,
            ).execute()

    def _create_default_nsg_deny_rules(self, request_actions, nsg_actions, resource_group_name, nsg_name):
        """"Create default NSG block rules

        PRIORITY 2xxx:
            Block access from internet to the private subnets
        :return:
        """
        for action in request_actions.prepare_private_subnet_actions:
            commands.CreateNSGDenyRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                rule_name=f"Deny_Internet_Traffic_To_Private_Subnet_{action.actionParams.cidr.replace('/', '-')}",
                resource_group_name=resource_group_name,
                nsg_name=nsg_name,
                # todo: create model for action with get_cidr method
                dst_address=action.get_cidr(),
                start_from=2000,
            ).execute()

    def _create_nsg_rulles_for_additional_mgmt_networks(self, resource_group_name, nsg_actions, nsg_name, sandbox_cidr):
        """Create NSG Allow rules for the Additional MGMT networks

        PRIORITY 4xxx:
            Allow inbound traffic from additional management networks (can configure on Azure cloud provider resource
            that additional networks are allowed to communicate with subnets and vms)
        :param str resource_group_name:
        :param str nsg_name:
        :param str sandbox_cidr:
        :return:
        """
        for mgmt_network in self._resource_config.additional_mgmt_networks:
            commands.CreateNSGAllowRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                rule_name=f"Allow_{mgmt_network.replace('/', '-')}_To_{sandbox_cidr.replace('/', '-')}",
                resource_group_name=resource_group_name,
                nsg_name=nsg_name,
                src_address=mgmt_network,
                dst_address=sandbox_cidr,
                # todo: add constants for these values !!!
                start_from=4000,
            ).execute()

    def _create_nsg_rule_allow_mgmt_vnet_to_sandbox(self, request_actions, network_actions, nsg_actions,
                                                    resource_group_name, nsg_name):
        """

        PRIORITY 4080:
            Allow MGMT vNET CIDR inbound traffic. Basically providing access to the infrastructure to manage
            elements in the sandbox
        :param request_actions:
        :param resource_group_name:
        :param nsg_name:
        :return:
        """
        commands.CreateNSGAllowMGMTVnetRuleCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            management_group_name=self._resource_config.management_group_name,
            resource_group_name=resource_group_name,
            network_actions=network_actions,
            nsg_actions=nsg_actions,
            nsg_name=nsg_name,
            sandbox_cidr=request_actions.sandbox_cidr,
            start_from=4080,
        ).execute()

    def _create_nsg_rule_deny_traffic_from_other_sandboxes(self, request_actions, network_actions, nsg_actions,
                                                           resource_group_name, nsg_name):
        """

        PRIORITY 4090
            Deny inbound traffic from Sandbox vNET (the azure account vNET with which subnets from all sandboxes
            are associated). The idea is to block traffic from other sandboxes in the account.
        :return:
        """
        commands.CreateNSGDenyTrafficFromOtherSandboxesRuleCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            management_group_name=self._resource_config.management_group_name,
            resource_group_name=resource_group_name,
            network_actions=network_actions,
            nsg_actions=nsg_actions,
            nsg_name=nsg_name,
            sandbox_cidr=request_actions.sandbox_cidr,
            start_from=4090,
        ).execute()

    def prepare_subnets(self, request_actions):
        """

        :param request_actions:
        :return:
        """
        resource_group_name = self._reservation_info.get_resource_group_name()
        nsg_name = self._reservation_info.get_network_security_group_name()
        tags = self._reservation_info.get_tags()

        resource_group_actions = ResourceGroupActions(azure_client=self._azure_client, logger=self._logger)
        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)
        network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)

        with self._rollback_manager:
            commands.CreateResourceGroupCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                resource_group_actions=resource_group_actions,
                resource_group_name=resource_group_name,
                region=self._resource_config.region,
                tags=tags).execute()

            nsg = commands.CreateNSGCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                nsg_name=nsg_name,
                resource_group_name=resource_group_name,
                region=self._resource_config.region,
                tags=tags).execute()

            self._create_default_nsg_allow_rules(request_actions=request_actions,
                                                 nsg_actions=nsg_actions,
                                                 resource_group_name=resource_group_name,
                                                 nsg_name=nsg_name)

            self._create_default_nsg_deny_rules(request_actions=request_actions,
                                                nsg_actions=nsg_actions,
                                                resource_group_name=resource_group_name,
                                                nsg_name=nsg_name)

            self._create_nsg_rulles_for_additional_mgmt_networks(resource_group_name=resource_group_name,
                                                                 nsg_actions=nsg_actions,
                                                                 nsg_name=nsg_name,
                                                                 sandbox_cidr=request_actions.sandbox_cidr)

            self._create_nsg_rule_allow_mgmt_vnet_to_sandbox(request_actions=request_actions,
                                                             network_actions=network_actions,
                                                             nsg_actions=nsg_actions,
                                                             resource_group_name=resource_group_name,
                                                             nsg_name=nsg_name)

            self._create_nsg_rule_deny_traffic_from_other_sandboxes(request_actions=request_actions,
                                                                    network_actions=network_actions,
                                                                    nsg_actions=nsg_actions,
                                                                    resource_group_name=resource_group_name,
                                                                    nsg_name=nsg_name)

            self._create_subnets(request_actions=request_actions,
                                 network_actions=network_actions,
                                 resource_group_name=resource_group_name,
                                 network_security_group=nsg)

    def _create_subnets(self, request_actions, network_actions, resource_group_name, network_security_group):
        """Create additional subnets requested by server

        :param request_actions:
        :param resource_group_name:
        :param network_security_group:
        :return:
        """
        with self._cancellation_manager:
            sandbox_vnet = network_actions.get_sandbox_virtual_network(
                resource_group_name=self._resource_config.management_group_name)

        for subnet_action in request_actions.prepare_subnets:
            commands.CreateSubnetCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                network_actions=network_actions,
                cidr=subnet_action.get_cidr(),
                vnet=sandbox_vnet,
                resource_group_name=resource_group_name,
                management_group_name=self._resource_config.management_group_name,
                network_security_group=network_security_group,
            ).execute()

    def create_ssh_keys(self, request_actions):
        """

        :param request_actions:
        :return: SSH Access key
        :rtype: str
        """
        resource_group_name = self._reservation_info.get_resource_group_name()
        storage_account_name = self._reservation_info.get_storage_account_name()
        tags = self._reservation_info.get_tags()

        ssh_actions = SSHKeyPairActions(azure_client=self._azure_client,
                                        logger=self._logger)

        storage_actions = StorageAccountActions(azure_client=self._azure_client,
                                                logger=self._logger)

        with self._rollback_manager:
            commands.CreateSandboxStorageAccountCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                storage_actions=storage_actions,
                storage_account_name=storage_account_name,
                resource_group_name=resource_group_name,
                region=self._resource_config.region,
                tags=tags).execute()

            private_key, public_key = ssh_actions.create_ssh_key_pair()

            commands.SaveSSHPublicKeyCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                storage_account_name=storage_account_name,
                resource_group_name=resource_group_name,
                public_key=public_key,
                ssh_actions=ssh_actions).execute()

            commands.SaveSSHPrivateKeyCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                storage_account_name=storage_account_name,
                resource_group_name=resource_group_name,
                private_key=private_key,
                ssh_actions=ssh_actions).execute()

        return private_key
