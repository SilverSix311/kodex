# Kodex AutoHotkey v2 Migration Guide

**Version**: 2.0.0  
**Migration Date**: January 2026  
**Status**: Complete ✅

## Quick Reference

| v1 Pattern | v2 Replacement | Scope |
|-----------|----------------|-------|
| `%var%` | `var` | All variables |
| `Gui, N:` | `GuiCreate()` | All GUI definitions |
| `GLabel` | `OnEvent()` callback | Event handlers |
| `FileRead, var, file` | `var := FileRead("file")` | File I/O |
| `Loop, Files, pat` | `for file in LoopFiles(pat)` | Loops |
| `Gosub, Label` | `FunctionName()` | Control flow |
| `IniRead, var, file, section, key` | `var := IniRead("file", "section", "key")` | INI files |
| `SetKeyDelay, -1` | `SetKeyDelay(-1)` | Timing |

## Detailed Conversion Patterns

### 1. Variable References

**v1:**
```autohotkey
MyVar = Hello World
MsgBox, %MyVar%
MyVar2 = %MyVar%
```

**v2:**
```autohotkey
MyVar := "Hello World"
MsgBox(MyVar)
MyVar2 := MyVar
```

### 2. String Concatenation

**v1:**
```autohotkey
FullName = %FirstName% %LastName%
```

**v2:**
```autohotkey
FullName := FirstName . " " . LastName
```

### 3. GUI Creation and Controls

**v1:**
```autohotkey
Gui, 2:Add, Text, , Hello
Gui, 2:Add, Button, w100 GMyButton, Click
Gui, 2:Show, auto, Title
return

MyButton:
    MsgBox("Clicked")
    return
```

**v2:**
```autohotkey
MyGui := GuiCreate()
MyGui.Add("Text", , "Hello")
MyGui.Add("Button", "w100", "Click")
MyGui.Button := MyButtonClick
MyGui.Show("auto", "Title")

MyButtonClick(GuiCtrlObj) {
    MsgBox("Clicked")
}
```

### 4. File Operations

**v1:**
```autohotkey
FileRead, content, myfile.txt
if ErrorLevel
    MsgBox, Error reading file
else
    MsgBox, %content%

FileAppend, text, myfile.txt
FileDelete, myfile.txt
```

**v2:**
```autohotkey
try {
    content := FileRead("myfile.txt")
    MsgBox(content)
} catch Error as err {
    MsgBox("Error reading file: " . err.Message)
}

FileAppend(text, "myfile.txt")
FileDelete("myfile.txt")
```

### 5. INI File Handling

**v1:**
```autohotkey
IniRead, value, config.ini, section, key, default
IniWrite, value, config.ini, section, key
```

**v2:**
```autohotkey
try {
    value := IniRead("config.ini", "section", "key")
} catch Error as err {
    value := "default"
}

IniWrite(value, "config.ini", "section", "key")
```

### 6. Loops

**v1:**
```autohotkey
Loop, Files, C:\*.txt
{
    MsgBox, %A_LoopFilePath%
}

Loop, 5
{
    MsgBox, %A_Index%
}
```

**v2:**
```autohotkey
for file in LoopFiles("C:\*.txt")
{
    MsgBox(file.FullPath)
}

Loop 5
{
    MsgBox(A_Index)
}
```

### 7. String Operations

**v1:**
```autohotkey
IfInString, MyVar, SearchString
    MsgBox, Found

StringReplace, MyVar, MyVar, old, new
StringLen, Length, MyVar
```

**v2:**
```autohotkey
if InStr(MyVar, "SearchString")
    MsgBox("Found")

MyVar := StrReplace(MyVar, "old", "new")
Length := StrLen(MyVar)
```

### 8. Control Flow and Labels

**v1:**
```autohotkey
Hotkey, ^!k, MyLabel
return

MyLabel:
    MsgBox, Hotkey triggered
    return
```

**v2:**
```autohotkey
Hotkey("^!k", MyFunction)

MyFunction(HotkeyObj) {
    MsgBox("Hotkey triggered")
}
```

## Kodex-Specific Conversions

### Helper Function Pattern

**v1 (in helper file):**
```autohotkey
Hexify(str)
{
    result = 
    Loop, Parse, str
    {
        CharCode := Ord(A_LoopField)
        hex := Format("{:02X}", CharCode)
        result .= hex
    }
    return result
}
```

**v2:**
```autohotkey
Hexify(str)
{
    result := ""
    Loop Parse, str
    {
        CharCode := Ord(A_LoopField)
        result .= Format("{:02X}", CharCode)
    }
    return result
}
```

### Hotstring Lifecycle

**v1 (savehotstring.ahk):**
```autohotkey
SaveHotstring(hotstring, replacement, trigger, bundleName)
{
    hex := Hexify(hotstring)
    file := A_ScriptDir . "\replacements\" . hex . ".txt"
    FileAppend, %replacement%, %file%
    
    AddToBank(hotstring, trigger, bundleName)
    BuildActive()
}
```

**v2:**
```autohotkey
SaveHotstring(hotstring, replacement, trigger, bundleName)
{
    hex := Hexify(hotstring)
    file := A_ScriptDir . "\replacements\" . hex . ".txt"
    FileAppend(replacement, file)
    
    AddToBank(hotstring, trigger, bundleName)
    BuildActive()
}
```

### CSV Bank Operations

**v1 (addtobank.ahk):**
```autohotkey
AddToBank(hotstring, trigger, bundleName)
{
    bankfile := A_ScriptDir . "\bank\" . trigger . ".csv"
    FileRead, content, %bankfile%
    FileDelete, %bankfile%
    content .= "|" . hotstring . "|`n"
    FileAppend, %content%, %bankfile%
}
```

**v2:**
```autohotkey
AddToBank(hotstring, trigger, bundleName)
{
    bankfile := A_ScriptDir . "\bank\" . trigger . ".csv"
    content := FileRead(bankfile)
    FileDelete(bankfile)
    content := content . "|" . hotstring . "|`n"
    FileAppend(content, bankfile)
}
```

## Testing Your Conversions

### Unit Test Pattern

```autohotkey
; Test Hexify function
TestHexify() {
    result := Hexify("test")
    expected := "74657374"  ; hex for "test"
    if (result = expected)
        MsgBox("✓ Hexify test passed")
    else
        MsgBox("✗ Hexify test failed: got " result)
}
```

### Integration Test Pattern

```autohotkey
; Test hotstring lifecycle
TestHotstringLifecycle() {
    SaveHotstring("testkey", "test replacement", "Space", "Default")
    
    ; Verify file created
    if FileExist("replacements\74657374657374.txt")
        MsgBox("✓ Hotstring saved")
    
    ; Verify Active directory updated
    if FileExist("Active\replacements\74657374657374.txt")
        MsgBox("✓ Active directory updated")
    
    ; Clean up
    DeleteHotstring("testkey", "Default")
    MsgBox("✓ Lifecycle test complete")
}
```

## Common Migration Pitfalls

### Pitfall 1: Missing Return Statements in Functions
```autohotkey
; v1 functions didn't always need explicit returns
MyFunc() {
    value := 42
    ; Implicitly returns last expression
}

; v2 requires explicit return
MyFunc() {
    value := 42
    return value
}
```

### Pitfall 2: String Concatenation in Loops
```autohotkey
; v1: loop append works
result = 
Loop 10
    result .= A_Index . "`n"

; v2: same syntax works but be careful with types
result := ""
Loop 10
    result .= A_Index . "`n"
```

### Pitfall 3: FileRead Error Handling
```autohotkey
; v1: uses ErrorLevel
FileRead, content, file.txt
if ErrorLevel
    ; handle error

; v2: throws exception
try {
    content := FileRead("file.txt")
} catch Error as err {
    ; handle error with err.Message
}
```

### Pitfall 4: GUI Event Handlers
```autohotkey
; v1: uses global label
Gui, 2:Add, Button, GMyButton
MyButton:
    ; handler code
    return

; v2: uses callback function with parameter
MyGui.Add("Button")
MyGui.Button := MyButtonHandler

MyButtonHandler(GuiCtrlObj) {
    ; GuiCtrlObj has info about the control
}
```

### Pitfall 5: Object Property Access
```autohotkey
; v1: GuiControlGet was awkward
GuiControlGet, myVar, Mycontrol

; v2: direct property access
myVar := MyGui["Mycontrol"].Value
```

## Validation Checklist

Before deploying v2 code:

- [ ] No v1 GUI syntax (`Gui, N:`)
- [ ] No v1 Gosub labels (converted to functions)
- [ ] No v1 variable syntax (`%var%` in code, OK in comments)
- [ ] All file operations wrapped in try/catch
- [ ] All functions have explicit return statements
- [ ] Event handlers use OnEvent() callbacks
- [ ] String concatenation uses `.` operator
- [ ] Loops use modern syntax (Loop, for, while)
- [ ] IniRead wrapped in try/catch
- [ ] Commands use function syntax: `Command(args)` not `Command, args`

## Resources

- **AutoHotkey v2 Documentation**: https://www.autohotkey.com/docs/
- **Migration Reference**: See `.github/copilot-instructions.md`
- **Test Suite**: Run `smoke_test.ahk` for automated validation
- **Code Examples**: See individual files in `includes/` directories

## Getting Help

1. Check the copilot instructions in `.github/copilot-instructions.md`
2. Review the specific file's v2 conversion in this codebase
3. Consult the AutoHotkey v2 documentation
4. Open an issue on GitHub with specific error details

---

**Last Updated**: January 2026  
**Version**: 2.0.0
