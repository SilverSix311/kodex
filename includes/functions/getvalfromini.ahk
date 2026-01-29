;; Get value from INI, write default if not found (method by Dustin Luck)
GetValFromIni(section, key, default := "")
{
    try
        IniVal := IniRead("kodex.ini", section, key)
    catch
        IniVal := "ERROR"

    if (IniVal = "ERROR")
    {
        IniWrite(default, "kodex.ini", section, key)
        IniVal := default
    }
    return IniVal
}
