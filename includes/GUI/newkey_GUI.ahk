; Kodex On-The-Fly Hotstring Creation GUI - AutoHotkey v2 Migrated Version

global NewKeyGui, KodexPNG

NewKeyGUI(CurrentBundleParam := "")
{
    global NewKeyGui, KodexPNG
    
    if (IsSet(NewKeyGui))
        NewKeyGui.Destroy()
    
    ; Build bundles list
    BundleList := "Default|"
    for Bundle in LoopFiles(A_ScriptDir . "\bundles", "D")
    {
        if (Bundle.Name != "Autocorrect")
            BundleList .= Bundle.Name . "|"
    }
    StringTrimRight(BundleList, BundleList, 1)
    
    ; Get current bundle if called from management GUI
    CurrentBundle := CurrentBundleParam != "" ? CurrentBundleParam : "Default"
    
    ; Get trigger defaults
    try
        EnterBox := IniRead("kodex.ini", "Triggers", "Enter", 0)
    catch
        EnterBox := 0
    
    try
        TabBox := IniRead("kodex.ini", "Triggers", "Tab", 0)
    catch
        TabBox := 0
    
    try
        SpaceBox := IniRead("kodex.ini", "Triggers", "Space", 0)
    catch
        SpaceBox := 0
    
    try
        NoTrigBox := IniRead("kodex.ini", "Triggers", "NoTrig", 0)
    catch
        NoTrigBox := 0
    
    ; Create GUI
    NewKeyGui := GuiCreate("+Owner +AlwaysOnTop")
    NewKeyGui.OnEvent("Escape", NewKeyGUI_Escape)
    NewKeyGui.OnEvent("Close", NewKeyGUI_Escape)
    
    NewKeyGui.Add("Text", "x10 y20", "Hotstring:")
    NewKeyGui.Add("Edit", "x13 y45 r1 W65 vRString")
    NewKeyGui.Add("Edit", "x100 y45 r4 W395 vFullText", "Enter your replacement text here...")
    
    NewKeyGui.Add("DropDownList", "x100 y15 w100 vTextOrScript", "Text||Script")
    NewKeyGui.Add("Text", "x315 y19", "Bundle:")
    NewKeyGui.Add("DropDownList", "x370 y15 w125 vBundle", BundleList)
    NewKeyGui.Bundle.Value := CurrentBundle
    
    NewKeyGui.Add("Text", "x115 y70", "Trigger:")
    NewKeyGui.Add("Checkbox", "yp x175 vEnterCbox Checked" . EnterBox, "Enter")
    NewKeyGui.EnterCbox.OnEvent("Click", CheckBox_DisableChecks)
    NewKeyGui.Add("Checkbox", "yp x242 vTabCbox Checked" . TabBox, "Tab")
    NewKeyGui.TabCbox.OnEvent("Click", CheckBox_DisableChecks)
    NewKeyGui.Add("Checkbox", "yp x305 vSpaceCbox Checked" . SpaceBox, "Space")
    NewKeyGui.SpaceCbox.OnEvent("Click", CheckBox_DisableChecks)
    NewKeyGui.Add("Checkbox", "yp x388 vNoTrigCbox Checked" . NoTrigBox, "Instant")
    NewKeyGui.NoTrigCbox.OnEvent("Click", CheckBox_DisableChecks)
    
    NewKeyGui.Add("Button", "w80 x320 Default vOKButton", "&OK")
    NewKeyGui.OKButton.OnEvent("Click", Button_NewKeyOK)
    NewKeyGui.Add("Button", "w80 xp+90 vCancelButton", "&Cancel")
    NewKeyGui.CancelButton.OnEvent("Click", Button_NewKeyCancel)
    
    NewKeyGui.Add("Picture", "x0 y105 h100 w500", KodexPNG)
    
    NewKeyGui.Show("W500 H200", "Add new hotstring...")
}

CheckBox_DisableChecks(GuiObjName, GuiObj)
{
    global NewKeyGui
    
    CheckedCbox := GuiObj.Name
    if (CheckedCbox = "NoTrigCbox")
    {
        NewKeyGui.EnterCbox.Value := 0
        NewKeyGui.TabCbox.Value := 0
        NewKeyGui.SpaceCbox.Value := 0
    }
    else
    {
        NewKeyGui.NoTrigCbox.Value := 0
    }
}

Button_NewKeyOK(GuiObjName, GuiObj)
{
    global NewKeyGui
    
    NewKeyGui.Submit(false)
    
    RString := NewKeyGui.RString.Value
    FullText := NewKeyGui.FullText.Value
    TextOrScript := NewKeyGui.TextOrScript.Value
    Bundle := NewKeyGui.Bundle.Value
    
    if (RString = "")
    {
        MsgBox("Please enter a hotstring.")
        return
    }
    
    hexRString := Hexify(RString)
    if (Bundle != "") and (Bundle != "Default")
        AddToDir := "Bundles\" . Bundle . "\"
    else
        AddToDir := ""
    
    if (FileExist(A_ScriptDir . "\" . AddToDir . "replacements\" . hexRString . ".txt"))
    {
        MsgBox("Hotstring already exists", "A replacement with the text " . RString . " already exists. Would you like to try again?", 1)
        return
    }
    
    IsScript := (TextOrScript = "Script")
    if (SaveHotstring(RString, FullText, IsScript, AddToDir, NewKeyGui.SpaceCbox.Value, NewKeyGui.TabCbox.Value, NewKeyGui.EnterCbox.Value, NewKeyGui.NoTrigCbox.Value))
    {
        NewKeyGui.Destroy()
    }
}

Button_NewKeyCancel(GuiObjName, GuiObj)
{
    global NewKeyGui
    NewKeyGui.Destroy()
}

NewKeyGUI_Escape(GuiObjName, GuiObj)
{
    global NewKeyGui
    if (IsSet(NewKeyGui))
        NewKeyGui.Destroy()
}
