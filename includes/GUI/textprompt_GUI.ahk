; Kodex Text Prompt GUI - AutoHotkey v2 Migrated Version

global TextPromptGui, escapePrompt, ReplacementText, promptText

textPrompt(thisText)
{
    global TextPromptGui, escapePrompt, ReplacementText, promptText
    
    if (IsSet(TextPromptGui))
        TextPromptGui.Destroy()
    
    escapePrompt := 0
    promptText := ""
    
    TextPromptGui := GuiCreate("+AlwaysOnTop")
    TextPromptGui.Add("Text", "x5 y5", "Enter the text you want to insert:")
    TextPromptGui.Add("Edit", "x20 y25 r1 w300 vpromptText")
    TextPromptGui.Add("Text", "x5 y50", "Your text will replace the %p variable:")
    TextPromptGui.Add("Text", "w300 Wrap x20 y70", thisText)
    
    TextPromptGui.Add("Button", "w80 x120 Default vSubmitBtn", "&OK")
    TextPromptGui.SubmitBtn.OnEvent("Click", Button_SubmitPrompt)
    TextPromptGui.Add("Button", "w80 xp+90 vCancelBtn", "&Cancel")
    TextPromptGui.CancelBtn.OnEvent("Click", Button_ExitPrompt)
    
    TextPromptGui.OnEvent("Escape", Button_ExitPrompt)
    TextPromptGui.Show("auto", "Enter desired text")
}

Button_SubmitPrompt(GuiObjName, GuiObj)
{
    global TextPromptGui, escapePrompt, ReplacementText, promptText
    
    TextPromptGui.Submit(false)
    promptText := TextPromptGui.promptText.Value
    ReplacementText := StrReplace(ReplacementText, "%p", promptText)
    escapePrompt := 0
    TextPromptGui.Destroy()
}

Button_ExitPrompt(GuiObjName, GuiObj)
{
    global TextPromptGui, escapePrompt
    
    escapePrompt := 1
    if (IsSet(TextPromptGui))
        TextPromptGui.Destroy()
}
