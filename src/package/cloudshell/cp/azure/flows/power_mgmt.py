from package.cloudshell.cp.azure.actions.vm import VMActions


class AzurePowerManagementFlow:
    def __init__(self, resource_config, azure_client, reservation_info, logger):
        """

        :param resource_config:
        :param azure_client:
        :param reservation_info:
        :param logging.Logger logger:
        """
        self._resource_config = resource_config
        self._azure_client = azure_client
        self._reservation_info = reservation_info
        self._logger = logger

    def power_on(self, deployed_app):
        """

        :param deployed_app:
        :return:
        """
        resource_group_name = self._reservation_info.get_resource_group_name()
        # todo: do we need to do it here ?????
        # vm_name = data_holder.name
        #
        # extension_time_out = self.vm_custom_params_extractor.get_custom_param_value(
        #     data_holder.vmdetails.vmCustomParams,
        #     "extension_time_out")
        #
        # if extension_time_out in ["True", "true", "1"]:
        #     cloudshell_session.SetResourceLiveStatus(resource_full_name, "Error", "Partially deployed app")
        #
        #     raise Exception("Partially deployed app: VM Custom Script Extension failed to "
        #                     "compete within the specified timeout")

        vm_actions = VMActions(azure_client=self._azure_client, logger=self._logger)
        vm_actions.start_vm(vm_name=deployed_app.name, resource_group_name=resource_group_name)

    def power_off(self, deployed_app):
        """

        :param deployed_app:
        :return:
        """
        resource_group_name = self._reservation_info.get_resource_group_name()

        vm_actions = VMActions(azure_client=self._azure_client, logger=self._logger)
        vm_actions.stop_vm(vm_name=deployed_app.name, resource_group_name=resource_group_name)
