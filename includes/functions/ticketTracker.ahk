; Kodex Freshdesk Ticket Time Tracker
; AutoHotkey v2
; 
; Features:
; - Detects Freshdesk ticket URLs in clipboard/selected text
; - Logs time entries to dated CSV files (timeTracker/[USERNAME].[MMDD].csv)
; - Displays transparent overlay timer while tracking
; - Toggle start/stop with configurable hotkey

#SingleInstance Force
SetWorkingDir(A_ScriptDir)

; Configuration
global TicketTrackerEnabled := false
global TicketTimerOverlay := 0
global CurrentTicketURL := ""
global TicketStartTime := ""
global TicketHotkey := "^+t"  ; Ctrl+Shift+T

; Hotkey for ticket tracking (Ctrl+Shift+T)
Hotkey(TicketHotkey, TicketTrackerToggle)

TicketTrackerToggle(HotkeyObj) {
    if (TicketTrackerEnabled = 1) {
        StopTicketTracking()
    } else {
        StartTicketTracking()
    }
}

StartTicketTracking() {
    ; Get text from clipboard
    clipped := A_Clipboard
    
    ; Check for Freshdesk ticket URL
    if !RegExMatch(clipped, "https://lindenlab\.freshdesk\.com/a/tickets/(\d+)", &match) {
        MsgBox("Error", "Ticket URL Not Found", "Please copy a Freshdesk ticket URL or select one in your clipboard.")
        return
    }
    
    TicketNumber := match[1]
    CurrentTicketURL := clipped
    TicketTimerOverlay := TicketNumber
    TicketStartTime := A_Now
    TicketTrackerEnabled := 1
    
    ; Log start time
    LogTicketEntry(TicketNumber, "Started", TicketStartTime)
    
    ; Show overlay timer
    ShowTicketTimerOverlay(TicketNumber, TicketStartTime)
}

StopTicketTracking() {
    if (CurrentTicketURL = "") {
        MsgBox("Error", "No Active Session", "No ticket tracking session is currently active.")
        return
    }
    
    match := RegExMatch(CurrentTicketURL, "https://lindenlab\.freshdesk\.com/a/tickets/(\d+)", &m)
    TicketNumber := m[1]
    TicketEndTime := A_Now
    
    ; Calculate duration
    StartTime := TicketStartTime
    EndTime := TicketEndTime
    
    ; Parse timestamps (format: YYYYMMDDHHMMSS)
    StartUnix := DateTimeToUnix(StartTime)
    EndUnix := DateTimeToUnix(EndTime)
    DurationSeconds := EndUnix - StartUnix
    DurationHours := Format("{:.2f}", DurationSeconds / 3600)
    
    ; Log end time with duration
    LogTicketEntry(TicketNumber, "Finished", TicketEndTime, DurationHours)
    
    ; Clean up overlay
    if (TicketTimerOverlay != 0) {
        try {
            TimerGuiDestroy()
        }
    }
    
    ; Reset tracking state
    TicketTrackerEnabled := 0
    TicketTimerOverlay := 0
    CurrentTicketURL := ""
    TicketStartTime := ""
    
    MsgBox("Success", "Session Logged", "Tracked " . DurationHours . " hours for ticket #" . TicketNumber)
}

LogTicketEntry(TicketNumber, Status, Timestamp, Duration := "") {
    ; Create CSV filename based on date: USERNAME.MMDD.csv
    Username := EnvGet("USERNAME")
    
    ; Parse timestamp (YYYYMMDDHHMMSS format from A_Now)
    Year := SubStr(Timestamp, 1, 4)
    Month := SubStr(Timestamp, 5, 2)
    Day := SubStr(Timestamp, 7, 2)
    Hour := SubStr(Timestamp, 9, 2)
    Minute := SubStr(Timestamp, 11, 2)
    Second := SubStr(Timestamp, 13, 2)
    
    ; Format for CSV
    DateStamp := Year . "-" . Month . "-" . Day
    TimeStamp := Hour . ":" . Minute . ":" . Second
    
    ; Create directory if it doesn't exist
    TrackerDir := A_ScriptDir . "\timeTracker"
    if !DirExist(TrackerDir) {
        try {
            DirCreate(TrackerDir)
        } catch Error as err {
            MsgBox("Error creating tracker directory: " . err.Message)
            return
        }
    }
    
    ; CSV filename: USERNAME.MMDD.csv
    CSVFilename := Username . "." . Month . Day . ".csv"
    CSVPath := TrackerDir . "\" . CSVFilename
    
    ; CSV line format: ticket_url,status,timestamp,duration_hours
    if (Status = "Started") {
        CSVLine := TicketNumber . ",Started," . DateStamp . " " . TimeStamp . ",`n"
    } else if (Status = "Finished") {
        CSVLine := TicketNumber . ",Finished," . DateStamp . " " . TimeStamp . "," . Duration . "`n"
    }
    
    ; Append to CSV
    try {
        FileAppend(CSVLine, CSVPath)
    } catch Error as err {
        MsgBox("Error logging ticket entry: " . err.Message)
    }
}

ShowTicketTimerOverlay(TicketNumber, StartTime) {
    global TimerGui, TimerStartTime
    
    TimerStartTime := StartTime
    
    ; Create transparent overlay GUI
    TimerGui := GuiCreate("+AlwaysOnTop +ToolWindow -Caption", "Kodex Ticket Timer")
    TimerGui.BackColor := "0x1e1e1e"  ; Dark background
    
    ; Calculate position: 25% from left, centered vertically
    ScreenWidth := A_ScreenWidth
    ScreenHeight := A_ScreenHeight
    OverlayWidth := ScreenWidth * 0.25
    OverlayHeight := 100
    XPos := 0
    YPos := (ScreenHeight - OverlayHeight) / 2
    
    TimerGui.Add("Text", "cWhite Center h100 w" . OverlayWidth, "Ticket #" . TicketNumber)
    TimerGui.Add("Text", "cGreen Center h50 w" . OverlayWidth . " vTimerDisplay", "00:00:00")
    
    TimerGui.Show("x" . XPos . " y" . YPos . " w" . OverlayWidth . " h" . OverlayHeight)
    
    ; Start timer update
    SetTimer(UpdateTicketTimer, 1000)
}

UpdateTicketTimer() {
    global TimerGui, TimerStartTime
    
    if (TicketTrackerEnabled != 1) {
        return
    }
    
    ; Calculate elapsed time
    CurrentTime := A_Now
    StartUnix := DateTimeToUnix(TimerStartTime)
    CurrentUnix := DateTimeToUnix(CurrentTime)
    ElapsedSeconds := CurrentUnix - StartUnix
    
    ; Format as HH:MM:SS
    Hours := ElapsedSeconds // 3600
    Minutes := (ElapsedSeconds mod 3600) // 60
    Seconds := ElapsedSeconds mod 60
    
    TimeDisplay := Format("{:02d}:{:02d}:{:02d}", Hours, Minutes, Seconds)
    
    try {
        TimerGui["TimerDisplay"].Value := TimeDisplay
    } catch {
        SetTimer(, 0)  ; Stop timer if GUI doesn't exist
    }
}

TimerGuiDestroy() {
    global TimerGui
    try {
        TimerGui.Destroy()
        SetTimer(UpdateTicketTimer, 0)
    }
}

DateTimeToUnix(Timestamp) {
    ; Convert AHK timestamp (YYYYMMDDHHMMSS) to Unix time
    Year := SubStr(Timestamp, 1, 4)
    Month := SubStr(Timestamp, 5, 2)
    Day := SubStr(Timestamp, 7, 2)
    Hour := SubStr(Timestamp, 9, 2)
    Minute := SubStr(Timestamp, 11, 2)
    Second := SubStr(Timestamp, 13, 2)
    
    ; Simple conversion (note: doesn't account for timezone)
    ; This is a simplified version - for production, use external time library
    DaysPerMonth := [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    ; Account for leap years
    if ((Year mod 4 = 0 and Year mod 100 != 0) or Year mod 400 = 0) {
        DaysPerMonth[2] := 29
    }
    
    ; Calculate total days since epoch (1970-01-01)
    TotalDays := 0
    
    ; Add days for all years since 1970
    Loop Year - 1970 {
        if ((Year - Loop.Index) mod 4 = 0 and (Year - Loop.Index) mod 100 != 0) or (Year - Loop.Index) mod 400 = 0 {
            TotalDays += 366
        } else {
            TotalDays += 365
        }
    }
    
    ; Add days for months in current year
    Loop Month - 1 {
        TotalDays += DaysPerMonth[A_Index]
    }
    
    ; Add remaining days
    TotalDays += Day - 1
    
    ; Convert to seconds
    return TotalDays * 86400 + Hour * 3600 + Minute * 60 + Second
}

; Optional: Add menu for easy access
CreateTrackerMenu() {
    MyTrayMenu := A_TrayMenu
    MyTrayMenu.Add("Start/Stop Ticket Tracker (" . TicketHotkey . ")", TicketTrackerToggle)
    MyTrayMenu.Add()
    MyTrayMenu.Add("Open Tracker Folder", OpenTrackerFolder)
}

OpenTrackerFolder() {
    Run(A_ScriptDir . "\timeTracker")
}

; Initialize menu
CreateTrackerMenu()

#Hotstring EndMark /
::tickettest/::Kodex Ticket Tracker Loaded
