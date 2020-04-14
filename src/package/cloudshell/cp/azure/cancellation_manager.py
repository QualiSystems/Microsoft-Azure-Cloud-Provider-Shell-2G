class CancellationContextManager:
    def __init__(self, cancellation_context):
        """

        :param cancellation_context:
        """
        self.cancellation_context = cancellation_context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cancellation_context.is_cancelled:
            raise Exception("Command was cancelled from the portal")
