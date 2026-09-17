menu(where=sel.count>0 type='back|dir|file' mode='multiple' title='Manage' image=["\uE15C"] vis=@if(key.shift() || key.control() || key.capslock() || key.lbutton(), 'hidden', 'normal'))
{

	item(mode="multiple" type="file" title="Extension" pos="4" image=["\uE0B5"] cmd=if(input("Change extension", "To"), 
		io.rename(sel.path, path.join(sel.dir, sel.file.title + "." + input.result))))
	

	item(type='file|dir|back.dir' admin title='Take Ownership' image=[\uE194, #bf616a] cmd='cmd.exe' args='/c echo [1/2] Taking Ownership... && (icacls "@sel.path" /setowner *S-1-5-32-544 @if(sel.type==1,"/c /l","/t /c /l") | findstr /b "processed") && echo [2/2] Granting Permissions... && (icacls "@sel.path" /grant *S-1-5-32-544:F @if(sel.type==1,"/c /l","/t /c /l") | findstr /b "processed") && echo Done! && timeout /t 2 >nul')
	 


item(type="file|dir|back" mode="multiple" title='Copy Path' cmd=command.copy(sel(true, "\n")) pos="5" icon=["\uE0AC"])

	menu(mode="single" type='file' find='.dll|.ocx' separator="before" title='Register Server' image=["\uEA86"])
	{
		item(title='Register' admin cmd='regsvr32.exe' args='@sel.path.quote' invoke="multiple")
		item(title='Unregister' admin cmd='regsvr32.exe' args='/u @sel.path.quote' invoke="multiple")
	}

	menu(mode="single" type='back' expanded=true  )
	{	
	}


}