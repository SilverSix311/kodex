DelFromBank(HotString, Bundle := "", Trigger := "")
{
	BankFile := A_ScriptDir . "\" . Bundle . "bank\" . Trigger . ".csv"
	if !FileExist(BankFile)
		return

	bank := FileRead(BankFile)
	if InStr(bank, HotString)
	{
		bank := StrReplace(bank, HotString . ",,", "", All)
		FileDelete(BankFile)
		FileAppend(bank, BankFile)
	}
	return
}