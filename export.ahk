; Kodex Export Utility - AutoHotkey v2 Migrated Version
; Exports selected hotstrings to a folder

#SingleInstance Force
SetWorkingDir(A_ScriptDir)

ExportUtility()

ExportUtility()
{
    ; Read bank files
    try
        EnterKeys := FileRead(A_WorkingDir . "\bank\enter.csv")
    catch
        EnterKeys := ""
    
    try
        TabKeys := FileRead(A_WorkingDir . "\bank\tab.csv")
    catch
        TabKeys := ""
    
    try
        SpaceKeys := FileRead(A_WorkingDir . "\bank\space.csv")
    catch
        SpaceKeys := ""
    
    ; Build file list
    FileList := ""
    for File in LoopFiles(A_WorkingDir . "\replacements\*.txt")
    {
        FileName := SubStr(File.Name, 1, StrLen(File.Name) - 4)  ; Remove .txt
        FileList .= FileName . "|"
    }
    StringTrimRight(FileList, FileList, 1)
    
    ; Create GUI
    ExportGui := GuiCreate()
    ExportGui.Add("Text", "x15 y20", "Hotstring:")
    ExportGui.Add("ListBox", "0x8 x13 y40 r15 W100 vExportChoice Sort", FileList)
    ExportGui.Add("Button", "w80 Default x420 yp+80 vExportBtn", "&Export")
    ExportGui.ExportBtn.OnEvent("Click", Button_ExportOK)
    ExportGui.Show("W600 H400", "Kodex Export")
    
    Button_ExportOK(GuiObjName, GuiObj)
    {
        ExportGui.Submit()
        ExportChoice := ExportGui.ExportChoice.Value
        ExportGui.Destroy()
        
        ; Create export directory
        ExportDir := A_WorkingDir . "\Kodex Export"
        if (!DirExist(ExportDir))
            DirCreate(ExportDir)
        
        ; Export selected hotstrings
        ExportItems := StrSplit(ExportChoice, "|")
        for Item in ExportItems
        {
            if (Item = "")
                continue
            
            ; Copy replacement file
            FileCopy(A_WorkingDir . "\replacements\" . Item . ".txt", ExportDir . "\" . Item . ".txt", true)
            
            ; Add to appropriate bank file
            if (InStr(EnterKeys, "|" . Item . "|"))
                FileAppend(Item . "`n", ExportDir . "\enter.csv")
            
            if (InStr(TabKeys, "|" . Item . "|"))
                FileAppend(Item . "`n", ExportDir . "\tab.csv")
            
            if (InStr(SpaceKeys, "|" . Item . "|"))
                FileAppend(Item . "`n", ExportDir . "\space.csv")
        }
        
        MsgBox("Export complete. Files saved to: " . ExportDir)
    }
}
