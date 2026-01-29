; Kodex Installer - AutoHotkey v2 Migrated Version
; Installs Kodex to the specified directory and optionally launches it

#SingleInstance Force
#NoTrayIcon

MainInstallGUI()

MainInstallGUI()
{
    InstallDir := A_ProgramFiles . "\Kodex"
    
    MyGui := GuiCreate()
    MyGui.Add("Text", "y10 x10", "Where would you like to install Kodex?")
    MyGui.Add("Edit", "x20 y30 r1 W300 vInstallDir", InstallDir)
    MyGui.Add("Button", "w80 GBrowse x320 y29", "&Browse")
    MyGui.Add("Button", "w80 default GInstall x225 yp+50", "&Install")
    MyGui.Add("Button", "w80 xp+90 GCancel", "&Cancel")
    
    MyGui.Show("auto", "Install Kodex")
    
    ; Define button handlers
    MyGui.Browse := Button_Browse
    MyGui.Install := (GuiCtrlObj) => Button_Install(MyGui)
    MyGui.Cancel := (GuiCtrlObj) => Button_Cancel(MyGui)
    
    ; Store reference for button handlers
    global g_InstallerGui := MyGui
}

Button_Browse(GuiCtrlObj)
{
    global g_InstallerGui
    InstallDir := DirSelect(, , "Select your installation folder")
    if (InstallDir != "")
        g_InstallerGui["InstallDir"].Value := InstallDir
}

Button_Install(MyGui)
{
    ; Get the install directory from the edit control
    InstallDir := MyGui["InstallDir"].Value
    
    MyGui.Destroy()
    
    ; Create the directory if it doesn't exist
    if !DirExist(InstallDir)
    {
        try
            DirCreate(InstallDir)
        catch Error as err
        {
            MsgBox("Error creating directory: " . err.Message)
            ExitApp()
        }
    }
    
    ; Close existing Kodex process
    try
        ProcessClose("kodex.exe")
    catch
    {
        ; Process not running, that's OK
    }
    
    ; Copy the executable (assuming it's embedded or in same directory)
    ; If using FileInstall, that requires the source file at compile time
    try
    {
        SourceExe := A_ScriptDir . "\kodex.exe"
        if FileExist(SourceExe)
        {
            FileCopy(SourceExe, InstallDir . "\kodex.exe", 1)  ; 1 = overwrite
        }
    }
    catch Error as err
    {
        MsgBox("Error installing Kodex: " . err.Message)
        ExitApp()
    }
    
    ; Show success dialog
    ResultGui := GuiCreate()
    ResultGui.Add("Text", "y10 x10", "Kodex successfully installed!")
    ResultGui.Add("Checkbox", "Checked y30 x20 vLaunch", "Launch Kodex")
    ResultGui.Add("Button", "w80 default GAutoRun x300 yp+65", "&Finish")
    
    ResultGui.Show("auto", "Installation complete")
    
    ResultGui.AutoRun := (GuiCtrlObj) => Button_AutoRun(ResultGui, InstallDir)
    
    global g_InstallerGui := ResultGui
}

Button_AutoRun(MyGui, InstallDir)
{
    LaunchValue := MyGui["Launch"].Value
    MyGui.Destroy()
    
    if (LaunchValue = 1)
    {
        try
            Run(InstallDir . "\kodex.exe")
        catch Error as err
        {
            MsgBox("Error launching Kodex: " . err.Message)
        }
    }
    
    ExitApp()
}

Button_Cancel(MyGui)
{
    MyGui.Destroy()
    ExitApp()
}
