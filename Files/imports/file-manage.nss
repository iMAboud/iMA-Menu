menu(where=sel.count>0 type='file|dir|drive|namespace|back' mode="multiple" title='File Manage' image=\uE253)
{

	item(mode="single" type="file" title="Change extension" pos="0" image=\uE0B5 cmd=if(input("Change extension", "Type extension"), 
		io.rename(sel.path, path.join(sel.dir, sel.file.title + "." + input.result))))
	

	
	item(type='file|dir|back.dir|drive' title='Take Ownership' image=[\uE194,#f00] admin
		cmd args='/K takeown /f "@sel.path" @if(sel.type==1,null,"/r /d y") && icacls "@sel.path" /grant *S-1-5-32-544:F @if(sel.type==1,"/c /l","/t /c /l /q")')
	separator


item(title='Search' cmd='C:\Program Files\Nilesoft Shell\script\search.bat' image='C:\Program Files\Nilesoft Shell\icons\search.ico')
item(title='Draw' cmd='C:\Program Files\Nilesoft Shell\script\draw.pyw' image='C:\Program Files\Nilesoft Shell\icons\draw.ico')
item(title='wallpaper' cmd='C:\Program Files\Nilesoft Shell\script\wallpaper.py' image='C:\Program Files\Nilesoft Shell\icons\wallpaper.ico')


	menu(mode="single" type='file' find='.dll|.ocx' separator="before" title='Register Server' image=\uea86)
	{
		item(title='Register' admin cmd='regsvr32.exe' args='@sel.path.quote' invoke="multiple")
		item(title='Unregister' admin cmd='regsvr32.exe' args='/u @sel.path.quote' invoke="multiple")
	}

	menu(mode="single" type='back' expanded=true)
	{	

	}
	
	item(title='Clean Temp' cmd='C:\Program Files\Nilesoft Shell\script\cleantemp.bat' icon='C:\Program Files\Nilesoft Shell\icons\broom.ico')
        item(title='Color' cmd='C:\Program Files\Nilesoft Shell\script\hex.py' icon='C:\Program Files\Nilesoft Shell\icons\color.ico')


        
}
