Set s = CreateObject("WScript.Shell")
result = s.Run("""C:\scripts\rodar_monitor.bat""", 0, True)
WScript.Quit result
