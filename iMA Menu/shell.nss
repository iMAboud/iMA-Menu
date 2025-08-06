settings
{

	priority=1
	showdelay = 0
	modify.remove.duplicate=1
	tip.enabled=true
        
}



menu( mode="multiple" vis=key.shift() title="Pin/Unpin" image=icon.pin)
{
}

menu(mode="multiple" title="Options" image=icon.more_options)
{

remove(find="undo|redo")
}

import 'imports/theme.nss'
import 'imports/images.nss'
import 'imports/modify.nss'
import 'imports/file-manage.nss'
import 'imports/taskbar.nss'
import 'imports/shortcut.nss'



