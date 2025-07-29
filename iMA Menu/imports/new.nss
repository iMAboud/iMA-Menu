menu(mode="single" type='back' expanded=true menu=title.options)
	{
		item(title='New Folder' cmd=io.dir.create(sys.datetime("ymdHMSs")) image=\uE0E7)
		menu(title='New File' image=icon.new_file)
		{
			$dt = sys.datetime("ymdHMSs")
			item(title='TXT' cmd=io.file.create('@(dt).txt'))
			item(title='HTML' cmd=io.file.create('@(dt).html'))
			item(title='JS' cmd=io.file.create('@(dt).js'))
			item(title='CSS' cmd=io.file.create('@(dt).css'))
		}
}
