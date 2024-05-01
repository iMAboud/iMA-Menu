menu(where=sel.count>0 type='file|dir|drive|namespace|back' mode="multiple" title='File Manage' image=\uE253)
{

	item(mode="single" type="file" title="Change extension" image=\uE0B5 cmd=if(input("Change extension", "Type extension"), 
		io.rename(sel.path, path.join(sel.dir, sel.file.title + "." + input.result))))
	
	item(type='file|dir|back.dir|drive' title='Take Ownership' image=[\uE194,#f00] admin
		cmd args='/K takeown /f "@sel.path" @if(sel.type==1,null,"/r /d y") && icacls "@sel.path" /grant *S-1-5-32-544:F @if(sel.type==1,"/c /l","/t /c /l /q")')
	separator

	menu(mode="single" type='file' find='.dll|.ocx' separator="before" title='Register Server' image=\uea86)
	{
		item(title='Register' admin cmd='regsvr32.exe' args='@sel.path.quote' invoke="multiple")
		item(title='Unregister' admin cmd='regsvr32.exe' args='/u @sel.path.quote' invoke="multiple")
	}

}