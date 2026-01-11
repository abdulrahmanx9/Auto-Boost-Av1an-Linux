import os
import shutil


def cleanup_workspace():
    # Directories to scan for trash
    scan_dirs = [".", "Input", "Output"]

    # Extensions to delete (Files)
    extensions = [
        ".ffindex",
        ".lwi",
        ".json",
        ".log",
        ".temp",
        ".vpy",
        ".stats",
        ".mbtree",
        ".zone",
        ".csv",
    ]

    print("Cleaning up workspace...")

    for d in scan_dirs:
        if not os.path.exists(d):
            continue

        for item in os.listdir(d):
            item_path = os.path.join(d, item)

            # 1. DELETE FILES
            if os.path.isfile(item_path):
                for ext in extensions:
                    if item.lower().endswith(ext):
                        try:
                            # Avoid deleting scenes json if needed?
                            # Usually cleanup removes json scenes. User accepted this behavior.
                            os.remove(item_path)
                            print(f"Deleted: {item_path}")
                        except:
                            pass
                        break

            # 2. DELETE DIRECTORIES (Temp folders)
            elif os.path.isdir(item_path):
                # Whitelist: Critical system/project folders to never touch
                if item in [
                    ".git",
                    ".vscode",
                    ".idea",
                    "Input",
                    "Output",
                    "tools",
                    "VapourSynth",
                    "__pycache__",
                    "venv",
                ]:
                    continue

                # Condition: Starts with "." (Hidden temp) OR ends with ".tmp" OR ends with "-source"
                if (
                    item.startswith(".")
                    or item.endswith(".tmp")
                    or item.endswith("-source")
                ):
                    try:
                        shutil.rmtree(item_path)
                        print(f"Deleted temp dir: {item_path}")
                    except:
                        pass


if __name__ == "__main__":
    cleanup_workspace()
