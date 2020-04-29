from cloudshell.cp.core.reservation_info import ReservationInfo

# from package.cloudshell.cp.azure.utils.name_generator import generate_name


class AzureReservationInfo(ReservationInfo):
    # TODO: SEEMS THAT we van create NSG with this prefix name, without adding resource group UUID !!!!
    SANDBOX_NSG_NAME_PREFIX = "NSG_sandbox_all_subnets_"

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
        # reservation_id = self.reservation_id.replace("-", "")
        # # we need to set a static postfix because we want to ensure we get the same storage account name if
        # # prepare connectivity will run more than once # todo::???? what does in mean ????
        # # todo: is it OK to do like this without this generation !!! ??????????
        # return generate_name(name=self.reservation_id,
        #                      postfix="cs",
        #                      max_length=24).replace("-", "")
        return self.reservation_id.replace("-", "")[:24]

    def get_network_security_group_name(self):
        """

        :rtype: str
        """
        return f"{self.SANDBOX_NSG_NAME_PREFIX}{self.reservation_id}"

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
