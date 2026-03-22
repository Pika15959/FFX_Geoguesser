import struct
import os

def append_geoguesser_data(file_path: str, hex_bytes_str: str) -> int:
    # 1. Parse the hex string into actual bytes
    new_data = bytes.fromhex(hex_bytes_str.replace(' ', ''))

    # 2. Read the entire original file
    with open(file_path, 'rb') as f:
        file_data = f.read()

    if not file_data:
        raise ValueError("File is empty.")

    # 3. Read the first pointer to determine where the pointer section ends.
    first_ptr_val = struct.unpack('<I', file_data[0:4])[0]
    
    # 0x00800000 mask for the "80" flag in the 3rd byte
    ptr_flag_mask = 0x00800000
    
    # Strip the "80" flag to get the true integer offset 
    data_start_offset = first_ptr_val & ~ptr_flag_mask

    # Calculate the index of the new pointer group we are about to add
    # Each duplicate pointer pair is 8 bytes long
    new_pointer_index = data_start_offset // 8

    # 4. Split the file into pointers and data
    pointer_section = file_data[:data_start_offset]
    data_section = file_data[data_start_offset:]

    # 5. Shift all existing pointers up by 8
    updated_pointers = bytearray()
    
    for i in range(0, len(pointer_section), 4):
        ptr_val = struct.unpack('<I', pointer_section[i:i+4])[0]
        
        flag = ptr_val & ptr_flag_mask
        pure_ptr = ptr_val & ~ptr_flag_mask
        
        # Shift up by 8
        new_pure_ptr = pure_ptr + 8
        
        new_ptr_val = new_pure_ptr | flag
        updated_pointers.extend(struct.pack('<I', new_ptr_val))

    # 6. Create the new 8-byte pointer for the appended data
    new_ptr_offset = len(file_data) + 8
    new_ptr_entry = struct.pack('<I', new_ptr_offset) * 2

    # 7. Reconstruct the file
    final_file_data = updated_pointers + new_ptr_entry + data_section + new_data

    # 8. Write the modified payload back to the file
    with open(file_path, 'wb') as f:
        f.write(final_file_data)
        
    print(f"Success! Inserted new pointer at index {new_pointer_index} and appended {len(new_data)} bytes to {os.path.basename(file_path)}.")
    
    # Return the 0-based index of the newly added pointer group
    return new_pointer_index

# Example usage:
# new_index = append_geoguesser_data(r"C:\Users\1\Desktop\Geoguesser\klyt0100.bin", "00 03 58 3A 78")
# print(f"The new data was added at index: {new_index}")
