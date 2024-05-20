import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton, QMessageBox

class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super(DragDropListWidget, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def dragEnterEvent(self, event):
        if event.source() != self:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() != self:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.source() != self:
            item = event.source().currentItem()
            event.source().takeItem(event.source().currentRow())
            self.addItem(item.text())

class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Nilesoft Shell Theme Editor")
        self.setGeometry(100, 100, 800, 600)

        global filepath, hide_list, more_list, shift_list, ids_list
        filepath = r"C:\Program Files\Nilesoft Shell\imports\modify.nss"
        content = read_file(filepath)

        hide_lines = extract_lines(content, "// hide\nmodify(mode=mode.multiple\nwhere=this.id(", ") vis=vis.remove)")
        more_lines = extract_lines(content, "// more\nmodify(mode=mode.multiple\nwhere=this.id(", ") menu=title.options)")
        shift_lines = extract_lines(content, "// shift\nmodify(mode=single\nwhere=this.id(", ") vis=key.shift())")

        self.init_ui(hide_lines, more_lines, shift_lines)

    def init_ui(self, hide_lines, more_lines, shift_lines):
        layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        layout.addLayout(left_layout)

        # Hide Listbox
        self.hide_label = QLabel("HIDE")
        left_layout.addWidget(self.hide_label)
        global hide_list
        hide_list = DragDropListWidget()
        hide_list.addItems(hide_lines)
        left_layout.addWidget(hide_list)

        # More Listbox
        self.more_label = QLabel("MORE")
        left_layout.addWidget(self.more_label)
        global more_list
        more_list = DragDropListWidget()
        more_list.addItems(more_lines)
        left_layout.addWidget(more_list)

        # Shift Listbox
        self.shift_label = QLabel("SHIFT")
        left_layout.addWidget(self.shift_label)
        global shift_list
        shift_list = DragDropListWidget()
        shift_list.addItems(shift_lines)
        left_layout.addWidget(shift_list)

        right_layout = QVBoxLayout()
        layout.addLayout(right_layout)

        # IDS Listbox
        self.ids_label = QLabel("IDS")
        right_layout.addWidget(self.ids_label)
        global ids_list
        ids_list = DragDropListWidget()
        placeholder_ids = ["id.add_a_network_location", "id.adjust_date_time", "id.align_icons_to_grid", "id.arrange_by",
    "id.auto_arrange_icons", "id.autoplay", "id.cancel", "id.cascade_windows", "id.cast_to_device",
    "id.cleanup", "id.collapse", "id.collapse_all_groups", "id.collapse_group", "id.command_prompt",
    "id.compressed", "id.configure", "id.content", "id.control_panel", "id.copy", "id.copy_as_path",
    "id.copy_here", "id.copy_path", "id.copy_to", "id.copy_to_folder", "id.cortana", "id.create_shortcut",
    "id.create_shortcuts_here", "id.customize_notification_icons", "id.customize_this_folder",
    "id.cut", "id.delete", "id.desktop", "id.details", "id.device_manager", "id.disconnect",
    "id.disconnect_network_drive", "id.display_settings", "id.edit", "id.eject", "id.empty_recycle_bin",
    "id.erase_this_disc", "id.exit_explorer", "id.expand", "id.expand_all_groups", "id.expand_group",
    "id.extra_large_icons", "id.extract_all", "id.extract_to",
    "id.file_explorer", "id.folder_options", "id.format", "id.give_access_to", "id.group_by",
    "id.include_in_library", "id.insert_unicode_control_character", "id.install", "id.large_icons",
    "id.list", "id.lock_all_taskbars", "id.lock_the_taskbar", "id.make_available_offline",
    "id.make_available_online", "id.manage", "id.map_as_drive", "id.map_network_drive", "id.medium_icons",
    "id.merge", "id.more_options", "id.mount", "id.move_here", "id.move_to", "id.move_to_folder",
    "id.new", "id.new_folder", "id.new_item", "id.news_and_interests", "id.next_desktop_background",
    "id.open", "id.open_as_portable", "id.open_autoplay", "id.open_command_prompt",
    "id.open_command_window_here", "id.open_file_location", "id.open_folder_location",
    "id.open_in_new_process", "id.open_in_new_tab", "id.open_in_new_window", "id.open_new_tab",
    "id.open_new_window", "id.open_powershell_window_here", "id.open_windows_powershell",
    "id.open_with", "id.options", "id.paste", "id.paste_shortcut", "id.personalize",
    "id.pin_current_folder_to_quick_access", "id.pin_to_quick_access", "id.pin_to_start",
    "id.pin_to_taskbar", "id.play", "id.power_options",
    "id.preview", "id.print", "id.properties", "id.reconversion", "id.redo", "id.refresh",
    "id.remove_from_quick_access", "id.remove_properties", "id.rename", "id.restore",
    "id.restore_default_libraries", "id.restore_previous_versions", "id.rotate_left", "id.rotate_right",
    "id.run", "id.run_as_administrator", "id.run_as_another_user", "id.search", "id.select_all",
    "id.send_to", "id.set_as_desktop_background", "id.set_as_desktop_wallpaper", "id.settings",
    "id.share", "id.share_with", "id.shield", "id.show_cortana_button",
    "id.show_desktop_icons", "id.show_file_extensions", "id.show_hidden_files", "id.show_libraries",
    "id.show_network", "id.show_pen_button", "id.show_people_on_the_taskbar", "id.show_task_view_button",
    "id.show_the_desktop", "id.show_this_pc", "id.show_touch_keyboard_button", "id.show_touchpad_button",
    "id.show_windows_side_by_side", "id.show_windows_stacked", "id.small_icons", "id.sort_by", "id.store",
    "id.task_manager", "id.taskbar_settings", "id.tiles", "id.troubleshoot_compatibility",
    "id.turn_off_bitlocker", "id.turn_on_bitlocker", "id.undo", "id.unpin_from_quick_access",
    "id.unpin_from_start", "id.unpin_from_taskbar", "id.view"]
        filtered_ids = self.filter_ids(placeholder_ids, hide_lines, more_lines, shift_lines)
        ids_list.addItems(filtered_ids)
        right_layout.addWidget(ids_list)

        right_layout.addStretch()

        button_layout = QHBoxLayout()

        # Save and Cancel Buttons
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(save_changes)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_button)

        right_layout.addLayout(button_layout)

        # Set the layout for the main window
        self.setLayout(layout)

    def filter_ids(self, ids, *lists):
        existing_ids = set()
        for lst in lists:
            existing_ids.update([id.strip().rstrip(',') for id in lst])
        return [id for id in ids if id.strip().rstrip(',') not in existing_ids]

def read_file(filepath):
    with open(filepath, 'r') as file:
        return file.read()

def write_file(filepath, content):
    with open(filepath, 'w') as file:
        file.write(content)

def extract_lines(content, start_marker, end_marker):
    sections = []
    start = content.find(start_marker)
    while start != -1:
        end = content.find(end_marker, start)
        if end == -1:
            break
        section = content[start:end].strip().split('\n')
        sections.extend([line.strip().rstrip(',') for line in section if line.strip().startswith("id")])
        start = content.find(start_marker, end)
    return sections

def save_changes():
    global filepath, hide_list, more_list, shift_list
    content = read_file(filepath)
    content = update_section(content, "// hide\nmodify(mode=mode.multiple\nwhere=this.id(", ") vis=vis.remove)", hide_list)
    content = update_section(content, "// more\nmodify(mode=mode.multiple\nwhere=this.id(", ") menu=title.options)", more_list)
    content = update_section(content, "// shift\nmodify(mode=single\nwhere=this.id(", ") vis=key.shift())", shift_list)
    write_file(filepath, content)
    QMessageBox.information(None, "Save", "Changes saved successfully.")

def update_section(content, start_marker, end_marker, listbox):
    start = content.find(start_marker)
    while start != -1:
        end = content.find(end_marker, start)
        if end == -1:
            break
        before_section = content[:start]
        section = content[start:end]
        after_section = content[end:]

        section_lines = section.strip().split('\n')
        new_ids = [listbox.item(i).text() for i in range(listbox.count())]

        if len(new_ids) < 1:
            QMessageBox.critical(None, "Error", "Each section must contain at least one ID.")
            return content

        new_ids = [new_id.strip() for new_id in new_ids if new_id.strip() != '']

        if len(new_ids) == 1:
            new_ids[0] = new_ids[0].rstrip(',')
        elif len(new_ids) > 1:
            for i in range(len(new_ids) - 1):
                new_ids[i] = new_ids[i].rstrip(',') + ","
            new_ids[-1] = new_ids[-1].rstrip(',')

        updated_lines = [line for line in section_lines if not line.strip().startswith("id")]
        updated_lines.extend(new_ids)

        updated_section = "\n".join(updated_lines)

        content = before_section + updated_section + after_section

        start = content.find(start_marker, start + len(updated_section))

    return content

def main():
    app = QApplication(sys.argv)  
    window = MainWindow()         
    window.show()                 
    sys.exit(app.exec_())         

if __name__ == "__main__":
    main()


