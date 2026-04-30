import os
import sys

def rename_files_in_directory(directory):
    try:
        for filename in os.listdir(directory):
            old_file = os.path.join(directory, filename)
            if os.path.isfile(old_file):
                # Example renaming logic: add a prefix "new_" to each file
                new_filename = f"new_{filename}"
                new_file = os.path.join(directory, new_filename)
                os.rename(old_file, new_file)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python rename_files.py <directory>")
        sys.exit(1)

    target_directory = sys.argv[1]
    rename_files_in_directory(target_directory)