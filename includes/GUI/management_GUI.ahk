; Kodex Management GUI - AutoHotkey v2 Migrated Version
; Implementation and GUI for management of hotstrings

global ManagementGui, FileList, Bundles, CurrentBundle, ActiveChoice, MakeActive
global IsScript, TextOrScript, FullText, SaveToDir, PSaveSuccessful
global EditThis, RString

; Build and show the management GUI
ManageGUI()
{
    global ManagementGui, FileList, Bundles, CurrentBundle, ActiveChoice, MakeActive
    
    ; Destroy previous instance
    if (IsSet(ManagementGui))
        ManagementGui.Destroy()
    
    ; Initialize variables
    CurrentBundle := "Default"
    ActiveChoice := ""
    MakeActive := ""
    
    ; Build menus
    ToolsMenu := Menu()
    ToolsMenu.Add("P&references...", ToolsMenu_Preferences)
    
    BundlesMenu := Menu()
    BundlesMenu.Add("&Export", BundlesMenu_Export)
    BundlesMenu.Add("&Import", BundlesMenu_Import)
    BundlesMenu.Add("&Add", BundlesMenu_AddBundle)
    BundlesMenu.Add("&Remove", BundlesMenu_DeleteBundle)
    
    HelpMenu := Menu()
    HelpMenu.Add("&Basic Use", HelpMenu_BasicUse)
    HelpMenu.Add("Ad&vanced Use", HelpMenu_Scripting)
    HelpMenu.Add("&Homepage", HelpMenu_Homepage)
    HelpMenu.Add("&About...", HelpMenu_About)
    
    MgmtMenuBar := Menu()
    MgmtMenuBar.Add("&Tools", ToolsMenu)
    MgmtMenuBar.Add("&Bundles", BundlesMenu)
    MgmtMenuBar.Add("&Help", HelpMenu)
    
    ; Get file list and bundles
    GetFileListGUI()
    
    ; Build bundle tabs
    BundleList := "Default"
    BundlesArray := []
    for Bundle in LoopFiles(A_ScriptDir . "\bundles\", "D")
    {
        thisBundle := Bundle.Name
        if (thisBundle != "Autocorrect")
        {
            BundleList .= "|" . thisBundle
            BundlesArray.Push(thisBundle)
        }
    }
    
    ; Create the GUI
    ManagementGui := GuiCreate()
    ManagementGui.MenuBar := MgmtMenuBar
    ManagementGui.OnEvent("Escape", ManagementGui_Escape)
    ManagementGui.OnEvent("Close", ManagementGui_Close)
    
    ; Tab control for bundles
    ManagementGui.Add("Tab", "x5 y5 h390 w597 vBundleTabs", BundleList)
    ManagementGui.BundleTabs.OnEvent("Change", TabControl_ListBundle)
    
    ; Hotstring list and controls
    ManagementGui.Add("Text", "Section")
    ManagementGui.Add("Text", "ys xs", "Hotstring:")
    ManagementGui.Add("ListBox", "xs r15 W100 vChoice Sort", FileList)
    ManagementGui.Choice.OnEvent("Change", ListBox_ShowString)
    
    ManagementGui.Add("Button", "w35 xs+10 vAddButton", "+")
    ManagementGui.AddButton.OnEvent("Click", Button_Add)
    ManagementGui.Add("Button", "w35 xp+40 vDeleteButton", "-")
    ManagementGui.DeleteButton.OnEvent("Click", Button_Delete)
    
    ManagementGui.Add("DropDownList", "Section ys vTextOrScript", "Text||Script")
    ManagementGui.TextOrScript.OnEvent("Change", DropDownList_TextOrScript)
    
    ManagementGui.Add("Edit", "r12 W460 xs vFullText")
    ManagementGui.Add("Text", "xs", "Trigger:")
    
    ManagementGui.Add("Checkbox", "gDisableChecks vEnterCbox yp xp+65", "Enter")
    ManagementGui.EnterCbox.OnEvent("Click", Checkbox_DisableChecks)
    ManagementGui.Add("Checkbox", "gDisableChecks vTabCbox yp xp+65", "Tab")
    ManagementGui.TabCbox.OnEvent("Click", Checkbox_DisableChecks)
    ManagementGui.Add("Checkbox", "gDisableChecks vSpaceCbox yp xp+60", "Space")
    ManagementGui.SpaceCbox.OnEvent("Click", Checkbox_DisableChecks)
    ManagementGui.Add("Checkbox", "gDisableChecks vNoTrigCbox yp xp+80", "Instant")
    ManagementGui.NoTrigCbox.OnEvent("Click", Checkbox_DisableChecks)
    
    ManagementGui.Add("Button", "w80 vSaveButton xs+375 yp", "&Save Hotstring")
    ManagementGui.SaveButton.OnEvent("Click", Button_PButtonSave)
    
    ; Bundle enabled checkbox
    try
        bundleCheck := IniRead("kodex.ini", "Bundles", "Default", 0)
    catch
        bundleCheck := 0
    
    ManagementGui.Add("Checkbox", "Checked" . bundleCheck . " vbundleCheck xs+360 yp+50", "Bundle Enabled")
    ManagementGui.bundleCheck.OnEvent("Click", Checkbox_ToggleBundle)
    
    ManagementGui.Add("Button", "w80 Default vOKButton xs+290 yp+30", "&OK")
    ManagementGui.OKButton.OnEvent("Click", Button_PButtonOK)
    ManagementGui.Add("Button", "w80 xp+90 vCancelButton", "&Cancel")
    ManagementGui.CancelButton.OnEvent("Click", Button_PButtonCancel)
    
    ManagementGui.Show(, "Kodex Management")
    ManagementGui.Choice.Focus()
    ListBundle_PopulateGUI()
}

; Helper function to get file list for the GUI
GetFileListGUI()
{
    global FileList
    FileList := ""
    for File in LoopFiles(A_ScriptDir . "\Active\replacements\*.txt")
    {
        hexName := SubStr(File.Name, 1, StrLen(File.Name) - 4)  ; Remove .txt
        plainName := DeHexify(hexName)
        FileList .= plainName . "|"
    }
    StringTrimRight(FileList, FileList, 1)  ; Remove trailing |
}

; Callback functions for menu items
ToolsMenu_Preferences(GuiObjName, GuiObj)
{
    ; TODO: Implement preferences dialog
}

BundlesMenu_Export(GuiObjName, GuiObj)
{
    ; TODO: Implement export functionality
}

BundlesMenu_Import(GuiObjName, GuiObj)
{
    ; TODO: Implement import functionality
}

BundlesMenu_AddBundle(GuiObjName, GuiObj)
{
    ; TODO: Implement add bundle functionality
}

BundlesMenu_DeleteBundle(GuiObjName, GuiObj)
{
    ; TODO: Implement delete bundle functionality
}

HelpMenu_BasicUse(GuiObjName, GuiObj)
{
    ; TODO: Implement basic use help
}

HelpMenu_Scripting(GuiObjName, GuiObj)
{
    ; TODO: Implement scripting help
}

HelpMenu_Homepage(GuiObjName, GuiObj)
{
    ; TODO: Implement homepage link
}

HelpMenu_About(GuiObjName, GuiObj)
{
    ; TODO: Implement about dialog
}

; Tab control callback
TabControl_ListBundle(GuiObjName, GuiObj)
{
    ListBundle_PopulateGUI()
}

; Populate the GUI when tab is changed
ListBundle_PopulateGUI()
{
    global ManagementGui, CurrentBundle, FileList, ActiveChoice, IsScript
    
    ; Get current bundle from tab control
    CurrentBundle := ManagementGui.BundleTabs.Value
    
    ; Disable controls initially
    GuiControl_DisableControls()
    
    ; Get bundle checkbox state
    try
        bundleCheck := IniRead("kodex.ini", "Bundles", CurrentBundle, 0)
    catch
        bundleCheck := 0
    
    ; Get file list for current bundle
    BundleFileList := ""
    if (CurrentBundle = "Default")
        BundlePath := A_ScriptDir . "\Active\replacements\*.txt"
    else
        BundlePath := A_ScriptDir . "\bundles\" . CurrentBundle . "\replacements\*.txt"
    
    for File in LoopFiles(BundlePath)
    {
        hexName := SubStr(File.Name, 1, StrLen(File.Name) - 4)
        plainName := DeHexify(hexName)
        BundleFileList .= plainName . "|"
    }
    StringTrimRight(BundleFileList, BundleFileList, 1)
    
    ManagementGui.Choice.Delete()
    ManagementGui.Choice.Add(StrSplit(BundleFileList, "|"))
    ManagementGui.FullText.Value := ""
    ManagementGui.EnterCbox.Value := 0
    ManagementGui.TabCbox.Value := 0
    ManagementGui.SpaceCbox.Value := 0
    ManagementGui.NoTrigCbox.Value := 0
    ManagementGui.bundleCheck.Value := bundleCheck
}

; ListBox change callback
ListBox_ShowString(GuiObjName, GuiObj)
{
    ShowString_PopulateFields()
}

; Populate hotstring details when selected
ShowString_PopulateFields()
{
    global ManagementGui, CurrentBundle, ActiveChoice, IsScript
    
    GuiControl_EnableControls()
    ActiveChoice := ManagementGui.Choice.Value
    
    if (ActiveChoice = "")
        return
    
    ; Get trigger states from bank files
    ActiveChoiceHex := Hexify(ActiveChoice)
    
    if (CurrentBundle = "Default")
        ReadFrom := A_ScriptDir . "\Active\"
    else
        ReadFrom := A_ScriptDir . "\bundles\" . CurrentBundle . "\"
    
    try
        enter := FileRead(ReadFrom . "bank\enter.csv")
    catch
        enter := ""
    
    try
        tab := FileRead(ReadFrom . "bank\tab.csv")
    catch
        tab := ""
    
    try
        space := FileRead(ReadFrom . "bank\space.csv")
    catch
        space := ""
    
    try
        notrig := FileRead(ReadFrom . "bank\notrig.csv")
    catch
        notrig := ""
    
    ManagementGui.EnterCbox.Value := InStr(enter, "|" . ActiveChoiceHex . "|") ? 1 : 0
    ManagementGui.TabCbox.Value := InStr(tab, "|" . ActiveChoiceHex . "|") ? 1 : 0
    ManagementGui.SpaceCbox.Value := InStr(space, "|" . ActiveChoiceHex . "|") ? 1 : 0
    ManagementGui.NoTrigCbox.Value := InStr(notrig, "|" . ActiveChoiceHex . "|") ? 1 : 0
    
    ; Read and display replacement text
    try
        Text := FileRead(ReadFrom . "replacements\" . ActiveChoiceHex . ".txt")
    catch
        Text := ""
    
    if (InStr(Text, "::scr::"))
    {
        ManagementGui.TextOrScript.Value := "Script"
        Text := StrReplace(Text, "::scr::")
        IsScript := true
    }
    else
    {
        ManagementGui.TextOrScript.Value := "Text"
        IsScript := false
    }
    
    ManagementGui.FullText.Value := Text
}

; Disable all controls
GuiControl_DisableControls()
{
    global ManagementGui
    ManagementGui.FullText.Opt("-Enabled")
    ManagementGui.EnterCbox.Opt("-Enabled")
    ManagementGui.TabCbox.Opt("-Enabled")
    ManagementGui.SpaceCbox.Opt("-Enabled")
    ManagementGui.NoTrigCbox.Opt("-Enabled")
    ManagementGui.SaveButton.Opt("-Enabled")
    ManagementGui.TextOrScript.Opt("-Enabled")
}

; Enable all controls
GuiControl_EnableControls()
{
    global ManagementGui
    ManagementGui.FullText.Opt("+Enabled")
    ManagementGui.EnterCbox.Opt("+Enabled")
    ManagementGui.TabCbox.Opt("+Enabled")
    ManagementGui.SpaceCbox.Opt("+Enabled")
    ManagementGui.NoTrigCbox.Opt("+Enabled")
    ManagementGui.SaveButton.Opt("+Enabled")
    ManagementGui.TextOrScript.Opt("+Enabled")
}

; Button click callbacks
Button_Add(GuiObjName, GuiObj)
{
    ; TODO: Open new hotstring dialog
}

Button_Delete(GuiObjName, GuiObj)
{
    global ManagementGui, ActiveChoice, CurrentBundle
    
    if (ActiveChoice = "")
        return
    
    result := MsgBox("Are you sure you want to delete this hotstring: " . ActiveChoice . "?", "Confirm Delete", 1)
    if (result = "OK")
    {
        DeleteHotstring(ActiveChoice, CurrentBundle)
        ListBundle_PopulateGUI()
        BuildActive()
    }
}

DropDownList_TextOrScript(GuiObjName, GuiObj)
{
    ; Optional: Handle text/script mode change
}

Checkbox_DisableChecks(GuiObjName, GuiObj)
{
    ; TODO: Implement disable checks logic
}

Button_PButtonSave(GuiObjName, GuiObj)
{
    global ManagementGui, CurrentBundle, ActiveChoice, FullText, IsScript, SaveToDir, PSaveSuccessful
    
    ManagementGui.Submit(false)
    IsScript := (ManagementGui.TextOrScript.Value = "Script")
    
    if (ActiveChoice != "")
    {
        if (CurrentBundle != "" and CurrentBundle != "Default")
            SaveToDir := "Bundles\" . CurrentBundle . "\"
        else
            SaveToDir := ""
        
        PSaveSuccessful := SaveHotstring(ActiveChoice, ManagementGui.FullText.Value, IsScript, 
                                        SaveToDir, ManagementGui.SpaceCbox.Value, 
                                        ManagementGui.TabCbox.Value, ManagementGui.EnterCbox.Value, 
                                        ManagementGui.NoTrigCbox.Value)
    }
    else
    {
        PSaveSuccessful := true
    }
}

Button_PButtonOK(GuiObjName, GuiObj)
{
    Button_PButtonSave(GuiObjName, GuiObj)
    if (PSaveSuccessful)
    {
        ManagementGui.Destroy()
    }
}

Button_PButtonCancel(GuiObjName, GuiObj)
{
    global ManagementGui
    ManagementGui.Destroy()
}

ManagementGui_Escape(GuiObjName, GuiObj)
{
    global ManagementGui
    ManagementGui.Destroy()
}

ManagementGui_Close(GuiObjName, GuiObj)
{
    return false
}

; Context menu for right-click on hotstring
ShowContextMenu(ControlName)
{
    global ManagementGui, ActiveChoice, EditThis
    
    EditThis := ManagementGui.Choice.Value
    if (EditThis = "")
        return
    
    RcMenu := Menu()
    RcMenu.Add("Rename " . EditThis . " hotstring...", ContextMenu_Rename)
    
    CoordMode("Mouse", "Screen")
    MouseGetPos(&x, &y)
    RcMenu.Show(x, y)
}

ContextMenu_Rename(ItemName, ItemPos, MenuName)
{
    global EditThis
    RenameHotstring(EditThis)
}