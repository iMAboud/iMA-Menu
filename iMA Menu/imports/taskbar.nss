menu(type="taskbar" sep=both pos=0 title="iMA Menu" image=\uE188)
{

        item(title='Settings' cmd='@app.dir\launcher\launcher.exe' image=\uE069)
	item(title="Directory" image=\uE0E8 cmd='"@app.dir"')
}

menu(where=(this.count== 0) type='taskbar' image=icon.settings expanded=true)
{
	item(title="Task Manager" sep=both image=icon.task_manager cmd='taskmgr.exe')
	item(title="Taskbar" sep=both image=inherit cmd='ms-settings:taskbar')
	item(title="Restart Explorer" vis=key.shift() image=\uE1AA cmd=command.restart_explorer)
}
