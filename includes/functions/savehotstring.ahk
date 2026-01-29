SaveHotstring(HotString, Replacement, IsScript, Bundle := "", SpaceIsTrigger := false, TabIsTrigger := false, EnterIsTrigger := false, NoTrigger := false)
{
	global EnterCSV, TabCSV, SpaceCSV, NoTrigCSV
	global EnterKeys, TabKeys, SpaceKeys, NoTrigKeys

	HotString := Hexify(HotString)
	successful := false

	if !(EnterIsTrigger || TabIsTrigger || SpaceIsTrigger || NoTrigger)
	{
		MsgBox("You need to choose a trigger method in order to save a hotstring replacement.", "Choose a trigger", "64")
		return false
	}

	if (HotString != "" && Replacement != "")
	{
		successful := true
		if IsScript
			Replacement := "::scr::" . Replacement

		IniWrite(SpaceIsTrigger, "kodex.ini", "Triggers", "Space")
		IniWrite(TabIsTrigger, "kodex.ini", "Triggers", "Tab")
		IniWrite(EnterIsTrigger, "kodex.ini", "Triggers", "Enter")
		IniWrite(NoTrigger, "kodex.ini", "Triggers", "NoTrig")

		target := A_ScriptDir . "\" . Bundle . "replacements\" . HotString . ".txt"
		FileDelete(target)
		FileAppend(Replacement, target)

		if EnterIsTrigger
			AddToBank(HotString, Bundle, "enter")
		else
			DelFromBank(HotString, Bundle, "enter")

		if TabIsTrigger
			AddToBank(HotString, Bundle, "tab")
		else
			DelFromBank(HotString, Bundle, "tab")

		if SpaceIsTrigger
			AddToBank(HotString, Bundle, "space")
		else
			DelFromBank(HotString, Bundle, "space")

		if NoTrigger
			AddToBank(HotString, Bundle, "notrig")
		else
			DelFromBank(HotString, Bundle, "notrig")
	}

	BuildActive()
	return successful
}

DeleteHotstring(Hotstring, Bundle := "")
{
	Hotstring := Hexify(Hotstring)
	if (Bundle != "" && Bundle != "Default")
		RemoveFromDir := "Bundles\" . Bundle . "\"
	else
		RemoveFromDir := ""

	path := A_ScriptDir . "\" . RemoveFromDir . "replacements\" . Hotstring . ".txt"
	FileDelete(path)
	DelFromBank(Hotstring, RemoveFromDir, "enter")
	DelFromBank(Hotstring, RemoveFromDir, "tab")
	DelFromBank(Hotstring, RemoveFromDir, "space")
	DelFromBank(Hotstring, RemoveFromDir, "notrig")

	; GUI migration pending: management GUI uses GuiControl calls
	; TODO: migrate these to Gui object calls when GUIs are converted to v2
	; GuiControl,2:,Choice,|%Bundle%
	; GuiControl,2:,FullText,
	; GuiControl,2:,EnterCbox,0
	; GuiControl,2:,TabCbox,0
	; GuiControl,2:,SpaceCbox,0

	BuildActive()
	return
}