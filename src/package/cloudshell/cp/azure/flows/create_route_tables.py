from package.cloudshell.cp.azure.actions.network import NetworkActions
from package.cloudshell.cp.azure.actions.route_tables import RouteTablesActions
from package.cloudshell.cp.azure.utils.cs_reservation_output import CloudShellReservationOutput


class CreateRouteTablesFlow:
    def __init__(self, resource_config, reservation_info, azure_client, cs_api, logger):
        """

        :param resource_config:
        :param reservation_info:
        :param azure_client:
        :param cs_api:
        :param logging.Logger logger:
        """
        self._resource_config = resource_config
        self._reservation_info = reservation_info
        self._azure_client = azure_client
        self._cs_api = cs_api
        self._logger = logger
        self._cs_reservation_output = CloudShellReservationOutput(cs_api=self._cs_api,
                                                                  reservation_id=self._reservation_info.reservation_id,
                                                                  logger=self._logger)

    def _find_sandbox_subnet(self, sandbox_vnet, subnet_name):
        """

        :param sandbox_vnet:
        :param subnet_name:
        :return:
        """
        for subnet in sandbox_vnet.subnets:
            if subnet.name == subnet_name:
                return subnet

        raise Exception(f"Unable to find subnet with name '{subnet_name}' under the Sandbox vNet")

    def create_route_tables(self, request_actions):
        """"

        :param request_actions:
        :return
        """
        resource_group_name = self._reservation_info.get_resource_group_name()

        network_actions = NetworkActions(azure_client=self._azure_client, logger=self._logger)
        route_tables_actions = RouteTablesActions(azure_client=self._azure_client, logger=self._logger)

        sandbox_vnet = network_actions.get_sandbox_virtual_network(
            resource_group_name=self._resource_config.management_group_name)

        for route_table_request in request_actions.route_tables:
            self._logger.info(f"Processing Route Table {route_table_request}")
            self._cs_reservation_output.write_message(f"Processing Route Table {route_table_request.name}")

            azure_route_table = route_tables_actions.create_route_table(resource_group_name=resource_group_name,
                                                                        route_table_name=route_table_request.name,
                                                                        region=self._resource_config.region,
                                                                        route_table=route_table_request)

            for subnet_name in route_table_request.subnets:
                subnet = self._find_sandbox_subnet(sandbox_vnet=sandbox_vnet, subnet_name=subnet_name)
                subnet.route_table = azure_route_table

                network_actions.update_subnet(subnet_name=subnet_name,
                                              vnet_name=sandbox_vnet.name,
                                              resource_group_name=self._resource_config.management_group_name,
                                              subnet=subnet)
