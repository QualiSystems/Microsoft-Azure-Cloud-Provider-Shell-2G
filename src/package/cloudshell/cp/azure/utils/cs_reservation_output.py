class CloudShellReservationOutput:
    ERROR_MESSAGE_HTML_TPL = "<html><body><span style='color: red;'>{message}</span></body></html>"

    def __init__(self, cs_api, reservation_id, logger):
        """

        :param cs_api:
        :param reservation_id:
        :param logger:
        """
        self._cs_api = cs_api
        self._reservation_id = reservation_id
        self._logger = logger

    def write_error_message(self, message):
        """

        :param message:
        :return:
        """
        self._logger.debug(f"Sending message: '{message}' to the reservation {self._reservation_id} output")
        self._cs_api.WriteMessageToReservationOutput(reservationId=self._reservation_id,
                                                     message=self.ERROR_MESSAGE_HTML_TPL.format(message=message))
