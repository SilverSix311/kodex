BuildActive:
activeBundles =
Loop,bundles\*,2
{
	IniRead,activeCheck,kodex.ini,Bundles,%A_LoopFileName%
	if activeCheck = 1
		activeBundles = %activeBundles%%A_LoopFileName%,
}
IniRead,activeCheck,kodex.ini,Bundles,Default
if activeCheck = 1
	activeBundles = %activeBundles%Default
if skipfirst <>
{
	BuildActive()
	{
		activeBundles := ""

		; Collect enabled bundles
		for File in LoopFiles("bundles\*")
		{
			activeCheck := IniRead("kodex.ini", "Bundles", File.Name, "")
			if (activeCheck = 1)
				activeBundles .= File.Name ","
		}

		activeCheck := IniRead("kodex.ini", "Bundles", "Default", "")
		if (activeCheck = 1)
			activeBundles .= "Default"

		if (skipfirst != "")
		{
			FileDelete("Active\replacements\*")
			FileDelete("Active\bank\*")

			fields := StrSplit(activeBundles, ",")
			for index, field in fields
			{
				if (field = "")
					continue

				if (field = "Default")
				{
					FileCopy("replacements\*.txt", "Active\replacements")
					tab := FileRead("bank\tab.csv")
					FileAppend(tab, "Active\bank\tab.csv")
					space := FileRead("bank\space.csv")
					FileAppend(space, "Active\bank\space.csv")
					enter := FileRead("bank\enter.csv")
					FileAppend(enter, "Active\bank\enter.csv")
					notrig := FileRead("bank\notrig.csv")
					FileAppend(notrig, "Active\bank\notrig.csv")
				}
				else
				{
					FileCopy("Bundles\" . field . "\replacements\*.txt", "Active\replacements")
					tab := FileRead("Bundles\" . field . "\bank\tab.csv")
					FileAppend(tab, "Active\bank\tab.csv")
					space := FileRead("Bundles\" . field . "\bank\space.csv")
					FileAppend(space, "Active\bank\space.csv")
					enter := FileRead("Bundles\" . field . "\bank\enter.csv")
					FileAppend(enter, "Active\bank\enter.csv")
					notrig := FileRead("Bundles\" . field . "\bank\notrig.csv")
					FileAppend(notrig, "Active\bank\notrig.csv")
				}
			}
		}
		skipfirst := 1

		EnterKeys := FileRead(A_WorkingDir . "\Active\bank\enter.csv")
		TabKeys := FileRead(A_WorkingDir . "\Active\bank\tab.csv")
		SpaceKeys := FileRead(A_WorkingDir . "\Active\bank\space.csv")
		NoTrigKeys := FileRead(A_WorkingDir . "\Active\bank\notrig.csv")

		ActiveList := ""
		HotStrings := "|"
		for File in LoopFiles("Active\replacements\*.txt")
		{
			ActiveList .= File.Name . "|"
			nameNoExt := StrReplace(File.Name, ".txt", "")
			This_HotString := DeHexify(nameNoExt)
			HotStrings .= This_HotString . "|"
		}

		if (Autocorrect = 1)
		{
			AutocorrectHotstrings := FileRead(A_WorkingDir . "\Active\Autocorrect\pipelist.txt")
			HotStrings .= AutocorrectHotstrings
		}

		ActiveList := StrReplace(ActiveList, ".txt", "")
		return
	}

	; Helper to iterate files similar to v1 Loop,dir
	LoopFiles(pattern)
	{
		local list := []
		Loop Files, pattern
			list.Push({ Name: A_LoopFileName, FullPath: A_LoopFileFullPath })
		return list
	}