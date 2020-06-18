from dataclasses import dataclass, field

from cloudshell.cp.core.request_actions.models import BaseRequestObject


@dataclass
class RouteTable(BaseRequestObject):
    name: str
    subnets: list = field(default_factory=list)
    routes: list = field(default_factory=list)


@dataclass
class Route(BaseRequestObject):
    name: str
    address_prefix: str
    next_hop_type: str
    next_hop_address: str
