class RollbackCommandsManager:
    def __init__(self, logger):
        self.commands = []
        self.logger = logger

    def register_command(self, command):
        """

        :param RollbackCommand command:
        :return:
        """
        self.commands.append(command)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            for command in self.commands[::-1]:
                if command.executed:
                    try:
                        # self.logger.info(f"Running rollback for command {command}")
                        command.rollback()
                    except Exception:
                        print(f"Unable to perform rollback for command {command}")
                        self.logger.warning(f"Unable to perform rollback for command {command}", exc_info=True)


class RollbackCommand:
    def __init__(self, rollback_manager, cancellation_manager, *args, **kwargs):
        """

        :param RollbackCommandsManager rollback_manager:
        :param cloudshell.cp.core.cancellation_manager.CancellationContextManager cancellation_manager:
        """
        self._rollback_manager = rollback_manager
        self._cancellation_manager = cancellation_manager
        self.executed = False
        rollback_manager.register_command(self)

    def _execute(self, *args, **kwargs):
        raise NotImplementedError(f"Class {type(self)} must implement method '_execute'")

    def rollback(self):
        raise NotImplementedError(f"Class {type(self)} must implement method 'rollback'")

    def execute(self):
        with self._rollback_manager:
            with self._cancellation_manager:
                command_result = self._execute()
                self.executed = True
                return command_result
