menu(mode="single" type='back' expanded=true menu=title.options)

{

    item(title='Folder' cmd=io.dir.create(sys.datetime("ymdHMSs")) image=["\uE0E7"])

    $dt = sys.datetime("dhms")  

    $clip = clipboard.get  

    

    item(where=clipboard.is_empty || (!str.contains(clipboard.get(), "<html") && !str.contains(clipboard.get(), "margin:") && !str.contains(clipboard.get(), "function") && !str.contains(clipboard.get(), "def ") && !str.contains(clipboard.get(), "@echo") && !str.contains(clipboard.get(), "Write-Host") && !str.contains(clipboard.get(), "WScript.") && !(str.contains(clipboard.get(), "{") && str.contains(clipboard.get(), ":")) && !str.contains(clipboard.get(), "menu(") && !str.contains(clipboard.get(), "item(") && !str.contains(clipboard.get(), "modify(") && !str.contains(clipboard.get(), "<?xml") && !str.contains(clipboard.get(), "Windows Registry Editor Version") && !str.contains(clipboard.get(), "HKEY_")) title='TXT' cmd=io.file.create('txt ' + sys.datetime("dmHMS") + '.txt', @clipboard.get()) icon=["\uE113"])



    item(where=!clipboard.is_empty && str.contains(clipboard.get(), "<html") title='HTML' cmd=io.file.create('html ' + sys.datetime("dmHMS") + '.html', @clipboard.get()) icon=["\uE11F"])

    

    item(where=!clipboard.is_empty && str.contains(clipboard.get(), "{") && (str.contains(clipboard.get(), "margin:") || str.contains(clipboard.get(), "color:")) title='CSS' cmd=io.file.create('css ' + sys.datetime("dmHMS") + '.css', @clipboard.get()) icon=["\uE116"])

    

    item(where=!clipboard.is_empty && str.contains(clipboard.get(), "function") title='JS' cmd=io.file.create('js ' + sys.datetime("dmHMS") + '.js', @clipboard.get()) icon=["\uE22E"])

    item(where=!clipboard.is_empty && str.contains(clipboard.get(), "def ") title='PY' cmd=io.file.create('py ' + sys.datetime("dmHMS") + '.py', @clipboard.get()) icon=["\uE230"])

    item(where=!clipboard.is_empty && str.contains(clipboard.get(), "@echo") title='BAT' cmd=io.file.create('bat ' + sys.datetime("dmHMS") + '.bat', @clipboard.get()) icon=["\uE05C"])

    item(where=!clipboard.is_empty && (str.contains(clipboard.get(), "Write-Host") || str.contains(clipboard.get(), "Write-Output") || str.contains(clipboard.get(), "Write-Error") || str.contains(clipboard.get(), "Write-Warning") || str.contains(clipboard.get(), "Write-Verbose") || str.contains(clipboard.get(), "Write-Debug") || str.contains(clipboard.get(), "param(") || str.contains(clipboard.get(), "function "))title='PS1' cmd=io.file.create('ps1 ' + sys.datetime("dmHMS") + '.ps1', @clipboard.get()) icon=["\uE218"])

item(where=!clipboard.is_empty && (str.contains(clipboard.get(), "Windows Registry Editor Version") || str.contains(clipboard.get(), "HKEY_")) title='REG' cmd=io.file.create('reg ' + sys.datetime("dmHMS") + '.reg', @clipboard.get()) icon=["\uE142"])

    item(where=!clipboard.is_empty && str.contains(clipboard.get(), "WScript.") title='VBS' cmd=io.file.create('vbs ' + sys.datetime("dmHMS") + '.vbs', @clipboard.get()) icon=["\uE271"])

    

    item(where=!clipboard.is_empty && str.contains(clipboard.get(), "{") && str.contains(clipboard.get(), ":") && !str.contains(clipboard.get(), "menu(") && !str.contains(clipboard.get(), "item(") title='JSON' cmd=io.file.create('json ' + sys.datetime("dmHMS") + '.json', @clipboard.get()) icon=["\uE143"])

    

item(where=!clipboard.is_empty && (str.contains(clipboard.get(), "menu(") || str.contains(clipboard.get(), "item(") || str.contains(clipboard.get(), "modify(")) title='NSS' cmd=io.file.create('nss ' + sys.datetime("dmHMS") + '.nss', @clipboard.get()) icon=["\uE249"])

    

    item(where=!clipboard.is_empty && str.contains(clipboard.get(), "<?xml") title='XML' cmd=io.file.create('xml ' + sys.datetime("dmHMS") + '.xml', @clipboard.get()) icon=["\uE256"])

        menu(title='New File' image=[ ["\uE1A6"], ["\uE012"] ])  

    {  



        item(title='TXT' cmd=io.file.create('@(dt).txt', '@(clip)') icon=["\uE113"])

separator  

        item(title='HTML' cmd=io.file.create('@(dt).html', '@(clip)') icon=["\uE11F"])  

        item(title='CSS' cmd=io.file.create('@(dt).css', '@(clip)') icon=["\uE116"])  

        item(title='JS' cmd=io.file.create('@(dt).js', '@(clip)') icon=["\uE22E"])

separator  

        item(title='Py' cmd=io.file.create('@(dt).py', '@(clip)') icon=["\uE230"])  

        item(title='BAT' cmd=io.file.create('@(dt).bat', '@(clip)') icon=["\uE05C"])  

        item(title='PS1' cmd=io.file.create('@(dt).ps1', '@(clip)') icon=["\uE218"])

        item(title='VBS' cmd=io.file.create('@(dt).vbs', '@(clip)') icon=["\uE271"])



separator

        item(title='JSON' cmd=io.file.create('@(dt).json', '@(clip)') icon=["\uE143"])  

        item(title='NSS' cmd=io.file.create('@(dt).nss', '@(clip)') icon=["\uE249"])  

        item(title='REG' cmd=io.file.create('@(dt).reg', '@(clip)') icon=["\uE142"])  

    }

}