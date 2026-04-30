import os
import sys
import datetime

def rename_files_in_directory(directory):
    try:
        # List all files in the directory
        files = os.listdir(directory)
        
        for filename in files:
            # Construct full file path
            old_file_path = os.path.join(directory, filename)
            
            # Check if it's a file and not a directory
            if os.path.isfile(old_file_path):
                # Create new filename with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                new_filename = f"{timestamp}_{filename}"
                new_file_path = os.path.join(directory, new_filename)
                
                # Rename the file
                os.rename(old_file_path, new_file_path)
                print(f"Renamed '{old_file_path}' to '{new_file_path}'")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python rename_files.py <directory>")
    else:
        directory = sys.argv[1]
        rename_files_in_directory(directory)