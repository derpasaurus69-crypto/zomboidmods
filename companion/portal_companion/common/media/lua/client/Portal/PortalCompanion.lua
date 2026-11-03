-- Portal companion: a PORTAL entry on the main menu that lists the Portal
-- towns installed, says how to make your own, and gives the credits.
-- Main menu only; it adds nothing to a running game.

require "ISUI/ISPanelJoypad"
require "ISUI/ISScrollingListBox"
require "ISUI/ISButton"
require "ISUI/ISLabel"
require "ISUI/ISRichTextPanel"
require "ISUI/ISImage"
require "ISUI/ISModalDialog"

PortalCompanion = PortalCompanion or {}

local SELF_ID = "portal_companion"
local DOWNLOAD_URL = "https://github.com/derpasaurus69-crypto/zomboidmods/releases"
local TIP_URL = "https://buymeacoffee.com/derpasauruo"
local SIZES = { downtown = "UI_portal_SizeDowntown", town = "UI_portal_SizeTown", city_core = "UI_portal_SizeCityCore" }

local FONT_HGT_SMALL = getTextManager():getFontHeight(UIFont.Small)
local FONT_HGT_MEDIUM = getTextManager():getFontHeight(UIFont.Medium)
local FONT_HGT_LARGE = getTextManager():getFontHeight(UIFont.Large)
local PAD = 16
local BTN_HGT = math.max(25, FONT_HGT_SMALL + 6 * 2)
local ROW_HGT = math.max(72, FONT_HGT_MEDIUM + FONT_HGT_SMALL * 2 + 16)
local POSTER = 192

-- ---- the towns ----------------------------------------------------------------

local function endsWith(s, suffix)
    return suffix == "" or s:sub(-#suffix) == suffix
end

local function sizeOf(id)
    for suffix, key in pairs(SIZES) do
        if endsWith(id, "_" .. suffix) then return getText(key) end
    end
    return ""
end

-- Every installed Portal town, enabled or not: a mod whose id starts with
-- portal_ and that adds a map. Same scan the Mods screen does.
function PortalCompanion.towns()
    local towns, seen = {}, {}
    local active = ActiveMods.getById("default")
    for _, dir in ipairs(getModDirectoryTable()) do
        local info = getModInfo(dir)
        local id = info and info:getId()
        if id and not seen[id] and luautils.stringStarts(id, "portal_") and id ~= SELF_ID then
            seen[id] = true
            local maps = getMapFoldersForMod(id)
            if maps and maps:size() > 0 then
                local workshopID = info:getWorkshopID()
                table.insert(towns, {
                    id = id,
                    name = info:getName() or id,
                    size = sizeOf(id),
                    poster = info:getPosterCount() > 0 and info:getPoster(0) or nil,
                    enabled = active ~= nil and active:isModActive(id),
                    workshopID = (workshopID and workshopID ~= "") and workshopID or nil,
                })
            end
        end
    end
    table.sort(towns, function(a, b) return string.lower(a.name) < string.lower(b.name) end)
    return towns
end

local function selfWorkshopID()
    local info = getModInfoByID(SELF_ID)
    local id = info and info:getWorkshopID()
    return (id and id ~= "") and id or nil
end

local function notice(text)
    local sw, sh = getCore():getScreenWidth(), getCore():getScreenHeight()
    local w, h = ISModalDialog.CalcSize(360, 160, text)
    local modal = ISModalDialog:new((sw - w) / 2, (sh - h) / 2, w, h, text, false, nil, nil)
    modal:initialise()
    modal:addToUIManager()
    modal:setAlwaysOnTop(true)
    PortalCompanion.notice = modal
    local joypadData = JoypadState.getMainMenuJoypad()
    if joypadData then  -- a controller has to be able to press OK
        modal.prevFocus = joypadData.focus
        joypadData.focus = modal
        updateJoypadFocus(joypadData)
    end
end

local function noticeOpen()
    return PortalCompanion.notice ~= nil and PortalCompanion.notice:isReallyVisible()
end

-- The game only lets mods open Steam and The Indie Stone's own sites, so a
-- GitHub link is copied instead of opened.
local function copyLink(url)
    Clipboard.setClipboard(url)
    notice(getText("UI_portal_LinkCopied", url))
end

local function openWorkshopItem(id)
    if id and isSteamOverlayEnabled() then
        activateSteamOverlayToWorkshopItem(id)
        return true
    end
    return false
end

-- ---- the list -----------------------------------------------------------------

local PortalTownList = ISScrollingListBox:derive("PortalTownList")

function PortalTownList:new(x, y, width, height)
    local o = ISScrollingListBox.new(self, x, y, width, height)
    o.itemheight = ROW_HGT
    o.drawBorder = true
    return o
end

function PortalTownList:doDrawItem(y, item, alt)
    local town = item.item
    if self.selected == item.index then
        self:drawRect(0, y, self:getWidth(), item.height - 1, 0.3, 0.7, 0.35, 0.15)
    elseif self.mouseoverselected == item.index and not self:isMouseOverScrollBar() then
        self:drawRect(1, y + 1, self:getWidth() - 2, item.height - 2, 0.95, 0.05, 0.05, 0.05)
    end
    self:drawRectBorder(0, y, self:getWidth(), item.height, 0.5, self.borderColor.r, self.borderColor.g, self.borderColor.b)
    local thumb = ROW_HGT - 8
    local tex = town.poster and getTexture(town.poster)
    if tex then
        self:drawTextureScaledAspect(tex, 4, y + 4, thumb, thumb, 1, 1, 1, 1)
    else
        self:drawRect(4, y + 4, thumb, thumb, 0.5, 0.2, 0.25, 0.2)
    end
    local x = thumb + 12
    self:drawText(town.name, x, y + 6, 1, 1, 1, 1, UIFont.Medium)
    self:drawText(town.size, x, y + 6 + FONT_HGT_MEDIUM, 0.8, 0.8, 0.8, 1, UIFont.Small)
    if town.enabled then
        self:drawText(getText("UI_portal_Enabled"), x, y + 6 + FONT_HGT_MEDIUM + FONT_HGT_SMALL, 0.4, 0.9, 0.4, 1, UIFont.Small)
    else
        self:drawText(getText("UI_portal_NotEnabled"), x, y + 6 + FONT_HGT_MEDIUM + FONT_HGT_SMALL, 0.7, 0.7, 0.7, 1, UIFont.Small)
    end
    return y + item.height
end

-- ---- the screen ---------------------------------------------------------------

PortalScreen = ISPanelJoypad:derive("PortalScreen")

function PortalScreen:new(x, y, width, height)
    local o = ISPanelJoypad.new(self, x, y, width, height)
    o.backgroundColor = { r = 0, g = 0, b = 0, a = 0.8 }
    o.borderColor = { r = 1, g = 1, b = 1, a = 0.5 }
    o:setAnchorsTBLR(true, true, true, true)
    return o
end

function PortalScreen:createChildren()
    ISPanelJoypad.createChildren(self)
    local top = PAD
    self.title = ISLabel:new(PAD, top, FONT_HGT_LARGE, getText("UI_portal_Title"), 1, 1, 1, 1, UIFont.Large, true)
    self.title:initialise()
    self:addChild(self.title)
    top = top + FONT_HGT_LARGE + 4

    self.intro = ISLabel:new(PAD, top, FONT_HGT_SMALL, getText("UI_portal_Intro"), 0.85, 0.85, 0.85, 1, UIFont.Small, true)
    self.intro:initialise()
    self:addChild(self.intro)
    top = top + FONT_HGT_SMALL + PAD

    local bottom = self.height - PAD - BTN_HGT
    local listW = math.floor((self.width - PAD * 3) * 0.45)
    self.list = PortalTownList:new(PAD, top, listW, bottom - PAD - top)
    self.list:initialise()
    self.list:instantiate()
    self.list:setAnchorsTBLR(true, true, true, false)
    self.list:setOnMouseDownFunction(self, PortalScreen.onSelectTown)
    self.list.joypadParent = self  -- so B and Left/Right leave the list
    self:addChild(self.list)

    local detailX = self.list:getRight() + PAD
    -- The poster is its own image: rich text splits paths at spaces, and
    -- Steam's folders have them.
    self.posterTop = top
    self.poster = ISImage:new(detailX, top, POSTER, POSTER, nil)
    self.poster:initialise()
    self.poster.autoScale = true
    self.poster:setVisible(false)
    self:addChild(self.poster)

    self.detail = ISRichTextPanel:new(detailX, top, self.width - detailX - PAD, self.list.height)
    self.detail:initialise()
    self.detail.autosetheight = false
    self.detail.clip = true
    self.detail.background = true
    self.detail.backgroundColor = { r = 0, g = 0, b = 0, a = 0.4 }
    self.detail.borderColor = { r = 1, g = 1, b = 1, a = 0.3 }
    self.detail:setAnchorsTBLR(true, true, true, true)
    self:addChild(self.detail)
    self.detail:addScrollBars()

    local function button(x, title, onclick, width)
        local w = width or (getTextManager():MeasureStringX(UIFont.Small, title) + PAD * 2)
        local b = ISButton:new(x, bottom, w, BTN_HGT, title, self, onclick)
        b:initialise()
        b:instantiate()
        b:setAnchorsTBLR(false, true, true, false)
        self:addChild(b)
        return b
    end
    self.backButton = button(PAD, getText("UI_btn_back"), PortalScreen.onBack, 100)
    self.makeButton = button(self.backButton:getRight() + PAD, getText("UI_portal_MakeYourOwn"), PortalScreen.onMakeYourOwn)
    self.copyButton = button(self.makeButton:getRight() + PAD, getText("UI_portal_CopyDownloadLink"), PortalScreen.onCopyDownload)
    self.townButton = button(self.copyButton:getRight() + PAD, getText("UI_portal_TownPage"), PortalScreen.onTownPage)
    self.tipButton = button(self.townButton:getRight() + PAD, getText("UI_portal_CopyTipLink"), PortalScreen.onCopyTip)

    self:insertNewLineOfButtons(self.list)
    self:insertNewLineOfButtons(self.backButton, self.makeButton, self.copyButton, self.townButton, self.tipButton)
end

function PortalScreen:refresh()
    self.list:clear()
    self.towns = PortalCompanion.towns()
    for _, town in ipairs(self.towns) do
        self.list:addItem(town.name, town)
    end
    self.list.selected = 0
    self.selectedTown = nil
    self.townButton:setEnable(false)
    self:showGuide()
end

-- Show the poster above the text, or give the text the whole column.
function PortalScreen:setPoster(path)
    local tex = path and getTexture(path)
    self.poster.texture = tex
    self.poster:setVisible(tex ~= nil)
    local y = tex and (self.posterTop + POSTER + PAD) or self.posterTop
    self.detail:setY(y)
    self.detail:setHeight(self.list:getBottom() - y)
end

function PortalScreen:showGuide()
    self:setPoster(nil)
    local text = " <SIZE:medium> " .. getText("UI_portal_HowTo") .. " <LINE> <SIZE:small> "
        .. "1. " .. getText("UI_portal_Step1") .. " <LINE> "
        .. "2. " .. getText("UI_portal_Step2") .. " <LINE> "
        .. "3. " .. getText("UI_portal_Step3") .. " <LINE> <LINE> "
        .. getText("UI_portal_Download") .. " <LINE> <RGB:0.4,0.8,1> " .. DOWNLOAD_URL .. " <RGB:1,1,1> <LINE> <LINE> "
    if #self.towns == 0 then
        text = text .. " <ORANGE> " .. getText("UI_portal_NoTowns") .. " <RGB:1,1,1> <LINE> <LINE> "
    else
        text = text .. getText("UI_portal_OneAtATime") .. " <LINE> <LINE> "
    end
    text = text .. " <SIZE:medium> " .. getText("UI_portal_CreditsTitle") .. " <LINE> <SIZE:small> "
        .. getText("UI_portal_CreditOSM") .. " <LINE> "
        .. getText("UI_portal_CreditKnoxMap") .. " <LINE> "
        .. getText("UI_portal_CreditTIS") .. " <LINE> <LINE> "
        .. getText("UI_portal_Tip") .. " <LINE> <RGB:0.4,0.8,1> " .. TIP_URL .. " <RGB:1,1,1> "
    self.detail:setText(text)
    self.detail:paginate()
    self.detail:setYScroll(0)
end

function PortalScreen:onSelectTown(town)
    self.selectedTown = town
    self.townButton:setEnable(town.workshopID ~= nil and isSteamOverlayEnabled())
    self:setPoster(town.poster)
    local text = " <SIZE:large> " .. town.name .. " <LINE> <SIZE:small> " .. town.size .. " <LINE> <LINE> "
    if town.enabled then
        text = text .. " <GREEN> " .. getText("UI_portal_Enabled") .. " <RGB:1,1,1> <LINE> " .. getText("UI_portal_HowToPlay")
    else
        text = text .. getText("UI_portal_NotEnabled") .. " <LINE> " .. getText("UI_portal_HowToEnable")
    end
    text = text .. " <LINE> <LINE> " .. getText("UI_portal_OneAtATime")
    self.detail:setText(text)
    self.detail:paginate()
    self.detail:setYScroll(0)
end

function PortalScreen:onMakeYourOwn()
    -- Portal's own Workshop page links the download; without Steam, copy it.
    if not openWorkshopItem(selfWorkshopID()) then copyLink(DOWNLOAD_URL) end
end

function PortalScreen:onCopyDownload()
    copyLink(DOWNLOAD_URL)
end

function PortalScreen:onCopyTip()
    copyLink(TIP_URL)
end

function PortalScreen:onTownPage()
    if self.selectedTown then openWorkshopItem(self.selectedTown.workshopID) end
end

function PortalScreen:onBack()
    self:setVisible(false)
    self:removeFromUIManager()
    PortalScreen.instance = nil
    local menu = MainScreen.instance
    if menu and menu.bottomPanel then
        menu.bottomPanel:setVisible(true)
        if self.joyfocus then
            self.joyfocus.focus = menu
            updateJoypadFocus(self.joyfocus)
        end
    end
end

-- Esc the way CreditsScreen does it: screens outside vanilla's list never get
-- key releases. Not while the "link copied" dialog is up.
local function onKeyPressed(key)
    local screen = PortalScreen.instance
    if key == Keyboard.KEY_ESCAPE and screen and screen:isReallyVisible() and not noticeOpen()
            and not UIManager.isModalVisible() then
        screen:onBack()
    end
end

function PortalScreen:onJoypadDown(button, joypadData)
    if button == Joypad.BButton then
        self:onBack()
    else
        ISPanelJoypad.onJoypadDown(self, button, joypadData)
    end
end

function PortalScreen.show(joypadData)
    if PortalScreen.instance then return end
    local sw, sh = getCore():getScreenWidth(), getCore():getScreenHeight()
    local w, h = math.floor(sw * 0.8), math.floor(sh * 0.8)
    local screen = PortalScreen:new((sw - w) / 2, (sh - h) / 2, w, h)
    screen:initialise()
    screen:instantiate()
    screen:addToUIManager()
    screen:setAlwaysOnTop(true)
    PortalScreen.instance = screen
    screen:refresh()
    screen:setVisible(true, joypadData)
end

-- ---- the main menu entry -------------------------------------------------------

-- Same clean-up and guards as vanilla's menu items (MainScreen.onMenuItemMouseDownMainMenu).
local function onPortalOption(item)
    local menu = MainScreen.instance
    if not menu then return end
    getSoundManager():playUISound("UIActivateMainMenuItem")
    if DebugScenarios and DebugScenarios.instance then
        menu:removeChild(DebugScenarios.instance)
        DebugScenarios.instance = nil
    end
    if menu.animPopup then menu.animPopup:removeFromUIManager() end
    if menu.termsOfServiceDialog then
        menu.termsOfServiceDialog:removeFromUIManager()
        menu.termsOfServiceDialog = nil
    end
    if (menu.delay or 0) > 0 or menu.tutorialButton or menu.checkSavefileModal then return end
    menu.bottomPanel:setVisible(false)
    PortalScreen.show(JoypadState.getMainMenuJoypad())
end

-- After Credits, the same size and highlight as the vanilla entries. Runs
-- again whenever the menu is rebuilt (mods changed, back from a game).
local function addMenuEntry()
    local menu = MainScreen.instance
    if not menu or menu.inGame or not menu.bottomPanel or not menu.creditOption or menu.portalOption then return end
    local panel = menu.bottomPanel
    local credit = menu.creditOption
    local hgt = credit:getHeight()
    local y = credit:getBottom()
    for _, child in pairs(panel:getChildren()) do
        if child ~= credit and child:getY() >= y then child:setY(child:getY() + hgt) end
    end
    local option = ISLabel:new(credit:getX(), y, hgt, getText("UI_portal_MenuEntry"), 1, 1, 1, 1, UIFont.Large, true)
    option.internal = "PORTAL"
    option:initialise()
    option.onMouseDown = onPortalOption
    panel:addChild(option)
    option.fade = UITransition.new()
    option.fade:setFadeIn(false)
    option.prerender = MainScreen.prerenderBottomPanelLabel
    -- Measure the text first; prerender gives every entry the shared width.
    menu.maxMenuItemWidth = math.max(menu.maxMenuItemWidth or 0, option:getWidth())
    option:setWidth(credit:getWidth())
    panel:setHeight(panel:getHeight() + hgt)
    menu.portalOption = option
end

-- Controllers: vanilla builds the menu's up/down list from its own entries
-- and routes A through onMenuItemMouseDownMainMenu, so add PORTAL to both.
local vanillaGainFocus = MainScreen.onGainJoypadFocus
function MainScreen:onGainJoypadFocus(joypadData)
    vanillaGainFocus(self, joypadData)
    local option = self.portalOption
    if not option or not option:isVisible() or not self.joypadButtonsY then return end
    option:setJoypadFocused(false)
    for k, row in ipairs(self.joypadButtonsY) do
        if row[1] == self.creditOption then
            table.insert(self.joypadButtonsY, k + 1, { option })
            if self.joypadIndexY and self.joypadIndexY > k then
                self.joypadIndexY = self.joypadIndexY + 1
                self.joypadButtons = self.joypadButtonsY[self.joypadIndexY]
            end
            break
        end
    end
end

local vanillaMenuItem = MainScreen.onMenuItemMouseDownMainMenu
MainScreen.onMenuItemMouseDownMainMenu = function(item, x, y)
    if item and item.internal == "PORTAL" then return onPortalOption(item) end
    return vanillaMenuItem(item, x, y)
end

-- A controller switched on while the panel is open should land on it.
local vanillaFocus = MainScreen.getCurrentFocusForController
function MainScreen:getCurrentFocusForController()
    local screen = PortalScreen.instance
    if screen and screen:isReallyVisible() and not (self.animPopup and self.animPopup:isReallyVisible()) then
        return screen
    end
    return vanillaFocus(self)
end

-- The panel is not one of MainScreen's children, so resize it ourselves.
local function onResolutionChange(oldw, oldh, neww, newh)
    local screen = PortalScreen.instance
    if not screen then return end
    local w, h = math.floor(neww * 0.8), math.floor(newh * 0.8)
    screen:setWidth(w)
    screen:setHeight(h)
    screen:setX((neww - w) / 2)
    screen:setY((newh - h) / 2)
    screen:recalcSize()
end

Events.OnMainMenuEnter.Add(addMenuEntry)
Events.OnKeyPressed.Add(onKeyPressed)
Events.OnResolutionChange.Add(onResolutionChange)
