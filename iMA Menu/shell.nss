settings
{

	priority=1
	exclude.where = !process.is_explorer
	showdelay = 0
	modify.remove.duplicate=1
	tip.enabled=true
}

import 'imports/theme.nss'
import 'imports/images.nss'

import 'imports/modify.nss'

menu( mode="multiple" vis=key.shift() title="Pin/Unpin" image=icon.pin)
{
}

menu(mode="multiple" title=title.options image=icon.more_options)
{

remove(find="undo|redo|add to fav")
}

import 'imports/file-manage.nss'
import 'imports/taskbar.nss'
import 'imports/iMShare.nss'
import 'imports/yt.nss'
import 'imports/tools.nss'
