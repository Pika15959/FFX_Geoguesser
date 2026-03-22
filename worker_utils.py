import os
import json
import struct
import subprocess
from data import ebp_patcher

# Constants from original logic
OBJECT_TOTAL_SIZE = 500
FIELDS = ["INIT", "MAIN", "TALK", "SCOUT", "CROSS", "TOUCH", "E06", "E07"]

def add_geoguess_worker(ebp_path):
    """
    Automates the appending of a worker to an EBP file based on 
    specifications in data/geoguess.json.
    """
    if not os.path.exists(ebp_path):
        print(f"Error: Target file {ebp_path} does not exist.")
        return False

    # 1. Load the specifications from geoguess.json
    json_path = os.path.join(os.path.dirname(__file__), "geoguess.json")
    try:
        with open(json_path, 'r') as f:
            data_store = json.load(f)
    except Exception as e:
        print(f"Error loading geoguess.json: {e}")
        return False

    # 2. Run the external patcher logic (Clone/Source ID)
    # Replicates: ebp_patcher.patch_ebp(k, n_clones=1, q_source_id=1)
    try:
        ebp_patcher.patch_ebp(ebp_path, n_clones=1, q_source_id=1)
    except Exception as e:
        print(f"ebp_patcher failed: {e}")
        return False

    # 3. Calculate File Pointers
    try:
        file_size = os.path.getsize(ebp_path)
        entry_val = file_size - 64
        jump_val = entry_val + 0x20
        
        # Determine code_start_val from offset 0x70
        with open(ebp_path, "rb") as f:
            f.seek(0x70)
            data = f.read(4)
            if len(data) < 4:
                return False
            val_at_70 = int.from_bytes(data, 'little')
            code_start_val = val_at_70 + 0x40

        # Update file pointers at the end of the file
        with open(ebp_path, "r+b") as f:
            f.seek(-20, 2) 
            f.write(entry_val.to_bytes(4, 'little'))
            f.write(jump_val.to_bytes(4, 'little'))



        # 4. Generate the Byte Object
        final_object = _generate_buffer(data_store, code_start_val, entry_val)
        
        if final_object:
            # Read the file that Code 3 just finished updating
            with open(ebp_path, "rb") as f:
                content = f.read()
                
            # Combine the existing file with the new 500-byte buffer
            full_content = bytearray(content + final_object)
            
            # Read from 0x76 to get the NEW minimum ID of the shifted workers
            new_nonsub_workers = int.from_bytes(full_content[0x76:0x78], 'little')
            
            # Use EXACTLY this value (removed the - 1)
            new_min_code = b'\xB3' + new_nonsub_workers.to_bytes(2, 'little')
            
            target_bytes = bytes.fromhex("987654")
            
            # Perform the global replacement
            if target_bytes in full_content:
                full_content = full_content.replace(target_bytes, new_min_code)
                print(f"Replaced {target_bytes.hex()} with {new_min_code.hex()}")
            else:
                print("Warning: 987654 was not found in the file or buffer.")
                
            # Overwrite the file with the final patched bytes
            with open(ebp_path, "wb") as f:
                f.write(full_content)
                
            print(f"Successfully patched: {os.path.basename(ebp_path)}")
            return True
            
    except Exception as e:
        print(f"File analysis/append failed: {e}")
        return False

def _generate_buffer(data_store, base_offset, custom_entry_ptr):
    """Internal helper to calculate pointers and build the 500-byte buffer."""
    def calc_ptr(rel_pos):
        return (rel_pos + 0x50 + custom_entry_ptr + 0x40 - base_offset) & 0xFFFFFFFF

    entry_vals = []
    jump_vals = {f"j{i:02X}": 0 for i in range(12)}
    all_code_bytes = bytearray()
    current_rel_ptr = 0

    for field in FIELDS:
        entry_vals.append(calc_ptr(current_rel_ptr))
        rows = data_store.get(field, [])
        for row in rows:
            tag = row.get('c1')
            if tag in jump_vals and jump_vals[tag] == 0:
                jump_vals[tag] = calc_ptr(current_rel_ptr)
            
            txt = row.get('text', "").replace(" ", "").strip()
            if txt:
                all_code_bytes.extend(bytes.fromhex(txt))
                current_rel_ptr += (len(txt) // 2)

    # Build the 500-byte block
    buffer = bytearray(b'\x3C' * OBJECT_TOTAL_SIZE)
    
    # Pack Entry Pointers (0x00)
    for i, val in enumerate(entry_vals):
        buffer[i*4 : i*4+4] = struct.pack('<I', val)
    
    # Pack Jump Pointers (0x20)
    for i in range(12):
        val = jump_vals[f"j{i:02X}"]
        buffer[32 + (i*4) : 32 + (i*4)+4] = struct.pack('<I', val)

    # Pack Code (0x50)
    CODE_START = 80
    FOOTER_START = OBJECT_TOTAL_SIZE - 16
    if len(all_code_bytes) > (FOOTER_START - CODE_START):
        print("Error: Code too long for buffer.")
        return None
    buffer[CODE_START : CODE_START + len(all_code_bytes)] = all_code_bytes

    # Footer (Anchor + Signature)
    buffer[FOOTER_START : FOOTER_START+4] = buffer[0:4]
    buffer[FOOTER_START+4 : FOOTER_START+16] = bytes.fromhex("81 82 83 80 71 72 73 70 61 62 63 60")
    
    return buffer
