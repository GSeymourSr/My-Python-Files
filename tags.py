import customtkinter as ctk
from tkinter import filedialog
import os
import json
from PIL import Image # Pillow for image handling

# Attempt to import pywin32 components
try:
    from win32com.propsys import propsys, pscon
    import pythoncom # Needed for VT_ constants, com_error, CoInitialize/Ex
    # import win32com.client # Not strictly needed if passing list directly to SetValue
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    # Define placeholders if imports fail
    propsys = None
    pscon = None
    pythoncom = None
    # win32com = None 
    print("WARNING: pywin32 library not found. Tagging functionality will be disabled.")
    print("Please install it: pip install pywin32")

# --- Configuration ---
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
TAGS_FILE = os.path.join(CONFIG_DIR, "tags.json")
DEFAULT_THUMBNAIL_SIZE = (75, 75)
GENERIC_FILE_ICON_PATH = None

# --- Helper Functions ---
def load_tags():
    initial_tags = sorted([
        "guitar", "clown", "skull", "tie-dye", "evil",
        "grid", "flower", "heart", "alien", "gsai"
    ])
    if not os.path.exists(TAGS_FILE):
        with open(TAGS_FILE, 'w') as f:
            json.dump(initial_tags, f, indent=2)
        return initial_tags
    try:
        with open(TAGS_FILE, 'r') as f:
            tags = json.load(f)
        return sorted(list(set(tags)))
    except (json.JSONDecodeError, IOError):
        with open(TAGS_FILE, 'w') as f:
            json.dump(initial_tags, f, indent=2)
        return initial_tags

def save_tags(tags_list):
    with open(TAGS_FILE, 'w') as f:
        json.dump(sorted(list(set(tags_list))), f, indent=2)

def create_thumbnail(file_path, size=DEFAULT_THUMBNAIL_SIZE):
    try:
        img = Image.open(file_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except IOError:
        if GENERIC_FILE_ICON_PATH and os.path.exists(GENERIC_FILE_ICON_PATH):
            try:
                generic_img = Image.open(GENERIC_FILE_ICON_PATH)
                generic_img.thumbnail(size, Image.Resampling.LANCZOS)
                return ctk.CTkImage(light_image=generic_img, dark_image=generic_img, size=size)
            except IOError:
                pass
        return None

# --- Main Application Class ---
class FileTaggerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._com_initialized = False # Initialize flag
        if PYWIN32_AVAILABLE:
            try:
                pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
                self._com_initialized = True
                print("COM Initialized in STA mode.")
            except pythoncom.com_error as e:
                if e.hresult == -2147417850: # RPC_E_CHANGED_MODE
                     print(f"COM already initialized with a different mode: {e}. Proceeding with caution.")
                     self._com_initialized = True # Still mark as 'initialized' for our logic
                else:
                    print(f"Critical CoInitializeEx error: {e}. COM features might be unstable or disabled.")
                    self._com_initialized = False


        self.title("Colorful File Tagger Pro")
        self.state('zoomed')
        self.minsize(800, 600)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.current_folder_path = ""
        self.all_tags = load_tags()
        self.selected_files_vars = {}
        self.displayed_file_paths_in_order = []
        self.last_selected_file_for_shift_click = None
        self.selected_tag_vars = {}

        self._shift_pressed_flag = False
        self.bind_all("<KeyPress-Shift_L>", self._on_shift_press)
        self.bind_all("<KeyPress-Shift_R>", self._on_shift_press)
        self.bind_all("<KeyRelease-Shift_L>", self._on_shift_release)
        self.bind_all("<KeyRelease-Shift_R>", self._on_shift_release)

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self.file_pane = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "gray20"))
        self.file_pane.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.file_pane.grid_rowconfigure(0, weight=0)
        self.file_pane.grid_rowconfigure(1, weight=0)
        self.file_pane.grid_rowconfigure(2, weight=1)
        self.file_pane.grid_columnconfigure(0, weight=1)
        self.file_pane.grid_columnconfigure(1, weight=1)

        self.browse_button = ctk.CTkButton(self.file_pane, text="Browse Folder", command=self.browse_folder,
                                           fg_color="#FF6347", hover_color="#E55337", text_color="white")
        self.browse_button.grid(row=0, column=0, padx=(10,5), pady=(10,5), sticky="ew")

        self.folder_path_label = ctk.CTkLabel(self.file_pane, text="No folder selected.", anchor="w",
                                              font=ctk.CTkFont(size=10), text_color=("gray50", "gray60"))
        self.folder_path_label.grid(row=0, column=1, padx=(5,10), pady=(10,5), sticky="ew")

        self.select_all_button = ctk.CTkButton(self.file_pane, text="Select All Files",
                                               command=self.select_all_files,
                                               fg_color="#5cb85c", hover_color="#4cae4c")
        self.select_all_button.grid(row=1, column=0, padx=(10,5), pady=(5,5), sticky="ew")

        self.deselect_all_button = ctk.CTkButton(self.file_pane, text="Deselect All Files",
                                                 command=self.deselect_all_files,
                                                 fg_color="#d9534f", hover_color="#c9302c")
        self.deselect_all_button.grid(row=1, column=1, padx=(5,10), pady=(5,5), sticky="ew")

        self.file_scroll_frame = ctk.CTkScrollableFrame(self.file_pane, label_text="Files in Folder",
                                                        label_fg_color="#4A90E2", label_text_color="white",
                                                        fg_color=("gray85", "gray25"))
        self.file_scroll_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(5,10), sticky="nsew")
        if hasattr(self.file_scroll_frame, '_scrollbar') and self.file_scroll_frame._scrollbar:
            self.file_scroll_frame._scrollbar.configure(button_color="#4A90E2", button_hover_color="#3A7BC8")

        self.tag_pane = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "gray20"))
        self.tag_pane.grid(row=0, column=1, padx=(0,10), pady=10, sticky="nsew")
        self.tag_pane.grid_rowconfigure(0, weight=1)
        self.tag_pane.grid_rowconfigure(1, weight=0)
        self.tag_pane.grid_rowconfigure(2, weight=0)
        self.tag_pane.grid_rowconfigure(3, weight=0)
        self.tag_pane.grid_columnconfigure(0, weight=1)

        self.tag_scroll_frame = ctk.CTkScrollableFrame(self.tag_pane, label_text="Available Tags",
                                                       label_fg_color="#34A853", label_text_color="white",
                                                       fg_color=("gray85", "gray25"))
        self.tag_scroll_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        if hasattr(self.tag_scroll_frame, '_scrollbar') and self.tag_scroll_frame._scrollbar:
            self.tag_scroll_frame._scrollbar.configure(button_color="#34A853", button_hover_color="#2A8A43")

        self.add_tag_label = ctk.CTkLabel(self.tag_pane, text="Add New Tag:", font=ctk.CTkFont(weight="bold"))
        self.add_tag_label.grid(row=1, column=0, padx=10, pady=(10,0), sticky="sw")

        self.add_tag_entry = ctk.CTkEntry(self.tag_pane, placeholder_text="Enter new tag name")
        self.add_tag_entry.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.add_tag_entry.bind("<Return>", self.add_new_tag_event)

        self.add_tag_button = ctk.CTkButton(self.tag_pane, text="Add Tag", command=self.add_new_tag,
                                            fg_color="#FFC107", hover_color="#E0A800", text_color="black")
        self.add_tag_button.grid(row=3, column=0, padx=10, pady=(0,10), sticky="ew")

        self.action_bar = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=("gray80", "gray15"))
        self.action_bar.grid(row=1, column=0, columnspan=2, padx=0, pady=0, sticky="sew")

        self.apply_tags_button = ctk.CTkButton(self.action_bar, text="Apply Tags to Selected Files",
                                               command=self.apply_tags, height=40,
                                               font=ctk.CTkFont(size=16, weight="bold"),
                                               fg_color="#1E90FF", hover_color="#1C86EE")
        self.apply_tags_button.pack(side="right", padx=20, pady=5)
        if not PYWIN32_AVAILABLE or not self._com_initialized :
            self.apply_tags_button.configure(state="disabled", text="Apply Tags (COM/pywin32 issue)")

        self.status_label = ctk.CTkLabel(self.action_bar, text="Ready.", anchor="w")
        self.status_label.pack(side="left", padx=20, pady=5)

        self.populate_tags_checkboxes()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        if PYWIN32_AVAILABLE and hasattr(self, '_com_initialized') and self._com_initialized:
            # Only uninitialize if our CoInitializeEx call didn't just report RPC_E_CHANGED_MODE.
            # A more robust check would involve inspecting the actual success/failure of CoInitializeEx.
            # For simplicity, if _com_initialized is True, we call CoUninitialize.
            # This assumes that if RPC_E_CHANGED_MODE occurred, we still "proceeded" and thus might need to uninit.
            # However, strictly speaking, if COM was already initialized by someone else, we shouldn't uninit it.
            # This area can be complex. The safest bet for a simple app is that if our CoInitializeEx
            # was the first successful STA init, we uninit. If it was RPC_E_CHANGED_MODE, we don't.
            # Let's refine this: only uninitialize if WE set it to STA and it wasn't already set.
            # This is tricky to track without more state. The current approach is a common attempt.
            try:
                pythoncom.CoUninitialize()
                print("COM Uninitialized.")
            except Exception as e:
                print(f"Error during CoUninitialize: {e}")
        self.destroy()

    def _on_shift_press(self, event):
        self._shift_pressed_flag = True

    def _on_shift_release(self, event):
        self._shift_pressed_flag = False

    def browse_folder(self):
        new_path = filedialog.askdirectory(initialdir=self.current_folder_path if self.current_folder_path else os.path.expanduser("~"))
        if new_path:
            self.current_folder_path = new_path
            self.folder_path_label.configure(text=f"Folder: ...{os.sep}{os.path.basename(self.current_folder_path)}")
            self.status_label.configure(text=f"Browsing: {self.current_folder_path}")
            self.populate_file_list()
        else:
            self.status_label.configure(text="Folder selection cancelled.")

    def populate_file_list(self):
        for widget in self.file_scroll_frame.winfo_children():
            widget.destroy()
        self.selected_files_vars.clear()
        self.displayed_file_paths_in_order.clear()
        self.last_selected_file_for_shift_click = None

        if not self.current_folder_path:
            return

        try:
            files = sorted([f for f in os.listdir(self.current_folder_path)
                            if os.path.isfile(os.path.join(self.current_folder_path, f))], key=str.lower)
        except OSError as e:
            self.status_label.configure(text=f"Error reading folder: {e}")
            return

        if not files:
            no_files_label = ctk.CTkLabel(self.file_scroll_frame, text="No files found in this folder.")
            no_files_label.pack(padx=10, pady=10)
            return

        row_num = 0; col_num = 0; max_cols = 5
        for filename in files:
            file_path = os.path.join(self.current_folder_path, filename)
            self.displayed_file_paths_in_order.append(file_path)
            file_item_frame = ctk.CTkFrame(self.file_scroll_frame, fg_color="transparent")
            file_item_frame.grid(row=row_num, column=col_num, padx=3, pady=3, sticky="nsew")
            var = ctk.BooleanVar()
            self.selected_files_vars[file_path] = var
            chk = ctk.CTkCheckBox(file_item_frame, variable=var, text="", width=18, checkbox_height=18, checkbox_width=18,
                                  fg_color="#4A90E2", hover_color="#3A7BC8",
                                  command=lambda fp=file_path: self.on_file_checkbox_clicked(fp))
            chk.pack(side="top", pady=(0,2))
            thumbnail_img = create_thumbnail(file_path)
            if thumbnail_img:
                thumb_label = ctk.CTkLabel(file_item_frame, image=thumbnail_img, text="")
            else:
                ext = f".{filename.split('.')[-1].upper()}" if '.' in filename else "FILE"
                thumb_label = ctk.CTkLabel(file_item_frame, text=ext, width=DEFAULT_THUMBNAIL_SIZE[0], height=DEFAULT_THUMBNAIL_SIZE[1]-20,
                                           font=ctk.CTkFont(size=10, weight="bold"), fg_color=("gray70", "gray40"), corner_radius=5)
            thumb_label.pack(side="top", fill="x", expand=False, pady=(0,2))
            name_label = ctk.CTkLabel(file_item_frame, text=filename, font=ctk.CTkFont(size=9), wraplength=DEFAULT_THUMBNAIL_SIZE[0]-5)
            name_label.pack(side="top", pady=(0,0), fill="x")
            col_num += 1
            if col_num >= max_cols: col_num = 0; row_num += 1
        for i in range(max_cols): self.file_scroll_frame.grid_columnconfigure(i, weight=1)

    def on_file_checkbox_clicked(self, file_path_clicked):
        current_selection_state = self.selected_files_vars[file_path_clicked].get()
        if self._shift_pressed_flag and self.last_selected_file_for_shift_click and \
           self.last_selected_file_for_shift_click != file_path_clicked and \
           self.last_selected_file_for_shift_click in self.displayed_file_paths_in_order and \
           file_path_clicked in self.displayed_file_paths_in_order:
            try:
                anchor_idx = self.displayed_file_paths_in_order.index(self.last_selected_file_for_shift_click)
                current_idx = self.displayed_file_paths_in_order.index(file_path_clicked)
                start_idx, end_idx = min(anchor_idx, current_idx), max(anchor_idx, current_idx)
                for i in range(start_idx, end_idx + 1):
                    fp_in_range = self.displayed_file_paths_in_order[i]
                    if fp_in_range in self.selected_files_vars:
                        self.selected_files_vars[fp_in_range].set(current_selection_state)
                self.status_label.configure(text=f"Range {'selected' if current_selection_state else 'deselected'}.")
            except ValueError:
                self.last_selected_file_for_shift_click = file_path_clicked
                self.status_label.configure(text=f"{os.path.basename(file_path_clicked)} {'selected' if current_selection_state else 'deselected'}.")
        else:
            self.last_selected_file_for_shift_click = file_path_clicked
            self.status_label.configure(text=f"{os.path.basename(file_path_clicked)} {'selected' if current_selection_state else 'deselected'}.")

    def select_all_files(self):
        if not self.selected_files_vars: self.status_label.configure(text="No files to select."); return
        for var in self.selected_files_vars.values(): var.set(True)
        self.status_label.configure(text="All files selected.")
        if self.displayed_file_paths_in_order: self.last_selected_file_for_shift_click = self.displayed_file_paths_in_order[-1]

    def deselect_all_files(self):
        if not self.selected_files_vars: self.status_label.configure(text="No files to deselect."); return
        for var in self.selected_files_vars.values(): var.set(False)
        self.status_label.configure(text="All files deselected.")
        self.last_selected_file_for_shift_click = None

    def populate_tags_checkboxes(self):
        for widget in self.tag_scroll_frame.winfo_children(): widget.destroy()
        self.selected_tag_vars.clear()
        for tag_name in self.all_tags:
            var = ctk.BooleanVar()
            self.selected_tag_vars[tag_name] = var
            chk = ctk.CTkCheckBox(self.tag_scroll_frame, text=tag_name, variable=var,
                                  fg_color="#34A853", hover_color="#2A8A43", text_color=("black", "white"))
            chk.pack(anchor="w", padx=10, pady=2, fill="x")

    def add_new_tag_event(self, event=None): self.add_new_tag()

    def add_new_tag(self):
        new_tag = self.add_tag_entry.get().strip()
        if new_tag and new_tag not in self.all_tags:
            self.all_tags.append(new_tag)
            self.all_tags = sorted(list(set(self.all_tags)))
            save_tags(self.all_tags)
            self.populate_tags_checkboxes()
            self.add_tag_entry.delete(0, 'end')
            self.status_label.configure(text=f"Tag '{new_tag}' added.")
        elif not new_tag: self.status_label.configure(text="Tag name cannot be empty.")
        else: self.status_label.configure(text=f"Tag '{new_tag}' already exists.")

    def apply_tags(self):
        if not PYWIN32_AVAILABLE:
            self.status_label.configure(text="Cannot apply tags: pywin32 library is missing.")
            return
        if not self._com_initialized:
            self.status_label.configure(text="COM not initialized properly. Cannot apply tags.")
            return

        selected_file_paths = [fp for fp, var in self.selected_files_vars.items() if var.get()]
        chosen_tags = [tag for tag, var in self.selected_tag_vars.items() if var.get()]

        if not selected_file_paths:
            self.status_label.configure(text="No files selected to tag.")
            return

        self.status_label.configure(text=f"Applying {len(chosen_tags)} tags to {len(selected_file_paths)} file(s)...")
        self.update_idletasks()

        successful_tags_count = 0
        errors_encountered_count = 0
        error_messages = []

        for file_path in selected_file_paths:
            try:
                properties = propsys.SHGetPropertyStoreFromParsingName(file_path)
                tags_to_apply = [str(tag) for tag in chosen_tags]

                # Using the direct Python list with SetValue
                if tags_to_apply:
                    properties.SetValue(pscon.PKEY_Keywords, tags_to_apply)
                else:
                    properties.SetValue(pscon.PKEY_Keywords, []) # Clear tags
                
                properties.Commit()
                successful_tags_count += 1
            except pythoncom.com_error as e:
                hr = e.hresult
                msg = e.strerror
                error_msg = f"Error tagging {os.path.basename(file_path)}: com_error - (HRESULT: {hr:08X}, '{msg}')"
                print(error_msg)
                error_messages.append(error_msg)
                errors_encountered_count += 1
            except Exception as e:
                error_msg = f"Error tagging {os.path.basename(file_path)}: {type(e).__name__} - {e}"
                print(error_msg)
                error_messages.append(error_msg)
                errors_encountered_count += 1

        if errors_encountered_count > 0:
            final_status = f"Completed. Tagged: {successful_tags_count}. Errors: {errors_encountered_count}."
            print("\n--- TAGGING ERRORS (Details) ---")
            for err_detail in error_messages: print(err_detail)
            print("---------------------------------")
        elif successful_tags_count > 0 :
            final_status = f"Successfully tagged {successful_tags_count} file(s)."
        else:
            if selected_file_paths and chosen_tags and successful_tags_count == 0 and errors_encountered_count == 0:
                 final_status = "Tagging attempted, but no changes were made (no errors reported)."
            elif not selected_file_paths: # This case should be caught earlier
                 final_status = "No files selected to tag."
            else: # This means no tags were chosen, or all attempts failed without explicit error (unlikely for SetValue)
                 final_status = "No files were tagged (or no tags chosen)."
        self.status_label.configure(text=final_status)

if __name__ == "__main__":
    app = FileTaggerApp()
    app.mainloop()