from azure.mgmt.network.models import RouteNextHopType, SecurityRuleProtocol, SecurityRuleAccess
from azure.mgmt.network.models import SecurityRule


class NetworkSecurityGroupActions:
    VM_NSG_NAME_TPL = "NSG_{vm_name}"
    INBOUND_RULE_DIRECTION = "Inbound"
    CUSTOM_NSG_RULE_PREFIX = "custom_rule_"
    CUSTOM_NSG_RULE_NAME_TPL = (f"{CUSTOM_NSG_RULE_PREFIX}{{vm_name}}_{{dst_address}}_port:"
                                f"{{dst_port_range}}:{{protocol}}")

    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def prepare_vm_nsg_name(self, vm_name):
        """

        :param str vm_name:
        :return:
        """
        return self.VM_NSG_NAME_TPL.format(vm_name=vm_name)

    def create_network_security_group(self, nsg_name, resource_group_name, region, tags):
        """

        :param str nsg_name:
        :param str resource_group_name:
        :param str region:
        :param dict tags:
        :return:
        """
        self._logger.info(f"Creating network security group {nsg_name}...")
        return self._azure_client.create_network_security_group(
            network_security_group_name=nsg_name,
            resource_group_name=resource_group_name,
            region=region,
            tags=tags)

    def get_network_security_group(self, nsg_name, resource_group_name):
        """

        :param str nsg_name:
        :param str resource_group_name:
        :return:
        """
        self._logger.info(f"Getting network security group {nsg_name}...")
        return self._azure_client.get_network_security_group(
            network_security_group_name=nsg_name,
            resource_group_name=resource_group_name)

    def delete_network_security_group(self, nsg_name, resource_group_name):
        """

        :param str nsg_name:
        :param str resource_group_name:
        :return:
        """
        self._logger.info(f"Deleting network security group {nsg_name}...")
        self._azure_client.delete_network_security_group(
            network_security_group_name=nsg_name,
            resource_group_name=resource_group_name)

    def create_vm_network_security_group(self, vm_name, resource_group_name, region, tags):
        """

        :param vm_name:
        :param resource_group_name:
        :param region:
        :param tags:
        :return:
        """
        return self.create_network_security_group(nsg_name=self.prepare_vm_nsg_name(vm_name=vm_name),
                                                  resource_group_name=resource_group_name,
                                                  region=region,
                                                  tags=tags)

    def get_vm_network_security_group(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        return self.get_network_security_group(nsg_name=self.prepare_vm_nsg_name(vm_name=vm_name),
                                               resource_group_name=resource_group_name)

    def delete_vm_network_security_group(self, vm_name, resource_group_name):
        """

        :param str vm_name:
        :param str resource_group_name:
        :return:
        """
        self.delete_network_security_group(nsg_name=self.prepare_vm_nsg_name(vm_name=vm_name),
                                           resource_group_name=resource_group_name)

    def create_custom_nsg_rule(self, vm_name, rule_priority, resource_group_name, nsg_name, dst_address=None,
                               src_address=None, dst_port_from=None, dst_port_to=None, protocol=None):
        """

        :param vm_name:
        :param rule_priority:
        :param resource_group_name:
        :param nsg_name:
        :param src_address:
        :param dst_address:
        :param dst_port_from:
        :param dst_port_to:
        :param protocol:
        :return:
        """
        if all([dst_port_from is None, dst_port_to is None]):
            dst_port_range = SecurityRuleProtocol.asterisk
        else:
            dst_port_range = dst_port_from if dst_port_from == dst_port_to else f"{dst_port_from}-{dst_port_to}"

        dst_address = dst_address or RouteNextHopType.internet
        protocol = protocol or SecurityRuleProtocol.asterisk
        src_address = src_address or RouteNextHopType.internet

        rule_name = self.CUSTOM_NSG_RULE_NAME_TPL.format(vm_name=vm_name,
                                                         dst_address=dst_address,
                                                         dst_port_range=dst_port_range,
                                                         protocol=protocol)

        return self.create_nsg_allow_rule(rule_name=rule_name,
                                          rule_priority=rule_priority,
                                          resource_group_name=resource_group_name,
                                          nsg_name=nsg_name,
                                          src_address=src_address,
                                          dst_address=dst_address,
                                          dst_port_range=dst_port_range,
                                          protocol=protocol)

    def create_nsg_allow_rule(self, rule_name, rule_priority, resource_group_name, nsg_name,
                              src_address=RouteNextHopType.internet,
                              dst_address=RouteNextHopType.internet,
                              src_port_range=SecurityRuleProtocol.asterisk,
                              dst_port_range=SecurityRuleProtocol.asterisk,
                              protocol=SecurityRuleProtocol.asterisk):
        """

        :param str rule_name:
        :param str rule_priority:
        :param str resource_group_name:
        :param str nsg_name:
        :param str src_address:
        :param str dst_address:
        :param str src_port_range:
        :param str dst_port_range:
        :param str protocol:
        :return:
        """
        self._logger.info(f"Creating security rule {rule_name} on NSG {nsg_name}...")

        rule = SecurityRule(
            name=rule_name,
            access=SecurityRuleAccess.allow,
            direction=self.INBOUND_RULE_DIRECTION,
            source_address_prefix=src_address,
            source_port_range=src_port_range,
            destination_address_prefix=dst_address,
            destination_port_range=dst_port_range,
            priority=rule_priority,
            protocol=protocol)

        self._azure_client.create_nsg_rule(
            resource_group_name=resource_group_name,
            nsg_name=nsg_name,
            rule=rule)

    def create_nsg_deny_rule(self, rule_name, rule_priority, resource_group_name, nsg_name,
                             src_address=RouteNextHopType.internet, dst_address=RouteNextHopType.internet,
                             src_port_range=SecurityRuleProtocol.asterisk,
                             dst_port_range=SecurityRuleProtocol.asterisk):
        """

        :param str rule_name:
        :param str rule_priority:
        :param str resource_group_name:
        :param str nsg_name:
        :param str src_address:
        :param str dst_address:
        :param str src_port_range:
        :param str dst_port_range:
        :return:
        """
        self._logger.info(f"Creating security rule {rule_name} on NSG {nsg_name}...")

        rule = SecurityRule(
            name=rule_name,
            access=SecurityRuleAccess.deny,
            direction=self.INBOUND_RULE_DIRECTION,
            source_address_prefix=src_address,
            source_port_range=src_port_range,
            destination_address_prefix=dst_address,
            destination_port_range=dst_port_range,
            priority=rule_priority,
            protocol=SecurityRuleProtocol.asterisk)

        self._azure_client.create_nsg_rule(
            resource_group_name=resource_group_name,
            nsg_name=nsg_name,
            rule=rule)

    def delete_nsg_rule(self, rule_name, nsg_name, resource_group_name):
        """

        :param str rule_name:
        :param str nsg_name:
        :param str resource_group_name:
        :return:
        """
        self._logger.info(f"Deleting security rule {rule_name} on NSG {nsg_name}...")
        self._azure_client.delete_nsg_rule(resource_group_name=resource_group_name,
                                           nsg_name=nsg_name,
                                           rule_name=rule_name)

    def get_nsg_rules(self, nsg_name, resource_group_name):
        """

        :param str nsg_name:
        :param str resource_group_name:
        :return:
        """
        return self._azure_client.get_nsg_rules(resource_group_name=resource_group_name, nsg_name=nsg_name)

    def delete_custom_nsg_rules(self, nsg_name, resource_group_name):
        """

        :param str nsg_name:
        :param str resource_group_name:
        :return:
        """
        all_rules = self.get_nsg_rules(nsg_name=nsg_name, resource_group_name=resource_group_name)

        for rule in (rule for rule in all_rules if rule.name.startswith(self.CUSTOM_NSG_RULE_PREFIX)):
            self.delete_nsg_rule(rule_name=rule.name,
                                 nsg_name=nsg_name,
                                 resource_group_name=resource_group_name)
