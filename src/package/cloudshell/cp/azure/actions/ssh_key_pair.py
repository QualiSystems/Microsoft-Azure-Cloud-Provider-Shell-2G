from cloudshell.cp.core.utils import generate_ssh_key_pair


class SSHKeyPairActions:
    SSH_FILE_SHARE_NAME = "sshkeypair"
    SSH_FILE_SHARE_DIRECTORY = ""
    SSH_PUB_KEY_NAME = "id_rsa.pub"
    SSH_PRIVATE_KEY_NAME = "id_rsa"

    def __init__(self, azure_client, logger):
        """

        :param cloudshell.cp.azure.client.AzureAPIClient azure_client:
        :param logging.Logger logger:
        """
        self._azure_client = azure_client
        self._logger = logger

    def create_ssh_key_pair(self):
        """

        :return:
        """
        return generate_ssh_key_pair()

    def save_ssh_public_key(self, resource_group_name, storage_account_name, public_key):
        """

        :param str resource_group_name:
        :param str storage_account_name:
        :param str public_key:
        :return:
        """
        self._azure_client.create_file(
            group_name=resource_group_name,
            storage_name=storage_account_name,
            share_name=self.SSH_FILE_SHARE_NAME,
            directory_name=self.SSH_FILE_SHARE_DIRECTORY,
            file_name=self.SSH_PUB_KEY_NAME,
            file_content=public_key.encode())

    def save_ssh_private_key(self, resource_group_name, storage_account_name, private_key):
        """

        :param str resource_group_name:
        :param str storage_account_name:
        :param str private_key:
        :return:
        """
        self._azure_client.create_file(
            group_name=resource_group_name,
            storage_name=storage_account_name,
            share_name=self.SSH_FILE_SHARE_NAME,
            directory_name=self.SSH_FILE_SHARE_DIRECTORY,
            file_name=self.SSH_PRIVATE_KEY_NAME,
            file_content=private_key.encode())
