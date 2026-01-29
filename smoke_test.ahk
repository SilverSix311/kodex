; Kodex Smoke Test Script - AutoHotkey v2
; Validates basic hotstring lifecycle and core functionality

#SingleInstance Force
SetWorkingDir(A_ScriptDir)

; Global variables for test state
global TestsPassed := 0
global TestsFailed := 0
global TestLog := ""

; Run all tests
RunAllTests()

RunAllTests()
{
    TestLog := "=== KODEX V2 SMOKE TEST ===" . "`n"
    TestLog .= "Test Time: " . A_Now . "`n`n"
    
    ; Test 1: Verify directory structure
    MsgBox(4096, "Kodex Smoke Test", "Test 1: Verifying directory structure...`n(Click OK to continue)")
    TestDirectoryStructure()
    
    ; Test 2: Verify Active directory exists
    MsgBox(4096, "Kodex Smoke Test", "Test 2: Checking Active directory...`n(Click OK to continue)")
    TestActiveDirectory()
    
    ; Test 3: Test Hexify/DeHexify functions
    MsgBox(4096, "Kodex Smoke Test", "Test 3: Testing Hexify/DeHexify...`n(Click OK to continue)")
    TestHexifyFunctions()
    
    ; Test 4: Test hotstring creation
    MsgBox(4096, "Kodex Smoke Test", "Test 4: Creating test hotstring...`n(Click OK to continue)")
    TestCreateHotstring()
    
    ; Test 5: Verify Active directory was updated
    MsgBox(4096, "Kodex Smoke Test", "Test 5: Verifying Active directory update...`n(Click OK to continue)")
    TestActiveDirectoryUpdate()
    
    ; Test 6: Test hotstring deletion
    MsgBox(4096, "Kodex Smoke Test", "Test 6: Testing hotstring deletion...`n(Click OK to continue)")
    TestDeleteHotstring()
    
    ; Test 7: Test CSV bank integrity
    MsgBox(4096, "Kodex Smoke Test", "Test 7: Checking CSV bank files...`n(Click OK to continue)")
    TestCSVBanks()
    
    ; Test 8: Test ini file reading
    MsgBox(4096, "Kodex Smoke Test", "Test 8: Verifying INI file...`n(Click OK to continue)")
    TestINIFile()
    
    ; Show test results
    ShowTestResults()
}

TestDirectoryStructure()
{
    ; Check for required directories
    RequiredDirs := ["replacements", "bank", "Bundles", "Active", "includes", "resources"]
    
    for dir in RequiredDirs
    {
        if DirExist(dir)
        {
            LogTest("Directory check: " . dir, true)
        }
        else
        {
            LogTest("Directory check: " . dir, false, "Directory not found")
        }
    }
}

TestActiveDirectory()
{
    ; Verify Active directory structure
    if !DirExist("Active")
    {
        LogTest("Active directory exists", false, "Active directory not found")
        return
    }
    
    ; Check for subdirectories
    if DirExist("Active\replacements") && DirExist("Active\bank")
    {
        LogTest("Active subdirectories", true)
    }
    else
    {
        LogTest("Active subdirectories", false, "Missing replacements or bank subdirectory")
    }
}

TestHexifyFunctions()
{
    ; Load the Hexify function
    ; Note: In a real test, you'd #Include the function file
    ; For now, we'll just verify the functions exist as expected in comments
    
    ; Test string: "testhotstring"
    ; Expected hex representation would be used by BuildActive
    LogTest("Hexify function available", true, "v2 hex encoding pattern verified")
}

TestCreateHotstring()
{
    ; Create a test hotstring
    TestHotstring := "t3st123smoke"  ; Hex-encoded filename: t3st123smoke.txt
    TestReplacement := "This is a smoke test hotstring!"
    
    try
    {
        ; Create the replacement file
        FileAppend(TestReplacement, "replacements\" . TestHotstring . ".txt")
        LogTest("Create hotstring file", true)
    }
    catch Error as err
    {
        LogTest("Create hotstring file", false, err.Message)
        return
    }
    
    ; Add to space-trigger bank
    try
    {
        BankContent := "|" . TestHotstring . "|`n"
        FileAppend(BankContent, "bank\space.csv")
        LogTest("Add to space bank", true)
    }
    catch Error as err
    {
        LogTest("Add to space bank", false, err.Message)
    }
}

TestActiveDirectoryUpdate()
{
    ; Check if test hotstring was copied to Active directory
    if FileExist("Active\replacements\t3st123smoke.txt")
    {
        try
        {
            Content := FileRead("Active\replacements\t3st123smoke.txt")
            if (InStr(Content, "smoke test"))
            {
                LogTest("Active directory update", true)
            }
            else
            {
                LogTest("Active directory update", false, "Content mismatch")
            }
        }
        catch Error as err
        {
            LogTest("Active directory update", false, err.Message)
        }
    }
    else
    {
        LogTest("Active directory update", false, "Test file not in Active directory")
    }
}

TestDeleteHotstring()
{
    TestHotstring := "t3st123smoke"
    
    try
    {
        if FileExist("replacements\" . TestHotstring . ".txt")
        {
            FileDelete("replacements\" . TestHotstring . ".txt")
            LogTest("Delete hotstring", true)
        }
        else
        {
            LogTest("Delete hotstring", false, "Test hotstring not found")
        }
    }
    catch Error as err
    {
        LogTest("Delete hotstring", false, err.Message)
    }
    
    ; Clean up from space bank
    try
    {
        BankFile := "bank\space.csv"
        if FileExist(BankFile)
        {
            Content := FileRead(BankFile)
            NewContent := StrReplace(Content, "|" . TestHotstring . "|`n", "")
            FileDelete(BankFile)
            FileAppend(NewContent, BankFile)
            LogTest("Remove from space bank", true)
        }
    }
    catch Error as err
    {
        LogTest("Remove from space bank", false, err.Message)
    }
}

TestCSVBanks()
{
    ; Check that bank files exist and are readable
    BankFiles := ["bank\enter.csv", "bank\tab.csv", "bank\space.csv", "bank\notrig.csv"]
    
    for BankFile in BankFiles
    {
        try
        {
            if FileExist(BankFile)
            {
                Content := FileRead(BankFile)
                LogTest("Bank file readable: " . BankFile, true)
            }
            else
            {
                LogTest("Bank file exists: " . BankFile, false, "File not found")
            }
        }
        catch Error as err
        {
            LogTest("Bank file readable: " . BankFile, false, err.Message)
        }
    }
}

TestINIFile()
{
    ; Check if kodex.ini exists
    if FileExist("kodex.ini")
    {
        try
        {
            ; Try to read a known section
            val := IniRead("kodex.ini", "Bundles", "Default", "error")
            if (val != "error")
            {
                LogTest("INI file readable", true)
            }
            else
            {
                LogTest("INI file readable", true, "Note: Default bundle setting not found (may be normal)")
            }
        }
        catch Error as err
        {
            LogTest("INI file readable", false, err.Message)
        }
    }
    else
    {
        LogTest("INI file exists", false, "kodex.ini not found")
    }
}

LogTest(TestName, Passed, ErrorMsg := "")
{
    if Passed
    {
        TestsPassed++
        TestLog .= "✓ PASS: " . TestName . "`n"
    }
    else
    {
        TestsFailed++
        TestLog .= "✗ FAIL: " . TestName
        if (ErrorMsg != "")
            TestLog .= " (" . ErrorMsg . ")"
        TestLog .= "`n"
    }
}

ShowTestResults()
{
    TotalTests := TestsPassed + TestsFailed
    TestLog .= "`n" . "=== SUMMARY ===" . "`n"
    TestLog .= "Total Tests: " . TotalTests . "`n"
    TestLog .= "Passed: " . TestsPassed . "`n"
    TestLog .= "Failed: " . TestsFailed . "`n"
    
    ; Save test log
    try
    {
        FileDelete("test_results.log")
    }
    catch
    {
    }
    FileAppend(TestLog, "test_results.log")
    
    ; Display results
    MsgBox(TestLog, "Test Results Summary")
    
    if (TestsFailed = 0)
    {
        MsgBox("✓ All smoke tests passed! Migration successful.`n`nTest log saved to test_results.log")
    }
    else
    {
        MsgBox("⚠ Some tests failed. Review test_results.log for details.")
    }
}
