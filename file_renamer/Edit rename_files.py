import logging

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def rename_file(old_name, new_name):
    try:
        import os
        os.rename(old_name, new_name)
        logging.info(f"Successfully renamed '{old_name}' to '{new_name}'.")
    except FileNotFoundError:
        logging.error(f"The file '{old_name}' does not exist.")
    except FileExistsError:
        logging.error(f"The file '{new_name}' already exists.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

# Example usage
if __name__ == "__main__":
    rename_file("example.txt", "new_example.txt")