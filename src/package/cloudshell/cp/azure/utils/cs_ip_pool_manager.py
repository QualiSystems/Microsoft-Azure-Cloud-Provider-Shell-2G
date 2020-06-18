import json

from netaddr import IPNetwork


# todo: refactor this class
class CSIPPoolManager:
    DEFAULT_POOL_OWNER = "Azure-Shell"

    def __init__(self, cs_api, logger):
        """

        :param cs_api:
        """
        self._cs_api = cs_api
        self._logger = logger

    def get_ip_from_pool(self, reservation_id, subnet_cidr, owner=None):
        """

        :param reservation_id:
        :param subnet_cidr:
        :param owner:
        :return:
        """
        request = {
            "type": "NextAvailableIP",
            "poolId": self._get_pool_id(reservation_id),
            "reservationId": reservation_id,
            "ownerId": self._get_pool_item_owner(owner),
            "isolation": "Exclusive",
            "subnetRange": subnet_cidr,
            "reservedIps": self._get_reserved_ips(subnet_cidr)
        }

        # if there is no free IP api will throw an error: CloudShell API error 100: Error: Could not find available IP
        result = self._cs_api.CheckoutFromPool(selectionCriteriaJson=json.dumps(request))
        available_ip = result.Items[0]
        self._logger.info(f"Retrieved available IP '{available_ip}' from the subnet '{subnet_cidr}'")

        return available_ip

    def _get_pool_item_owner(self, owner):
        """

        :param str owner:
        :return:
        """
        return owner or self.DEFAULT_POOL_OWNER

    def _get_reserved_ips(self, subnet_cidr):
        # todo: check and rework this function
        # Calculate reserved ips by azure - The first and last IP addresses of each subnet are reserved for protocol
        # conformance, along with the x.x.x.1-x.x.x.3 addresses of each subnet, which are used for Azure services.
        ip_network = IPNetwork(subnet_cidr)
        reserved_ips = list(ip_network[0:4]) + [ip_network[-1]]
        reserved_ips_str_arr = [str(x) for x in reserved_ips]

        return reserved_ips_str_arr

    def _get_pool_id(self, reservation_id):
        """

        :param reservation_id:
        :return:
        """
        return "{}-private-ips".format(reservation_id)

    def release_ips(self, reservation_id, ips, owner=None):
        """

        :param str reservation_id:
        :param list[str] ips:
        :return:
        """
        self._cs_api.ReleaseFromPool(values=ips,
                                     poolId=self._get_pool_id(reservation_id),
                                     reservationId=reservation_id,
                                     ownerId=self._get_pool_item_owner(owner))

        self._logger.info(f"Released IPs from the pool: {ips}")
