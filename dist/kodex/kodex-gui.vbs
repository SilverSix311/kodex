Set WshShell = CreateObject("WScript.Shell")
kodexDir = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
WshShell.Run Chr(34) & kodexDir & "python\pythonw.exe" & Chr(34) & _
    " -m kodex_py.cli --db " & Chr(34) & kodexDir & "data\kodex.db" & Chr(34) & " run", 0, False
