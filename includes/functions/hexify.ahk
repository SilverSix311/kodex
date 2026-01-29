; AutoHotkey v2-compatible Hexify / DeHexify
Hexify(str) {
    hex := ""
    len := StrLen(str)
    Loop len
    {
        ch := SubStr(str, A_Index, 1)
        hexPart := Format("{:02X}", Asc(ch))
        hex .= hexPart
    }
    return hex
}

DeHexify(hexStr) {
    result := ""
    len := StrLen(hexStr)
    i := 1
    while (i <= len)
    {
        part := SubStr(hexStr, i, 2)
        num := ("0x" part)
        result .= Chr(num)
        i += 2
    }
    return result
}
