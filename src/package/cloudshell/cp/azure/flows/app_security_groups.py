from cloudshell.cp.core.flows.app_security_groups import AbstractAppSecurityGroupsFlow
from requests.utils import is_valid_cidr

from package.cloudshell.cp.azure.actions.network import NetworkActions
from package.cloudshell.cp.azure.actions.network_security_group import NetworkSecurityGroupActions
from package.cloudshell.cp.azure.actions.vm import VMActions
from package.cloudshell.cp.azure.utils.azure_name_parser import get_name_from_resource_id
from package.cloudshell.cp.azure.utils.nsg_rules_priority_generator import NSGRulesPriorityGenerator


class AzureAppSecurityGroupsFlow(AbstractAppSecurityGroupsFlow):
    def __init__(self, resource_config, reservation_info, azure_client, lock_manager, logger):
        """

        :param resource_config:
        :param reservation_info:
        :param azure_client:
        :param logging.Logger logger:
        """
        super().__init__(logger=logger)
        self._resource_config = resource_config
        self._reservation_info = reservation_info
        self._azure_client = azure_client
        self._lock_manager = lock_manager

    def _get_sandbox_subnet_name(self, subnet_id, resource_group_name):
        """

        :param str subnet_id:
        :param str resource_group_name:
        :return:
        """
        network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)

        # if in a single subnet scenario (default subnet), the subnet id will be
        # a simple CIDR that looks like this: 10.0.3.0/24
        if is_valid_cidr(subnet_id):
            return network_actions.prepare_sandbox_subnet_name(resource_group_name=resource_group_name, cidr=subnet_id)

        # if in multiple subnets mode, a subnet id will look like this:
        # *4032ffa7-ada9-4ee4-9d33-70ce3c1b06e1_10.0.3.0-24
        return get_name_from_resource_id(subnet_id)

    def _get_private_ip_by_subnet_map(self, vm_name, resource_group_name):
        """

        :param str vm_name:
        :param str resource_group_name:
        :rtype: dict[str, str]
        """
        network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)
        vm_actions = VMActions(azure_client=self._azure_client, logger=self._logger)

        vm = vm_actions.get_vm(vm_name=vm_name, resource_group_name=resource_group_name)

        private_ip_map = {}
        for interface_ref in vm.network_profile.network_interfaces:
            interface = network_actions.get_vm_network(interface_name=get_name_from_resource_id(interface_ref.id),
                                                       resource_group_name=resource_group_name)

            ip_configuration = interface.ip_configurations[0]
            subnet_name = get_name_from_resource_id(ip_configuration.subnet.id)
            private_ip_map[subnet_name] = ip_configuration.private_ip_address

        return private_ip_map

    def _set_app_security_group(self, security_group):
        """"

        :param security_group:
        :return
        """
        resource_group_name = self._reservation_info.get_resource_group_name()
        vm_name = security_group.deployed_app.name

        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)
        vm_nsg_name = nsg_actions.prepare_vm_nsg_name(vm_name=vm_name)

        private_ips_map = self._get_private_ip_by_subnet_map(vm_name=vm_name,
                                                             resource_group_name=resource_group_name)

        with self._lock_manager.get_lock(vm_nsg_name):
            nsg_actions.delete_custom_nsg_rules(nsg_name=vm_nsg_name, resource_group_name=resource_group_name)

            rules_priority_generator = NSGRulesPriorityGenerator(nsg_name=vm_nsg_name,
                                                                 resource_group_name=resource_group_name,
                                                                 include_existing_rules=True,
                                                                 nsg_actions=nsg_actions)

            for security_group_config in security_group.security_group_configs:
                subnet_name = self._get_sandbox_subnet_name(subnet_id=security_group_config.subnet_id,
                                                            resource_group_name=resource_group_name)

                dst_ip_address = private_ips_map.get(subnet_name)
                for rule in security_group_config.rules:
                    nsg_actions.create_custom_nsg_rule(
                        vm_name=vm_name,
                        resource_group_name=resource_group_name,
                        nsg_name=vm_nsg_name,
                        src_address=rule.source,
                        dst_address=dst_ip_address,
                        dst_port_from=rule.from_port,
                        dst_port_to=rule.to_port,
                        protocol=rule.protocol,
                        rule_priority=rules_priority_generator.get_priority())
