; Kodex - AutoHotkey v2 Migrated Version
; Author:         Klyde Linden
; Script Function:
;	A text replacement/substitution application for Windows.

; --- SCRIPT SETUP AND CONFIGURATION ---
SetWorkingDir(A_ScriptDir)  ; Ensures the script's working directory is where the script file is located.
#SingleInstance Force       ; Replaces the old instance of the script automatically when a new one is run.
StringCaseSense(true)       ; Makes string comparisons case-sensitive by default.
SetKeyDelay(-1)             ; Sets the delay between keystrokes to -1 (no delay), for maximum speed.
SetWinDelay(0)              ; Sets the delay after each windowing command to 0.

; --- GLOBAL VARIABLE DECLARATIONS ---
global Version, EnterCSV, TabCSV, SpaceCSV, NoTrigCSV, AutocorrectCSV, ReplaceWAV, KodexPNG, KodexICO, StyleCSS, Throbber, SpecialKey, EndKeys
global Disable, EnterKeys, TabKeys, SpaceKeys, NoTrigKeys, AutocorrectKeys
global HotStrings, ActiveList, MakeActive, PossibleMatch, PossHexMatch, Match, ReadFrom
global Autocorrect, ExSound, Synergy, Default, MODE, EnterBox, TabBox, SpaceBox, OnStartup
global cancel, ignore, keys, otfhotkey, managehotkey, disablehotkey
global CurrentBundle, editThis, enter, tab, space, notrig, skipfirst
global expanded, chars_saved, thisWindow, MeasurementText, CursorPoint, ClipLength, ReturnTo

; --- INITIALIZATION ---
AssignVars()
ResourcesInit()
ReadINI()
TrayMenu_Init()
BuildActive()

; Read active hotstring lists
EnterKeys := FileRead(EnterCSV)
TabKeys := FileRead(TabCSV)
SpaceKeys := FileRead(SpaceCSV)
NoTrigKeys := FileRead(NoTrigCSV)
AutocorrectKeys := FileRead(AutocorrectCSV)

; --- MAIN INPUT LOOP ---
Starting := 1
while (true)
{
    ; Wait for matching hotstring
    if (Disable = 1)
        continue

    if (Starting != "")
    {
        loop
        {
            if (Disable = 1)
                break

            ; Input command waits for a single character. 'V' makes it visible (not hidden). 'M' ignores modifiers.
            ; 'L1' means the length of the input is 1 character.
            try
            {
                UserInput := Input(, , EndKeys)
            }
            catch Error as err
            {
                if (InStr(err.Message, "Interrupted"))
                    break
                else if (InStr(err.Message, "Timeout"))
                    continue
                else
                    throw
            }

            ; Check if an EndKey was pressed
            if (InStr(UserInput, "`t") || InStr(UserInput, "`n") || InStr(UserInput, " "))
            {
                PossibleMatch := ""
            }
            else
            {
                PossibleMatch := PossibleMatch . UserInput
            }

            ; Check if we have a match in the hotstring list
            if (InStr(HotStrings, "|" . PossibleMatch . "|"))
                break
        }
    }

    ; Convert typed string to hex for matching
    PossHexMatch := Hexify(PossibleMatch)

    ; --- AUTOCORRECT HANDLING ---
    if (Autocorrect = 1)
    {
        if (InStr(AutocorrectKeys, "|" . PossibleMatch . "|"))
        {
            ReadFrom := A_ScriptDir . "\Active\Autocorrect\replacements"
            Match := Hexify(PossibleMatch)

            ; Wait for Shift key to be released
            while (GetKeyState("Shift", "P"))
                Sleep(10)
        }
    }
    ; --- TRIGGERLESS HOTSTRING HANDLING ---
    else if (InStr(NoTrigKeys, PossHexMatch))
    {
        Match := PossHexMatch
        ReadFrom := A_ScriptDir . "\Active\replacements"

        ; Wait for Shift key to be released
        while (GetKeyState("Shift", "P"))
            Sleep(10)
    }
    ; --- TRIGGER-BASED HOTSTRING HANDLING ---
    else
    {
        try
        {
            UserInput := Input(, , EndKeys)
        }
        catch Error as err
        {
            PossibleMatch := ""
            Starting := 1
            continue
        }

        ; Check modifier key states
        AltState := GetKeyState("Alt", "P")
        CtrlState := GetKeyState("Ctrl", "P")
        ShiftState := GetKeyState("Shift", "P")
        LWinState := GetKeyState("LWin", "P")
        RWinState := GetKeyState("RWin", "P")
        WinState := LWinState || RWinState
        Modifier := ""

        if (AltState || CtrlState || WinState || ShiftState)
        {
            if (AltState)
                Modifier := "!"
            if (CtrlState)
                Modifier .= "^"
            if (ShiftState)
                Modifier .= "+"
            if (WinState)
                Modifier .= "#"
        }

        ; Extract trigger from ErrorLevel
        Trigger := ""
        if (InStr(UserInput, "{"))
        {
            Trigger := SubStr(UserInput, 2, StrLen(UserInput) - 2)
        }

        ; Handle Backspace for typo correction
        if (Trigger = "BackSpace")
        {
            Send(Modifier . "{BS}")
            PossibleMatch := SubStr(PossibleMatch, 1, StrLen(PossibleMatch) - 1)
            continue
        }

        ; Check if this hotstring/trigger combination exists
        Bank := Trigger . "Keys"
        BankContent := %Bank%
        PossHexMatch := Hexify(PossibleMatch)

        if (InStr(BankContent, PossHexMatch))
        {
            ReadFrom := A_ScriptDir . "\Active\replacements"
            Match := PossHexMatch
        }
        else
        {
            ; No match found, send keys as typed
            if (AltState && !CtrlState && !ShiftState && !WinState)
            {
                Send("{Alt Down}`{" . Trigger . "`}")
                while (GetKeyState("Alt", "P"))
                    Sleep(10)
                Send("{Alt Up}")
            }
            else if (AltState || CtrlState || WinState || ShiftState)
            {
                Send(Modifier . "`{" . Trigger . "`}")
            }
            else
            {
                Send("`{" . Trigger . "`}")
            }

            PossibleMatch := ""
            Starting := 1
            continue
        }
    }

    ; Execute matched hotstring
    if (Match != "")
    {
        Execute()
        PossibleMatch := ""
        PossHexMatch := ""
        Match := ""
        Starting := 1
        continue
    }
    else
    {
        ; No match, pass through keystrokes
        if (AltState && false)  ; Placeholder for Alt handling
        {
            ; Alt handling code
        }
        else
        {
            PossibleMatch := PossibleMatch . UserInput
            SendRaw(UserInput)
        }
        Starting := ""
        Modifier := ""
    }
}

; --- EXECUTE MATCHED HOTSTRING ---
Execute()
{
    global Match, ReadFrom, PossibleMatch, Autocorrect, ExSound, MODE, ReplaceWAV, expanded, chars_saved
    global ReturnTo, ClipLength, ReplacementText

    WinGetActiveTitle(&thisWindow)
    SendMode("Input")

    if (ExSound = 1)
        SoundPlay(ReplaceWAV)

    ReturnTo := 0
    hexInput := DeHexify(Match)
    BSlength := StrLen(hexInput)
    Send("{BS " . BSlength . "}")

    ReplacementText := FileRead(ReadFrom . "\" . Match . ".txt")
    ClipLength := StrLen(ReplacementText)

    ; --- SCRIPT MODE HANDLING (::scr::) ---
    if (InStr(ReplacementText, "::scr::"))
    {
        ReplacementText := StrReplace(ReplacementText, "`r`n", "`n", "All")
        ReplacementText := StrReplace(ReplacementText, "::scr::", "")

        if (InStr(ReplacementText, "%p"))
        {
            textPrompt(ReplacementText)
            if (escapePrompt = 1)
                return
        }

        SendInput(ReplacementText)
        return
    }

    ; --- STANDARD REPLACEMENT MODE ---
    if (MODE = 0)
        ReplacementText := StrReplace(ReplacementText, "`r`n", "`n", "All")

    ; --- VARIABLE REPLACEMENT ---
    if (InStr(ReplacementText, "%c"))
        ReplacementText := StrReplace(ReplacementText, "%c", A_Clipboard, "All")

    if (InStr(ReplacementText, "%t"))
    {
        CurrTime := FormatTime(, "Time")
        ReplacementText := StrReplace(ReplacementText, "%t", CurrTime, "All")
    }

    if (InStr(ReplacementText, "%ds"))
    {
        SDate := FormatTime(, "ShortDate")
        ReplacementText := StrReplace(ReplacementText, "%ds", SDate, "All")
    }

    if (InStr(ReplacementText, "%dl"))
    {
        LDate := FormatTime(, "LongDate")
        ReplacementText := StrReplace(ReplacementText, "%dl", LDate, "All")
    }

    if (InStr(ReplacementText, "%tl"))
    {
        LTime := FormatTime(, "HH:mm:ss tt")
        ReplacementText := StrReplace(ReplacementText, "%tl", LTime, "All")
    }

    if (InStr(ReplacementText, "%p"))
    {
        textPrompt(ReplacementText)
        if (escapePrompt = 1)
            return
    }

    ; --- CURSOR POSITIONING HANDLING (%|) ---
    if (InStr(ReplacementText, "%|"))
    {
        MeasurementText := ReplacementText
        if (MODE = 0)
            MeasurementText := StrReplace(MeasurementText, "`r`n", "`n", "All")

        CursorPoint := InStr(MeasurementText, "%|") - 1
        ReplacementText := StrReplace(ReplacementText, "%|", "")
        MeasurementText := StrReplace(MeasurementText, "%|", "")
        ClipLength := StrLen(MeasurementText)
        ReturnTo := ClipLength - CursorPoint
    }

    ; --- SEND/PASTE LOGIC ---
    if (MODE = 0)
    {
        if (ReturnTo > 0)
        {
            SendMode("Event")
            WinActivate(thisWindow)
            SendRaw(ReplacementText)
            Send("{Left " . ReturnTo . "}")
            SendMode("Input")
        }
        else
        {
            WinActivate(thisWindow)
            SendInput("{Raw}" . ReplacementText)
        }
    }
    else
    {
        oldClip := ClipboardAll()
        A_Clipboard := ReplacementText
        ClipWait(2)
        WinActivate(thisWindow)
        Send("^v")
        Sleep(200)
        A_Clipboard := oldClip
    }

    ; --- STATISTICS AND CLEANUP ---
    SendMode("Event")
    try
    {
        expanded := IniRead("kodex.ini", "Stats", "Expanded", 0)
        chars_saved := IniRead("kodex.ini", "Stats", "Characters", 0)
        expanded++
        chars_saved += ClipLength
        IniWrite(expanded, "kodex.ini", "Stats", "Expanded")
        IniWrite(chars_saved, "kodex.ini", "Stats", "Characters")
    }
    catch
    {
        ; Silently ignore INI errors
    }
}

; --- INITIALIZATION FUNCTION ---
AssignVars()
{
    global Version, EnterCSV, TabCSV, SpaceCSV, NoTrigCSV, AutocorrectCSV
    global ReplaceWAV, KodexPNG, KodexICO, StyleCSS, Throbber, SpecialKey, EndKeys, Disable

    Version := "0.1"
    EnterCSV := A_ScriptDir . "\Active\bank\enter.csv"
    TabCSV := A_ScriptDir . "\Active\bank\tab.csv"
    SpaceCSV := A_ScriptDir . "\Active\bank\space.csv"
    NoTrigCSV := A_ScriptDir . "\Active\bank\notrig.csv"
    AutocorrectCSV := A_ScriptDir . "\Active\Autocorrect\pipelist.txt"
    ReplaceWAV := A_ScriptDir . "\resources\kodex.wav"
    KodexPNG := A_ScriptDir . "\resources\kodex.png"
    KodexICO := A_ScriptDir . "\resources\kodex.ico"
    StyleCSS := A_ScriptDir . "\resources\kodex.css"
    Throbber := A_ScriptDir . "\resources\throbber.gif"
    SpecialKey := "vkFF"
    EndKeys := "{Enter}{Esc} {Tab}{Right}{Left}{Up}{Down}{Del}{BS}{Home}{End}{PgUp}{PgDn}{" . SpecialKey . "}{F1}{F2}{F3}{F4}{F5}{F6}{F7}{F8}{F9}{F10}{F11}{F12}"
    Disable := 0
}

ResourcesInit()
{
    ; TODO: Implement resource checking
}

; --- READ INI CONFIGURATION ---
ReadINI()
{
    global Version, EnterCSV, TabCSV, SpaceCSV, NoTrigCSV, Disable
    global cancel, ignore, keys, otfhotkey, managehotkey, disablehotkey
    global MODE, EnterBox, TabBox, SpaceBox, ExSound, Synergy, Autocorrect, Default, OnStartup, HotStrings

    IniWrite(Version, "kodex.ini", "Preferences", "Version")
    IniWrite(0, "kodex.ini", "Settings", "Disable")

    cancel := GetValFromIni("Cancel", "Keys", "{Escape}")
    ignore := GetValFromIni("Ignore", "Keys", "{Tab}`,{Enter}`,{Space}")
    IniWrite("{Escape}`,{Tab}`,{Enter}`,{Space}`,{Left}`,{Right}`,{Up}`,{Down}", "kodex.ini", "Autocomplete", "Keys")
    keys := GetValFromIni("Autocomplete", "Keys", "{Escape}`,{Tab}`,{Enter}`,{Space}`,{Left}`,{Right}`,{Esc}`,{Up}`,{Down}")
    otfhotkey := GetValFromIni("Hotkey", "OntheFly", "^+H")
    managehotkey := GetValFromIni("Hotkey", "Management", "^+M")
    disablehotkey := GetValFromIni("Hotkey", "Disable", "")
    MODE := GetValFromIni("Settings", "Mode", 0)
    EnterBox := GetValFromIni("Triggers", "Enter", 0)
    TabBox := GetValFromIni("Triggers", "Tab", 0)
    SpaceBox := GetValFromIni("Triggers", "Space", 0)
    ExSound := GetValFromIni("Preferences", "ExSound", 1)
    Synergy := GetValFromIni("Preferences", "Synergy", 0)
    Autocorrect := GetValFromIni("Preferences", "AutoCorrect", 1)
    Default := GetValFromIni("Bundles", "Default", 1)
    OnStartup := GetValFromIni("Settings", "Startup", 0)

    ; Set up hotkeys
    if (otfhotkey != "")
    {
        HotKey(otfhotkey, Hotkey_NEWKEY)
    }
    if (managehotkey != "")
    {
        HotKey(managehotkey, Hotkey_MANAGE)
    }
    if (disablehotkey != "")
    {
        HotKey(disablehotkey, DISABLE)
    }

    ; Reset buffer on mouse clicks
    HotKey("~LButton", ResetBuffer)
    HotKey("~RButton", ResetBuffer)
    HotKey("~MButton", ResetBuffer)
}

ResetBuffer()
{
    global PossibleMatch
    PossibleMatch := ""
}

TrayMenu_Init()
{
    ; TODO: Implement tray menu
}

; --- INCLUDE FILES ---
#Include includes\GUI\newkey_GUI.ahk
#Include includes\GUI\traymenu_GUI.ahk
#Include includes\GUI\about_GUI.ahk
#Include includes\GUI\help_GUI.ahk
#Include includes\GUI\preferences_GUI.ahk
#Include includes\GUI\management_GUI.ahk
#Include includes\GUI\textprompt_GUI.ahk
#Include includes\GUI\disablechecks.ahk

; Include function libraries
#Include includes\functions\disable.ahk
#Include includes\functions\urls.ahk
#Include includes\functions\getfilelist.ahk
#Include includes\functions\buildactive.ahk
#Include includes\functions\bundles.ahk
#Include includes\functions\getvalfromini.ahk
#Include includes\functions\savehotstring.ahk
#Include includes\functions\addtobank.ahk
#Include includes\functions\delfrombank.ahk
#Include includes\functions\enabletriggers.ahk
#Include includes\functions\resources.ahk
#Include includes\functions\printablelist.ahk
#Include includes\functions\updatecheck.ahk
#Include includes\functions\hexify.ahk
#Include includes\functions\InsSpecKeys.ahk
#Include includes\functions\MonitorWindows.ahk
#Include includes\functions\renameHotstring.ahk
#Include includes\functions\InstallAutocorrect.ahk

; --- HOTKEY WRAPPER FUNCTIONS ---
Hotkey_NEWKEY(HotkeyObj)
{
    ; TODO: Implement on-the-fly hotstring creation dialog
}

Hotkey_MANAGE(HotkeyObj)
{
    ManageGUI()
}

Hotkey_DISABLE(HotkeyObj)
{
    ; TODO: Implement disable toggle
}

ExitApp(0)
 