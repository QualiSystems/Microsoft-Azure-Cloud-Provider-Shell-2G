import json
from dataclasses import dataclass, field

from package.cloudshell.cp.azure.models.route_table import RouteTable, Route


@dataclass
class CreateRouteTablesRequestActions:
    route_tables: list = field(default_factory=list)

    @classmethod
    def from_request(cls, request):
        """Create CreateRouteTablesRequestActions object from the string request.

        :param str request:
        :rtype: CreateRouteTablesRequestActions
        """
        data = json.loads(request)
        route_tables = []

        for route_table_data in data["route_tables"]:
            route_table = RouteTable(
                name=route_table_data["name"],
                subnets=route_table_data["subnets"],
                routes=[Route(
                    name=route_data["name"],
                    address_prefix=route_data["address_prefix"],
                    next_hop_type=route_data["next_hop_type"],
                    next_hop_address=route_data["next_hop_address"]) for route_data in route_table_data["routes"]])

            route_tables.append(route_table)

        return cls(route_tables=route_tables)
