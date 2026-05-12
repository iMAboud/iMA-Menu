menu(type="taskbar" sep=both title="iMA Menu" image=[ ["\uE166"], ["\uE167"] ] menu='')
{

        item(title='Settings' cmd='@app.dir\launcher\launcher.exe' image=[ ["\uE069"], ["\uE002"] ] menu='')
	item(title="Directory" image=[ ["\uE011"], ["\uE07A"] ] cmd='"@app.dir"' menu='')
}

menu(where=(this.count== 0) type='taskbar' image=icon.settings expanded=true)
{
	item(title="Task Manager" sep=both image=icon.task_manager cmd='taskmgr.exe')
	item(title="Taskbar" sep=both image=inherit cmd='ms-settings:taskbar')
	item(title="Restart Explorer" vis=key.shift() image=["\uE1EA"] cmd='command.restart_explorer' menu='')
}
