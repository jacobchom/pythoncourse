-- Client UI: jump counter, stage, rebirth/daily/codes/2x buttons, toasts.
local Players = game:GetService("Players")
local MarketplaceService = game:GetService("MarketplaceService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local remotes = ReplicatedStorage:WaitForChild("Remotes")
local player = Players.LocalPlayer

local gui = Instance.new("ScreenGui")
gui.Name = "HUD"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = false
gui.Parent = player:WaitForChild("PlayerGui")

local function corner(parent, radius)
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, radius or 12)
	c.Parent = parent
end

local function label(props)
	local l = Instance.new("TextLabel")
	l.BackgroundTransparency = 1
	l.Font = Enum.Font.FredokaOne
	l.TextColor3 = Color3.new(1, 1, 1)
	l.TextStrokeTransparency = 0.2
	l.TextScaled = true
	for k, v in props do
		l[k] = v
	end
	l.Parent = gui
	return l
end

local function button(text: string, color: Color3, position: UDim2)
	local b = Instance.new("TextButton")
	b.Size = UDim2.new(0, 150, 0, 48)
	b.Position = position
	b.AnchorPoint = Vector2.new(0, 0.5)
	b.BackgroundColor3 = color
	b.Font = Enum.Font.FredokaOne
	b.TextColor3 = Color3.new(1, 1, 1)
	b.TextScaled = true
	b.Text = text
	b.AutoButtonColor = true
	corner(b)
	b.Parent = gui
	return b
end

-- Top-centre jump counter (the screenshot-worthy number)
local jumpLabel = label({
	Size = UDim2.new(0.5, 0, 0, 60),
	Position = UDim2.new(0.25, 0, 0, 8),
	Text = "Jump: 50",
})
local subLabel = label({
	Size = UDim2.new(0.5, 0, 0, 26),
	Position = UDim2.new(0.25, 0, 0, 68),
	Text = "+1 / sec",
	TextColor3 = Color3.fromRGB(255, 230, 120),
})

-- Left buttons
local rebirthBtn = button("Rebirth", Color3.fromRGB(170, 70, 255), UDim2.new(0, 12, 0.40, 0))
local dailyBtn = button("Daily 🎁", Color3.fromRGB(40, 170, 90), UDim2.new(0, 12, 0.40, 56))
local codesBtn = button("Codes", Color3.fromRGB(240, 140, 30), UDim2.new(0, 12, 0.40, 112))
local passBtn
if Config.GAMEPASS_2X_JUMP ~= 0 then
	passBtn = button("2x Jump ⚡", Color3.fromRGB(230, 60, 90), UDim2.new(0, 12, 0.40, 168))
end

-- Toast
local toast = label({
	Size = UDim2.new(0.6, 0, 0, 40),
	Position = UDim2.new(0.2, 0, 0.78, 0),
	Text = "",
	TextTransparency = 1,
	TextStrokeTransparency = 1,
})
local toastToken = 0
local function showToast(text: string)
	toastToken += 1
	local my = toastToken
	toast.Text = text
	toast.TextTransparency = 0
	toast.TextStrokeTransparency = 0.2
	task.delay(2.5, function()
		if my == toastToken then
			TweenService:Create(toast, TweenInfo.new(0.4), { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
		end
	end)
end
remotes:WaitForChild("Notify").OnClientEvent:Connect(showToast)

-- Codes panel
local panel = Instance.new("Frame")
panel.Size = UDim2.new(0, 320, 0, 140)
panel.Position = UDim2.new(0.5, -160, 0.5, -70)
panel.BackgroundColor3 = Color3.fromRGB(30, 30, 45)
panel.Visible = false
corner(panel, 16)
panel.Parent = gui

local box = Instance.new("TextBox")
box.Size = UDim2.new(1, -24, 0, 44)
box.Position = UDim2.new(0, 12, 0, 14)
box.PlaceholderText = "Enter code"
box.Text = ""
box.ClearTextOnFocus = false
box.Font = Enum.Font.FredokaOne
box.TextScaled = true
box.BackgroundColor3 = Color3.fromRGB(255, 255, 255)
corner(box, 10)
box.Parent = panel

local redeem = Instance.new("TextButton")
redeem.Size = UDim2.new(1, -24, 0, 44)
redeem.Position = UDim2.new(0, 12, 0, 76)
redeem.Text = "Redeem"
redeem.Font = Enum.Font.FredokaOne
redeem.TextScaled = true
redeem.TextColor3 = Color3.new(1, 1, 1)
redeem.BackgroundColor3 = Color3.fromRGB(240, 140, 30)
corner(redeem, 10)
redeem.Parent = panel

-- Wiring
local busy = false
local function call(rfName: string, ...)
	if busy then
		return
	end
	busy = true
	local ok, success, message = pcall(remotes:WaitForChild(rfName).InvokeServer, remotes[rfName], ...)
	busy = false
	if not ok then
		showToast("Something went wrong, try again")
		return
	end
	showToast(message or (success and "Done!" or "Failed"))
	return success
end

rebirthBtn.Activated:Connect(function()
	call("Rebirth")
end)
dailyBtn.Activated:Connect(function()
	call("ClaimDaily")
end)
codesBtn.Activated:Connect(function()
	panel.Visible = not panel.Visible
end)
redeem.Activated:Connect(function()
	if call("RedeemCode", box.Text) then
		box.Text = ""
		panel.Visible = false
	end
end)
if passBtn then
	passBtn.Activated:Connect(function()
		MarketplaceService:PromptGamePassPurchase(player, Config.GAMEPASS_2X_JUMP)
	end)
end

-- Live stats
local function update()
	local stats = player:FindFirstChild("leaderstats")
	local jump = stats and stats:FindFirstChild("Jump")
	if jump then
		jumpLabel.Text = "Jump: " .. jump.Value
	end
	local stage = player:GetAttribute("Stage") or 1
	local stageInfo = Config.STAGES[stage]
	subLabel.Text = string.format(
		"+%d / sec  •  %s",
		player:GetAttribute("Gain") or 1,
		stageInfo and stageInfo.name or ""
	)
	rebirthBtn.Text = string.format("Rebirth (%d 🏆)", player:GetAttribute("RebirthCost") or Config.REBIRTH_BASE_COST)
end

player:GetAttributeChangedSignal("Stage"):Connect(update)
player:GetAttributeChangedSignal("Gain"):Connect(update)
player:GetAttributeChangedSignal("RebirthCost"):Connect(update)
local stats = player:WaitForChild("leaderstats")
stats:WaitForChild("Jump").Changed:Connect(update)
update()
