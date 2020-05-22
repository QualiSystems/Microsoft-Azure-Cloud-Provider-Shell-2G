from cloudshell.cp.core.reservation_info import ReservationInfo


class AzureReservationInfo(ReservationInfo):
    # todo: remove reservation id from the sandbox name
    SANDBOX_NSG_NAME_TPL = "NSG_sandbox_all_subnets_{reservation_id}"

    class TagNames:
        created_by = "CreatedBy"
        owner = "Owner"
        blueprint = "Blueprint"
        sandbox_id = "SandboxId"
        domain = "Domain"

    class TagValues:
        created_by = "CloudShell"

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

    def get_tags(self):
        """

        :return:
        :rtype: dict[str, str]
        """
        return {
            self.TagNames.created_by: self.TagValues.created_by,
            self.TagNames.owner: self.owner,
            self.TagNames.blueprint: self.blueprint,
            self.TagNames.sandbox_id: self.reservation_id,
            self.TagNames.domain: self.domain,
        }
