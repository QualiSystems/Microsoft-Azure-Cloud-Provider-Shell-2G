import traceback

from msrest.exceptions import ClientRequestError
from msrestazure.azure_exceptions import CloudError
# todo: check if this should be replaced to requests.exceptions.ConnectionError
from requests.packages.urllib3.exceptions import ConnectionError

RETRYABLE_ERROR_STRING = "retryable"
RETRYABLE_WAIT_TIME = 2000
RETRYABLE_ERROR_MAX_ATTEMPTS = 20


def retry_on_connection_error(exception):
    """Return True if we should retry (in this case when it's an IOError), False otherwise

    :param exception:
    """
    return any([isinstance(exception, ClientRequestError),
                isinstance(exception, ConnectionError),
                _is_pool_closed_error()])


def _is_pool_closed_error():
    return "pool is closed" in traceback.format_exc()


def retry_on_retryable_error(exception):
    """Return True if we should retry (in this case when it's an RetryableError), False otherwise

    :param exceptions.Exception exception:
    """
    return isinstance(exception, CloudError) and RETRYABLE_ERROR_STRING in exception.message.lower()
