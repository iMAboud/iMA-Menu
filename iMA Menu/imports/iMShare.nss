
item(type='file|dir|drive|namespace' mode="multiple" title='Upload' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\upload.pyw"' image=\uE214)


item(type='back' title='Download' cmd='@app.dir\script\download.pyw' image=\uE213)


