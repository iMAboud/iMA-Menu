// hide
modify(mode=mode.multiple
where=this.id,
id.turn_off_bitlocker(

) vis=vis.remove)

// more
modify(mode=mode.multiple
where=this.id(

id.eject,
id.create_shortcut,
id.create_shortcuts_here) menu=title.options)

// shift
modify(mode=single
where=this.id(

id.details

) vis=key.shift())

modify(type="recyclebin" where=window.is_desktop and this.id==id.empty_recycle_bin pos=1 sep)

modify(find="unpin*" pos="bottom" menu="Pin/Unpin")

modify(find="pin*" pos="top" menu="Pin/Unpin")

modify(where=this.id==id.copy_as_path menu="Manage")

modify(type="dir.back|drive.back" where=this.id==id.customize_this_folder pos=1 sep="top" menu="file manage")

modify(where=str.equals(this.name, ["open in terminal", "open linux shell here"]) || this.id==id.open_powershell_window_here
	pos="bottom" menu="Terminal")
