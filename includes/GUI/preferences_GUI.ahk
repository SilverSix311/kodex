; Kodex Preferences GUI - AutoHotkey v2 Migrated Version

global PreferencesGui, MODE, otfhotkey, managehotkey, disablehotkey

PreferencesGUI()
{
    global PreferencesGui, KodexICO, MODE
    
    if (IsSet(PreferencesGui))
        PreferencesGui.Destroy()
    
    try
        otfhotkey := IniRead("kodex.ini", "Hotkey", "OntheFly", "")
    catch
        otfhotkey := ""
    
    try
        managehotkey := IniRead("kodex.ini", "Hotkey", "Management", "")
    catch
        managehotkey := ""
    
    try
        disablehotkey := IniRead("kodex.ini", "Hotkey", "Disable", "")
    catch
        disablehotkey := ""
    
    try
        StartupValue := IniRead("kodex.ini", "Settings", "Startup", 0)
    catch
        StartupValue := 0
    
    try
        UpdateValue := IniRead("kodex.ini", "Preferences", "UpdateCheck", 1)
    catch
        UpdateValue := 1
    
    try
        AutoCorrValue := IniRead("kodex.ini", "Preferences", "AutoCorrect", 1)
    catch
        AutoCorrValue := 1
    
    try
        ExSoundValue := IniRead("kodex.ini", "Preferences", "ExSound", 1)
    catch
        ExSoundValue := 1
    
    try
        SynergyValue := IniRead("kodex.ini", "Preferences", "Synergy", 0)
    catch
        SynergyValue := 0
    
    try
        expanded := IniRead("kodex.ini", "Stats", "Expanded", 0)
    catch
        expanded := 0
    
    try
        chars_saved := IniRead("kodex.ini", "Stats", "Characters", 0)
    catch
        chars_saved := 0
    
    time_saved := chars_saved / 24000
    
    PreferencesGui := GuiCreate()
    PreferencesGui.Add("Tab", "x5 y5 w500 h350 vTabs", "General|Print|Stats")
    
    ; General tab
    PreferencesGui.Add("Text", "x10 y40", "On-the-Fly shortcut:")
    PreferencesGui.Add("Hotkey", "x120 y40 w100 vsotfhotkey", otfhotkey)
    
    PreferencesGui.Add("Text", "x10 y70", "Hotstring Management shortcut:")
    PreferencesGui.Add("Hotkey", "x120 y70 w100 vsmanagehotkey", managehotkey)
    
    PreferencesGui.Add("Text", "x10 y100", "Global disable shortcut:")
    PreferencesGui.Add("Hotkey", "x120 y100 w100 vdisablehotkey", disablehotkey)
    
    PreferencesGui.Add("Radio", "x10 y130 vModeGroup" . (MODE ? "" : " Checked"), "Compatibility mode (Default)")
    PreferencesGui.Add("Radio", "x10 y150" . (MODE ? " Checked" : ""), "Clipboard mode (Faster, but less compatible)")
    
    PreferencesGui.Add("Checkbox", "x10 y180 vStartup Checked" . StartupValue, "Run Kodex at start up")
    PreferencesGui.Add("Checkbox", "x10 y200 vUpdate Checked" . UpdateValue, "Check for updates at launch?")
    PreferencesGui.Add("Checkbox", "x10 y220 vAutoCorrect Checked" . AutoCorrValue, "Enable Universal Spelling AutoCorrect?")
    PreferencesGui.Add("Checkbox", "x10 y240 vExSound Checked" . ExSoundValue, "Play sound when replacement triggered?")
    PreferencesGui.Add("Checkbox", "x10 y260 vSynergy Checked" . SynergyValue, "Make Kodex compatible across computers with Synergy?")
    
    ; Print tab
    PreferencesGui.Tab(2)
    PreferencesGui.Add("Button", "w150 h150 x10 y40 vPrintBtn", "Create Printable Kodex Cheatsheet")
    PreferencesGui.PrintBtn.OnEvent("Click", Button_PrintableList)
    PreferencesGui.Add("Text", "x170 y50 w150 Wrap", "Click the big button to export a printable cheatsheet of all your Kodex hotstrings, replacements, and triggers.")
    
    ; Stats tab
    PreferencesGui.Tab(3)
    PreferencesGui.Add("Text", "x10 y40", "Your Kodex stats:")
    PreferencesGui.Add("Text", "x25 y60", "Snippets expanded: " . expanded)
    PreferencesGui.Add("Text", "x25 y80", "Characters saved: " . chars_saved)
    PreferencesGui.Add("Text", "x25 y100", "Hours saved: " . Format("{:.2f}", time_saved) . " (assuming 400 chars/minute)")
    
    ; Buttons
    PreferencesGui.Add("Button", "w75 x285 y330 Default vOKBtn", "&OK")
    PreferencesGui.OKBtn.OnEvent("Click", Button_PreferencesOK)
    PreferencesGui.Add("Button", "w75 x365 y330 vCancelBtn", "&Cancel")
    PreferencesGui.CancelBtn.OnEvent("Click", Button_PreferencesCancel)
    
    PreferencesGui.Show("w450 h360", "Kodex Preferences")
}

Button_PrintableList(GuiObjName, GuiObj)
{
    ; TODO: Implement printable list generation
}

Button_PreferencesOK(GuiObjName, GuiObj)
{
    global PreferencesGui, MODE, otfhotkey, managehotkey, disablehotkey
    
    PreferencesGui.Submit(false)
    
    sotfhotkey := PreferencesGui.sotfhotkey.Value
    smanagehotkey := PreferencesGui.smanagehotkey.Value
    sdisablehotkey := PreferencesGui.disablehotkey.Value
    NewMode := PreferencesGui.ModeGroup.Value - 1
    
    ; Handle hotkey changes
    if (sotfhotkey != otfhotkey)
    {
        otfhotkey := sotfhotkey
        IniWrite(otfhotkey, "kodex.ini", "Hotkey", "OntheFly")
    }
    
    if (smanagehotkey != managehotkey)
    {
        managehotkey := smanagehotkey
        IniWrite(managehotkey, "kodex.ini", "Hotkey", "Management")
    }
    
    IniWrite(sdisablehotkey, "kodex.ini", "Hotkey", "Disable")
    
    MODE := NewMode
    IniWrite(MODE, "kodex.ini", "Settings", "Mode")
    IniWrite(PreferencesGui.Update.Value, "kodex.ini", "Preferences", "UpdateCheck")
    IniWrite(PreferencesGui.Startup.Value, "kodex.ini", "Settings", "Startup")
    IniWrite(PreferencesGui.AutoCorrect.Value, "kodex.ini", "Preferences", "AutoCorrect")
    IniWrite(PreferencesGui.ExSound.Value, "kodex.ini", "Preferences", "ExSound")
    IniWrite(PreferencesGui.Synergy.Value, "kodex.ini", "Preferences", "Synergy")
    
    ; Handle startup shortcut
    if (PreferencesGui.Startup.Value = 1)
    {
        if (!FileExist(A_StartMenu . "\Programs\Startup\Kodex.lnk"))
        {
            IconLocation := A_IsCompiled ? A_ScriptFullPath : (FileExist(A_ScriptDir . "\resources\kodex.ico") ? A_ScriptDir . "\resources\kodex.ico" : A_AhkPath)
            FileCreateShortcut(A_ScriptFullPath, A_StartMenu . "\Programs\Startup\Kodex.lnk", A_ScriptDir, , "Text replacement system tray application", IconLocation)
        }
    }
    else
    {
        if (FileExist(A_StartMenu . "\Programs\Startup\Kodex.lnk"))
            FileDelete(A_StartMenu . "\Programs\Startup\Kodex.lnk")
    }
    
    PreferencesGui.Destroy()
}

Button_PreferencesCancel(GuiObjName, GuiObj)
{
    global PreferencesGui
    PreferencesGui.Destroy()
}
