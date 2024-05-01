    menu(title='iMShare' image ='C:\Program Files\Nilesoft Shell\icons\Share.ico')
    {
        item(type='file|dir|drive' title='Upload' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "C:\Program Files\Nilesoft Shell\script\croc.bat"' image='C:\Program Files\Nilesoft Shell\icons\upload.ico')
        separator

item(title='Download' cmd='cmd.exe' args='/c start "" "C:\Program Files\Nilesoft Shell\script\download.bat"' image='C:\Program Files\Nilesoft Shell\icons\download.ico')

    }

