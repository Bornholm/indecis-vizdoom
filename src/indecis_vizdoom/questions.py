"""The two questions asked at every decision, in the TypeSafe decision format.

The trained model answers them with its heads, recognized by their names
(fire, turn). The backbone alone answers them in open mode, by comparing the
state with the instructions and the criteria.
"""

FIRE = {
    "type": "noul",
    "instructions": "An enemy is lined up with the crosshair, so firing now would hit it.",
}

TURN_OPTIONS = ("left", "nudge_left", "right", "nudge_right", "hold", "advance", "scan")

TURN = {
    "type": "choice",
    "instructions": "Aim at the nearest enemy, close the distance to it, or search for one.",
    "criteria": {
        "left": "The nearest enemy is well to the left of the crosshair, so turn left toward it",
        "nudge_left": "The nearest enemy is slightly to the left of the crosshair, so turn left a little",
        "right": "The nearest enemy is well to the right of the crosshair, so turn right toward it",
        "nudge_right": "The nearest enemy is slightly to the right of the crosshair, so turn right a little",
        "hold": "The nearest enemy is lined up with the crosshair and close, so stop and shoot",
        "advance": "The nearest enemy is lined up with the crosshair but not close, so walk toward it",
        "scan": "No enemy is in sight, so walk and turn to search the room",
    },
}

QUESTIONS = {"fire": FIRE, "turn": TURN}
