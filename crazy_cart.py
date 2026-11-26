import random

TRACK_LENGTH = 100
RIVAL_NAMES = ["Turbo Gran", "Captain Wobble", "Sir Skids"]

CRAZY_EVENTS = [
    ("A banana peel! You spin out.", -8),
    ("A rogue goat headbutts you forward!", 10),
    ("Your engine sneezes.", -4),
    ("A tailwind made of pigeons carries you!", 7),
    ("You hit a puddle of custard.", -6),
    ("A rocket falls from the sky and lands in your cart. Whoosh!", 15),
    ("Nothing crazy happens. Suspicious...", 0),
]


def draw_track(racers):
    print()
    for name, position in racers.items():
        spot = min(position, TRACK_LENGTH) * 40 // TRACK_LENGTH
        lane = "." * spot + "🛒" + "." * (40 - spot)
        print(f"{name:>15} |{lane}| {min(position, TRACK_LENGTH)}m")
    print()


def player_move(fuel):
    print(f"Fuel: {fuel}")
    print("1) Drive   (safe, 5-10m)")
    print("2) Boost   (12-20m, costs 3 fuel, might backfire)")
    print("3) Gamble  (roll the crazy dice)")
    choice = input("Pick 1, 2 or 3: ").strip()

    if choice == "2" and fuel >= 3:
        fuel -= 3
        if random.random() < 0.25:
            print("BOOM! The boost backfired. You go backwards.")
            return -5, fuel
        distance = random.randint(12, 20)
        print(f"ZOOOM! Boosted {distance}m.")
        return distance, fuel

    if choice == "2":
        print("Not enough fuel! You just drive instead.")
    elif choice == "3":
        message, distance = random.choice(CRAZY_EVENTS)
        print(message)
        return distance, fuel

    distance = random.randint(5, 10)
    print(f"You drive {distance}m.")
    return distance, fuel


def rival_move(name):
    if random.random() < 0.2:
        message, distance = random.choice(CRAZY_EVENTS)
        print(f"{name}: {message}")
        return distance
    return random.randint(5, 12)


def main():
    print("=== CRAZY CART ===")
    player = input("What's your racer name? ").strip().capitalize() or "You"

    racers = {player: 0}
    for rival in RIVAL_NAMES:
        racers[rival] = 0

    fuel = 9
    turn = 1

    while max(racers.values()) < TRACK_LENGTH:
        print(f"\n--- Turn {turn} ---")
        draw_track(racers)

        distance, fuel = player_move(fuel)
        racers[player] = max(0, racers[player] + distance)

        for rival in RIVAL_NAMES:
            racers[rival] = max(0, racers[rival] + rival_move(rival))

        turn += 1

    draw_track(racers)
    winner = max(racers, key=racers.get)
    if winner == player:
        print(f"🏆 {player} WINS in {turn - 1} turns! Absolute madness.")
    else:
        print(f"{winner} wins. {player} finished at {racers[player]}m. Rematch?")


if __name__ == "__main__":
    main()
