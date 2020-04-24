from cloudshell.cp.flows.prepare_sandbox_infra import AbstractPrepareSandboxInfraFlow

from package.cloudshell.cp.azure.actions.resource_group import ResourceGroupActions
from package.cloudshell.cp.azure.actions.storage_account import StorageAccountActions
from package.cloudshell.cp.azure.actions.ssh_key_pair import SSHKeyPairActions
from package.cloudshell.cp.azure.actions.network_security_group import NetworkSecurityGroupActions
from package.cloudshell.cp.azure.actions.network import NetworkActions
from package.cloudshell.cp.azure.flows.prepare_sandbox_infra import commands
from package.cloudshell.cp.azure.utils.rollback import RollbackCommandsManager


# TODO: run different commands in threads !!!!!!!!!!!!!!!!
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
                tags=tags,
            ).execute()

            nsg = commands.CreateNSGCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                nsg_name=nsg_name,
                resource_group_name=resource_group_name,
                region=self._resource_config.region,
                tags=tags,
            ).execute()

            self._create_nsg_rules(request_actions=request_actions,
                                   network_actions=network_actions,
                                   nsg_actions=nsg_actions,
                                   resource_group_name=resource_group_name,
                                   nsg_name=nsg_name)

            self._create_subnets(request_actions=request_actions,
                                 network_actions=network_actions,
                                 resource_group_name=resource_group_name,
                                 network_security_group=nsg)

    def _create_nsg_rules(self, request_actions, network_actions, nsg_actions, resource_group_name, nsg_name):
        """

        :param request_actions:
        :param network_actions:
        :param nsg_actions:
        :param resource_group_name:
        :param nsg_name:
        :return:
        """
        for action in request_actions.prepare_subnets:
            commands.CreateAllowSandboxTrafficToSubnetRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                nsg_name=nsg_name,
                resource_group_name=resource_group_name,
                sandbox_cidr=request_actions.sandbox_cidr,
                subnet_cidr=action.get_cidr(),
            ).execute()

        for action in request_actions.prepare_private_subnets:
            commands.CreateDenyAccessToPrivateSubnetRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                nsg_name=nsg_name,
                resource_group_name=resource_group_name,
                sandbox_cidr=request_actions.sandbox_cidr,
                subnet_cidr=action.get_cidr(),
            ).execute()

        # todo: we need to use one priority generator here !!!
        for mgmt_network in self._resource_config.additional_mgmt_networks:
            commands.CreateAdditionalMGMTNetworkRuleCommand(
                rollback_manager=self._rollback_manager,
                cancellation_manager=self._cancellation_manager,
                nsg_actions=nsg_actions,
                nsg_name=nsg_name,
                resource_group_name=resource_group_name,
                mgmt_network=mgmt_network,
                sandbox_cidr=request_actions.sandbox_cidr,
            ).execute()

        commands.CreateAllowMGMTVnetRuleCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            mgmt_resource_group_name=self._resource_config.management_group_name,
            resource_group_name=resource_group_name,
            network_actions=network_actions,
            nsg_actions=nsg_actions,
            nsg_name=nsg_name,
            sandbox_cidr=request_actions.sandbox_cidr,
        ).execute()

        commands.CreateDenyTrafficFromOtherSandboxesRuleCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            mgmt_resource_group_name=self._resource_config.management_group_name,
            resource_group_name=resource_group_name,
            network_actions=network_actions,
            nsg_actions=nsg_actions,
            sandbox_cidr=request_actions.sandbox_cidr,
            nsg_name=nsg_name,
        ).execute()

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
                mgmt_resource_group_name=self._resource_config.management_group_name,
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
