import tkinter as tk
from tkinter import ttk, messagebox
import pymem
import pymem.process
import struct
import csv
import os
import shutil
import re

from data.worker_utils import add_geoguess_worker
from data.appendtobin import append_geoguesser_data

# ==========================================
# TAB 1: FFX GeoGuesser Tool (Code 1)
# ==========================================
class FFXMonitor:
    def __init__(self, parent):
        self.master = parent
        self.master.configure(bg='#2c3e50')

        # 1. Load CSV data safely
        self.model_data = {}
        self.load_csv()

        # UI Styling
        lbl_style = {"bg": "#2c3e50", "fg": "#ecf0f1", "font": ("Arial", 10, "bold")}
        val_style = {"bg": "#2c3e50", "fg": "#3498db", "font": ("Consolas", 10)}
        code_style = {"bg": "#1a252f", "fg": "#2ecc71", "font": ("Consolas", 10)}

        # --- TOP: DROPDOWN ---
        tk.Label(self.master, text="Model:", **lbl_style).pack(pady=(10, 0))
        self.model_var = tk.StringVar()
        self.dropdown = ttk.Combobox(self.master, textvariable=self.model_var, state="readonly", width=30)
        
        if self.model_data:
            self.dropdown['values'] = list(self.model_data.keys())
        else:
            self.dropdown['values'] = ["No data found"]
        self.dropdown.current(0)
        self.dropdown.pack(pady=5)

        # --- MIDDLE: LIVE DATA ---
        stats_frame = tk.Frame(self.master, bg='#2c3e50')
        stats_frame.pack(pady=10)

        self.lbl_ebp = self.create_stat_row(stats_frame, "EBP:", 0, val_style)
        self.lbl_x = self.create_stat_row(stats_frame, "X Position:", 1, val_style)
        self.lbl_y = self.create_stat_row(stats_frame, "Y Position:", 2, val_style)
        self.lbl_z = self.create_stat_row(stats_frame, "Z Position:", 3, val_style)
        self.lbl_rot = self.create_stat_row(stats_frame, "Rotation:", 4, val_style)

        # --- BOTTOM: CODES ---
        tk.Label(self.master, text="--- CODES ---", **lbl_style).pack(pady=5)
        
        self.code_line1 = tk.Label(self.master, text="N/A", **code_style)
        self.code_line1.pack(fill="x", padx=20, pady=2)

        self.code_line2 = tk.Label(self.master, text="N/A", **code_style)
        self.code_line2.pack(fill="x", padx=20, pady=2)

        self.code_line3 = tk.Label(self.master, text="N/A", **code_style)
        self.code_line3.pack(fill="x", padx=20, pady=2)

        # Added Fourth Code Line (CSV Column 3)
        self.code_line4 = tk.Label(self.master, text="N/A", **code_style)
        self.code_line4.pack(fill="x", padx=20, pady=2)

        # Added Fifth Code Line (CSV Column 4)
        self.code_line5 = tk.Label(self.master, text="N/A", **code_style)
        self.code_line5.pack(fill="x", padx=20, pady=2)

        # --- BUTTON: ADD GEOGUESS ---
        self.btn_add = tk.Button(self.master, text="Add a Geoguess", bg="#27ae60", fg="white", font=("Arial", 10, "bold"), command=self.add_geoguess)
        self.btn_add.pack(pady=15)

        self.pm = None
        self.base_address = 0
        self.current_ebp = "" # Variable to store the clean EBP string
        self.update_data()

    def create_stat_row(self, frame, label, row, style):
        tk.Label(frame, text=label, bg='#2c3e50', fg='#ecf0f1', font=("Arial", 9)).grid(row=row, column=0, sticky="e", padx=5)
        l = tk.Label(frame, text="0.0", **style)
        l.grid(row=row, column=1, sticky="w")
        return l

    def load_csv(self):
        csv_path = os.path.join("data", "modeldata.csv")
        if not os.path.exists(csv_path):
            return
            
        encodings_to_try = ['utf-8-sig', 'cp1252', 'latin1']
        for enc in encodings_to_try:
            try:
                with open(csv_path, mode='r', encoding=enc) as f:
                    reader = csv.reader(f)
                    self.model_data = {} 
                    for row in reader:
                        if len(row) >= 2:
                            col2 = row[1]
                            col3 = row[2] if len(row) >= 3 else "N/A"
                            col4 = row[3] if len(row) >= 4 else "N/A" # New Column 4 Logic
                            self.model_data[row[0]] = (col2, col3, col4)
                break 
            except Exception:
                continue

    def setup_memory(self):
        try:
            self.pm = pymem.Pymem("FFX.exe")
            self.base_address = pymem.process.module_from_name(self.pm.process_handle, "FFX.exe").lpBaseOfDll
        except:
            self.pm = None

    def float_to_le_hex(self, val):
        try:
            val_int = int(val) & 0xFFFF
            packed = struct.pack('<H', val_int)
            return f"AE{packed[0]:02X}{packed[1]:02X}"
        except:
            return "AE0000"


    def add_geoguess(self):
        if not self.current_ebp or self.current_ebp == "0.0":
            self.flash_button_feedback("No EBP Loaded!", "#e74c3c")
            return

        # ==========================================
        # NEW: Check for Tab 2 Text before proceeding
        # ==========================================
        hex_data = self.text_converter_app.output_text.get("1.0", "end-1c").strip()
        if not hex_data:
            self.flash_button_feedback("No Text in Tab 2!", "#e67e22")
            messagebox.showwarning("Warning", "You must enter and generate text on Tab 2 before adding a GeoGuess!")
            return
        # ==========================================

        data_dir = "data"
        output_dir = "outputs"
        
        # Ensure outputs directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        base_name, _ = os.path.splitext(self.current_ebp)
        target_bin = base_name + ".bin"

        final_ebp_path = ""
        final_bin_path = ""

        # --- STEP 1: LOCATE FILES ---
        for search_root in [output_dir, data_dir]:
            ebp_found_here = ""
            bin_found_here = ""
            
            for root, dirs, files in os.walk(search_root):
                if not ebp_found_here and self.current_ebp in files:
                    ebp_found_here = os.path.join(root, self.current_ebp)
                if not bin_found_here and target_bin in files:
                    bin_found_here = os.path.join(root, target_bin)
                
                if ebp_found_here and bin_found_here:
                    break
            
            if ebp_found_here and bin_found_here:
                if search_root == data_dir:
                    try:
                        rel_ebp = os.path.relpath(ebp_found_here, data_dir)
                        rel_bin = os.path.relpath(bin_found_here, data_dir)
                        
                        final_ebp_path = os.path.join(output_dir, rel_ebp)
                        final_bin_path = os.path.join(output_dir, rel_bin)
                        
                        os.makedirs(os.path.dirname(final_ebp_path), exist_ok=True)
                        os.makedirs(os.path.dirname(final_bin_path), exist_ok=True)
                        
                        shutil.copy2(ebp_found_here, final_ebp_path)
                        shutil.copy2(bin_found_here, final_bin_path)
                        print(f"Copied new files to outputs: {rel_ebp}")
                    except Exception as e:
                        print(f"Copy Error: {e}")
                        self.flash_button_feedback("Copy Error!", "#e74c3c")
                        return
                else:
                    final_ebp_path = ebp_found_here
                    final_bin_path = bin_found_here
                    print(f"Using existing files in outputs: {final_ebp_path}")
                
                break

        # --- STEP 2: PERFORM OPERATIONS ---
        if not final_ebp_path or not final_bin_path:
            self.flash_button_feedback("Files Not Found!", "#e67e22")
            return

        # 1. Add Worker
        success = add_geoguess_worker(final_ebp_path)
        
        new_index = None 
        
        # 2. Append to BIN
        if success:
            try:
                if hex_data:
                    hex_data += " 00"
                    new_index = append_geoguesser_data(final_bin_path, hex_data)
                    print(f"Success: New data added at index {new_index}")
            except Exception as e:
                print(f"BIN Error: {e}")
                success = False

        # 3. Patch EBP Bytes
        if success:
            success = self.patch_ebp_file(final_ebp_path, new_index)
            if success:
                self.flash_button_feedback("Added Successfully!", "#27ae60")
            else:
                self.flash_button_feedback("Patch Failed!", "#e74c3c")
        else:
            self.flash_button_feedback("Operation Failed!", "#e74c3c")

    def patch_ebp_file(self, filepath, new_index=None):
        try:
            with open(filepath, "rb") as f:
                content = f.read()

            def to_bytes(hex_str):
                clean_hex = hex_str.replace(" ", "").strip()
                try:
                    return bytes.fromhex(clean_hex)
                except ValueError:
                    print(f"Warning: Could not convert '{hex_str}' to bytes.")
                    return b""

            # 1. Grab strings directly from the UI labels
            line1_bytes = to_bytes(self.code_line1.cget("text"))
            line2_bytes = to_bytes(self.code_line2.cget("text"))
            line3_bytes = to_bytes(self.code_line3.cget("text"))
            line4_bytes = to_bytes(self.code_line4.cget("text"))
            line5_bytes = to_bytes(self.code_line5.cget("text")) # New Line 5 Bytes

            # 2. Define our Search -> Replace mappings
            replacements = [
                (bytes.fromhex("AE5656D80100"), line1_bytes),
                (bytes.fromhex("AE9191AE9191AE9191D81300"), line2_bytes),
                (bytes.fromhex("61616171717181818191"), line3_bytes),
                (bytes.fromhex("888888999999222222"), line4_bytes),
                (bytes.fromhex("406040938271"), line5_bytes) # New Replacement Mapping
            ]

            # ---> NEW DYNAMIC INDEX REPLACEMENT <---
            if new_index is not None:
                search_target = bytes.fromhex("909080807070606050")
                index_bytes = struct.pack('<H', int(new_index))
                replace_target = bytes.fromhex("AE0100AE") + index_bytes + bytes.fromhex("D86400")
                replacements.append((search_target, replace_target))
                print(f"Replacing index bytes with: {replace_target.hex().upper()}")
            # ---------------------------------------

            # 3. Apply the replacements
            for search_bytes, replace_bytes in replacements:
                if replace_bytes: 
                    content = content.replace(search_bytes, replace_bytes)

            with open(filepath, "wb") as f:
                f.write(content)
                
            print(f"Success: Patched .ebp file at {filepath}")
            return True

        except Exception as e:
            print(f"Error patching .ebp file: {e}")
            return False

    def flash_button_feedback(self, text, color):
        self.btn_add.config(text=text, bg=color)
        self.master.after(2000, lambda: self.btn_add.config(text="Add a Geoguess", bg="#27ae60"))

    def update_data(self):
        if not self.pm:
            self.setup_memory()

        if self.pm:
            try:
                # 1. Read EBP
                raw_ebp = self.pm.read_string(self.base_address + 0x1FCBC8D, 12)
                self.current_ebp = raw_ebp.split('\x00', 1)[0].strip()
                self.lbl_ebp.config(text=self.current_ebp)

                # 2. Read XYZ
                x = self.pm.read_float(self.base_address + 0xF25D78)
                y = self.pm.read_float(self.base_address + 0xF25D7C)
                z = self.pm.read_float(self.base_address + 0xF25D80)
                
                self.lbl_x.config(text=f"{x:.3f}")
                self.lbl_y.config(text=f"{y:.3f}")
                self.lbl_z.config(text=f"{z:.3f}")

                # 3. Read Rotation
                rot_ptr = self.pm.read_int(self.base_address + 0xEA2280)
                rot = self.pm.read_float(rot_ptr + 0x168)
                self.lbl_rot.config(text=f"{rot:.3f}")

                # 4. Update CODES
                current_model = self.model_var.get()
                model_info = self.model_data.get(current_model, ("N/A", "N/A", "N/A")) # Updated Tuple Default

                self.code_line1.config(text=model_info[0])

                hex_x = self.float_to_le_hex(x)
                hex_y = self.float_to_le_hex(y)
                hex_z = self.float_to_le_hex(z)
                self.code_line2.config(text=f"{hex_x} {hex_y} {hex_z} D81300")

                hex_rot = self.float_to_le_hex(rot * 100)
                self.code_line3.config(text=f"{hex_rot} AE6400 17 D89500")

                self.code_line4.config(text=model_info[1])
                self.code_line5.config(text=model_info[2]) # New Line Update

            except Exception:
                self.pm = None

        self.master.after(100, self.update_data)


# ==========================================
# TAB 2: Custom Hex Text Encoder (Code 2)
# ==========================================
class TextCodeConverter:
    def __init__(self, parent):
        self.parent = parent
        
        self.pad_x = 10
        self.pad_y = 10
        
        # 1. THE DATA MAPPING
        self.char_map = {
            '0': '30', '1': '31', '2': '32', '3': '33', '4': '34', '5': '35', '6': '36', '7': '37', '8': '38', '9': '39',
            ' ': '3A', '!': '3B', '"': '3C', '#': '3D', '$': '3E', '%': '3F', '&': '40', "'": '41', '(': '42', ')': '43',
            '*': '44', '+': '45', ',': '46', '-': '47', '.': '48', '/': '49', ':': '4A', ';': '4B', '<': '4C', '=': '4D',
            '>': '4E', '?': '4F', '@': '00', 
            'A': '50', 'B': '51', 'C': '52', 'D': '53', 'E': '54', 'F': '55', 'G': '56', 'H': '57', 'I': '58', 'J': '59',
            'K': '5A', 'L': '5B', 'M': '5C', 'N': '5D', 'O': '5E', 'P': '5F', 'Q': '60', 'R': '61', 'S': '62', 'T': '63',
            'U': '64', 'V': '65', 'W': '66', 'X': '67', 'Y': '68', 'Z': '69',
            '[': '6A', '\\': '6B', ']': '6C', '^': '6D', '_': '6E', '‘': '6F',
            'a': '70', 'b': '71', 'c': '72', 'd': '73', 'e': '74', 'f': '75', 'g': '76', 'h': '77', 'i': '78', 'j': '79',
            'k': '7A', 'l': '7B', 'm': '7C', 'n': '7D', 'o': '7E', 'p': '7F', 'q': '80', 'r': '81', 's': '82', 't': '83',
            'u': '84', 'v': '85', 'w': '86', 'x': '87', 'y': '88', 'z': '89',
            '{': '8A', '|': '8B', '}': '8C', '~': '8D', '·': '8E', '【': '8F', '】': '90',
            '♪': '91', '♥': '92', 'Œ': '93', '“': '94', '”': '95', '—': '96', 'œ': '97', '¡': '98',
            '↑': '99', '↓': '9A', '←': '9B', '→': '9C', '¨': '9D', '«': '9E', '°': '9F', 
            '»': 'A1', '¿': 'A2',
            'À': 'A3', 'Á': 'A4', 'Â': 'A5', 'Ä': 'A6', 'Ç': 'A7', 'È': 'A8', 'É': 'A9', 'Ê': 'AA', 'Ë': 'AB',
            'Ì': 'AC', 'Í': 'AD', 'Î': 'AE', 'Ï': 'AF', 'Ñ': 'B0', 'Ò': 'B1', 'Ó': 'B2', 'Ô': 'B3', 'Ö': 'B4',
            'Ù': 'B5', 'Ú': 'B6', 'Û': 'B7', 'Ü': 'B8', 'ß': 'B9',
            'à': 'BA', 'á': 'BB', 'â': 'BC', 'ä': 'BD', 'ç': 'BE', 'è': 'BF', 'é': 'C0', 'ê': 'C1', 'ë': 'C2',
            'ì': 'C3', 'í': 'C4', 'î': 'C5', 'ï': 'C6', 'ñ': 'C7', 'ò': 'C8', 'ó': 'C9', 'ô': 'CA', 'ö': 'CB',
            'ù': 'CC', 'ú': 'CD', 'û': 'CE', 'ü': 'CF',
            'ƒ': 'D1', '„': 'D2', '…': 'D3', '’': 'D5', '™': 'D9', '›': 'DB', '§': 'DC', '©': 'DD', 'ᵃ': 'DE',
            '®': 'DF', '±': 'E0', '²': 'E1', '³': 'E2', '¼': 'E3', '½': 'E4', '¾': 'E5', '×': 'E6', '÷': 'E7',
            '‹': 'E8', '⋯': 'E9', 'ă': 'EB', '★': 'EC', '☆': 'ED', '■': 'EE', '∞': 'EF', '□': 'F0', '℠': 'F1'
        }
        
        # 1.5 NEW COLOR TAG MAPPING
        self.color_map = {
            '{WHITE}': '0A 41', '{YELLOW}': '0A 43', '{GREY}': '0A 52', '{BLUE}': '0A 88',
            '{RED}': '0A 94', '{PINK}': '0A 97', '{PURPLE}': '0A A1', '{CYAN}': '0A B1'
        }
        
        # 2. SETUP UI
        self.setup_ui()

    def setup_ui(self):
        # --- Input Section ---
        input_frame = ttk.LabelFrame(self.parent, text="Type Text Here", padding=self.pad_x)
        input_frame.pack(fill="both", expand=True, padx=self.pad_x, pady=self.pad_y)

        self.input_text = tk.Text(input_frame, height=8, font=("Consolas", 12))
        self.input_text.pack(fill="both", expand=True)
        self.input_text.bind("<KeyRelease>", self.convert_text_to_code)

        # --- Color Buttons Section ---
        color_frame = ttk.LabelFrame(self.parent, text="Color Tags (Click to Insert)", padding=self.pad_x)
        color_frame.pack(fill="x", padx=self.pad_x, pady=5)
        
        colors = ['{WHITE}', '{YELLOW}', '{GREY}', '{BLUE}', '{RED}', '{PINK}', '{PURPLE}', '{CYAN}']
        for i, color_tag in enumerate(colors):
            btn_text = color_tag.replace('{', '').replace('}', '') 
            b = ttk.Button(color_frame, text=btn_text, width=7, command=lambda c=color_tag: self.insert_char(c))
            b.grid(row=0, column=i, padx=2, pady=2)

        # --- Special Characters Section ---
        btn_frame = ttk.LabelFrame(self.parent, text="Special Characters (Click to Insert)", padding=self.pad_x)
        btn_frame.pack(fill="x", padx=self.pad_x, pady=5)

        special_chars = ['★', '♥','☆','■', '♪', '∞', '™', '©', '®', '↑', '↓', '←', '→']
        for i, char in enumerate(special_chars):
            b = ttk.Button(btn_frame, text=char, width=4, command=lambda c=char: self.insert_char(c))
            b.grid(row=0, column=i, padx=2, pady=2)

        # --- Output Section ---
        output_frame = ttk.LabelFrame(self.parent, text="Generated Code", padding=self.pad_x)
        output_frame.pack(fill="both", expand=True, padx=self.pad_x, pady=self.pad_y)

        self.output_text = tk.Text(output_frame, height=8, state="disabled", font=("Consolas", 12), bg="#f0f0f0")
        self.output_text.pack(fill="both", expand=True)

        # --- Control Buttons ---
        ctrl_frame = ttk.Frame(self.parent)
        ctrl_frame.pack(fill="x", padx=self.pad_x, pady=self.pad_y)

        ttk.Button(ctrl_frame, text="Clear All", command=self.clear_all).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="Copy Code to Clipboard", command=self.copy_to_clipboard).pack(side="right", padx=5)

    def convert_text_to_code(self, event=None):
        content = self.input_text.get("1.0", "end-1c")
        code_output = []
        
        tokens = re.findall(r'\{[A-Z]+\}|.', content, re.DOTALL)
        
        for token in tokens:
            if token in self.color_map:
                code_output.append(self.color_map[token])
            elif token == '\n':
                code_output.append('03\n') 
            else:
                code = self.char_map.get(token)
                if code:
                    code_output.append(code)
                else:
                    code_output.append(f"[?{token}?]")

        final_string = " ".join(code_output)
        final_string = final_string.replace("03\n ", "03\n")

        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", final_string)
        self.output_text.config(state="disabled")

    def insert_char(self, char):
        self.input_text.insert("insert", char)
        self.convert_text_to_code()

    def clear_all(self):
        self.input_text.delete("1.0", "end")
        self.convert_text_to_code()

    def copy_to_clipboard(self):
        code = self.output_text.get("1.0", "end-1c")
        self.parent.clipboard_clear()
        self.parent.clipboard_append(code)
        messagebox.showinfo("Success", "Code copied to clipboard!")


# ==========================================
# MAIN APPLICATION ROOT
# ==========================================
class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FFX Modding Suite")
        self.root.geometry("750x700")  # Sized to accommodate both comfortably

        # Apply general theme
        style = ttk.Style()
        style.theme_use('clam')

        # Initialize the Notebook (Tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True)

        # Create frames for each tab
        self.tab1 = tk.Frame(self.notebook, bg='#2c3e50')
        self.tab2 = tk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.tab1, text="GeoGuesser Tool")
        self.notebook.add(self.tab2, text="Dialogue Editor")

        # Load the applications into their respective tabs
        self.app1 = FFXMonitor(self.tab1)
        self.app2 = TextCodeConverter(self.tab2)        
        self.app1.text_converter_app = self.app2


if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
