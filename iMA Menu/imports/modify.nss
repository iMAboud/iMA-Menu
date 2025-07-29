// hide
modify(mode=mode.multiple
where=this.id(
id.print,
id.cortana,
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
id.copy_here,
id.copy_to,
id.copy_to_folder,
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
id.new_item,
id.next_desktop_background,
id.news_and_interests,
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
id.reconversion,
id.redo,
id.restore_default_libraries,
id.restore_previous_versions,
id.rotate_left,
id.rotate_right,
id.run,
id.search,
id.select_all,
id.set_as_desktop_wallpaper,
id.share,
id.share_with,
id.shield,
id.show_cortana_button,
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
id.sort_by,
id.store,
id.tiles,
id.small_icons,
id.undo,
id.turn_on_bitlocker,
id.turn_off_bitlocker,
id.troubleshoot_compatibility,
id.remove_properties,
id.open,
id.show_desktop_icons,
id.new
) vis=vis.remove)

// more
modify(mode=mode.multiple
where=this.id(
id.send_to,
id.eject,
id.copy_path,
id.compressed,
id.create_shortcut,
id.cut,
id.rename,
id.paste,
id.copy
) menu=title.options)

// shift
modify(mode=single
where=this.id(
id.open_with,
id.options,
id.install,
id.display_settings,
id.pin_current_folder_to_quick_access,
id.pin_to_quick_access,
id.pin_to_start,
id.pin_to_taskbar,
id.preview,
id.remove_from_quick_access,
id.run_as_another_user,
id.settings,
id.unpin_from_taskbar,
id.unpin_from_start,
id.unpin_from_quick_access,
id.command_prompt,
id.open_windows_powershell,
id.open_command_prompt,
id.open_command_window_here,
id.open_powershell_window_here,
id.personalize,
id.view
) vis=key.shift())



modify(find='Edit With photo' menu='Tools' image=\uE150)

modify(type="recyclebin" where=window.is_desktop and this.id==id.empty_recycle_bin pos=1 sep)

modify(where=this.id==id.copy_as_path title='Path' menu="Manage")

modify(where=str.equals(this.name, ["open in terminal", "open linux shell here"]) || this.id==id.open_powershell_window_here
    pos="bottom" menu="Terminal")

modify(find='EDIT IN NOTEPAD' title='Edit Notepad' icon=\uE113)
modify(find='7-ZIP' title='Zip' icon=\uE0D0)
modify(find='edit with idle' title='Edit with IDLE' icon=\uE230)
modify(find='Winrar' title='WinRAR' icon=\uE0CF)
