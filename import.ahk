; Kodex Import Utility - AutoHotkey v2 Migrated Version
; Imports hotstrings from a folder into Kodex

#SingleInstance Force
SetWorkingDir(A_ScriptDir)

ImportUtility()

ImportUtility()
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
    
    ; Select import folder
    ImportFrom := DirSelect(, , "Select the Kodex import folder")
    if (ImportFrom = "")
        return
    
    ; Create import directory
    ImportDir := A_WorkingDir . "\Import"
    if (!DirExist(ImportDir))
        DirCreate(ImportDir)
    
    ; Copy files from import folder
    for File in LoopFiles(ImportFrom . "\*.txt")
    {
        FileCopy(File.FullPath, ImportDir . "\" . File.Name, true)
    }
    
    ; Process bank files
    try
        ImportEnter := FileRead(ImportFrom . "\enter.csv")
    catch
        ImportEnter := ""
    
    try
        ImportTab := FileRead(ImportFrom . "\tab.csv")
    catch
        ImportTab := ""
    
    try
        ImportSpace := FileRead(ImportFrom . "\space.csv")
    catch
        ImportSpace := ""
    
    ; Merge bank files - only add new entries
    for Item in StrSplit(ImportEnter, "|")
    {
        if (Item != "" && !InStr(EnterKeys, "|" . Item . "|"))
            FileAppend(Item . "`n", ImportDir . "\enter.csv")
    }
    
    for Item in StrSplit(ImportTab, "|")
    {
        if (Item != "" && !InStr(TabKeys, "|" . Item . "|"))
            FileAppend(Item . "`n", ImportDir . "\tab.csv")
    }
    
    for Item in StrSplit(ImportSpace, "|")
    {
        if (Item != "" && !InStr(SpaceKeys, "|" . Item . "|"))
            FileAppend(Item . "`n", ImportDir . "\space.csv")
    }
    
    MsgBox("Import complete. Files saved to: " . ImportDir)
}
