; Kodex Tray Menu - AutoHotkey v2 Migrated Version

TrayMenu_Init()
{
    global A_TrayMenu, Disable
    
    TrayMenu := A_TrayMenu
    TrayMenu.Delete()
    TrayMenu.Add("&Manage hotstrings", TrayMenu_Manage)
    TrayMenu.Add("&Create new hotstring", TrayMenu_NewKey)
    TrayMenu.Add()
    TrayMenu.Add("P&references...", TrayMenu_Preferences)
    TrayMenu.Add("&Import bundle", TrayMenu_Import)
    TrayMenu.Add("&Help", TrayMenu_Help)
    TrayMenu.Add()
    TrayMenu.Add("&About...", TrayMenu_About)
    TrayMenu.Add("&Disable", TrayMenu_Disable)
    if (Disable = 1)
        TrayMenu.Check("&Disable")
    TrayMenu.Add()
    TrayMenu.Add("E&xit", TrayMenu_Exit)
    TrayMenu.Default := "&Manage hotstrings"
    TrayMenu.Tip := "Kodex"
}

TrayMenu_Manage(ItemName, ItemPos, MenuName)
{
    ManageGUI()
}

TrayMenu_NewKey(ItemName, ItemPos, MenuName)
{
    NewKeyGUI()
}

TrayMenu_Preferences(ItemName, ItemPos, MenuName)
{
    PreferencesGUI()
}

TrayMenu_Import(ItemName, ItemPos, MenuName)
{
    ; TODO: Implement import functionality
}

TrayMenu_Help(ItemName, ItemPos, MenuName)
{
    HelpGUI()
}

TrayMenu_About(ItemName, ItemPos, MenuName)
{
    AboutGUI()
}

TrayMenu_Disable(ItemName, ItemPos, MenuName)
{
    global Disable
    Disable := Disable ? 0 : 1
    IniWrite(Disable, "kodex.ini", "Settings", "Disable")
}

TrayMenu_Exit(ItemName, ItemPos, MenuName)
{
    ExitApp(0)
}
