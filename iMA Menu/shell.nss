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

remove(find="undo|redo|edit with sharex|upload|open with visual|add to fav|SCAN|edit with paint|set as desktop|run as diff|add to media|play with media")
}

import 'imports/theme.nss'
import 'imports/images.nss'
import 'imports/modify.nss'
import 'imports/file-manage.nss'
import 'imports/taskbar.nss'
import 'imports/iMShare.nss'
import 'imports/yt.nss'
import 'imports/tools.nss'
import 'imports/shortcut.nss'
