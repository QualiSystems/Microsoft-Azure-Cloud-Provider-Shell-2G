def get_name_from_resource_id(resource_id):
    """Get resource name from the Azure resource id

    :param str resource_id: Azure resource Id
    :return: Azure resource name
    :rtype: str
    """
    return resource_id.split("/")[-1]
