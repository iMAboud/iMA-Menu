settings
{
    priority=1
    showdelay = 0
    modify.remove.duplicate=1
    tip.enabled=true
    screenshot.enabled=true
    screenshot.directory=user.desktop
    modify.enabled=true
}

menu(mode="multiple" vis=key.shift() title="Pin/Unpin" image=[["\uE03F"], ["\uE041"]] menu='')
{
}

menu(mode="multiple" title="Options" image=[["\uE08D"], ["\uE08E"]] menu='')
{
}

import 'imports/file-manage.nss'
import 'imports/images.nss'
import 'imports/modify.nss'
import 'imports/shortcut.nss'
import 'imports/taskbar.nss'
import 'imports/theme.nss'
import 'imports/new.nss'
