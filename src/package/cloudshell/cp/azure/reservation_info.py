from cloudshell.cp.core.reservation_info import ReservationInfo


class AzureReservationInfo(ReservationInfo):
    SANDBOX_NSG_NAME_TPL = "NSG_sandbox_all_subnets_{reservation_id}"

    def get_resource_group_name(self):
        """

        :rtype: str
        """
        return self.reservation_id

    def get_storage_account_name(self):
        """Storage account name in azure must be between 3-24 chars. Dashes are not allowed as well.

        :rtype: str
        """
        return self.reservation_id.replace("-", "")[:24]

    def get_network_security_group_name(self):
        """

        :rtype: str
        """
        return self.SANDBOX_NSG_NAME_TPL.format(reservation_id=self.reservation_id)
