
item(type='file|dir|drive|namespace' mode="multiple" title='Upload' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\croc.bat"' image=\uE214)


item(type='back' title='Download' cmd='@app.dir\script\download.bat' image=\uE213)


