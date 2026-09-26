"""Muay Thai - a turn-based fighting game in the terminal.

Run it with:   python muay_thai/game.py
Fighter stats live in characters.py.

How a fight works:
- Each exchange, both fighters secretly pick a move, then both moves happen.
  Faster moves go first (a jab beats a kick to the punch).
- You are either at range (outside) or locked up in the clinch.
  At range, reach matters and kicks are strong. In the clinch, reach stops
  mattering and knees, elbows and sweeps take over.
- Win by KO (health hits 0), TKO (3 knockdowns) or on the judges' scorecards.
"""
import random
import time

from characters import FIGHTERS, SPECIALS

ROUNDS = 3
EXCHANGES_PER_ROUND = 8
MAX_STAMINA = 100
KNOCKDOWNS_FOR_TKO = 3

# damage, stamina cost, base accuracy (%), speed (higher goes first)
MOVES = {
    "jab": {"name": "Jab", "damage": 4, "stamina": 3, "accuracy": 85, "speed": 3,
            "tip": "fast and cheap, low damage"},
    "cross": {"name": "Right cross", "damage": 8, "stamina": 6, "accuracy": 72, "speed": 2,
              "tip": "solid punch"},
    "teep": {"name": "Teep", "damage": 5, "stamina": 6, "accuracy": 75, "speed": 2,
             "tip": "push kick - stops knees, elbows and clinch grabs"},
    "kick": {"name": "Roundhouse kick", "damage": 12, "stamina": 12, "accuracy": 65, "speed": 1,
             "tip": "big damage but slow and tiring, gets checked by a block"},
    "elbow": {"name": "Elbow", "damage": 10, "stamina": 8, "accuracy": 65, "speed": 2,
              "tip": "hard hitting, better in the clinch"},
    "knee": {"name": "Knee", "damage": 10, "stamina": 9, "accuracy": 68, "speed": 2,
             "tip": "hard hitting, best in the clinch"},
    "clinch": {"name": "Grab the clinch", "damage": 0, "stamina": 6, "accuracy": 0, "speed": 1,
               "tip": "tie them up - reach stops mattering"},
    "sweep": {"name": "Sweep", "damage": 3, "stamina": 10, "accuracy": 0, "speed": 1,
              "tip": "dump them - drains their stamina, judges love it"},
    "break": {"name": "Break the clinch", "damage": 0, "stamina": 5, "accuracy": 0, "speed": 2,
              "tip": "shove them off, back to range"},
    "block": {"name": "Block", "damage": 0, "stamina": 0, "accuracy": 0, "speed": 4,
              "tip": "take 70% less damage, get stamina back"},
}

OUTSIDE_MOVES = ["jab", "cross", "teep", "kick", "elbow", "knee", "clinch", "block"]
CLINCH_MOVES = ["knee", "elbow", "sweep", "break", "block"]
LONG_MOVES = ["jab", "cross", "teep", "kick"]

# Muay Thai judges score kicks and knees higher than punches
SCORING_BONUS = {"kick": 1.3, "knee": 1.3}


# ---------- fighters ----------

def make_fighter(name, cpu):
    fighter = dict(FIGHTERS[name])
    fighter["name"] = name
    fighter["cpu"] = cpu
    fighter["max_hp"] = round(70 + fighter["weight"] * 0.5)
    fighter["hp"] = fighter["max_hp"]
    fighter["stamina"] = MAX_STAMINA
    fighter["knockdowns"] = 0
    fighter["round_knockdowns"] = 0
    fighter["points"] = 0  # judges' points this round
    fighter["card"] = 0  # total on the scorecards
    fighter["history"] = []  # moves used so far (the CPU watches yours)
    return fighter


def reach(fighter):
    if fighter["special"] == "long_reach":
        return fighter["height"] + 4
    return fighter["height"]


def format_height(inches):
    return f"{int(inches // 12)}'{inches % 12:g}\""


def stamina_cost(fighter, move):
    cost = MOVES[move]["stamina"]
    if move == "kick" and fighter["special"] == "fast_kicks":
        cost = round(cost * 0.6)
    return cost


def move_speed(fighter, move):
    if move == "kick" and fighter["special"] == "fast_kicks":
        return 3
    return MOVES[move]["speed"]


# ---------- the fight ----------

def new_fight(fighter1, fighter2, quiet=False):
    return {
        "fighters": [fighter1, fighter2],
        "position": "outside",
        "quiet": quiet,  # True = no printing (used by the balance test)
        "winner": None,
        "method": None,
        "pushed": None,  # fighter pushed back by a teep this exchange
        "dropped": None,  # fighter knocked down this exchange
    }


def say(fight, text):
    if not fight["quiet"]:
        print(text)


def available_moves(fight):
    if fight["position"] == "clinch":
        return CLINCH_MOVES
    return OUTSIDE_MOVES


def hit_chance(fight, att, dfn, move):
    chance = MOVES[move]["accuracy"]
    chance -= (dfn["fight_iq"] - 5) * 2
    if fight["position"] == "clinch":
        # inside it's more about grip and position than slick technique
        chance += (att["skill"] - dfn["skill"]) * 1.5
        if att["special"] == "clinch":
            chance += 15
    else:
        chance += (att["skill"] - dfn["skill"]) * 3
        if move in LONG_MOVES:
            reach_edge = reach(att) - reach(dfn)
            chance += max(-10, min(10, reach_edge))
        else:
            # knees and elbows from range mean stepping in first
            chance -= 15
            if dfn["special"] == "long_reach":
                chance -= 10
    if move == "kick" and att["special"] == "fast_kicks":
        chance += 15
    if att["stamina"] < 30:
        chance -= (30 - att["stamina"]) // 2
    return max(5, min(95, round(chance)))


def damage(att, move, in_clinch, crit, blocked):
    dmg = MOVES[move]["damage"]
    dmg *= 0.75 + att["strength"] * 0.04 + (att["weight"] - 55) * 0.003
    dmg *= 0.7 + 0.3 * att["stamina"] / MAX_STAMINA
    special = att["special"]
    if special == "power_kicks" and move in ["kick", "teep"]:
        dmg *= 1.4
    if special == "fast_kicks" and move == "kick":
        dmg *= 0.85
    if special == "right_cross" and move == "cross":
        dmg *= 1.6
    if in_clinch and move in ["knee", "elbow"]:
        dmg *= 1.2
        if special == "clinch":
            dmg *= 1.3
    dmg *= random.uniform(0.85, 1.15)
    if crit:
        dmg *= 1.5
    if blocked:
        dmg *= 0.3
    return max(1, round(dmg))


def knockdown(fight, att, dfn):
    dfn["knockdowns"] += 1
    dfn["round_knockdowns"] += 1
    att["points"] += 10
    fight["dropped"] = dfn
    fight["position"] = "outside"
    say(fight, f"*** {dfn['name'].upper()} GOES DOWN! *** (knockdown {dfn['knockdowns']} of {KNOCKDOWNS_FOR_TKO})")


def strike(fight, att, dfn, move, dfn_move):
    label = MOVES[move]["name"].lower()
    in_clinch = fight["position"] == "clinch"
    if random.randint(1, 100) > hit_chance(fight, att, dfn, move):
        say(fight, f"{att['name']}'s {label} misses.")
        return

    blocked = dfn_move == "block"
    crit = not blocked and random.randint(1, 100) <= att["skill"] * 2
    dmg = damage(att, move, in_clinch, crit, blocked)
    dfn["hp"] -= dmg
    att["points"] += dmg * SCORING_BONUS.get(move, 1)
    if move == "teep":
        fight["pushed"] = dfn

    if blocked:
        say(fight, f"{dfn['name']} blocks {att['name']}'s {label}, still takes {dmg}.")
        if move == "kick" and att["special"] != "fast_kicks":
            att["hp"] -= 3
            say(fight, f"Checked! {att['name']} kicks a shin and takes 3 back.")
        if random.randint(1, 100) <= dfn["fight_iq"] * 4:
            counter = damage(dfn, "jab", in_clinch, False, False)
            att["hp"] -= counter
            dfn["points"] += counter
            say(fight, f"{dfn['name']} reads it and counters for {counter}.")
    elif crit:
        say(fight, f"CLEAN SHOT! {att['name']}'s {label} lands for {dmg}!")
        knockdown_chance = 30
        if move == "cross" and att["special"] == "right_cross":
            knockdown_chance = 60
        if dfn["hp"] > 0 and random.randint(1, 100) <= knockdown_chance:
            knockdown(fight, att, dfn)
    else:
        say(fight, f"{att['name']}'s {label} lands for {dmg}.")

    double_kick = move == "kick" and att["special"] == "fast_kicks" and random.randint(1, 100) <= 35
    if double_kick and dfn["hp"] > 0 and fight["dropped"] is not dfn:
        second = damage(att, "kick", in_clinch, False, blocked)
        dfn["hp"] -= second
        att["points"] += second * SCORING_BONUS["kick"]
        say(fight, f"Too fast! {att['name']} snaps in a second kick for {second}.")


def attempt_clinch(fight, att, dfn, dfn_move):
    if fight["position"] == "clinch":
        say(fight, f"{att['name']} and {dfn['name']} lock up.")
        return
    if fight["pushed"] is att:
        say(fight, f"{att['name']} gets teeped away before they can grab.")
        return
    chance = 55 + (att["strength"] - dfn["strength"]) * 4 + (att["skill"] - dfn["skill"]) * 2
    if att["special"] == "clinch":
        chance += 20
    if dfn["special"] == "long_reach":
        chance -= 10
    if dfn_move == "block":
        chance += 10
    if random.randint(1, 100) <= max(10, min(90, chance)):
        fight["position"] = "clinch"
        say(fight, f"{att['name']} grabs the clinch!")
    else:
        say(fight, f"{dfn['name']} fights off {att['name']}'s clinch attempt.")


def attempt_break(fight, att, dfn):
    chance = 60 + (att["strength"] - dfn["strength"]) * 5 + (att["skill"] - dfn["skill"]) * 2
    if dfn["special"] == "clinch":
        chance -= 30
    if random.randint(1, 100) <= max(10, min(90, chance)):
        fight["position"] = "outside"
        say(fight, f"{att['name']} shoves {dfn['name']} off and breaks the clinch.")
    else:
        say(fight, f"{att['name']} can't break {dfn['name']}'s grip.")


def attempt_sweep(fight, att, dfn):
    chance = 40 + (att["strength"] - dfn["strength"]) * 4 + (att["skill"] - dfn["skill"]) * 3
    chance += (att["weight"] - dfn["weight"]) * 0.5
    if att["special"] == "clinch":
        chance += 20
    if random.randint(1, 100) <= max(5, min(90, chance)):
        dfn["hp"] -= MOVES["sweep"]["damage"]
        dfn["stamina"] = max(0, dfn["stamina"] - 15)
        att["points"] += 8
        fight["position"] = "outside"
        say(fight, f"{att['name']} dumps {dfn['name']} on the canvas! Big points with the judges.")
    else:
        say(fight, f"{dfn['name']} keeps their balance.")


def do_move(fight, att, move, dfn, dfn_move):
    att["stamina"] = max(0, att["stamina"] - stamina_cost(att, move))
    label = MOVES[move]["name"].lower()
    if move == "block":
        return
    if move == "clinch":
        attempt_clinch(fight, att, dfn, dfn_move)
    elif move not in available_moves(fight):
        say(fight, f"{att['name']}'s {label} comes to nothing - the position changed.")
    elif fight["pushed"] is att and move in ["knee", "elbow"]:
        say(fight, f"{att['name']} gets teeped away and can't land the {label}.")
    elif move == "break":
        attempt_break(fight, att, dfn)
    elif move == "sweep":
        attempt_sweep(fight, att, dfn)
    else:
        strike(fight, att, dfn, move, dfn_move)


def exchange(fight, moves):
    fight["pushed"] = None
    fight["dropped"] = None
    f1, f2 = fight["fighters"]
    turns = [(f1, moves[0], f2, moves[1]), (f2, moves[1], f1, moves[0])]

    # faster move goes first, a tie is a coin flip
    speed1 = move_speed(f1, moves[0])
    speed2 = move_speed(f2, moves[1])
    if speed2 > speed1 or (speed2 == speed1 and random.random() < 0.5):
        turns.reverse()

    for att, move, dfn, dfn_move in turns:
        if fight["dropped"] is att:
            say(fight, f"{att['name']} is on the canvas and can't fire back.")
            continue
        do_move(fight, att, move, dfn, dfn_move)
        if att["hp"] <= 0 or dfn["hp"] <= 0:
            break

    for fighter, move in zip(fight["fighters"], moves):
        fighter["history"].append(move)
        if move == "block":
            fighter["stamina"] = min(MAX_STAMINA, fighter["stamina"] + 15)
        else:
            fighter["stamina"] = min(MAX_STAMINA, fighter["stamina"] + 5)


def check_finish(fight):
    f1, f2 = fight["fighters"]
    for loser, winner in [(f1, f2), (f2, f1)]:
        if loser["hp"] <= 0:
            fight["winner"] = winner
            fight["method"] = "KO"
            return True
        if loser["knockdowns"] >= KNOCKDOWNS_FOR_TKO:
            fight["winner"] = winner
            fight["method"] = f"TKO ({KNOCKDOWNS_FOR_TKO} knockdowns)"
            return True
    return False


def score_round(fight, round_num):
    f1, f2 = fight["fighters"]
    card1, card2 = 10, 10
    gap = f1["points"] - f2["points"]
    if gap > 3:
        card2 = 9
    elif gap < -3:
        card1 = 9
    card1 -= f1["round_knockdowns"]
    card2 -= f2["round_knockdowns"]
    f1["card"] += card1
    f2["card"] += card2
    say(fight, f"\nJudges score round {round_num}: {f1['name']} {card1} - {card2} {f2['name']}")
    for fighter in fight["fighters"]:
        fighter["points"] = 0
        fighter["round_knockdowns"] = 0


# ---------- choosing moves ----------

def cpu_choose(fight, me, opp):
    options = available_moves(fight)

    # low fight IQ = more wild, random choices
    if random.randint(1, 100) <= (10 - me["fight_iq"]) * 7:
        return random.choice(options)

    weights = {move: 1 for move in options}
    recent = opp["history"][-3:]

    if me["stamina"] < 20:
        weights["block"] += 6

    if fight["position"] == "outside":
        reach_gap = reach(me) - reach(opp)
        if reach_gap >= 3:
            weights["jab"] += 3
            weights["teep"] += 2
            weights["kick"] += 2
        elif reach_gap <= -3:
            weights["clinch"] += 3
            weights["knee"] += 1
        if me["special"] in ["power_kicks", "fast_kicks"]:
            weights["kick"] += 4
        if me["special"] == "right_cross":
            weights["cross"] += 4
        if me["special"] == "clinch":
            weights["clinch"] += 4
        if me["special"] == "long_reach":
            weights["jab"] += 2
            weights["teep"] += 2
        if recent.count("kick") >= 2:
            weights["block"] += 3
            weights["clinch"] += 2
        if recent.count("clinch") + recent.count("knee") + recent.count("elbow") >= 2:
            weights["teep"] += 4
        if recent.count("block") >= 2:
            weights["clinch"] += 3
        if opp["hp"] < opp["max_hp"] * 0.25:
            weights["kick"] += 2
            weights["cross"] += 2
    else:
        clinch_edge = me["strength"] - opp["strength"] + (me["weight"] - opp["weight"]) / 5
        if me["special"] == "clinch":
            clinch_edge += 5
        if opp["special"] == "clinch":
            clinch_edge -= 5
        if clinch_edge >= 0:
            weights["knee"] += 4
            weights["elbow"] += 2
            weights["sweep"] += 2
        else:
            weights["break"] += 4
            weights["elbow"] += 1
        if recent.count("block") >= 2:
            weights["sweep"] += 3

    moves = list(weights)
    return random.choices(moves, weights=[weights[m] for m in moves])[0]


def ask_number(prompt, low, high):
    while True:
        answer = input(prompt).strip()
        if answer.isdigit() and low <= int(answer) <= high:
            return int(answer)
        print(f"Type a number from {low} to {high}.")


def human_choose(fight, me, opp, opp_move):
    # high fight IQ = sometimes you see what the CPU is about to do
    if opp_move is not None and random.randint(1, 100) <= (me["fight_iq"] - 2) * 7:
        print(f"  [Fight IQ] You read {opp['name']} - they're going for a {MOVES[opp_move]['name'].lower()}!")
    options = available_moves(fight)
    print(f"{me['name']}, pick your move:")
    for number, move in enumerate(options, start=1):
        print(f"  {number}) {MOVES[move]['name']:<17} (stamina {stamina_cost(me, move):>2})  {MOVES[move]['tip']}")
    return options[ask_number("> ", 1, len(options)) - 1]


def choose_moves(fight):
    f1, f2 = fight["fighters"]
    pairs = [(f1, f2), (f2, f1)]
    moves = [None, None]
    # CPUs pick first so a human with good fight IQ can read them
    for i, (me, opp) in enumerate(pairs):
        if me["cpu"]:
            moves[i] = cpu_choose(fight, me, opp)
    for i, (me, opp) in enumerate(pairs):
        if not me["cpu"]:
            cpu_move = moves[1 - i] if opp["cpu"] else None
            moves[i] = human_choose(fight, me, opp, cpu_move)
            if i == 0 and not f2["cpu"]:
                input("Press Enter, then hand over to the other player...")
                print("\n" * 50)
    return moves


# ---------- screens ----------

def bar(value, maximum, width):
    filled = round(width * max(0, value) / maximum)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def show_status(fight, round_num, exchange_num):
    if fight["quiet"]:
        return
    where = "IN THE CLINCH" if fight["position"] == "clinch" else "at range"
    print(f"\n--- Round {round_num}/{ROUNDS}, exchange {exchange_num}/{EXCHANGES_PER_ROUND} - {where} ---")
    for f in fight["fighters"]:
        print(f"{f['name']:<6} HP {bar(f['hp'], f['max_hp'], 20)} {max(0, f['hp']):>3}/{f['max_hp']:<4}"
              f"STA {bar(f['stamina'], MAX_STAMINA, 10)} {f['stamina']:>3}")


def show_roster():
    print(f"\n   {'Name':<7}{'Height':<8}{'Weight':<8}{'Str':<5}{'Skill':<7}{'IQ':<4}Special")
    for number, (name, s) in enumerate(FIGHTERS.items(), start=1):
        print(f"{number}) {name:<7}{format_height(s['height']):<8}{str(s['weight']) + 'kg':<8}"
              f"{s['strength']:<5}{s['skill']:<7}{s['fight_iq']:<4}{SPECIALS[s['special']]}")


def show_tale_of_the_tape(f1, f2):
    print(f"\nTALE OF THE TAPE: {f1['name']} vs {f2['name']}")
    print(f"  Reach:  {reach(f1)}in vs {reach(f2)}in")
    print(f"  Weight: {f1['weight']}kg vs {f2['weight']}kg")
    print(f"  Health: {f1['max_hp']} vs {f2['max_hp']}")


def pick_fighter(prompt, taken=None):
    names = list(FIGHTERS)
    while True:
        name = names[ask_number(prompt, 1, len(names)) - 1]
        if name != taken:
            return name
        print(f"{name} is already in the fight - pick someone else.")


def run_fight(fight):
    f1, f2 = fight["fighters"]
    for round_num in range(1, ROUNDS + 1):
        say(fight, f"\n========== ROUND {round_num} ==========")
        for exchange_num in range(1, EXCHANGES_PER_ROUND + 1):
            show_status(fight, round_num, exchange_num)
            moves = choose_moves(fight)
            say(fight, "")
            exchange(fight, moves)
            if check_finish(fight):
                say(fight, f"\n{fight['winner']['name'].upper()} WINS BY {fight['method']}!")
                return fight["winner"]
            if f1["cpu"] and f2["cpu"] and not fight["quiet"]:
                time.sleep(1.2)
        score_round(fight, round_num)
        # rest in the corner between rounds
        for fighter in fight["fighters"]:
            fighter["stamina"] = min(MAX_STAMINA, fighter["stamina"] + 40)
            fighter["hp"] = min(fighter["max_hp"], fighter["hp"] + round(fighter["max_hp"] * 0.05))
        fight["position"] = "outside"

    say(fight, f"\nFINAL SCORECARDS: {f1['name']} {f1['card']} - {f2['card']} {f2['name']}")
    if f1["card"] == f2["card"]:
        say(fight, "It's a DRAW!")
        return None
    fight["winner"] = f1 if f1["card"] > f2["card"] else f2
    fight["method"] = "decision"
    say(fight, f"{fight['winner']['name'].upper()} WINS BY DECISION!")
    return fight["winner"]


def play_match(humans):
    show_roster()
    if humans == 0:
        name1 = pick_fighter("Pick the first CPU fighter: ")
        name2 = pick_fighter("Pick the second CPU fighter: ", taken=name1)
    else:
        name1 = pick_fighter("Player 1, pick your fighter: ")
        if humans == 2:
            name2 = pick_fighter("Player 2, pick your fighter: ", taken=name1)
        else:
            name2 = pick_fighter("Pick your CPU opponent: ", taken=name1)
    f1 = make_fighter(name1, cpu=humans == 0)
    f2 = make_fighter(name2, cpu=humans < 2)
    show_tale_of_the_tape(f1, f2)
    run_fight(new_fight(f1, f2))


def balance_test(fights_per_matchup=200):
    """CPU vs CPU for every matchup - shows who beats who and how often."""
    names = list(FIGHTERS)
    print(f"\nRunning {fights_per_matchup} fights per matchup...")
    print("Win % of the row fighter against the column fighter:\n")
    print(" " * 7 + "".join(f"{name:>7}" for name in names) + "  overall")
    for name in names:
        row = f"{name:<7}"
        total_wins = 0
        for other in names:
            if other == name:
                row += f"{'-':>7}"
                continue
            wins = 0
            for _ in range(fights_per_matchup):
                fight = new_fight(make_fighter(name, cpu=True), make_fighter(other, cpu=True), quiet=True)
                winner = run_fight(fight)
                if winner is not None and winner["name"] == name:
                    wins += 1
            total_wins += wins
            row += f"{100 * wins // fights_per_matchup:>6}%"
        overall = 100 * total_wins // (fights_per_matchup * (len(names) - 1))
        print(row + f"{overall:>8}%")
    print("\n(Draws count as not winning. CPU smarts come from fight IQ, so this")
    print(" measures the stats AND how well each CPU plays.)")


def main():
    print("=" * 40)
    print("        M U A Y   T H A I")
    print("     the art of eight limbs")
    print("=" * 40)
    while True:
        print("\n1) Player vs CPU")
        print("2) Player vs Player (same keyboard)")
        print("3) Watch CPU vs CPU")
        print("4) Balance test (who beats who)")
        print("5) Quit")
        choice = ask_number("> ", 1, 5)
        if choice == 1:
            play_match(humans=1)
        elif choice == 2:
            play_match(humans=2)
        elif choice == 3:
            play_match(humans=0)
        elif choice == 4:
            balance_test()
        else:
            print("Wai kru. See you next time.")
            break


if __name__ == "__main__":
    main()
