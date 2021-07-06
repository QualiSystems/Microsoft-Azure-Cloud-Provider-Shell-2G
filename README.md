![Image][1]

# **Microsoft Azure Cloud Provider Shell 2G**

Release date: August 2020

`Shell version: 2.1.0`

`Document version: 2.0`

# In This Guide

* [Overview](#overview)
* [Downloading the Shell](#downloading-the-shell)
* [Importing and Configuring the Shell](#importing-and-configuring-the-shell)
* [Updating Python Dependencies for Shells](#updating-python-dependencies-for-shells)
* [Typical Workflows](#typical-workflows)
* [References](#references)
* [Release Notes](#release-notes)


# Overview
A shell integrates a device model, application or other technology with CloudShell. A shell consists of a data model that defines how the device and its properties are modeled in CloudShell, along with automation that enables interaction with the device via CloudShell.

### Cloud Provider Shells
CloudShell Cloud Providers shells provide L2 or L3 connectivity between resources and/or Apps.

### Microsoft Azure Cloud Provider Shell 2G
Microsoft Azure Cloud Provider Shell 2G provides you with apps deployment and management capabilities. 

For more information on the device, see the vendor's official product documentation.

### Standard version
Microsoft Azure Cloud Provider Shell 2G is based on the Cloud Provider Standard version **1.0.0**.

For detailed information about the shell’s structure and attributes, see the [Cloud Provider Standard](https://github.com/QualiSystems/cloudshell-standards/blob/master/Documentation/cloud_provider_standard.md) in GitHub.

### Requirements

Release: Microsoft Azure Cloud Provider Shell 2G

▪ CloudShell version **9.3 and above**

**Note:** If your CloudShell version does not support this shell, you should consider upgrading to a later version of CloudShell or contact customer support. 

### Data Model

The shell's data model includes all shell metadata, families, and attributes.

#### **Microsoft Azure Cloud Provider Shell 2G Attributes**

The attribute names and types are listed in the following section of the Cloud Provider Shell Standard:

[Common Cloud Provider Attributes](https://github.com/QualiSystems/cloudshell-standards/blob/master/Documentation/cloud_provider_standard.md#attributes)

The following table describes attributes that are unique to this shell and are not documented in the Shell Standard: 


|Attribute Name|Data Type|Description|
|:---|:---|:---|
|VM Size|String|The Microsoft Azure VM Size. The VM Size determines the CPU, memory, disk size and networking capacity of the VM. For example: “Standard_A1_v2”|
|Azure Subscription ID|String|The Subscription ID of the Azure user|
|Azure Tenant ID|String|The Azure Tenant Id that is associated with your Azure Active Directory (AAD) instance. For example: ccd13026-98e3-4e90-01f4-28e2afdf3213. The Tenant ID is created for the Active Directory and can be retrieved when creating the Azure API web application or retrieved from Azure CLI|
|Azure Application ID|String|Application Id associated with the Azure API application. The application ID allows CloudShell to access the Azure API and is generated as part of the web application’s configuration process|
|Azure Application Key|Password|Application key associated with the Azure API application. The application key allows CloudShell to access the Azure API and is generated as part of the Azure application’s configuration process|
|Management Group Name|String|The name of the Management Resource Group|
|Additional Mgmt Networks|String|Networks to be allowed to interact with all sandboxes. This is used for allowing connectivity to Azure resources outside the CloudShell Management VNet that should be available to CloudShell sandboxes. The syntax is comma separated CIDRs.|
|Custom Tags|string|Semi-colon separated list of up to 9 tags to be applied to all related Azure objects created during the App deployment, such as the sandbox's resource group, VNETs, subnets, NSGs and VMs. Attribute supports the following syntax: [TagName]=[TagValue]; [TagName]=[TagValue]. For example: “Tag1=Val1;Tag2=Val2”.|
|Private IP Allocation Method|String|Defines the method that will be used to allocated private IP addresses to VMs. When Cloudshell Allocation method is selected the Azure-Shell will use the CloudShell Pool API to checkout the next available IP address when needed. When the instance is deleted the checked out IP addresses will be released. When Azure Allocation method is selected the private ips will be assigned by Azure when creating the network interface.|


### Automation
This section describes the automation (driver) associated with the data model. The shell’s driver is provided as part of the shell package. There are two types of automation processes, Autoload and Resource. Autoload is executed when creating the resource in the **Inventory** dashboard.

For detailed information on each available commands, see the following section of the Cloud Provider Standard:

[Common Cloud Provider Commands](https://github.com/QualiSystems/cloudshell-standards/blob/master/Documentation/cloud_provider_standard.md#commands)

# Azure Integration Process
In order to integrate CloudShell with Azure, you need to first deploy the CloudShell management and sandbox VNets on your Azure region. This is done using Azure templates that define the management and sandbox VNets, the connection to your Quali Server and more. Additional steps are required, such as configuring the integration's management VMs and creating App templates which include the definition of the VMs, images and configuration management to be performed on the deployed VMs. For details, see CloudShell Help's [Azure Integration](https://help.quali.com/Online%20Help/2021.2/portal/Content/Admn/Azure-VNET-Ovrv.htm) chapter.

# Downloading the Shell
The Microsoft Azure Cloud Provider Shell 2G shell is available from the [Quali Community Integrations](https://community.quali.com/integrations) page. 

Download the files into a temporary location on your local machine. 

The shell comprises:

|File name|Description|
|:---|:---|
|Microsoft Azure Cloud Provider Shell 2G.zip|Device shell package|
|cloudshell-azure-dependencies-package-1.0.x.zip|Shell Python dependencies (for offline deployments only)|

# Importing and Configuring the Shell
This section describes how to import the Microsoft Azure Cloud Provider Shell 2G shell and configure and modify the shell’s devices.

### Importing the shell into CloudShell

**To import the shell into CloudShell:**
  1. Make sure you have the shell’s zip package. If not, download the shell from the [Quali Community's Integrations](https://community.quali.com/integrations) page.
  
  2. In CloudShell Portal, as Global administrator, open the **Manage – Shells** page.
  
  3. Click **Import**.
  
  4. In the dialog box, navigate to the shell's zip package, select it and click **Open**. <br><br>The shell is displayed in the **Shells** page and can be used by domain administrators in all CloudShell domains to create new inventory resources, as explained in [Adding Inventory Resources](http://help.quali.com/Online%20Help/9.0/Portal/Content/CSP/INVN/Add-Rsrc-Tmplt.htm?Highlight=adding%20inventory%20resources). 

### Offline installation of a shell

**Note:** Offline installation instructions are relevant only if CloudShell Execution Server has no access to PyPi. You can skip this section if your execution server has access to PyPi. For additional information, see the online help topic on offline dependencies.

In offline mode, import the shell into CloudShell and place any dependencies in the appropriate dependencies folder. The dependencies folder may differ, depending on the CloudShell version you are using:

* For CloudShell version 8.3 and above, see [Adding Shell and script packages to the local PyPi Server repository](#adding-shell-and-script-packages-to-the-local-pypi-server-repository).

* For CloudShell version 8.2, perform the appropriate procedure: [Adding Shell and script packages to the local PyPi Server repository](#adding-shell-and-script-packages-to-the-local-pypi-server-repository) or [Setting the Python pythonOfflineRepositoryPath configuration key](#setting-the-python-pythonofflinerepositorypath-configuration-key).

* For CloudShell versions prior to 8.2, see [Setting the Python pythonOfflineRepositoryPath configuration key](#setting-the-python-pythonofflinerepositorypath-configuration-key).

### Adding shell and script packages to the local PyPi Server repository
If your Quali Server and/or execution servers work offline, you will need to copy all required Python packages, including the out-of-the-box ones, to the PyPi Server's repository on the Quali Server computer (by default *C:\Program Files (x86)\QualiSystems\CloudShell\Server\Config\Pypi Server Repository*).

For more information, see [Configuring CloudShell to Execute Python Commands in Offline Mode](http://help.quali.com/Online%20Help/9.0/Portal/Content/Admn/Cnfgr-Pyth-Env-Wrk-Offln.htm?Highlight=Configuring%20CloudShell%20to%20Execute%20Python%20Commands%20in%20Offline%20Mode).

**To add Python packages to the local PyPi Server repository:**
  1. If you haven't created and configured the local PyPi Server repository to work with the execution server, perform the steps in [Add Python packages to the local PyPi Server repository (offline mode)](http://help.quali.com/Online%20Help/9.0/Portal/Content/Admn/Cnfgr-Pyth-Env-Wrk-Offln.htm?Highlight=offline%20dependencies#Add). 
  
  2. For each shell or script you add into CloudShell, do one of the following (from an online computer):
      * Connect to the Internet and download each dependency specified in the *requirements.txt* file with the following command: 
`pip download -r requirements.txt`. 
     The shell or script's requirements are downloaded as zip files.

      * In the [Quali Community's Integrations](https://community.quali.com/integrations) page, locate the shell and click the shell's **Download** link. In the page that is displayed, from the Downloads area, extract the dependencies package zip file.

3. Place these zip files in the local PyPi Server repository.
 
### Configuring a new resource
This section explains how to create a new resource from the shell.

In CloudShell, the component that models the device is called a resource. It is based on the shell that models the device and allows the CloudShell user and API to remotely control the device from CloudShell.

You can also modify existing resources, see [Managing Resources in the Inventory](http://help.quali.com/Online%20Help/9.0/Portal/Content/CSP/INVN/Mng-Rsrc-in-Invnt.htm?Highlight=managing%20resources).

**To create a resource for the device:**  
  1. In the CloudShell Portal, in the **Inventory** dashboard, click **Add New**.
     ![Image][2]
     
  3. From the list, select **Microsoft Azure Cloud Provider Shell 2G**.
  
  4. Click **Create**.
  
  5. In the **Resource** dialog box, enter the following mandatory attributes with data from step 1:
        - **Azure Application ID** - Paste here your Azure Application ID
        - **Azure Application Key** - Paste here your Azure Application Key
        - **Azure Subscription ID** - Paste here your Azure Subscription ID
        - **Azure Tenant ID** - Paste here your Azure Tenant ID
        - **VM Size** - Paste here default VM Size for the VMs
        - **Region** - Paste here the public cloud region to be used
        - **Management Group Name** - Paste here the name of the Management Resource Group
  6. Click **Continue**.

CloudShell validates provided settings and creates the new resource.

_**Microsoft Azure Cloud Provider Shell 2G requires you to create an appropriate App template, which would be deployed as part of the sandbox reservation. For details, see the following CloudShell Help article: [Applications' Typical Workflow](https://help.quali.com/Online%20Help/0.0/Portal/Content/CSP/MNG/Mng-Apps.htm?Highlight=App#Adding)**_

# Updating Python Dependencies for Shells
This section explains how to update your Python dependencies folder. This is required when you upgrade a shell that uses new/updated dependencies. It applies to both online and offline dependencies.
### Updating offline Python dependencies
**To update offline Python dependencies:**
1. Download the latest Python dependencies package zip file locally.

2. Extract the zip file to the suitable offline package folder(s). 

3. Terminate the shell’s instance, as explained [here](http://help.quali.com/Online%20Help/9.0/Portal/Content/CSP/MNG/Mng-Exctn-Srv-Exct.htm#Terminat). 

### Updating online Python dependencies
In online mode, the execution server automatically downloads and extracts the appropriate dependencies file to the online Python dependencies repository every time a new instance of the driver or script is created.

**To update online Python dependencies:**
* If there is a live instance of the shell's driver or script, terminate the shell’s instance, as explained [here](http://help.quali.com/Online%20Help/9.0/Portal/Content/CSP/MNG/Mng-Exctn-Srv-Exct.htm#Terminat). If an instance does not exist, the execution server will download the Python dependencies the next time a command of the driver or script runs.

# Typical Workflows
### Connecting Azure Apps to predefined subnets
Using the Azure 2nd Gen shell, it is possible to connect Azure Apps to subnets residing in the Sandbox VNet.

__To connect Azure Apps to a predefined subnet:__
1. Download the _Azure.Subnet.zip_ from the Azure 2nd Gen shell's Integrations [page](https://community.quali.com/repos/5247/azure-cloud-provider-shell-2g).
2. Import the ZIP file into CloudShell Portal.
3. Open the blueprint or sandbox.
4. From the __App / Service__ pane, drag the new __Azure Subnet__ service into the diagram.
5. Set the following details on the service:
   - __Public__: Subnet's privacy policy - __Public__ to enable connections to the subnet's VMs from outside the subnet or __Private__. 
   - __Subnet Name__: The name of the subnet, as displayed in the __Subnets__ blade on Azure.
6. Click __Add__.
7. Deploy the connection(s), as appropriate.
<br>The connection is created like with any other VLAN service. This includes by deploying the App, connecting the purple Connector line if the App is already deployed, and reserving the blueprint.

# References
To download and share integrations, see [Quali Community's Integrations](https://community.quali.com/integrations). 

For instructional training and documentation, see [Quali University](https://www.quali.com/university/).

To suggest an idea for the product, see [Quali's Idea box](https://community.quali.com/ideabox). 

To connect with Quali users and experts from around the world, ask questions and discuss issues, see [Quali's Community forums](https://community.quali.com/forums). 

# Release Notes 

### What's New

For release updates, see the shell's [GitHub releases page](https://github.com/QualiSystems/Microsoft-Azure-Cloud-Provider-Shell-2G/releases).


[1]: https://github.com/QualiSystems/cloudshell-shells-documentaion-templates/blob/master/cloudshell_logo.png
[2]: https://github.com/QualiSystems/cloudshell-shells-documentaion-templates/blob/master/create_a_resource_device.png
