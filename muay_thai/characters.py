# Muay Thai fighter stats - edit these to change the fighters.
#
# height   - in inches (5'2" = 62, 5'10.5" = 70.5). Taller = longer reach.
# weight   - in kg. Heavier = more health, a bit more power, better sweeps.
# strength - 1 to 10. More damage, better in the clinch.
# skill    - 1 to 10. Land more, get more clean shots (crits).
# fight_iq - 1 to 10. Harder to hit, counter-punches, reads the opponent's
#            next move, and makes the CPU fight smarter.
# special  - one of the keys in SPECIALS below, or None.
#
# You only gave the ORDER for strength / skill / fight IQ, not how big the
# gaps are, so the exact numbers are a guess. Change them to tune the game.

FIGHTERS = {
    "Ralph": {"height": 62, "weight": 60, "strength": 5, "skill": 4, "fight_iq": 6, "special": "clinch"},
    "Zhen": {"height": 63, "weight": 52, "strength": 4, "skill": 5, "fight_iq": 4, "special": "fast_kicks"},
    # Akira was missing from the strength order - 6 is a placeholder guess.
    "Akira": {"height": 67, "weight": 62, "strength": 6, "skill": 7, "fight_iq": 8, "special": "right_cross"},
    # Jed doesn't have a special ability yet.
    "Jed": {"height": 68, "weight": 60, "strength": 6, "skill": 8, "fight_iq": 9, "special": None},
    "Tim": {"height": 69.5, "weight": 85, "strength": 9, "skill": 6, "fight_iq": 5, "special": "power_kicks"},
    "Jacob": {"height": 70.5, "weight": 55, "strength": 7, "skill": 9, "fight_iq": 7, "special": "long_reach"},
}

SPECIALS = {
    "long_reach": "Long reach - long strikes land more, hard to get close to",
    "power_kicks": "Really strong kicks - kicks and teeps hit much harder",
    "clinch": "Clinch master - easy to grab, brutal knees/elbows inside",
    "right_cross": "Really strong right cross - hits harder, drops people",
    "fast_kicks": "Really fast kicks - land first, can double up, bit softer",
    None: "None yet",
}
