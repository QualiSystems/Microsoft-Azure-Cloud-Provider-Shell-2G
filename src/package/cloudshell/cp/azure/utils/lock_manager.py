from threading import Lock


class ThreadLockManager:
    def __init__(self):
        self._locks = {}

    def get_lock(self, key):
        """

        :param str key:
        :return:
        """
        if key not in self._locks:
            self._locks[key] = Lock()

        return self._locks[key]

    def remove_lock(self, key):
        """

        :param key:
        :return:
        """
        try:
            del self._locks[key]
        except KeyError:
            pass
