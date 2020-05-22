from azure.mgmt.network.models import RouteNextHopType, SecurityRuleProtocol, SecurityRuleAccess
from azure.mgmt.network.models import SecurityRule


class NetworkSecurityGroupActions:
    RULE_DEFAULT_PRIORITY = 1000
    RULE_PRIORITY_INCREASE_STEP = 5
    VM_NSG_NAME_TPL = "NSG_{vm_name}"

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
        self.get_network_security_group(nsg_name=self.VM_NSG_NAME_TPL.format(vm_name=vm_name),
                                        resource_group_name=resource_group_name)

    def delete_vm_network_security_group(self, vm_name, resource_group_name):
        """

        :param str vm_name:
        :param str resource_group_name:
        :return:
        """
        self.delete_network_security_group(nsg_name=self.VM_NSG_NAME_TPL.format(vm_name=vm_name),
                                           resource_group_name=resource_group_name)

    def get_rule_priority_generator(self, resource_group_name, nsg_name, start_from=None):
        """Endless priority generator for NSG rules

        :param str resource_group_name:
        :param str nsg_name:
        :param int start_from: rule priority number to start from
        :return: priority generator => (int) next available priority
        """
        existing_rules = self._azure_client.get_nsg_rules(resource_group_name=resource_group_name,
                                                          nsg_name=nsg_name)

        # TODO: check and refactor this method
        if start_from is None:
            start_from = self.RULE_DEFAULT_PRIORITY

        existing_priorities = [rule.priority for rule in existing_rules]
        start_limit = start_from - self.RULE_PRIORITY_INCREASE_STEP
        end_limit = float("inf")
        existing_priorities.extend([start_limit, end_limit])

        relevant_existing_priorities = [ep for ep in existing_priorities if ep >= start_limit]
        relevant_existing_priorities = sorted(relevant_existing_priorities)

        i = 0
        while True:
            priority = relevant_existing_priorities[i] + self.RULE_PRIORITY_INCREASE_STEP
            if relevant_existing_priorities[i + 1] > priority:
                relevant_existing_priorities.insert(i + 1, priority)
                yield priority

            i += 1

    def create_nsg_allow_rule(self, rule_name, resource_group_name, nsg_name, src_address=RouteNextHopType.internet,
                              dst_address=RouteNextHopType.internet, src_port_range=SecurityRuleProtocol.asterisk,
                              dst_port_range=SecurityRuleProtocol.asterisk, protocol=SecurityRuleProtocol.asterisk,
                              rule_priority_generator=None, start_from=None):
        """

        :param str rule_name:
        :param str resource_group_name:
        :param str nsg_name:
        :param str src_address:
        :param str dst_address:
        :param str src_port_range:
        :param str dst_port_range:
        :param rule_priority_generator:
        :param str protocol:
        :param int start_from:
        :return:
        """
        # todo: do we really need Lock for priority_rule_generator here???? it will be created only once
        #  for the only one NSG in reservation during the prepare_connectivuty action !!!??? -- seems that it
        #  also used in the deploy actions - there might be dozen of simultauso deployments in the one reservation
        self._logger.info(f"Creating security rule {rule_name} on NSG {nsg_name}...")
        # todo: deal with rule_priority_generator in some better way
        if rule_priority_generator is None:
            rule_priority_generator = self.get_rule_priority_generator(resource_group_name=resource_group_name,
                                                                       nsg_name=nsg_name,
                                                                       start_from=start_from)

        rule = SecurityRule(
            name=rule_name,
            access=SecurityRuleAccess.allow,
            direction="Inbound",
            source_address_prefix=src_address,
            source_port_range=src_port_range,
            destination_address_prefix=dst_address,
            destination_port_range=dst_port_range,
            priority=next(rule_priority_generator),
            protocol=protocol)

        self._azure_client.create_nsg_rule(
            resource_group_name=resource_group_name,
            nsg_name=nsg_name,
            rule=rule)

    def create_nsg_deny_rule(self, rule_name, resource_group_name, nsg_name, src_address=RouteNextHopType.internet,
                             dst_address=RouteNextHopType.internet, src_port_range=SecurityRuleProtocol.asterisk,
                             dst_port_range=SecurityRuleProtocol.asterisk, rule_priority_generator=None,
                             start_from=None):
        """

        :param str rule_name:
        :param str resource_group_name:
        :param str nsg_name:
        :param str src_address:
        :param str dst_address:
        :param str src_port_range:
        :param str dst_port_range:
        :param rule_priority_generator:
        :param int start_from:
        :return:
        """
        # todo: do we really need Lock for priority_rule_generator here???? it will be created only once
        #  for the only one NSG in reservation during the prepare_connectivuty action !!!??? -- seems that it
        #  also used in the deploy actions - there might be dozen of simultauso deployments in the one reservation
        self._logger.info(f"Creating security rule {rule_name} on NSG {nsg_name}...")
        if rule_priority_generator is None:
            rule_priority_generator = self.get_rule_priority_generator(resource_group_name=resource_group_name,
                                                                       nsg_name=nsg_name,
                                                                       start_from=start_from)
        rule = SecurityRule(
            name=rule_name,
            access=SecurityRuleAccess.deny,
            direction="Inbound",
            source_address_prefix=src_address,
            source_port_range=src_port_range,
            destination_address_prefix=dst_address,
            destination_port_range=dst_port_range,
            priority=next(rule_priority_generator),
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
