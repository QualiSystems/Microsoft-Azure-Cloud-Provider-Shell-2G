class AzureTagsManager:
    class TagNames:
        created_by = "CreatedBy"
        owner = "Owner"
        blueprint = "Blueprint"
        sandbox_id = "SandboxId"
        domain = "Domain"
        vm_name = "Name"

    class TagValues:
        created_by = "CloudShell"

    def __init__(self, reservation_info):
        """

        :param reservation_info:
        """
        self._reservation_info = reservation_info

    def get_tags(self, vm_name=None):
        """

        :param vm_name:
        :return:
        """
        tags = {
            self.TagNames.created_by: self.TagValues.created_by,
            self.TagNames.owner: self._reservation_info.owner,
            self.TagNames.blueprint: self._reservation_info.blueprint,
            self.TagNames.sandbox_id: self._reservation_info.reservation_id,
            self.TagNames.domain: self._reservation_info.domain,
        }
        if vm_name is not None:
            tags[self.TagNames.vm_name] = vm_name

        return tags

