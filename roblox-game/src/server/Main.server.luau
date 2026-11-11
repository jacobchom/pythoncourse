-- Server entry point: player data, jump growth, checkpoints, wins, rebirths,
-- promo codes, daily reward and gamepass.
local Players = game:GetService("Players")
local DataStoreService = game:GetService("DataStoreService")
local MarketplaceService = game:GetService("MarketplaceService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local WorldBuilder = require(script.Parent:WaitForChild("WorldBuilder"))

local world = WorldBuilder.build()

-- Remotes ---------------------------------------------------------------
local remotes = Instance.new("Folder")
remotes.Name = "Remotes"
remotes.Parent = ReplicatedStorage

local function remote(className: string, name: string)
	local r = Instance.new(className)
	r.Name = name
	r.Parent = remotes
	return r
end

local RebirthRF = remote("RemoteFunction", "Rebirth")
local RedeemCodeRF = remote("RemoteFunction", "RedeemCode")
local ClaimDailyRF = remote("RemoteFunction", "ClaimDaily")
local NotifyRE = remote("RemoteEvent", "Notify")

-- Data ------------------------------------------------------------------
local store = DataStoreService:GetDataStore(Config.DATASTORE_NAME)
local sessions = {} -- [player] = data table

local function defaultData()
	return {
		jump = Config.BASE_JUMP,
		wins = 0,
		rebirths = 0,
		stage = 1,
		codes = {},
		lastDaily = 0,
	}
end

local function load(player: Player)
	local ok, result = pcall(function()
		return store:GetAsync("u_" .. player.UserId)
	end)
	local data = defaultData()
	if ok and type(result) == "table" then
		for key, value in result do
			data[key] = value
		end
	elseif not ok then
		warn("Load failed for", player.Name, result)
		data.loadFailed = true -- never overwrite real data with defaults
	end
	return data
end

local function save(player: Player)
	local data = sessions[player]
	if not data or data.loadFailed then
		return
	end
	local payload = {
		jump = data.jump,
		wins = data.wins,
		rebirths = data.rebirths,
		stage = data.stage,
		codes = data.codes,
		lastDaily = data.lastDaily,
	}
	local ok, err = pcall(function()
		store:SetAsync("u_" .. player.UserId, payload)
	end)
	if not ok then
		warn("Save failed for", player.Name, err)
	end
end

-- Helpers ---------------------------------------------------------------
local function hasGamepass(player: Player): boolean
	if Config.GAMEPASS_2X_JUMP == 0 then
		return false
	end
	local cached = player:GetAttribute("Has2x")
	if cached ~= nil then
		return cached
	end
	local ok, owns = pcall(function()
		return MarketplaceService:UserOwnsGamePassAsync(player.UserId, Config.GAMEPASS_2X_JUMP)
	end)
	local result = ok and owns or false
	player:SetAttribute("Has2x", result)
	return result
end

local function jumpGain(player: Player, data): number
	local mult = 1 + data.rebirths * Config.REBIRTH_MULTIPLIER_STEP
	if hasGamepass(player) then
		mult *= Config.GAMEPASS_MULTIPLIER
	end
	return Config.JUMP_PER_SECOND * mult
end

local function refresh(player: Player)
	local data = sessions[player]
	if not data then
		return
	end
	data.jump = math.min(data.jump, Config.MAX_JUMP)
	local stats = player:FindFirstChild("leaderstats")
	if stats then
		stats.Wins.Value = data.wins
		stats.Rebirths.Value = data.rebirths
		stats.Jump.Value = math.floor(data.jump)
	end
	player:SetAttribute("Stage", data.stage)
	player:SetAttribute("Gain", jumpGain(player, data))
	player:SetAttribute("RebirthCost", Config.rebirthCost(data.rebirths))

	local humanoid = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
	if humanoid then
		humanoid.UseJumpPower = true
		humanoid.JumpPower = data.jump
	end
end

local function notify(player: Player, text: string)
	NotifyRE:FireClient(player, text)
end

-- Player lifecycle ------------------------------------------------------
local function onCharacter(player: Player, character: Model)
	local data = sessions[player]
	if not data then
		return
	end
	local root = character:WaitForChild("HumanoidRootPart", 10)
	local pad = world.checkpoints[data.stage] or world.checkpoints[1]
	if root and data.stage > 1 then
		task.wait() -- let the default spawn finish first
		character:PivotTo(CFrame.new(pad.Position + Vector3.new(0, 5, 0)))
	end
	refresh(player)
end

local function onPlayerAdded(player: Player)
	local stats = Instance.new("Folder")
	stats.Name = "leaderstats"
	for _, name in { "Wins", "Rebirths", "Jump" } do
		local v = Instance.new("IntValue")
		v.Name = name
		v.Parent = stats
	end
	stats.Parent = player

	sessions[player] = load(player)
	if sessions[player].loadFailed then
		notify(player, "⚠️ Couldn't load your save. Progress this session won't be saved.")
	end

	player.CharacterAdded:Connect(function(character)
		onCharacter(player, character)
	end)
	if player.Character then
		onCharacter(player, player.Character)
	end
	refresh(player)
end

Players.PlayerAdded:Connect(onPlayerAdded)
for _, player in Players:GetPlayers() do
	task.spawn(onPlayerAdded, player)
end

Players.PlayerRemoving:Connect(function(player)
	save(player)
	sessions[player] = nil
end)

game:BindToClose(function()
	if RunService:IsStudio() then
		task.wait(1)
	end
	for _, player in Players:GetPlayers() do
		task.spawn(save, player)
	end
	task.wait(3)
end)

task.spawn(function()
	while true do
		task.wait(Config.AUTOSAVE_INTERVAL)
		for _, player in Players:GetPlayers() do
			task.spawn(save, player)
		end
	end
end)

-- Core loop: +jump every second ----------------------------------------
task.spawn(function()
	while true do
		task.wait(1)
		for player, data in sessions do
			local humanoid = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
			if humanoid and humanoid.Health > 0 and data.jump < Config.MAX_JUMP then
				data.jump += jumpGain(player, data)
				refresh(player)
			end
		end
	end
end)

-- Checkpoints and summit ------------------------------------------------
local lastSummit = {}

local function playerFromHit(hit: BasePart): Player?
	local character = hit.Parent
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not humanoid or humanoid.Health <= 0 then
		return nil
	end
	return Players:GetPlayerFromCharacter(character)
end

for index, pad in world.checkpoints do
	pad.Touched:Connect(function(hit)
		local player = playerFromHit(hit)
		local data = player and sessions[player]
		if not data then
			return
		end

		if pad == world.summit then
			local now = os.clock()
			if lastSummit[player] and now - lastSummit[player] < Config.SUMMIT_COOLDOWN then
				return
			end
			-- Basic exploit guard: you must actually be able to make the last jump.
			if data.jump < world.finalRequiredJump * 0.9 then
				return
			end
			lastSummit[player] = now
			local reward = Config.WINS_PER_SUMMIT * (data.rebirths + 1)
			data.wins += reward
			data.stage = 1
			refresh(player)
			notify(player, string.format("🏆 SUMMIT! +%d Win%s", reward, reward == 1 and "" or "s"))
			task.delay(1.5, function()
				if player.Character then
					player.Character:PivotTo(CFrame.new(world.checkpoints[1].Position + Vector3.new(0, 5, 0)))
				end
			end)
		elseif index > data.stage then
			data.stage = index
			refresh(player)
			notify(player, "Checkpoint: " .. Config.STAGES[index].name)
		end
	end)
end

Players.PlayerRemoving:Connect(function(player)
	lastSummit[player] = nil
end)

-- Rebirth ---------------------------------------------------------------
RebirthRF.OnServerInvoke = function(player)
	local data = sessions[player]
	if not data then
		return false, "Data not loaded"
	end
	local cost = Config.rebirthCost(data.rebirths)
	if data.wins < cost then
		return false, string.format("Need %d wins (you have %d)", cost, data.wins)
	end
	data.wins -= cost
	data.rebirths += 1
	data.jump = Config.BASE_JUMP
	data.stage = 1
	refresh(player)
	if player.Character then
		player.Character:PivotTo(CFrame.new(world.checkpoints[1].Position + Vector3.new(0, 5, 0)))
	end
	return true, string.format("Rebirth %d! Jump gain is now x%d", data.rebirths, 1 + data.rebirths)
end

-- Codes -----------------------------------------------------------------
RedeemCodeRF.OnServerInvoke = function(player, rawCode)
	local data = sessions[player]
	if not data or type(rawCode) ~= "string" or #rawCode > 32 then
		return false, "Invalid code"
	end
	local code = string.upper((rawCode:gsub("%s", "")))
	local reward = Config.CODES[code]
	if not reward then
		return false, "Invalid code"
	end
	if table.find(data.codes, code) then
		return false, "Already redeemed"
	end
	table.insert(data.codes, code)
	if reward.jump then
		data.jump += reward.jump
	end
	if reward.wins then
		data.wins += reward.wins
	end
	refresh(player)
	return true, "Code redeemed!"
end

-- Daily reward ----------------------------------------------------------
ClaimDailyRF.OnServerInvoke = function(player)
	local data = sessions[player]
	if not data then
		return false, "Data not loaded"
	end
	local now = os.time()
	local waitLeft = data.lastDaily + Config.DAILY_COOLDOWN - now
	if waitLeft > 0 then
		return false, string.format("Come back in %dh %dm", waitLeft // 3600, (waitLeft % 3600) // 60)
	end
	data.lastDaily = now
	data.wins += Config.DAILY_REWARD_WINS
	refresh(player)
	return true, string.format("+%d Wins! See you tomorrow.", Config.DAILY_REWARD_WINS)
end

-- Gamepass purchase in-game ---------------------------------------------
MarketplaceService.PromptGamePassPurchaseFinished:Connect(function(player, passId, purchased)
	if purchased and passId == Config.GAMEPASS_2X_JUMP then
		player:SetAttribute("Has2x", true)
		refresh(player)
		notify(player, "2x Jump unlocked! Thanks for the support 💛")
	end
end)
