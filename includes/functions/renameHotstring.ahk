RenameHotstring()
{
    global CurrentBundle, editThis, enter, tab, space, notrig
    local ActiveChoice, NewName, Text, IsScript, AddToDir, EnterCbox, TabCbox, SpaceCbox, NoTrigCbox

    ; TODO: GUI migration pending - this needs GuiObj calls and GuiSubmit
    ; Gui,9: Submit
    ; Gui,9: Destroy

    EnterCbox := InStr(enter, ActiveChoice) ? true : false
    TabCbox := InStr(tab, ActiveChoice) ? true : false
    SpaceCbox := InStr(space, ActiveChoice) ? true : false
    NoTrigCbox := InStr(notrig, ActiveChoice) ? true : false

    if (CurrentBundle != "" && CurrentBundle != "Default")
        AddToDir := "Bundles\" . CurrentBundle . "\"
    else
        AddToDir := ""

    if (NewName = editThis)
        return
    else if (SaveHotstring(NewName, Text, IsScript, AddToDir, SpaceCbox, TabCbox, EnterCbox, NoTrigCbox))
    {
        DeleteHotstring(editThis, CurrentBundle)
        MakeActive := NewName
        ListBundle()
    }
    return
}

RenameHotstring_GuiEscape(GuiObj)
{
    ; TODO: GUI migration pending
    ; Gui,9: Destroy
    return
}