import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def rename_files_in_directory(directory):
    for filename in os.listdir(directory):
        old_file = os.path.join(directory, filename)
        if os.path.isdir(old_file): 
            continue
        if not os.path.isfile(old_file):
            logging.warning(f"Skipping non-file item: {old_file}")
            continue
        if not filename.startswith('renamed_'):
            new_file = os.path.join(directory, f"renamed_{filename}")
            os.rename(old_file, new_file)
            print(f"Renamed {old_file} to {new_file}")
            logging.info(f"Renamed '{old_file}' to '{new_file}'")
        else:
            logging.info(f"File already renamed: {old_file}")
if __name__ == "__main__":
    if len(sys.argv) != 2:
        logging.error("Usage: python rename_files.py <directory>")
        sys.exit(1)
    
    target_directory = sys.argv[1]
    if not os.path.isdir(target_directory):
        logging.error(f"Error: {target_directory} is not a valid directory")
        sys.exit(1)
    
    # Update the routing logic for self-improvement requests
    if "self_improvement" in target_directory:
        target_directory = os.path.join(target_directory, "jarvis_app_files")
    
    rename_files_in_directory(target_directory)
    logging.info("Files renamed successfully")