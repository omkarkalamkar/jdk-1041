"""This Lists all rules required for ObsState aggregation
"""

from rule_engine import Rule

HEALTH_STATE_RULES = {
    "OK": [
        Rule(
            '["OK"] == all_unique_health_states '
            'and ["ONLINE"] == all_unique_admin_modes'
        )
    ],
    "DEGRADED": [
        Rule(
            '"DEGRADED" in all_unique_health_states'
            ' and["OFFLINE"] == all_unique_admin_modes'
        )
    ],
    "FAILED": [Rule('"FAILED" in all_unique_health_states')],
    "UNKNOWN": [Rule('"FAILED" in all_unique_health_states')],
}

HEALTH_STATE_RULES_MID = HEALTH_STATE_RULES | {
    "OK": [
        Rule('["OK"] == all_unique_health_states'),
        Rule('["ONLINE"] == all_unique_admin_modes'),
    ],
    "DEGRADED": [
        Rule('"DEGRADED" in all_unique_health_states'),
        Rule('["OFFLINE"] == all_unique_admin_modes'),
    ],
    "FAILED": [
        Rule('"FAILED" in all_unique_health_states'),
        Rule(
            'any([key.contains("elt/master") '
            'and event_data.health_state_data[key].health_state == "FAILED" '
            "for key in event_data.health_state_data])"
        ),
    ],
    "UNKNOWN": [Rule('"FAILED" in all_unique_health_states')],
}

HEALTH_STATE_RULES_LOW = HEALTH_STATE_RULES | {
    "OK": [
        Rule('["OK"] == all_unique_health_states'),
        Rule('["ONLINE"] == all_unique_admin_modes'),
    ],
    "DEGRADED": [
        Rule('"DEGRADED" in all_unique_health_states'),
        Rule('["OFFLINE"] == all_unique_admin_modes'),
    ],
    "FAILED": [Rule('"FAILED" in all_unique_health_states')],
    "UNKNOWN": [Rule('"FAILED" in all_unique_health_states')],
}
