from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.request_actions import (
    CleanupSandboxInfraRequestActions,
    DeployedVMActions,
    DeployVMRequestActions,
    GetVMDetailsRequestActions,
    PrepareSandboxInfraRequestActions,
    SetAppSecurityGroupsRequestActions,
)
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext

from cloudshell.cp.azure import constants
from cloudshell.cp.azure.azure_client import AzureAPIClient
from cloudshell.cp.azure.flows.access_key import AzureGetAccessKeyFlow
from cloudshell.cp.azure.flows.app_security_groups import AzureAppSecurityGroupsFlow
from cloudshell.cp.azure.flows.application_ports import AzureGetApplicationPortsFlow
from cloudshell.cp.azure.flows.autoload import AzureAutoloadFlow
from cloudshell.cp.azure.flows.available_ip import AzureGetAvailablePrivateIPFlow
from cloudshell.cp.azure.flows.cleanup import AzureCleanupSandboxInfraFlow
from cloudshell.cp.azure.flows.create_route_tables import CreateRouteTablesFlow
from cloudshell.cp.azure.flows.delete_instance import AzureDeleteInstanceFlow
from cloudshell.cp.azure.flows.deploy_vm.deploy_custom_vm import AzureDeployCustomVMFlow
from cloudshell.cp.azure.flows.deploy_vm.deploy_marketplace_vm import (
    AzureDeployMarketplaceVMFlow,
)
from cloudshell.cp.azure.flows.deploy_vm.deploy_shared_gallery_vm import (
    AzureDeployGalleryImageVMFlow,
)
from cloudshell.cp.azure.flows.power_mgmt import AzurePowerManagementFlow
from cloudshell.cp.azure.flows.prepare_sandbox_infra import AzurePrepareSandboxInfraFlow
from cloudshell.cp.azure.flows.reconfigure_vm import AzureReconfigureVMFlow
from cloudshell.cp.azure.flows.refresh_ip import AzureRefreshIPFlow
from cloudshell.cp.azure.flows.vm_details import AzureGetVMDetailsFlow
from cloudshell.cp.azure.models.deploy_app import (
    AzureVMFromCustomImageDeployApp,
    AzureVMFromMarketplaceDeployApp,
    AzureVMFromSharedGalleryImageDeployApp,
)
from cloudshell.cp.azure.models.deployed_app import (
    AzureVMFromCustomImageDeployedApp,
    AzureVMFromMarketplaceDeployedApp,
    AzureVMFromSharedGalleryImageDeployedApp,
)
from cloudshell.cp.azure.request_actions import CreateRouteTablesRequestActions
from cloudshell.cp.azure.reservation_info import AzureReservationInfo
from cloudshell.cp.azure.resource_config import AzureResourceConfig
from cloudshell.cp.azure.utils.cs_ip_pool_manager import CSIPPoolManager
from cloudshell.cp.azure.utils.lock_manager import ThreadLockManager

import re
import json
import jsonpickle


from cloudshell.cp.azure.actions.vm import VMActions
from cloudshell.cp.azure.actions.vm_details import VMDetailsActions
from cloudshell.cp.azure.actions.network import NetworkActions
from cloudshell.cp.azure.utils.azure_name_parser import get_name_from_resource_id

from cloudshell.cp.core.request_actions.models import (
    VmDetailsData,
    VmDetailsNetworkInterface,
    VmDetailsProperty,
)

from cloudshell.cp.core.request_actions.models import DeployedApp
from cloudshell.cp.core.request_actions.models import VmDetailsData
from cloudshell.shell.core.driver_context import (
    ApiVmCustomParam,
    ApiVmDetails,
    AutoLoadAttribute,
    AutoLoadCommandContext,
    AutoLoadDetails,
    AutoLoadResource,
    CancellationContext,
    InitCommandContext,
    ResourceCommandContext,
    ResourceRemoteCommandContext,
    UnreservedResourceCommandContext,
)


class AzureDriver(ResourceDriverInterface):
    SHELL_NAME = constants.SHELL_NAME

    def __init__(self):
        """Init function.

        ctor must be without arguments, it is created with reflection at run time
        """
        self.lock_manager = ThreadLockManager()

    def initialize(self, context):
        """Called every time a new instance of the driver is created.

        This method can be left unimplemented but this is a good place to
        load and cache the driver configuration, initiate sessions etc.
        Whatever you choose, do not remove it.
        :param InitCommandContext context: the context the command runs on
        """
        pass

    def get_inventory(self, context):
        """Called when the cloud provider resource is created in the inventory.

        Method validates the values of the cloud provider attributes, entered by
        the user as part of the cloud provider resource creation. In addition,
        this would be the place to assign values programmatically to optional
        attributes that were not given a value by the user. If one of the
        validations failed, the method should raise an exception
        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource
        you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Autoload command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            autoload_flow = AzureAutoloadFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                logger=logger,
            )

            return autoload_flow.discover()

    def PrepareSandboxInfra(self, context, request, cancellation_context):
        """Called in the beginning of the orchestration flow (preparation stage).

        Prepares all of the required infrastructure needed for a sandbox operating
        with L3 connectivity. For example, creating networking infrastructure
        like VPC, subnets or routing tables in AWS, storage entities  such as
        S3 buckets, or keyPair objects for authentication. In general, any other
        entities needed on the sandbox level should be created here.

        Note:
        PrepareSandboxInfra can be called multiple times in a sandbox.
        Setup can be called multiple times in the sandbox, and every time
        setup is called, the PrepareSandboxInfra method will be called again.
        Implementation should support this use case and take under consideration that
        the cloud resource might already exist. It's recommended to follow the
        "get or create" pattern when implementing this method.

        When an error is raised or method returns action result with success false
        Cloudshell will fail sandbox creation, so bear that in mind when doing so.
        :param ResourceCommandContext context:
        :param str request:
        :param CancellationContext cancellation_context:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Prepare Sandbox Infra command...")
            logger.debug(f"Request: {request}")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            request_actions = PrepareSandboxInfraRequestActions.from_request(request)
            reservation_info = AzureReservationInfo.from_resource_context(context)
            cancellation_manager = CancellationContextManager(cancellation_context)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            prepare_sandbox_flow = AzurePrepareSandboxInfraFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                reservation_info=reservation_info,
                cancellation_manager=cancellation_manager,
                logger=logger,
            )

            return prepare_sandbox_flow.prepare(request_actions=request_actions)

    def Deploy(self, context, request, cancellation_context=None):
        """Called when reserving a sandbox during setup.

        Method creates the compute resource in the cloud provider -
        VM instance or container. If App deployment fails, return a
        "success false" action result.
        :param ResourceCommandContext context:
        :param str request: A JSON string with the list of requested
        deployment actions
        :param CancellationContext cancellation_context:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Deploy command...")
            logger.debug(f"Request: {request}")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            cancellation_manager = CancellationContextManager(cancellation_context)
            reservation_info = AzureReservationInfo.from_resource_context(context)
            cs_ip_pool_manager = CSIPPoolManager(cs_api=api, logger=logger)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            for deploy_app_cls in (
                AzureVMFromMarketplaceDeployApp,
                AzureVMFromCustomImageDeployApp,
                AzureVMFromSharedGalleryImageDeployApp,
            ):
                DeployVMRequestActions.register_deployment_path(deploy_app_cls)

            request_actions = DeployVMRequestActions.from_request(
                request=request, cs_api=api
            )

            if isinstance(request_actions.deploy_app, AzureVMFromMarketplaceDeployApp):
                deploy_flow_class = AzureDeployMarketplaceVMFlow
            elif isinstance(
                request_actions.deploy_app, AzureVMFromCustomImageDeployApp
            ):
                deploy_flow_class = AzureDeployCustomVMFlow
            else:
                deploy_flow_class = AzureDeployGalleryImageVMFlow

            deploy_flow = deploy_flow_class(
                resource_config=resource_config,
                azure_client=azure_client,
                cs_api=api,
                reservation_info=reservation_info,
                cancellation_manager=cancellation_manager,
                cs_ip_pool_manager=cs_ip_pool_manager,
                lock_manager=self.lock_manager,
                logger=logger,
            )

            return deploy_flow.deploy(request_actions=request_actions)

    def PowerOnHidden(self, context, ports):
        self.PowerOn(context, ports)
        # set live status on deployed app if power on passed
        api = CloudShellSessionContext(context).get_api()
        resource = context.remote_endpoints[0]
        api.SetResourceLiveStatus(resource.fullname, "Online", "Active")

    def PowerOn(self, context, ports):
        """Called when reserving a sandbox during setup.

        Call for each app in the sandbox can also be run manually by
        the sandbox end-user from the deployed App's commands pane.
        Method spins up the VM If the operation fails, method should raise an exception.
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Power On command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            reservation_info = AzureReservationInfo.from_remote_resource_context(
                context
            )

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            for deploy_app_cls in (
                AzureVMFromMarketplaceDeployedApp,
                AzureVMFromCustomImageDeployedApp,
                AzureVMFromSharedGalleryImageDeployedApp,
            ):
                DeployedVMActions.register_deployment_path(deploy_app_cls)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMActions.from_remote_resource(
                resource=resource, cs_api=api
            )

            power_mgmt_flow = AzurePowerManagementFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                reservation_info=reservation_info,
                logger=logger,
            )

            return power_mgmt_flow.power_on(
                deployed_app=deployed_vm_actions.deployed_app
            )

    def PowerOff(self, context, ports):
        """Called during sandbox's teardown.

        Can also be run manually by the sandbox end-user from the deployed
        App's commands pane. Method shuts down (or powers off) the VM instance.
        If the operation fails, method should raise an exception.
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Power Off command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            reservation_info = AzureReservationInfo.from_remote_resource_context(
                context
            )

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            for deploy_app_cls in (
                AzureVMFromMarketplaceDeployedApp,
                AzureVMFromCustomImageDeployedApp,
                AzureVMFromSharedGalleryImageDeployedApp,
            ):
                DeployedVMActions.register_deployment_path(deploy_app_cls)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMActions.from_remote_resource(
                resource=resource, cs_api=api
            )

            power_mgmt_flow = AzurePowerManagementFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                reservation_info=reservation_info,
                logger=logger,
            )

            return power_mgmt_flow.power_off(
                deployed_app=deployed_vm_actions.deployed_app
            )

    def PowerCycle(self, context, ports, delay):
        pass

    def remote_refresh_ip(self, context, ports, cancellation_context):
        """Called when reserving a sandbox during setup.

        Call for each app in the sandbox can also be run manually by the
        sandbox end-user from the deployed App's commands pane.
        Method retrieves the VM's updated IP address from the cloud provider
        and sets it on the deployed App resource. Both private and public IPs
        are retrieved, as appropriate. If the operation fails, method should
        raise an exception.
        :param ResourceRemoteCommandContext context:
        :param ports:
        :param CancellationContext cancellation_context:
        :return:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Remote Refresh IP command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            reservation_info = AzureReservationInfo.from_remote_resource_context(
                context
            )
            cancellation_manager = CancellationContextManager(cancellation_context)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            for deploy_app_cls in (
                AzureVMFromMarketplaceDeployedApp,
                AzureVMFromCustomImageDeployedApp,
                AzureVMFromSharedGalleryImageDeployedApp,
            ):
                DeployedVMActions.register_deployment_path(deploy_app_cls)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMActions.from_remote_resource(
                resource=resource, cs_api=api
            )

            refresh_ip_flow = StaticAzureRefreshIPFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                cs_api=api,
                reservation_info=reservation_info,
                cancellation_manager=cancellation_manager,
                logger=logger,
            )

            return refresh_ip_flow.refresh_ip(
                deployed_app=deployed_vm_actions.deployed_app
            )

    def reconfigure_vm(
        self,
        context,
        ports,
        cancellation_context,
        vm_size,
        os_disk_size,
        os_disk_type,
        data_disks,
    ):
        """Reconfigure VM Size and Data Disks."""
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Reconfigure VM command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            reservation_info = AzureReservationInfo.from_remote_resource_context(
                context
            )
            cancellation_manager = CancellationContextManager(cancellation_context)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            for deployed_app_cls in (
                AzureVMFromMarketplaceDeployedApp,
                AzureVMFromCustomImageDeployedApp,
                AzureVMFromSharedGalleryImageDeployedApp,
            ):
                DeployedVMActions.register_deployment_path(deployed_app_cls)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMActions.from_remote_resource(
                resource=resource, cs_api=api
            )

            reconfigure_vm_flow = AzureReconfigureVMFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                cs_api=api,
                reservation_info=reservation_info,
                cancellation_manager=cancellation_manager,
                logger=logger,
            )

            return reconfigure_vm_flow.reconfigure(
                deployed_app=deployed_vm_actions.deployed_app,
                vm_size=vm_size,
                os_disk_size=os_disk_size,
                os_disk_type=os_disk_type,
                data_disks=data_disks,
            )

    def GetVmDetails(self, context, requests, cancellation_context):
        """Called when reserving a sandbox during setup.

        Call for each app in the sandbox can also be run manually by the sandbox
        end-user from the deployed App's VM Details pane. Method queries
        cloud provider for instance operating system, specifications and networking
        information and returns that as a json serialized driver response
        containing a list of VmDetailsData. If the operation fails,
        method should raise an exception.
        :param ResourceCommandContext context:
        :param str requests:
        :param CancellationContext cancellation_context:
        :return:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get VM Details command...")
            logger.debug(f"Requests: {requests}")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            for deploy_app_cls in (
                AzureVMFromMarketplaceDeployedApp,
                AzureVMFromCustomImageDeployedApp,
                AzureVMFromSharedGalleryImageDeployedApp,
            ):
                GetVMDetailsRequestActions.register_deployment_path(deploy_app_cls)

            request_actions = GetVMDetailsRequestActions.from_request(
                request=requests, cs_api=api
            )

            cancellation_manager = CancellationContextManager(cancellation_context)
            reservation_info = AzureReservationInfo.from_resource_context(context)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            vm_details_flow = StaticGetVmDetailsFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                reservation_info=reservation_info,
                cancellation_manager=cancellation_manager,
                logger=logger,
            )

            return vm_details_flow.get_vm_details(request_actions=request_actions)

    def DeleteInstance(self, context, ports):
        """Called when removing a deployed App from the sandbox.

        Method deletes the VM from the cloud provider. If the operation fails,
        method should raise an exception.
        :param ResourceRemoteCommandContext context:
        :param ports:
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Delete Instance command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            reservation_info = AzureReservationInfo.from_remote_resource_context(
                context
            )
            cs_ip_pool_manager = CSIPPoolManager(cs_api=api, logger=logger)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            for deploy_app_cls in (
                AzureVMFromMarketplaceDeployedApp,
                AzureVMFromCustomImageDeployedApp,
                AzureVMFromSharedGalleryImageDeployedApp,
            ):
                GetVMDetailsRequestActions.register_deployment_path(deploy_app_cls)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMActions.from_remote_resource(
                resource=resource, cs_api=api
            )

            delete_flow = AzureDeleteInstanceFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                reservation_info=reservation_info,
                cs_ip_pool_manager=cs_ip_pool_manager,
                lock_manager=self.lock_manager,
                logger=logger,
            )

            delete_flow.delete_instance(deployed_app=deployed_vm_actions.deployed_app)

    def CleanupSandboxInfra(self, context, request):
        """Called at the end of reservation teardown.

        Cleans all entities (beside VMs) created for sandbox, usually
        entities created in the PrepareSandboxInfra command. Basically all
        created entities for the sandbox will be deleted by calling
        the methods: DeleteInstance, CleanupSandboxInfra.
        If a failure occurs, return a "success false" action result.
        :param ResourceCommandContext context:
        :param str request:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Cleanup Sandbox Infra command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            request_actions = CleanupSandboxInfraRequestActions.from_request(request)
            reservation_info = AzureReservationInfo.from_resource_context(context)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            cleanup_flow = AzureCleanupSandboxInfraFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                reservation_info=reservation_info,
                lock_manager=self.lock_manager,
                logger=logger,
            )

            return cleanup_flow.cleanup(request_actions=request_actions)

    def CreateRouteTables(self, context, request):
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Create Route Tables command...")
            api = CloudShellSessionContext(context).get_api()

            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            request_actions = CreateRouteTablesRequestActions.from_request(request)
            reservation_info = AzureReservationInfo.from_resource_context(context)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            route_table_flow = CreateRouteTablesFlow(
                resource_config=resource_config,
                reservation_info=reservation_info,
                azure_client=azure_client,
                cs_api=api,
                logger=logger,
            )

            return route_table_flow.create_route_tables(request_actions=request_actions)

    def SetAppSecurityGroups(self, context, request):
        """Called via cloudshell API call.

        Programmatically set which ports will be open on each of the apps
        in the sandbox, and from where they can be accessed. This is an
        optional command that may be implemented. Normally, all outbound
        traffic from a deployed app should be allowed.  For inbound traffic,
        we may use this method to specify the allowed traffic. An app may have
        several networking interfaces in the sandbox. For each such interface,
        this command allows to set which ports may be opened, the protocol and
        the source CIDR. If operation fails, return a "success false" action result.
        :param ResourceCommandContext context:
        :param str request:
        :return:
        :rtype: str
        """
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Set App Security Groups command...")
            logger.debug(f"Request: {request}")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            request_actions = SetAppSecurityGroupsRequestActions.from_request(request)
            reservation_info = AzureReservationInfo.from_resource_context(context)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            app_security_groups_flow = AzureAppSecurityGroupsFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                reservation_info=reservation_info,
                lock_manager=self.lock_manager,
                logger=logger,
            )

            return app_security_groups_flow.set_app_security_groups(
                request_actions=request_actions
            )

    def cleanup(self):
        """Destroy the driver session.

        This function is called every time a driver instance is destroyed.
        This is a good place to close any open sessions, finish writing
        to log files, etc.
        """
        pass

    def GetApplicationPorts(self, context, ports):
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get Application Ports command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            reservation_info = AzureReservationInfo.from_remote_resource_context(
                context
            )

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            for deploy_app_cls in (
                AzureVMFromMarketplaceDeployedApp,
                AzureVMFromCustomImageDeployedApp,
                AzureVMFromSharedGalleryImageDeployedApp,
            ):
                DeployedVMActions.register_deployment_path(deploy_app_cls)

            resource = context.remote_endpoints[0]
            deployed_vm_actions = DeployedVMActions.from_remote_resource(
                resource=resource, cs_api=api
            )

            application_ports_flow = AzureGetApplicationPortsFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                reservation_info=reservation_info,
                logger=logger,
            )

            return application_ports_flow.get_application_ports(
                deployed_app=deployed_vm_actions.deployed_app
            )

    def GetAccessKey(self, context, ports):
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get Access Key command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            reservation_info = AzureReservationInfo.from_remote_resource_context(
                context
            )

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            access_key_flow = AzureGetAccessKeyFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                reservation_info=reservation_info,
                logger=logger,
            )

            return access_key_flow.get_access_key()

    def GetAvailablePrivateIP(self, context, subnet_cidr, owner):
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get Available Private IP command...")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            reservation_info = AzureReservationInfo.from_remote_resource_context(
                context
            )
            cs_ip_pool_manager = CSIPPoolManager(cs_api=api, logger=logger)

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            get_available_ip_flow = AzureGetAvailablePrivateIPFlow(
                resource_config=resource_config,
                azure_client=azure_client,
                cs_ip_pool_manager=cs_ip_pool_manager,
                reservation_info=reservation_info,
                logger=logger,
            )

            return get_available_ip_flow.get_available_private_ip(
                subnet_cidr=subnet_cidr, owner=owner
            )

    def get_vms(self, context: ResourceCommandContext) -> str:
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get VMs command")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            res_groups_mapping = {rg.name.upper(): rg.name for rg in
                                  azure_client._resource_client.resource_groups.list()}

            vms = []  # list[dict["path": resource_group/vm_name, "uuid": vm_id]]

            for vm in azure_client._compute_client.virtual_machines.list_all():
                match = re.search(r"resourceGroups/(?P<rg_name>\S+?)/.*",
                                  vm.id,
                                  re.IGNORECASE)
                if match:
                    vm_res_group = res_groups_mapping.get(match.group("rg_name"))
                    path = f"{vm_res_group}/{vm.name}"
                else:
                    path = vm.name

                vms.append({"path": path, "uuid": vm.vm_id})

            vms.sort(key=lambda vm: vm["path"].lower())
            return json.dumps(vms)

    def get_autoload_details_for_vm(
        self,
        context: ResourceCommandContext,
        vm_path: str,
        model: str,
        port_model: str,
    ) -> str:
        with LoggingSessionContext(context) as logger:
            logger.info("Starting Get Autoload Details For VM command")
            api = CloudShellSessionContext(context).get_api()
            resource_config = AzureResourceConfig.from_context(
                shell_name=self.SHELL_NAME, context=context, api=api
            )

            azure_client = AzureAPIClient(
                azure_subscription_id=resource_config.azure_subscription_id,
                azure_tenant_id=resource_config.azure_tenant_id,
                azure_application_id=resource_config.azure_application_id,
                azure_application_key=resource_config.azure_application_key,
                logger=logger,
            )

            resource_group_name, vm_name = vm_path.split("/")
            vm = azure_client.get_vm(
                resource_group_name=resource_group_name,
                vm_name=vm_name
            )

            actions = StaticVmDetailsActions(azure_client=azure_client, logger=logger)

            vm_details = actions._prepare_vm_details(
                virtual_machine=vm,
                resource_group_name=resource_group_name,
                prepare_vm_instance_data_function=actions._prepare_common_vm_instance_data
            )

            autoload_details = self._get_autoload_details(
                vm,
                model,
                port_model,
                vm_details,
                resource_config,
            )

            return jsonpickle.encode(autoload_details)

    def _get_autoload_details(
        self,
        vm,
        model: str,
        port_model: str,
        vm_details: VmDetailsData,
        resource_config: AzureResourceConfig,
    ) -> AutoLoadDetails:
        resources = []

        vm_custom_params = [
            ApiVmCustomParam(data.key, data.value) for data in vm_details.vmInstanceData
        ]
        api_vm_details = ApiVmDetails(resource_config.name, vm.vm_id, vm_custom_params)
        os_type = ""
        for prop in vm_details.vmInstanceData:
            if prop.key == "Operating System":
                os_type = prop.value
                break

        attributes = [
            AutoLoadAttribute("", f"{model}.OS Type", os_type),
            AutoLoadAttribute(
                "", "VmDetails", jsonpickle.encode(api_vm_details, unpicklable=False)
            ),
        ]

        # ports resources and attributes
        for iface_index, vnic in enumerate(vm_details.vmNetworkData, start=1):
            rel_path = f"P{iface_index}"
            res = AutoLoadResource(
                name=f"Port{iface_index}",
                model=port_model,
                relative_address=rel_path,
            )
            resources.append(res)
            attributes.append(
                AutoLoadAttribute(
                    rel_path, f"{port_model}.Requested vNIC Name", iface_index
                )
            )
            attr_mapping = {
                "IP": "Private IP",
                "Public IP": "Public IP",
                "MAC Address": "MAC Address",
            }

            for prop in vnic.networkData:
                if prop.key in attr_mapping:
                    attributes.append(
                        AutoLoadAttribute(
                            rel_path,
                            f"{port_model}.{attr_mapping[prop.key]}",
                            prop.value
                        )
                    )

        return AutoLoadDetails(resources, attributes)


class StaticGetVmDetailsFlow(AzureGetVMDetailsFlow):
    def _get_vm_details(self, deployed_app):
        """Get VM Details."""
        sandbox_resource_group_name = self._reservation_info.get_resource_group_name()
        if hasattr(deployed_app, "resource_group_name"):
            vm_resource_group_name = (
                deployed_app.resource_group_name or sandbox_resource_group_name
            )
            vm_name = deployed_app.name
        else:
            for k, v in deployed_app.attributes.items():
                if k.endswith("VM Name"):
                    vm_resource_group_name, vm_name = v.split("/")
                    break

        vm_actions = VMActions(azure_client=self._azure_client, logger=self._logger)
        vm_details_actions = StaticVmDetailsActions(
            azure_client=self._azure_client, logger=self._logger
        )

        with self._cancellation_manager:
            vm = vm_actions.get_vm(
                vm_name=vm_name, resource_group_name=vm_resource_group_name
            )

        if isinstance(deployed_app, AzureVMFromMarketplaceDeployedApp):
            return vm_details_actions.prepare_marketplace_vm_details(
                virtual_machine=vm, resource_group_name=vm_resource_group_name
            )
        elif isinstance(deployed_app, AzureVMFromSharedGalleryImageDeployedApp):
            return vm_details_actions.prepare_shared_gallery_vm_details(
                virtual_machine=vm, resource_group_name=vm_resource_group_name
            )
        elif isinstance(deployed_app, AzureVMFromCustomImageDeployedApp):
            return vm_details_actions.prepare_custom_vm_details(
                virtual_machine=vm, resource_group_name=vm_resource_group_name
            )

        return vm_details_actions._prepare_vm_details(
                virtual_machine=vm,
                resource_group_name=vm_resource_group_name,
                prepare_vm_instance_data_function=vm_details_actions._prepare_common_vm_instance_data
            )


class StaticVmDetailsActions(VMDetailsActions):
    def _prepare_vm_details(
        self,
        virtual_machine,
        resource_group_name: str,
        prepare_vm_instance_data_function
    ):
        """Prepare VM details."""
        try:
            return VmDetailsData(
                appName=virtual_machine.name,
                vmInstanceData=prepare_vm_instance_data_function(
                    virtual_machine=virtual_machine,
                    resource_group_name=resource_group_name,
                ),
                vmNetworkData=self._prepare_vm_network_data(
                    virtual_machine=virtual_machine,
                    resource_group_name=resource_group_name,
                ),
            )
        except Exception as e:
            self._logger.exception(
                f"Error getting VM details for {virtual_machine.name}"
            )
            return VmDetailsData(appName=virtual_machine.name, errorMessage=str(e))

    def _prepare_vm_network_data(self, virtual_machine, resource_group_name):
        """Prepare VM Network data.

        :param virtual_machine:
        :param str resource_group_name:
        :return:
        """
        vm_network_interfaces = []
        for network_interface in virtual_machine.network_profile.network_interfaces:
            interface_name = get_name_from_resource_id(network_interface.id)
            interface = self.get_vm_network(
                interface_name=interface_name, resource_group_name=resource_group_name
            )

            ip_configuration = interface.ip_configurations[0]
            private_ip_addr = ip_configuration.private_ip_address

            network_data = [
                VmDetailsProperty(key="IP", value=ip_configuration.private_ip_address),
                VmDetailsProperty(key="MAC Address", value=interface.mac_address),
            ]

            subnet_name = ip_configuration.subnet.id.split("/")[-1]

            if ip_configuration.public_ip_address:
                public_ip = self._azure_client.get_public_ip(
                    public_ip_name=ip_configuration.public_ip_address.name,
                    resource_group_name=resource_group_name,
                )
                network_data.extend(
                    [
                        VmDetailsProperty(key="Public IP", value=public_ip.ip_address),
                        VmDetailsProperty(
                            key="Public IP Type",
                            value=public_ip.public_ip_allocation_method,
                        ),
                    ]
                )

                public_ip_addr = public_ip.ip_address
            else:
                public_ip_addr = ""

            vm_network_interface = VmDetailsNetworkInterface(
                interfaceId=interface.resource_guid,
                networkId=subnet_name,
                isPrimary=interface.primary,
                networkData=network_data,
                privateIpAddress=private_ip_addr,
                publicIpAddress=public_ip_addr,
            )

            vm_network_interfaces.append(vm_network_interface)

        return vm_network_interfaces


class StaticAzureRefreshIPFlow(AzureRefreshIPFlow):
    def refresh_ip(self, deployed_app):
        """Refresh Public and Private IPs on the CloudShell resource."""
        sandbox_resource_group_name = self._reservation_info.get_resource_group_name()
        if hasattr(deployed_app, "resource_group_name"):
            vm_resource_group_name = (
                deployed_app.resource_group_name or sandbox_resource_group_name
            )
            vm_name = deployed_app.name
        else:
            for k, v in deployed_app.attributes.items():
                if k.endswith("VM Name"):
                    vm_resource_group_name, vm_name = v.split("/")
                    break

        vm_actions = VMActions(azure_client=self._azure_client, logger=self._logger)
        network_actions = NetworkActions(
            azure_client=self._azure_client, logger=self._logger
        )

        vm = vm_actions.get_active_vm(
            vm_name=vm_name, resource_group_name=vm_resource_group_name
        )

        primary_interface_ref = self._get_primary_vm_interface(vm)
        interface_name = get_name_from_resource_id(primary_interface_ref.id)

        vm_network = network_actions.get_vm_network(
            interface_name=interface_name, resource_group_name=vm_resource_group_name
        )

        vm_ip_configuration = vm_network.ip_configurations[0]
        private_ip_on_azure = vm_ip_configuration.private_ip_address
        public_ip_reference = vm_ip_configuration.public_ip_address

        if public_ip_reference is None:
            self._logger.info(
                f"There is no Public IP attached to the VM {deployed_app.name}"
            )
            public_ip_on_azure = ""
        else:
            self._logger.info(f"Retrieving Public IP for the VM {deployed_app.name}")
            pub_ip_addr = self._azure_client.get_public_ip(
                public_ip_name=vm_ip_configuration.public_ip_address.name,
                resource_group_name=vm_resource_group_name,
            )

            public_ip_on_azure = pub_ip_addr.ip_address

        self._logger.info(f"Public IP on Azure: {public_ip_on_azure}")
        self._logger.info(f"Public IP on CloudShell: {deployed_app.public_ip}")

        if public_ip_on_azure != deployed_app.public_ip:
            self._logger.info(
                f"Updating Public IP on the VM {deployed_app.name} "
                f"to {public_ip_on_azure}"
            )
            deployed_app.update_public_ip(public_ip_on_azure)

        self._logger.info(f"Private IP on Azure: {private_ip_on_azure}")
        self._logger.info(f"Private IP on CloudShell: {deployed_app.private_ip}")

        if private_ip_on_azure != deployed_app.private_ip:
            self._logger.info(
                f"Updating Private IP on the resource to {private_ip_on_azure}"
            )
            self._cs_api.UpdateResourceAddress(
                resourceFullPath=deployed_app.name, resourceAddress=private_ip_on_azure
            )
