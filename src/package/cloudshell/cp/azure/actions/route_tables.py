from azure.mgmt.network.models import RouteTable, Route


class RouteTablesActions:
    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def create_route_table(self, resource_group_name, route_table_name, region, route_table):
        """

        :param str resource_group_name:
        :param str route_table_name:
        :param str region:
        :param route_table:
        :return:
        """
        self._logger.info(f"Creating Route Table: {route_table_name}")
        route_table = RouteTable(location=region,
                                 routes=[Route(name=route.name,
                                               next_hop_ip_address=route.next_hop_address,
                                               next_hop_type=route.next_hop_type,
                                               address_prefix=route.address_prefix) for route in route_table.routes])

        return self._azure_client.create_route_table(resource_group_name=resource_group_name,
                                                     route_table_name=route_table_name,
                                                     route_table=route_table)
