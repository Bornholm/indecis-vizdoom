"""The two questions asked at every decision, in the TypeSafe decision format.

The trained model answers them with its heads, recognized by their names
(fire, turn). The backbone alone answers them in open mode, by comparing the
state with the instructions and the criteria.
"""

FIRE = {
    "type": "noul",
    "instructions": "An enemy is lined up with the crosshair, so firing now would hit it.",
}

TURN_OPTIONS = ("left", "right", "hold", "advance", "scan")

TURN = {
    "type": "choice",
    "instructions": "Aim at the nearest enemy, close the distance to it, or search for one.",
    "criteria": {
        "left": "The nearest enemy is to the left of the crosshair, so turn left toward it",
        "right": "The nearest enemy is to the right of the crosshair, so turn right toward it",
        "hold": "The nearest enemy is lined up with the crosshair and close enough, so stop and shoot",
        "advance": "The nearest enemy is lined up with the crosshair but far away, so walk toward it",
        "scan": "No enemy is in sight, so keep turning to search the room",
    },
}

QUESTIONS = {"fire": FIRE, "turn": TURN}
