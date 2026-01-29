GetFileList()
{
	FileList := ""
	first := true
	for File in LoopFiles(A_ScriptDir . "\replacements\*.txt")
	{
		thisFile := DeHexify(StrReplace(File.Name, ".txt", ""))
		if (first)
		{
			FileList := "|" . thisFile . "|"
			first := false
		}
		else
			FileList .= thisFile . "|"
	}
	CurrentBundle := "Default"
	FileList := StrReplace(FileList, ".txt", "")
	return FileList
}