// hide
modify(mode=mode.multiple
where=this.id(
    id.add_a_network_location,
    id.align_icons_to_grid,
    id.arrange_by,
    id.auto_arrange_icons,
    id.autoplay,
    id.cancel,
    id.cascade_windows,
    id.cast_to_device,
    id.cleanup,
    id.collapse,
    id.collapse_all_groups,
    id.collapse_group,
    id.configure,
    id.content,
    id.control_panel,
    id.copy_as_path,
    id.copy_here,
    id.copy_to,
    id.copy_to_folder,
    id.cortana,
    id.create_shortcuts_here,
    id.customize_notification_icons,
    id.customize_this_folder,
    id.desktop,
    id.details,
    id.device_manager,
    id.disconnect,
    id.disconnect_network_drive,
    id.erase_this_disc,
    id.expand,
    id.expand_all_groups,
    id.expand_group,
    id.extra_large_icons,
    id.folder_options,
    id.give_access_to,
    id.group_by,
    id.include_in_library,
    id.insert_unicode_control_character,
    id.large_icons,
    id.list,
    id.lock_all_taskbars,
    id.lock_the_taskbar,
    id.make_available_offline,
    id.make_available_online,
    id.manage,
    id.map_as_drive,
    id.map_network_drive,
    id.medium_icons,
    id.merge,
    id.more_options,
    id.move_here,
    id.move_to,
    id.move_to_folder,
    id.new,
    id.new_item,
    id.news_and_interests,
    id.next_desktop_background,
    id.open,
    id.open_as_portable,
    id.open_autoplay,
    id.open_in_new_process,
    id.open_in_new_tab,
    id.open_in_new_window,
    id.open_new_tab,
    id.open_new_window,
    id.paste_shortcut,
    id.play,
    id.power_options,
    id.print,
    id.reconversion,
    id.redo,
    id.remove_properties,
    id.restore_default_libraries,
    id.restore_previous_versions,
    id.rotate_left,
    id.rotate_right,
    id.run,
    id.run_as_another_user,
    id.search,
    id.select_all,
    id.share,
    id.share_with,
    id.shield,
    id.show_cortana_button,
    id.show_desktop_icons,
    id.show_libraries,
    id.show_network,
    id.show_pen_button,
    id.show_people_on_the_taskbar,
    id.show_task_view_button,
    id.show_the_desktop,
    id.show_this_pc,
    id.show_touch_keyboard_button,
    id.show_touchpad_button,
    id.show_windows_stacked,
    id.small_icons,
    id.sort_by,
    id.store,
    id.tiles,
    id.troubleshoot_compatibility,
    id.turn_off_bitlocker,
    id.turn_on_bitlocker,
    id.undo
) vis=vis.remove)

// more
modify(mode=mode.multiple
where=this.id(
    id.compressed,
    id.create_shortcut,
    id.eject,
    id.send_to
) menu=title.options)

// shift
modify(mode=single
where=this.id(
    id.command_prompt,
    id.open_command_prompt,
    id.open_command_window_here,
    id.open_file_location,
    id.open_powershell_window_here,
    id.open_windows_powershell,
    id.options,
    id.pin_current_folder_to_quick_access,
    id.pin_to_quick_access,
    id.pin_to_start,
    id.pin_to_taskbar,
    id.preview,
    id.settings,
    id.unpin_from_quick_access,
    id.unpin_from_start,
    id.unpin_from_taskbar,
    id.view

) vis=key.shift())


modify(where=str.equals(this.name, ["open in terminal", "open linux shell here"]) || this.id==id.open_powershell_window_here
    pos="bottom" menu="Terminal")

// -- iMA Managed --
    modify(find='Refresh' pos='top' vis='@if(key.shift() || key.control(), 'hidden', 'normal')')
    modify(find='Delete' pos='-1' vis='@if(key.shift() || key.control(), "hidden", "normal")' image=[\uE0B4, #ba473f])
    modify(find='Edit' vis='@if(key.shift() || key.control(), "hidden", "normal")')
    modify(find='Open' vis=vis.remove)
    modify(find='Edit With photo' menu='Tools' icon=\uE150)
    modify(find='EDIT IN NOTEPAD' title='Edit Notepad' icon=\uE113)
    modify(find='set as desktop' title='Background')
    modify(find='edit with photos' title='Edit Photo')
    modify(find='Open file loc' title='File Location')
    modify(find='unpin from start' title='Unpin Start')
    modify(find='pin to task' title='Pin Taskbar')
    modify(find='choose' in='open with' title='Choose App' icon=\uE283)
    modify(find='windows explorer' in='open with' icon=\uE0CF)
    modify(find='open with command' title='Open with CMD' icon=\uE0AB)
    modify(find='media player' in='open with' icon=\uE151)
    modify(find='movie' in='open with' icon=\uE12C)
    modify(find='photo' in='open with' icon=\uE150)
    modify(find='format' image=[\uE0C4, #ba473f])
    modify(find='search the' in='open with' vis=vis.hidden)
    modify(find='undo' vis=vis.hidden)
    modify(find='redo' vis=vis.remove)
    modify(find='add to fav' vis=vis.hidden)
    modify(find='scan' vis=vis.remove)
    modify(find='create with designer' vis=vis.remove)
    modify(find='microsoft edge' in='open with' vis=vis.hidden)
    modify(find='add to media' vis=vis.remove)
    modify(find='play with media' vis=vis.hidden)
    modify(find='open with vis' vis=vis.remove)
    modify(find='run as diff' vis=vis.remove)
    modify(find='nvidia app' vis=vis.hidden)
    modify(find='open with' pos=top)
    modify(find='winrar' title='WinRAR' image=\uE0D0)
    modify(find='"add to archive"' in='winrar' pos=top title='Archive' icon=\uE0DF)
    modify(find='"extract here"' in='winrar' pos='top' title='Extract Here' image=\uE0E0)
    modify(find='"extract files"' in='winrar' pos='1' title='Extract File' icon=\uE0E0)
// -- End iMA Managed --

