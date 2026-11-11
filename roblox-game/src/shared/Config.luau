-- All tunable numbers live here so balancing never touches game logic.
local Config = {}

Config.GAME_NAME = "Sky Jump: +1 Jump Every Second"

-- Jump growth
Config.BASE_JUMP = 50 -- default Roblox jump power
Config.JUMP_PER_SECOND = 1 -- multiplied by rebirth + gamepass multipliers
Config.MAX_JUMP = 950 -- keep below engine/physics weirdness

-- Each stage is a floating island. `gap` = studs above the previous island.
-- Jump height in studs ~= JumpPower^2 / (2 * Gravity), so a gap of G needs
-- JumpPower of about sqrt(2 * 196.2 * G). The last gap (600) needs ~485.
Config.STAGES = {
	{ name = "Meadow", gap = 0, color = Color3.fromRGB(106, 190, 48) },
	{ name = "Sandbar", gap = 8, color = Color3.fromRGB(237, 201, 120) },
	{ name = "Mushroom Grove", gap = 18, color = Color3.fromRGB(196, 72, 72) },
	{ name = "Crystal Cliffs", gap = 35, color = Color3.fromRGB(110, 200, 230) },
	{ name = "Cloud Docks", gap = 60, color = Color3.fromRGB(235, 235, 245) },
	{ name = "Storm Shelf", gap = 95, color = Color3.fromRGB(90, 90, 120) },
	{ name = "Aurora Ledge", gap = 140, color = Color3.fromRGB(120, 255, 170) },
	{ name = "Moon Rock", gap = 200, color = Color3.fromRGB(180, 180, 180) },
	{ name = "Star Forge", gap = 280, color = Color3.fromRGB(255, 170, 40) },
	{ name = "Galaxy Rim", gap = 400, color = Color3.fromRGB(140, 80, 255) },
	{ name = "THE SUMMIT", gap = 600, color = Color3.fromRGB(255, 215, 0) },
}

Config.ISLAND_SIZE = Vector3.new(44, 6, 44)
Config.ISLAND_SPACING = 50 -- horizontal offset so islands never overlap vertically

-- Wins and rebirths
Config.WINS_PER_SUMMIT = 1 -- multiplied by (rebirths + 1)
Config.SUMMIT_COOLDOWN = 5 -- seconds between wins per player
Config.REBIRTH_BASE_COST = 3 -- wins; cost = BASE * (rebirths + 1)
Config.REBIRTH_MULTIPLIER_STEP = 1 -- each rebirth adds +1x jump gain

-- Daily reward
Config.DAILY_COOLDOWN = 20 * 60 * 60
Config.DAILY_REWARD_WINS = 2

-- Monetization (create these on the Creator Dashboard, then paste the IDs)
Config.GAMEPASS_2X_JUMP = 0 -- 0 = disabled
Config.GAMEPASS_MULTIPLIER = 2

-- Promo codes: share these in TikTok captions / Discord to drive installs.
-- jump = instant jump power, wins = instant wins.
Config.CODES = {
	RELEASE = { jump = 100 },
	SKYHIGH = { wins = 1 },
	["1KLIKES"] = { jump = 250 }, -- announce when the game hits 1,000 likes
}

Config.DATASTORE_NAME = "SkyJumpData_v1"
Config.AUTOSAVE_INTERVAL = 90

function Config.rebirthCost(rebirths: number): number
	return Config.REBIRTH_BASE_COST * (rebirths + 1)
end

return Config
