; Kodex Help GUI - AutoHotkey v2 Migrated Version

global HelpGui, KodexPNG

HelpGUI()
{
    global HelpGui, KodexPNG
    
    if (IsSet(HelpGui))
        HelpGui.Destroy()
    
    HelpGui := GuiCreate()
    HelpGui.BackColor := "F8FAF0"
    HelpGui.OnEvent("Escape", HelpGUI_Close)
    HelpGui.OnEvent("Close", HelpGUI_Close)
    
    HelpGui.Add("Picture", "x200 y5", KodexPNG)
    HelpGui.Add("Text", "x20 y40 s36", "Kodex")
    HelpGui.Add("Text", "x10 y100 w300", "For help by topic, click on one of the following:")
    
    HelpGui.Add("Text", "x30 y120 cBlue", "Basic Use:")
    HelpGui.Add("Text", "x50 y140 w280", "Covers how to create basic text replacement hotstrings.")
    
    HelpGui.Add("Text", "x30 y180 cBlue", "Sending advanced keystrokes:")
    HelpGui.Add("Text", "x50 y200 w280", "Kodex is capable of sending advanced keystrokes, like keyboard combinations. This section lists all of the special characters used in script creation, and offers a few examples of how you might use scripts.")
    
    HelpGui.Add("Text", "x19 y285 w300 center", "All of Kodex's documentation can be found online at the")
    HelpGui.Add("Text", "x125 y305 cBlue", "Kodex homepage")
    
    HelpGui.Show("auto", "Kodex Help")
}

HelpGUI_Close(GuiObjName, GuiObj)
{
    global HelpGui
    if (IsSet(HelpGui))
        HelpGui.Destroy()
}
