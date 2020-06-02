from package.cloudshell.cp.azure.actions.network import NetworkActions


class AzureGetAvailablePrivateIPFlow:
    def __init__(self, resource_config, azure_client, cs_ip_pool_manager, reservation_info, logger):
        """

        :param resource_config:
        :param reservation_info:
        :param logging.Logger logger:
        """
        self._resource_config = resource_config
        self._azure_client = azure_client
        self._cs_ip_pool_manager = cs_ip_pool_manager
        self._reservation_info = reservation_info
        self._logger = logger

    def get_available_private_ip(self, subnet_cidr, owner):
        """

        :param str subnet_cidr:
        :param str owner:
        :return:
        """
        resource_group_name = self._reservation_info.get_resource_group_name()

        self._validate_ip_allocation_method(ip_allocation_method=self._resource_config.private_ip_allocation_method)
        self._validate_subnet_exists(subnet_cidr=subnet_cidr, resource_group_name=resource_group_name)

        return self._cs_ip_pool_manager.get_ip_from_pool(reservation_id=self._reservation_info.reservation_id,
                                                         subnet_cidr=subnet_cidr,
                                                         owner=owner)

    def _validate_ip_allocation_method(self, ip_allocation_method):
        """

        :param ip_allocation_method:
        :return:
        """
        if ip_allocation_method != NetworkActions.CLOUDSHELL_PRIVATE_IP_ALLOCATION_METHOD:
            raise Exception(
                f"Get Available Private IP command is supported only when the Cloud Provider "
                f"'Private IP Allocation Method' attribute is set to "
                f"'{NetworkActions.CLOUDSHELL_PRIVATE_IP_ALLOCATION_METHOD}'. Current allocation method is"
                f" '{self._resource_config.private_ip_allocation_method}'")

    def _validate_subnet_exists(self, subnet_cidr, resource_group_name):
        """

        :param subnet_cidr:
        :param resource_group_name:
        :return:
        """
        network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)

        sandbox_vnet = network_actions.get_sandbox_virtual_network(
            resource_group_name=self._resource_config.management_group_name)

        network_actions.get_sandbox_subnet(cidr=subnet_cidr,
                                           vnet_name=sandbox_vnet.name,
                                           resource_group_name=resource_group_name,
                                           mgmt_resource_group_name=self._resource_config.management_group_name)
