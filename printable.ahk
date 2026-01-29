; Kodex Printable Cheatsheet Generator - AutoHotkey v2 Migrated Version
; Generates an HTML file listing all hotstrings and their replacements

#SingleInstance Force
SetWorkingDir(A_ScriptDir)

PrintableList()

PrintableList()
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
    
    ; Delete old file
    try
        FileDelete(A_WorkingDir . "\resources\Kodex Replacement Guide.html")
    catch
    {
        ; File might not exist, that's OK
    }
    
    ; Build HTML
    HtmlContent := "<html><head><title>Kodex Hotstrings and Replacement Text Cheatsheet</title><style>
    body { font-family: Arial, sans-serif; }
    table { border-collapse: collapse; margin: 20px; }
    th, td { border: 1px solid #333; padding: 8px; text-align: left; }
    th { background-color: #4CAF50; color: white; }
    tr:nth-child(even) { background-color: #f2f2f2; }
    </style></head><body>
    <h2>Kodex Hotstrings and Replacement Text Cheatsheet</h2>
    <table>
    <tr><th>Hotstring</th><th>Replacement Text</th><th>Trigger(s)</th></tr>"
    
    ; Loop through replacements
    for File in LoopFiles(A_WorkingDir . "\replacements\*.txt")
    {
        hs := SubStr(File.Name, 1, StrLen(File.Name) - 4)  ; Remove .txt
        
        try
            rp := FileRead(File.FullPath)
        catch
            rp := ""
        
        ; Determine triggers
        trig := ""
        if (InStr(EnterKeys, "|" . hs . "|"))
            trig .= " Enter"
        if (InStr(TabKeys, "|" . hs . "|"))
            trig .= " Tab"
        if (InStr(SpaceKeys, "|" . hs . "|"))
            trig .= " Space"
        
        if (trig = "")
            trig := "Instant"
        else
            trig := SubStr(trig, 2)  ; Remove leading space
        
        ; HTML escape special characters
        rp := StrReplace(rp, "<", "&lt;")
        rp := StrReplace(rp, ">", "&gt;")
        rp := StrReplace(rp, "&", "&amp;")
        
        ; Add table row
        HtmlContent .= "<tr><td>" . hs . "</td><td>" . rp . "</td><td>" . trig . "</td></tr>"
    }
    
    HtmlContent .= "</table></body></html>"
    
    ; Write HTML file
    try
        FileAppend(HtmlContent, A_WorkingDir . "\resources\Kodex Replacement Guide.html")
    catch Error as err
    {
        MsgBox("Error creating file: " . err.Message)
        return
    }
    
    ; Open in default browser
    Run(A_WorkingDir . "\resources\Kodex Replacement Guide.html")
    MsgBox("Printable cheatsheet created and opened in your browser.")
}
