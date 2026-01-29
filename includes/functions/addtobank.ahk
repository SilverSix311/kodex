AddToBank(HotString, Bundle := "", Trigger := "")
{
	; HotString is expected to be hex-encoded already
	BankFile := A_ScriptDir . "\" . Bundle . "bank\" . Trigger . ".csv"
	if !FileExist(BankFile)
		FileAppend("", BankFile)

	bank := FileRead(BankFile)
	if !InStr(bank, HotString)
	{
		FileAppend(HotString . ",,", BankFile)
		; refresh bank content if caller expects it
		bank := FileRead(BankFile)
	}
	return
}