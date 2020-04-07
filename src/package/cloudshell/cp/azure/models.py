from dataclasses import dataclass

from package.cloudshell.cp.azure.utils.name_generator import generate_name


# todo: move it to the cloudshell-cp-core
@dataclass
class ReservationInfo:
    reservation_id: str
    owner: str
    blueprint: str
    domain: str

    @classmethod
    def from_context(cls, context):
        return cls(reservation_id=context.reservation_id,
                   owner=context.owner_user,
                   blueprint=context.environment_name,
                   domain=context.domain)


class AzureReservationInfo(ReservationInfo):
    SANDBOX_NSG_NAME_PREFIX = "NSG_sandbox_all_subnets_"
    CREATED_BY_TAG = "Cloudshell"

    class TagNames(object):
        created_by = "CreatedBy"
        owner = "Owner"
        blueprint = "Blueprint"
        sandbox_id = "SandboxId"
        domain = "Domain"

    def get_resource_group_name(self):
        """

        :rtype: str
        """
        return self.reservation_id

    def get_storage_account_name(self):
        """Storage account name in azure must be between 3-24 chars. Dashes are not allowed as well.

        :rtype: str
        """
        reservation_id = self.reservation_id.replace("-", "")
        # we need to set a static postfix because we want to ensure we get the same storage account name if
        # prepare connectivity will run more than once
        return generate_name(name=self.reservation_id,
                             postfix="cs",
                             max_length=24).replace("-", "")

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
            self.TagNames.created_by: self.CREATED_BY_TAG,
            self.TagNames.owner: self.owner,
            self.TagNames.blueprint: self.blueprint,
            self.TagNames.sandbox_id: self.reservation_id,
            self.TagNames.domain: self.domain,
        }
