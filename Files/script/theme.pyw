import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import shutil
import os

class ThemeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("iMTheme")
        self.theme_file = r"C:\Program Files\Nilesoft Shell\imports\theme.nss"
        self.backup_file = self.theme_file + ".backup"
        
        self.backup_current_theme()
        self.load_theme_file()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True)

        self.create_tabs()
        self.create_buttons()

    def backup_current_theme(self):
        if os.path.exists(self.theme_file):
            shutil.copyfile(self.theme_file, self.backup_file)

    def load_theme_file(self):
        with open(self.theme_file, 'r') as file:
            self.theme_content = file.readlines()

    def save_theme_file(self):
        with open(self.theme_file, 'w') as file:
            file.writelines(self.theme_content)

    def import_theme_file(self):
        file_path = filedialog.askopenfilename(title="Select Theme File", filetypes=[("NSS files", "*.nss")])
        if file_path:
            self.backup_current_theme()
            shutil.copyfile(file_path, self.theme_file)
            self.load_theme_file()
            messagebox.showinfo("Success", "Theme imported successfully.")
        
    def reset_to_default(self):
        if os.path.exists(self.backup_file):
            shutil.copyfile(self.backup_file, self.theme_file)
            self.load_theme_file()
            messagebox.showinfo("Success", "Theme reset to default successfully.")
        else:
            messagebox.showwarning("Warning", "No backup file found. Cannot reset to default.")

    def update_theme(self, section, key, value, parent_section=None):
        section_found = False
        parent_found = False if parent_section else True

        for i, line in enumerate(self.theme_content):
            if parent_section and parent_section in line:
                parent_found = True

            if parent_found and section in line:
                section_found = True

            if section_found and key in line:
                if isinstance(value, str):
                    value_str = f'{value}'  
                else:
                    value_str = str(value)
                self.theme_content[i] = f"\t\t{key.strip()} = {value_str}\n"
                break

            if section_found and "}" in line:
                break

    def create_slider(self, parent, label, from_, to, command, initial, current_value):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(frame, text=label).pack(side='left')

        slider_value = tk.IntVar(value=current_value)
        value_label = ttk.Label(frame, text=str(current_value))
        value_label.pack(side='left', padx=5)

        slider = ttk.Scale(frame, from_=from_, to=to, orient='horizontal', 
                           command=lambda value: self.update_slider_value(value, slider_value, value_label, command))
        slider.set(initial)
        slider.pack(side='left', fill='x', expand=True)

        return slider

    def update_slider_value(self, value, slider_value, value_label, command):
        value = int(float(value))
        slider_value.set(value)
        value_label.config(text=str(value))
        command(value)

    def create_dropdown(self, parent, label, options, command):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=35, pady=35)
        ttk.Label(frame, text=label).pack(side='left')
        selected_option = tk.StringVar()
        dropdown = ttk.OptionMenu(frame, selected_option, options[0], *options, command=command)
        dropdown.pack(side='right', fill='x', expand=False)
        return dropdown

    def create_color_picker(self, parent, label, section, key, parent_section=None):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(frame, text=label).pack(side='left')
        
        color_var = tk.StringVar()
        color_entry = ttk.Entry(frame, textvariable=color_var, width=10)
        color_entry.pack(side='right', padx=5)

        def pick_color():
            color = colorchooser.askcolor()[1]
            if color:
                color_var.set(color)
                self.update_theme(section, key, color, parent_section)
        
        color_var.trace_add("write", lambda *args: self.update_theme(section, key, color_var.get(), parent_section))

        button = ttk.Button(frame, text="Choose Color", command=pick_color)
        button.pack(side='right', fill='x', expand=False)

        return button, color_entry

    def create_tabs(self):
        self.create_theme_tab()
        self.create_text_tab()
        self.create_background_tab()
        self.create_item_tab()
        self.create_border_tab()
        self.create_shadow_tab()
        self.create_font_tab()
        self.create_separator_tab()
        self.create_symbol_tab()
        self.create_image_tab()

    def create_text_tab(self):
        text_tab = ttk.Frame(self.notebook)
        self.notebook.add(text_tab, text='Text')

        # Frame for text colors
        text_frame = ttk.Frame(text_tab)
        text_frame.pack(fill='x', padx=5, pady=5)
        
        for label, color_key in [("TEXT", "normal"),
                                 ("Disabled", "normal.disabled"),
                                 ("Selected", "select"),
                                 ("Selected Disabled", "select.disabled")]:
            self.create_color_picker(text_tab, label, 'text', color_key, 'item')

        # Frame for text colors
        text_frame = ttk.Frame(text_tab)
        text_frame.pack(fill='x', padx=10, pady=10)
        
        for label, color_key in [("BACK", "select"),
                                 ("Disabled BACK", "select.disabled")]:
            self.create_color_picker(text_tab, label, 'back', color_key, 'item')

        # Frame for text colors
        text_frame = ttk.Frame(text_tab)
        text_frame.pack(fill='x', padx=10, pady=10)
        
        for label, color_key in [("BORDER", "normal"),
                                 ("Disabled BORDER", "normal.disabled"),
                                 ("Selected BORDER", "select"),
                                 ("Selected Disabled BORDER", "select.disabled")]:
            self.create_color_picker(text_tab, label, 'border', color_key, 'item')

    def create_background_tab(self):
        background_tab = ttk.Frame(self.notebook)
        self.notebook.add(background_tab, text='Background')
        
        text_frame = ttk.Frame(background_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_color_picker(background_tab, "Background Color", 'background', 'color')

        text_frame = ttk.Frame(background_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_slider(background_tab, "Background Opacity", 0, 100, lambda value: self.update_theme('background', 'opacity', value), 100, 100)
        
        text_frame = ttk.Frame(background_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_dropdown(background_tab, "Effect: 1 Transparent, 2 Blur, 3 Acrylic", ["Disable", "1", "2", "3"], lambda value: self.update_theme('background', 'effect', f'{value}'))

    def create_item_tab(self):
        item_tab = ttk.Frame(self.notebook)
        self.notebook.add(item_tab, text='Item')
        
        text_frame = ttk.Frame(item_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_slider(item_tab, "Item Opacity", 0, 100, lambda value: self.update_theme('item', 'opacity', value), 100, 100)

        text_frame = ttk.Frame(item_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_slider(item_tab, "Item Radius", 0, 4, lambda value: self.update_theme('item', 'radius', value), 3, 4)

    def create_border_tab(self):
        border_tab = ttk.Frame(self.notebook)
        self.notebook.add(border_tab, text='Border')

        self.create_dropdown(border_tab, "Enable Border", ["true", "false"], lambda value: self.update_theme('theme', 'border.enabled', value))
        self.create_color_picker(border_tab, "Border Color", 'theme', 'border.color')
        self.create_slider(border_tab, "Border Size", 0, 10, lambda value: self.update_theme('theme', 'border.size', value), 0, 10)
        self.create_slider(border_tab, "Border Opacity", 0, 100, lambda value: self.update_theme('theme', 'border.opacity', value), 0, 100)
        self.create_slider(border_tab, "Border Radius", 0, 4, lambda value: self.update_theme('theme', 'border.radius', value), 3, 4)
        
    def create_shadow_tab(self):
        shadow_tab = ttk.Frame(self.notebook)
        self.notebook.add(shadow_tab, text='Shadow')

        self.create_dropdown(shadow_tab, "Enable Shadow", ["true", "false"], lambda value: self.update_theme('shadow', 'enabled', value))
        self.create_color_picker(shadow_tab, "Shadow Color", 'shadow', 'color')
        self.create_slider(shadow_tab, "Shadow Size", 0, 30, lambda value: self.update_theme('shadow', 'size', value), 0, 10)
        self.create_slider(shadow_tab, "Shadow Opacity", 0, 100, lambda value: self.update_theme('shadow', 'opacity', value), 0, 100)

    def create_font_tab(self):
        font_tab = ttk.Frame(self.notebook)
        self.notebook.add(font_tab, text='Font')

        self.create_slider(font_tab, "Font Size", 6, 100, lambda value: self.update_theme('font', 'size', value), 14, 100)
        self.create_dropdown(font_tab, "Font Name", ["Segoe UI Variable Text", "tahoma", "verdana", "arial"], lambda value: self.update_theme('font', 'name', f'"{value}"'))
        self.create_slider(font_tab, "Weight", 1, 9, lambda value: self.update_theme('font', 'weight', value), 1, 9)
        self.create_dropdown(font_tab, "Font Italic", ["true", "false"], lambda value: self.update_theme('font', 'italic', value))

    def create_theme_tab(self):
        theme_tab = ttk.Frame(self.notebook)
        self.notebook.add(theme_tab, text='Theme')
        self.create_dropdown(theme_tab, "Theme", ["auto", "modern", "classic", "white", "black"], lambda value: self.update_theme('theme', 'name', f'"{value}"'))
        self.create_dropdown(theme_tab, "Theme Size", ["auto", "small", "medium", "large", "wide", "compact"], lambda value: self.update_theme('theme', 'view', f'view.{value}'))
        self.create_dropdown(theme_tab, "Dark Mode", ["true", "false"], lambda value: self.update_theme('theme', 'dark', value))

    def create_separator_tab(self):
        separator_tab = ttk.Frame(self.notebook)
        self.notebook.add(separator_tab, text='Separator')

        text_frame = ttk.Frame(separator_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_slider(separator_tab, "Separator Size", 0, 40, lambda value: self.update_theme('separator', 'size', value), 0, 40)

        text_frame = ttk.Frame(separator_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_color_picker(separator_tab, "Separator Color", 'separator', 'color')

        text_frame = ttk.Frame(separator_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_slider(separator_tab, "Separator Opacity", 0, 100, lambda value: self.update_theme('separator', 'opacity', value), 100, 100)

    def create_symbol_tab(self):
        symbol_tab = ttk.Frame(self.notebook)
        self.notebook.add(symbol_tab, text='Symbol')

        self.create_color_picker(symbol_tab, "Normal Symbol", 'symbol', 'normal')

        text_frame = ttk.Frame(symbol_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_color_picker(symbol_tab, "Selected Symbol", 'symbol', 'select')

        text_frame = ttk.Frame(symbol_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_color_picker(symbol_tab, "Disabled Symbol", 'symbol', 'normal-disabled')

        text_frame = ttk.Frame(symbol_tab)
        text_frame.pack(fill='x', padx=18, pady=18)
        
        self.create_color_picker(symbol_tab, "Selected Disabled Symbol", 'symbol', 'select-disabled')

    def create_image_tab(self):
        image_tab = ttk.Frame(self.notebook)
        self.notebook.add(image_tab, text='Image')

        self.create_dropdown(image_tab, "Enable Image", ["true", "false"], lambda value: self.update_theme('theme', 'image.enabled', value))
        self.create_color_picker(image_tab, "Image Color", 'theme', 'image.color')
        self.create_dropdown(image_tab, "Image Scale", ["true", "false"], lambda value: self.update_theme('theme', 'image.scale', value))
        self.create_dropdown(image_tab, "Image Align", ["0", "1", "2"], lambda value: self.update_theme('theme', 'image.align', value))

    def create_buttons(self):
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill='x', pady=10)

        save_button = ttk.Button(button_frame, text="Save", command=self.save_theme_file)
        save_button.pack(side='left', padx=5)

        import_button = ttk.Button(button_frame, text="Import Theme", command=self.import_theme_file)
        import_button.pack(side='left', padx=5)

        reset_button = ttk.Button(button_frame, text="Reset to Default", command=self.reset_to_default)
        reset_button.pack(side='left', padx=5)

        exit_button = ttk.Button(button_frame, text="Exit", command=self.root.quit)
        exit_button.pack(side='right', padx=5)

if __name__ == "__main__":
    root = tk.Tk()
    app = ThemeEditor(root)
    root.mainloop()
