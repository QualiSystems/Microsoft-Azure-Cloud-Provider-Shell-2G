import uuid
import re


def generate_name(name, postfix=None, max_length=24):
    """Generate name based on the given one with a maximum allowed length.

    Will replace all special characters (some Azure resources have this requirements).
    :param str name: App name
    :param str postfix: If postfix is empty method will generate unique 8 char long id
    :param int max_length: Maximum allowed length for the generated name
    :return: (str) generated name
    :rtype: str
    """
    # replace special characters. Remove dash character only if at the beginning.
    name = re.sub("[^a-zA-Z0-9-]|^-+", "", name)

    if postfix is None:
        postfix = generate_short_unique_string()

    name = name[:max_length-len(postfix)-1]
    name.rstrip("-")

    return f"{name}-{postfix}"


def generate_short_unique_string():
    """Generate a short unique string

    method generate a guid and return the first 8 characteres of the new guid
    :rtype: str
    """
    unique_id = str(uuid.uuid4())[:8]
    return unique_id


def format_subnet_name(resource_group_name, subnet_cidr):
    return (resource_group_name + '_' + subnet_cidr).replace(' ', '').replace('/', '-')
