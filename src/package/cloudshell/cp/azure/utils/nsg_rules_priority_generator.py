class NSGRulesPriorityGenerator:
    RULE_DEFAULT_PRIORITY = 1000
    RULE_PRIORITY_INCREASE_STEP = 5

    def __init__(self, nsg_name, resource_group_name, include_existing_rules=False, nsg_actions=None):
        """

        :param str nsg_name:
        :param str resource_group_name:
        :param bool include_existing_rules:
        :param nsg_actions:
        """
        self._nsg_name = nsg_name
        self._resource_group_name = resource_group_name
        self._nsg_actions = nsg_actions
        self._existing_priorities = []

        if include_existing_rules:
            self._populate_existing_rules_priorities()

        self._existing_priorities.append(float("inf"))

    def _populate_existing_rules_priorities(self):
        """

        :return:
        """
        self._existing_priorities = [rule.priority for rule in self._nsg_actions.get_nsg_rules(
            resource_group_name=self._resource_group_name,
            nsg_name=self._nsg_name)]

        self._existing_priorities.sort()

    def get_priority(self, start_from=RULE_DEFAULT_PRIORITY, increase_step=RULE_PRIORITY_INCREASE_STEP):
        """

        :param int start_from:
        :param int increase_step:
        :return:
        """
        priority = start_from
        i = 0

        while i <= len(self._existing_priorities):
            if priority > self._existing_priorities[i]:
                i += 1

            elif priority == self._existing_priorities[i]:
                priority += increase_step
                i += 1

            else:
                self._existing_priorities.insert(i, priority)
                return priority
