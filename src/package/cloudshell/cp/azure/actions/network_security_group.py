from azure.mgmt.network.models import RouteNextHopType, SecurityRuleProtocol, SecurityRuleAccess
from azure.mgmt.network.models import SecurityRule


class NetworkSecurityGroupActions:
    VM_NSG_NAME_TPL = "NSG_{vm_name}"
    INBOUND_RULE_DIRECTION = "Inbound"

    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

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
        return self.create_network_security_group(nsg_name=self.VM_NSG_NAME_TPL.format(vm_name=vm_name),
                                                  resource_group_name=resource_group_name,
                                                  region=region,
                                                  tags=tags)

    def get_vm_network_security_group(self, vm_name, resource_group_name):
        """

        :param vm_name:
        :param resource_group_name:
        :return:
        """
        return self.get_network_security_group(nsg_name=self.VM_NSG_NAME_TPL.format(vm_name=vm_name),
                                               resource_group_name=resource_group_name)

    def delete_vm_network_security_group(self, vm_name, resource_group_name):
        """

        :param str vm_name:
        :param str resource_group_name:
        :return:
        """
        self.delete_network_security_group(nsg_name=self.VM_NSG_NAME_TPL.format(vm_name=vm_name),
                                           resource_group_name=resource_group_name)

    def create_nsg_allow_rule(self, rule_name, rule_priority, resource_group_name, nsg_name,
                              src_address=RouteNextHopType.internet, dst_address=RouteNextHopType.internet,
                              src_port_range=SecurityRuleProtocol.asterisk,
                              dst_port_range=SecurityRuleProtocol.asterisk, protocol=SecurityRuleProtocol.asterisk):
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
