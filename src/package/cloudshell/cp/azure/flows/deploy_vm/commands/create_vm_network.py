from package.cloudshell.cp.azure.utils.rollback import RollbackCommand


class CreateVMNetworkCommand(RollbackCommand):
    def __init__(self, rollback_manager, cancellation_manager, network_actions, interface_name, add_public_ip,
                 resource_group_name, subnet, network_security_group, public_ip_type, private_ip_allocation_method,
                 cs_ip_pool_manager, reservation_id, enable_ip_forwarding, region, tags):
        """

        :param rollback_manager:
        :param cancellation_manager:
        :param network_actions:
        :param interface_name:
        :param add_public_ip:
        :param resource_group_name:
        :param subnet:
        :param network_security_group:
        :param public_ip_type:
        :param cs_ip_pool_manager:
        :param reservation_id:
        :param region:
        :param tags:
        """
        super().__init__(rollback_manager=rollback_manager, cancellation_manager=cancellation_manager)
        self._network_actions = network_actions
        self._interface_name = interface_name
        self._add_public_ip = add_public_ip
        self._resource_group_name = resource_group_name
        self._subnet = subnet
        self._network_security_group = network_security_group
        self._public_ip_type = public_ip_type
        self._private_ip_allocation_method = private_ip_allocation_method
        self._cs_ip_pool_manager = cs_ip_pool_manager
        self._reservation_id = reservation_id
        self._enable_ip_forwarding = enable_ip_forwarding
        self._region = region
        self._tags = tags
        self._private_ip_address = None

    def _execute(self):
        # private_ip_address in required only in the case of static allocation method
        # in the case of dynamic allocation method is ignored
        # purpose of static allocation -> on restart machine, the ip can get lost. By using static we ensure the ip
        # will remain the same
        private_ip_allocation_method = self._network_actions.convert_cloudshell_private_ip_allocation_type(
            ip_type=self._private_ip_allocation_method)

        if self._network_actions.is_static_ip_allocation_type(ip_type=private_ip_allocation_method):
            self._private_ip_address = self._cs_ip_pool_manager.get_ip_from_pool(
                reservation_id=self._reservation_id,
                subnet_cidr=self._subnet.address_prefix)

        return self._network_actions.create_vm_network(interface_name=self._interface_name,
                                                       subnet=self._subnet,
                                                       network_security_group=self._network_security_group,
                                                       public_ip_type=self._public_ip_type,
                                                       resource_group_name=self._resource_group_name,
                                                       region=self._region,
                                                       tags=self._tags,
                                                       private_ip_allocation_method=private_ip_allocation_method,
                                                       private_ip_address=self._private_ip_address,
                                                       add_public_ip=self._add_public_ip,
                                                       enable_ip_forwarding=self._enable_ip_forwarding)

    def rollback(self):
        if self._private_ip_address:
            self._cs_ip_pool_manager.release_ips(reservation_id=self._reservation_info.reservation_id,
                                                 ips=[self._private_ip_address])
