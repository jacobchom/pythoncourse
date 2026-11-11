-- Builds the whole map from Config.STAGES so no .rbxl file is needed.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))

local WorldBuilder = {}

-- Spiral directions so each island sits beside (not under) the next one.
local DIRECTIONS = {
	Vector3.new(1, 0, 0),
	Vector3.new(0, 0, 1),
	Vector3.new(-1, 0, 0),
	Vector3.new(0, 0, -1),
}

local function makePart(props)
	local part = Instance.new("Part")
	part.Anchored = true
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	for key, value in props do
		part[key] = value
	end
	return part
end

local function addLabel(parent: BasePart, text: string, color: Color3)
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromOffset(300, 60)
	gui.StudsOffset = Vector3.new(0, 10, 0)
	gui.AlwaysOnTop = false
	gui.MaxDistance = 250
	gui.Parent = parent

	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.FredokaOne
	label.TextScaled = true
	label.TextColor3 = color
	label.TextStrokeTransparency = 0
	label.Text = text
	label.Parent = gui
end

local function requiredJump(gap: number): number
	return math.ceil(math.sqrt(2 * workspace.Gravity * gap))
end

-- Returns { checkpoints = {BasePart}, summit = BasePart, finalRequiredJump = number }
function WorldBuilder.build()
	local folder = Instance.new("Folder")
	folder.Name = "Islands"
	folder.Parent = workspace

	local checkpoints = {}
	local position = Vector3.new(0, 0, 0)
	local finalRequiredJump = 0

	for index, stage in Config.STAGES do
		if index > 1 then
			local dir = DIRECTIONS[((index - 2) % #DIRECTIONS) + 1]
			position += dir * Config.ISLAND_SPACING + Vector3.new(0, stage.gap, 0)
		end

		local island = makePart({
			Name = string.format("Stage%02d_%s", index, stage.name),
			Size = Config.ISLAND_SIZE,
			Position = position,
			Color = stage.color,
			Material = Enum.Material.SmoothPlastic,
		})
		island:SetAttribute("Stage", index)
		island.Parent = folder

		local isSummit = index == #Config.STAGES
		local need = requiredJump(stage.gap)
		if isSummit then
			finalRequiredJump = need
		end

		local text = isSummit and "🏆 THE SUMMIT 🏆"
			or (index == 1 and "Jump higher every second!" or string.format("%s  (needs %d jump)", stage.name, need))
		addLabel(island, text, Color3.new(1, 1, 1))

		local pad = makePart({
			Name = isSummit and "SummitPad" or "Checkpoint",
			Size = Vector3.new(12, 1, 12),
			Position = position + Vector3.new(0, Config.ISLAND_SIZE.Y / 2 + 0.5, 0),
			Color = isSummit and Color3.fromRGB(255, 215, 0) or Color3.fromRGB(255, 255, 255),
			Material = Enum.Material.Neon,
			CanCollide = false,
		})
		pad:SetAttribute("Stage", index)
		pad.Parent = island
		checkpoints[index] = pad
	end

	-- Spawn on the first island.
	local spawn = Instance.new("SpawnLocation")
	spawn.Anchored = true
	spawn.Size = Vector3.new(10, 1, 10)
	spawn.Position = checkpoints[1].Position + Vector3.new(14, 0, 14)
	spawn.Neutral = true
	spawn.Duration = 0
	spawn.Transparency = 0.5
	spawn.Parent = workspace

	-- Kill floor far below so a missed jump sends you to your checkpoint.
	local void = makePart({
		Name = "Void",
		Size = Vector3.new(4000, 2, 4000),
		Position = Vector3.new(0, -60, 0),
		Transparency = 1,
		CanCollide = false,
	})
	void.Parent = workspace
	void.Touched:Connect(function(hit)
		local humanoid = hit.Parent and hit.Parent:FindFirstChildOfClass("Humanoid")
		if humanoid then
			humanoid.Health = 0
		end
	end)

	return {
		checkpoints = checkpoints,
		summit = checkpoints[#checkpoints],
		finalRequiredJump = finalRequiredJump,
	}
end

return WorldBuilder
