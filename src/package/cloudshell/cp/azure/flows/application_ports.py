from package.cloudshell.cp.azure.actions.network_security_group import NetworkSecurityGroupActions


class AzureGetApplicationPortsFlow:
    def __init__(self, resource_config, azure_client, reservation_info, logger):
        """

        :param resource_config:
        :param azure_client:
        :param reservation_info:
        :param logging.Logger logger:
        """
        self._resource_config = resource_config
        self._azure_client = azure_client
        self._reservation_info = reservation_info
        self._logger = logger

    def get_application_ports(self, deployed_app):
        """

        :param deployed_app:
        :return:
        """
        resource_group_name = self._reservation_info.get_resource_group_name()

        nsg_actions = NetworkSecurityGroupActions(azure_client=self._azure_client, logger=self._logger)

        vm_nsg = nsg_actions.get_vm_network_security_group(vm_name=deployed_app.name,
                                                           resource_group_name=resource_group_name)

        result = [f"App Name: {deployed_app.name}",
                  f"Allow Sandbox Traffic: {deployed_app.allow_all_sandbox_traffic}"]

        for rule in vm_nsg.security_rules:
            result.append(f"Port(s): {rule.destination_port_range}, "
                          f"Protocol: {rule.protocol}, "
                          f"Destination: {rule.destination_address_prefix}")

        return "\n".join(result)
