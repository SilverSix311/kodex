; Kodex About GUI - AutoHotkey v2 Migrated Version

global AboutGui, KodexPNG, Version

AboutGUI()
{
    global AboutGui, KodexPNG, Version
    
    if (IsSet(AboutGui))
        AboutGui.Destroy()
    
    AboutGui := GuiCreate()
    AboutGui.BackColor := "F8FAF0"
    AboutGui.OnEvent("Escape", AboutGUI_Close)
    AboutGui.OnEvent("Close", AboutGUI_Close)
    
    AboutGui.Add("Picture", "x200 y0", KodexPNG)
    AboutGui.Add("Text", "x10 y35 s36", "Kodex")
    AboutGui.Add("Text", "x171 y77 s8", Version)
    AboutGui.Add("Text", "x10 y110 w300 center", "Kodex is a text replacement utility designed to save you countless keystrokes on repetitive text entry by replacing user-defined abbreviations (or hotstrings) with your frequently-used text snippets.`n`nKodex is written by Adam Pash and distributed by Lifehacker under the GNU Public License. For details on how to use Kodex, check out the")
    AboutGui.Add("Text", "x110 y230 cBlue", "Kodex homepage")
    
    AboutGui.Show("auto", "About Kodex")
}

AboutGUI_Close(GuiObjName, GuiObj)
{
    global AboutGui
    if (IsSet(AboutGui))
        AboutGui.Destroy()
}
