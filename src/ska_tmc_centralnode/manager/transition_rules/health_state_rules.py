"""This Lists all rules required for ObsState aggregation"""

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
            '$all(["DEGRADED" in all_unique_health_states'
            ' or "OFFLINE" in all_unique_admin_modes, '
            '"FAILED" not in all_unique_health_states])'
        )
    ],
    "FAILED": [Rule('"FAILED" in all_unique_health_states')],
    "UNKNOWN": [Rule('"UNKNOWN" in all_unique_health_states')],
}

HEALTH_STATE_RULES_MID = HEALTH_STATE_RULES | {
    "FAILED": [
        Rule('"FAILED" in all_unique_health_states'),
        Rule(
            '$any(["elt/master" in key and '
            'event_data.health_state_data[key]["health_state"] == "FAILED" '
            "for key in event_data.health_state_data.keys])"
        ),
    ]
}
