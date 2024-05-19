menu(type="taskbar" sep=both pos=0 title=app.name image=\uE249)
{
	item(title="config" image=\uE10A cmd='"@app.cfg"')
	item(title="directory" image=\uE0E8 cmd='"@app.dir"')
        item(title='Theme' cmd='C:\Program Files\Nilesoft Shell\script\theme.pyw' image='C:\Program Files\Nilesoft Shell\icons\theme.ico')
}
menu(where=@(this.count == 0) type='taskbar' image=icon.settings expanded=true)
{


	item(title=title.task_manager sep=both image=icon.task_manager cmd='taskmgr.exe')
	item(title=title.taskbar_Settings sep=both image=inherit cmd='ms-settings:taskbar')
	item(vis=key.shift() title=title.exit_explorer cmd=command.restart_explorer)
}
