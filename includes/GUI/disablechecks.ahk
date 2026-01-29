; Kodex Disable Checks Helper - AutoHotkey v2 Migrated Version
; This ensures that only one trigger type is selected at a time
; (triggerless/instant mode cannot be combined with other trigger types)

; NOTE: This functionality is now handled by individual checkbox click handlers
; in each GUI file that uses the CheckBox_DisableChecks callback function.
; The pattern is:
;     CheckBox.OnEvent("Click", CheckBox_DisableChecks)
; 
; The CheckBox_DisableChecks function should be implemented in the GUI that uses it.
; Example:
;     CheckBox_DisableChecks(GuiObjName, GuiObj)
;     {
;         global MyGui
;         CheckedCbox := GuiObj.Name
;         if (CheckedCbox = "NoTrigCbox")
;         {
;             MyGui.EnterCbox.Value := 0
;             MyGui.TabCbox.Value := 0
;             MyGui.SpaceCbox.Value := 0
;         }
;         else
;         {
;             MyGui.NoTrigCbox.Value := 0
;         }
;     }
