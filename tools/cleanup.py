import os
import glob
import shutil

def cleanup_workspace():
    # Get the current working directory (root folder where .bat was run)
    cwd = os.getcwd()
    print(f"Cleaning workspace in: {cwd}")

    # 1. Delete files matching *.ffindex and *.json
    file_extensions = ['*.ffindex', '*.json']
    for ext in file_extensions:
        files = glob.glob(os.path.join(cwd, ext))
        for file_path in files:
            try:
                os.remove(file_path)
                print(f"Deleted file: {os.path.basename(file_path)}")
            except OSError as e:
                print(f"Error deleting {os.path.basename(file_path)}: {e}")

    # 2. Delete 'logs' directory
    logs_dir = os.path.join(cwd, 'logs')
    if os.path.exists(logs_dir) and os.path.isdir(logs_dir):
        try:
            shutil.rmtree(logs_dir)
            print("Deleted folder: logs")
        except OSError as e:
            print(f"Error deleting logs folder: {e}")

    # 3. Delete Temp Folders based on naming convention
    # Looks for folders ending in "-source", "-source_scenedetect.scene-detection.tmp"
    # OR folders that start with a period (e.g., .temp, .cache)
    
    # Iterate over all items in the current directory
    for item in os.listdir(cwd):
        item_path = os.path.join(cwd, item)
        
        if os.path.isdir(item_path):
            # Check for the specific temp folder suffixes or prefix
            if (item.endswith("-source") or 
                item.endswith("-source_scenedetect.scene-detection.tmp") or 
                item.startswith(".")):
                
                try:
                    shutil.rmtree(item_path)
                    print(f"Deleted temp folder: {item}")
                except OSError as e:
                    print(f"Error deleting folder {item}: {e}")

if __name__ == "__main__":
    cleanup_workspace()