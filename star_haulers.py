"""
STAR HAULERS - a text-based space colonisation & trading game.

You've just founded a tiny startup in an age where the biggest industry is
colonising planets, extracting resources, refining them and shipping them
across the colonised universe. Mega-corporations own most of the galaxy and
pirates prowl the shipping lanes. Build your empire before the 60 turns run out.

Run:  python star_haulers.py
"""

import random

# ---------------------------------------------------------------- game data
RAW = {"ore": 20, "ice": 15, "gas": 25, "crystal": 60}
REFINED = {"ore": ("alloy", 70), "ice": ("water", 45),
           "gas": ("fuel", 80), "crystal": ("chip", 200)}

PLANETS = {
    "Terra Nova":  {"raw": "ice",     "dist": 0, "danger": 0.00, "colony_cost": 0},
    "Ferrox":      {"raw": "ore",     "dist": 2, "danger": 0.10, "colony_cost": 2000},
    "Glacius":     {"raw": "ice",     "dist": 3, "danger": 0.10, "colony_cost": 1500},
    "Vapora":      {"raw": "gas",     "dist": 4, "danger": 0.20, "colony_cost": 3000},
    "Shard Prime": {"raw": "crystal", "dist": 6, "danger": 0.35, "colony_cost": 6000},
    "Black Reach": {"raw": "crystal", "dist": 8, "danger": 0.50, "colony_cost": 4500},
}

RIVALS = ["Helix Dominion", "Omnicorp Stellar", "Vanta Mining Combine"]

START_CREDITS = 3000
MAX_TURNS = 60
WIN_WORTH = 100_000


def make_market():
    """Each planet gets its own random price multiplier per good."""
    goods = list(RAW) + [r[0] for r in REFINED.values()]
    return {p: {g: random.uniform(0.6, 1.6) for g in goods} for p in PLANETS}


def base_price(good):
    if good in RAW:
        return RAW[good]
    for name, price in REFINED.values():
        if name == good:
            return price
    raise ValueError(good)


# ---------------------------------------------------------------- game state
class Game:
    def __init__(self, name):
        self.name = name
        self.credits = START_CREDITS
        self.turn = 1
        self.location = "Terra Nova"
        self.cargo = {}
        self.cargo_cap = 50
        self.hull = 100
        self.guns = 0
        self.colonies = {"Terra Nova": {"mines": 1, "refinery": False, "stock": 0}}
        self.market = make_market()
        self.reputation = 0
        # rivals own planets; owning one raises its colony price
        self.rival_claims = {}

    # ---- helpers
    def cargo_used(self):
        return sum(self.cargo.values())

    def price(self, good, planet=None):
        planet = planet or self.location
        return max(1, int(base_price(good) * self.market[planet][good]))

    def net_worth(self):
        worth = self.credits
        worth += sum(self.price(g) * q for g, q in self.cargo.items())
        for p, c in self.colonies.items():
            worth += c["mines"] * 800 + (2500 if c["refinery"] else 0)
        return worth

    def add_cargo(self, good, qty):
        space = self.cargo_cap - self.cargo_used()
        qty = min(qty, space)
        if qty > 0:
            self.cargo[good] = self.cargo.get(good, 0) + qty
        return qty

    # ---- display
    def status(self):
        print("\n" + "=" * 60)
        print(f" {self.name.upper()}  |  Turn {self.turn}/{MAX_TURNS}  |  "
              f"Credits: {self.credits:,}  |  Net worth: {self.net_worth():,}")
        print(f" Location: {self.location}  |  Hull: {self.hull}%  |  "
              f"Guns: {self.guns}  |  Cargo: {self.cargo_used()}/{self.cargo_cap}")
        if self.cargo:
            print(" Hold: " + ", ".join(f"{g} x{q}" for g, q in self.cargo.items()))
        print(" Colonies: " + ", ".join(
            f"{p} (mines {c['mines']}{', refinery' if c['refinery'] else ''}, "
            f"stock {c['stock']})" for p, c in self.colonies.items()))
        print("=" * 60)

    # ---- actions
    def show_market(self):
        print(f"\nMarket at {self.location}:")
        for g in self.market[self.location]:
            print(f"  {g:<8} {self.price(g):>5} cr")

    def buy(self):
        self.show_market()
        good = input("Buy what? ").strip().lower()
        if good not in self.market[self.location]:
            print("Not sold here.")
            return
        p = self.price(good)
        qty = ask_int(f"How many? (max {min(self.credits // p, self.cargo_cap - self.cargo_used())}) ")
        qty = min(qty, self.credits // p)
        got = self.add_cargo(good, qty)
        self.credits -= got * p
        print(f"Bought {got} {good} for {got * p:,} cr.")

    def sell(self):
        if not self.cargo:
            print("Your hold is empty.")
            return
        self.show_market()
        good = input("Sell what? ").strip().lower()
        if good not in self.cargo:
            print("You don't have that.")
            return
        qty = min(ask_int(f"How many? (have {self.cargo[good]}) "), self.cargo[good])
        earned = qty * self.price(good)
        self.cargo[good] -= qty
        if self.cargo[good] == 0:
            del self.cargo[good]
        self.credits += earned
        # dumping goods pushes the local price down
        self.market[self.location][good] *= max(0.5, 1 - qty * 0.004)
        print(f"Sold {qty} {good} for {earned:,} cr.")

    def travel(self):
        print("\nDestinations:")
        here = PLANETS[self.location]["dist"]
        options = [p for p in PLANETS if p != self.location]
        for i, p in enumerate(options, 1):
            d = PLANETS[p]
            days = abs(d["dist"] - here) or 1
            owner = "YOURS" if p in self.colonies else self.rival_claims.get(p, "unclaimed")
            print(f"  {i}. {p:<12} {days} turns  danger {int(d['danger']*100):>2}%  "
                  f"[{d['raw']}]  {owner}")
        choice = ask_int("Go where? (0 cancel) ")
        if not 1 <= choice <= len(options):
            return
        dest = options[choice - 1]
        days = abs(PLANETS[dest]["dist"] - here) or 1
        fuel_cost = days * 40
        if self.credits < fuel_cost:
            print(f"You can't afford the {fuel_cost} cr fuel bill.")
            return
        self.credits -= fuel_cost
        print(f"Burning {fuel_cost} cr of fuel... ({days} turns)")
        for _ in range(days):
            self.end_turn()
            if self.hull <= 0 or self.turn > MAX_TURNS:
                return
        danger = max(PLANETS[dest]["danger"], PLANETS[self.location]["danger"])
        self.location = dest
        if random.random() < danger + 0.05:
            self.pirate_attack()
        print(f"Arrived at {dest}.")

    def colony_menu(self):
        here = self.location
        if here not in self.colonies:
            if here in self.rival_claims:
                cost = int(PLANETS[here]["colony_cost"] * 2.5)
                print(f"{self.rival_claims[here]} owns this world. Buying them out costs {cost:,} cr.")
            else:
                cost = PLANETS[here]["colony_cost"]
                print(f"{here} is unclaimed. Founding a colony costs {cost:,} cr.")
            if input("Do it? (y/n) ").lower().startswith("y"):
                if self.credits >= cost:
                    self.credits -= cost
                    self.colonies[here] = {"mines": 1, "refinery": False, "stock": 0}
                    self.rival_claims.pop(here, None)
                    self.reputation += 1
                    print(f"The {self.name} flag now flies over {here}!")
                else:
                    print("Not enough credits.")
            return

        col = self.colonies[here]
        raw = PLANETS[here]["raw"]
        refined = REFINED[raw][0]
        mine_cost = 600 + col["mines"] * 400
        print(f"\nColony {here}: {col['mines']} mines, refinery: {col['refinery']}, "
              f"stock: {col['stock']} {refined if col['refinery'] else raw}")
        print(f"  1. Build mine ({mine_cost} cr)")
        print(f"  2. Build refinery (2500 cr) - turns {raw} into {refined}")
        print("  3. Load stock into hold")
        print("  0. Back")
        c = ask_int("> ")
        if c == 1 and self.credits >= mine_cost:
            self.credits -= mine_cost
            col["mines"] += 1
            print("New mine online.")
        elif c == 2 and not col["refinery"] and self.credits >= 2500:
            self.credits -= 2500
            col["refinery"] = True
            col["stock"] = 0  # old raw stock is fed into the startup
            print("Refinery built. Output will now be refined.")
        elif c == 3:
            good = refined if col["refinery"] else raw
            got = self.add_cargo(good, col["stock"])
            col["stock"] -= got
            print(f"Loaded {got} {good}.")
        elif c in (1, 2):
            print("Can't do that (no money or already built).")

    def shipyard(self):
        print("\nShipyard:")
        print("  1. Cargo pods +25 capacity (1500 cr)")
        print("  2. Laser turret +1 gun   (1200 cr)")
        print(f"  3. Repair hull to 100%   ({(100 - self.hull) * 10} cr)")
        print("  0. Back")
        c = ask_int("> ")
        if c == 1 and self.credits >= 1500:
            self.credits -= 1500
            self.cargo_cap += 25
        elif c == 2 and self.credits >= 1200:
            self.credits -= 1200
            self.guns += 1
        elif c == 3 and self.credits >= (100 - self.hull) * 10:
            self.credits -= (100 - self.hull) * 10
            self.hull = 100
        elif c:
            print("Not enough credits.")

    # ---- events
    def pirate_attack(self):
        strength = random.randint(1, 4)
        print(f"\n!!! PIRATES! A raider gang (strength {strength}) is closing in!")
        c = input("(f)ight, (r)un, or (p)ay tribute? ").lower()
        if c.startswith("p"):
            toll = min(self.credits, 300 * strength)
            self.credits -= toll
            print(f"You paid {toll} cr. They let you pass, sneering.")
        elif c.startswith("f"):
            if random.random() < (self.guns + 1) / (self.guns + 1 + strength):
                loot = random.randint(200, 800) * strength
                self.credits += loot
                print(f"Victory! You scavenge {loot} cr from the wreckage.")
                self.reputation += 1
            else:
                dmg = random.randint(15, 35)
                self.hull -= dmg
                self.lose_cargo(0.5)
                print(f"You lost! Hull -{dmg}% and they stole half your cargo.")
        else:
            if random.random() < 0.5:
                print("You punch the engines and escape!")
            else:
                dmg = random.randint(10, 25)
                self.hull -= dmg
                print(f"They clip your engines as you flee. Hull -{dmg}%.")

    def lose_cargo(self, frac):
        for g in list(self.cargo):
            self.cargo[g] -= int(self.cargo[g] * frac)
            if self.cargo[g] <= 0:
                del self.cargo[g]

    def random_event(self):
        r = random.random()
        if r < 0.08:
            planet = random.choice(list(PLANETS))
            good = random.choice(list(self.market[planet]))
            self.market[planet][good] *= 2
            print(f"\n[NEWS] Shortage! {good} prices spike on {planet}.")
        elif r < 0.14:
            planet = random.choice(list(PLANETS))
            good = random.choice(list(self.market[planet]))
            self.market[planet][good] *= 0.5
            print(f"\n[NEWS] Glut! {good} crashes on {planet}.")
        elif r < 0.20:
            free = [p for p in PLANETS if p not in self.colonies and p not in self.rival_claims]
            if free:
                p = random.choice(free)
                rival = random.choice(RIVALS)
                self.rival_claims[p] = rival
                print(f"\n[NEWS] {rival} has claimed {p}. Colony prices there just rose.")
        elif r < 0.24 and len(self.colonies) > 1:
            p = random.choice([c for c in self.colonies if c != "Terra Nova"])
            rival = random.choice(RIVALS)
            if self.reputation >= 3:
                print(f"\n[NEWS] {rival} tried a hostile takeover of {p}, "
                      f"but your reputation scared off their lawyers.")
            else:
                self.colonies[p]["stock"] = 0
                print(f"\n[NEWS] {rival} sabotaged {p}! Its stockpile was destroyed.")
        elif r < 0.27:
            p = random.choice(list(self.colonies))
            self.colonies[p]["mines"] += 1
            print(f"\n[NEWS] Miners on {p} found a rich vein. +1 mine for free!")

    def end_turn(self):
        for p, col in self.colonies.items():
            produced = col["mines"] * random.randint(3, 6)
            if col["refinery"]:
                produced = max(1, produced // 2)  # refining halves volume
            col["stock"] = min(col["stock"] + produced, 300)
        # markets slowly drift back toward normal
        for prices in self.market.values():
            for g in prices:
                prices[g] += (1.0 - prices[g]) * 0.05 + random.uniform(-0.05, 0.05)
        self.random_event()
        self.turn += 1


# ---------------------------------------------------------------- main loop
def ask_int(prompt):
    try:
        return max(0, int(input(prompt)))
    except ValueError:
        return 0


def main():
    print(__doc__)
    name = input("Name your company: ").strip() or "Nova Haulage Co."
    g = Game(name)
    print(f"\nWelcome, CEO of {g.name}. You start on Terra Nova with one ice mine,")
    print(f"one rusty freighter and {START_CREDITS} cr. Reach {WIN_WORTH:,} cr net worth to "
          f"rival the megacorps.")

    actions = {"1": g.show_market, "2": g.buy, "3": g.sell, "4": g.travel,
               "5": g.colony_menu, "6": g.shipyard}
    while g.turn <= MAX_TURNS and g.hull > 0 and g.net_worth() < WIN_WORTH:
        g.status()
        print("1 Market  2 Buy  3 Sell  4 Travel  5 Colony  6 Shipyard  7 Wait a turn  q Quit")
        c = input("> ").strip().lower()
        if c == "q":
            break
        if c == "7":
            g.end_turn()
        elif c in actions:
            actions[c]()

    print("\n" + "#" * 60)
    if g.hull <= 0:
        print("Your freighter breaks apart. The megacorps buy your colonies for scrap.")
    elif g.net_worth() >= WIN_WORTH:
        print(f"{g.name} is now a galactic power! The megacorps want to merge with YOU.")
    else:
        print(f"Game over. Final net worth: {g.net_worth():,} cr.")
    print("#" * 60)


if __name__ == "__main__":
    main()
