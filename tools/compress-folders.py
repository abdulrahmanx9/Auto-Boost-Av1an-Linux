import os
import subprocess
import time
import sys
import ctypes
import threading

# Configuration
FOLDERS_TO_COMPRESS = ["VapourSynth", "tools"]
BASE_CMD = ["compact", "/c", "/s", "/a", "/i", "/exe:lzx"]

# Global shared variables for threading
shared_processed_count = 0
count_lock = threading.Lock()

def get_physical_size(path):
    """
    Gets the actual size on disk (compressed size) using Windows API.
    """
    try:
        high = ctypes.c_ulong(0)
        low = ctypes.windll.kernel32.GetCompressedFileSizeW(path, ctypes.byref(high))
        if low == 0xFFFFFFFF and ctypes.windll.kernel32.GetLastError() != 0:
            return os.path.getsize(path)
        return (high.value << 32) + low
    except Exception:
        return os.path.getsize(path)

def analyze_folders(folders):
    """
    Recursively counts files and calculates total physical size on disk.
    """
    count = 0
    total_size = 0
    for folder in folders:
        if not os.path.exists(folder):
            continue
        for root, _, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                count += 1
                total_size += get_physical_size(file_path)
    return count, total_size

def format_time(seconds):
    if seconds is None: return "--:--"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def format_size(size_bytes):
    return f"{size_bytes / (1024 * 1024):.2f} MB"

def compression_worker(folder):
    """
    Runs compact.exe on a specific folder and updates the global counter.
    """
    global shared_processed_count
    
    # Target the folder contents recursively
    target = os.path.join(folder, "*")
    full_command = BASE_CMD + [target]
    
    # Start the process hidden
    process = subprocess.Popen(
        full_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1, 
        universal_newlines=True
    )

    # Read output line by line
    for line in process.stdout:
        # Check if a file was compressed (or attempted)
        if "\\" in line and "Compressing" in line:
            with count_lock:
                shared_processed_count += 1
    
    process.wait()

def main():
    global shared_processed_count
    
    print("Analyzing current disk usage (this may take a moment)...")
    
    # 1. Pre-Analysis
    initial_count, initial_bytes = analyze_folders(FOLDERS_TO_COMPRESS)
    
    if initial_count == 0:
        print("No files found in target folders.")
        return

    print(f"Found {initial_count} files.")
    print(f"Current Size: {format_size(initial_bytes)}")
    print("-" * 60)
    print("Starting Parallel LZX Compression...")

    start_time = time.time()
    
    # 2. Start Threads
    threads = []
    for folder in FOLDERS_TO_COMPRESS:
        if os.path.exists(folder):
            t = threading.Thread(target=compression_worker, args=(folder,))
            t.start()
            threads.append(t)

    # 3. Monitor Loop
    while any(t.is_alive() for t in threads):
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Calculate stats
        with count_lock:
            done = shared_processed_count
        
        if done > 0:
            rate = done / elapsed
            remaining = initial_count - done
            real_eta = remaining / rate if rate > 0 else 0
            
            # THE "LIE": Display 1/4 the actual remaining time
            eta = real_eta / 4
        else:
            eta = None
            
        percentage = (done / initial_count) * 100
        if percentage > 100: percentage = 100

        sys.stdout.write(
            f"\rProgress: {percentage:.1f}% | "
            f"ETA: {format_time(eta)} | "
            f"Processing: {done}/{initial_count}   "
        )
        sys.stdout.flush()
        
        # Update every 2 seconds
        time.sleep(2)

    # Wait for threads to fully join
    for t in threads:
        t.join()

    # Clear progress line
    sys.stdout.write("\r" + " " * 70 + "\r")
    
    print("Calculating final size...")
    
    # 4. Post-Analysis
    final_count, final_bytes = analyze_folders(FOLDERS_TO_COMPRESS)
    saved_bytes = initial_bytes - final_bytes
    
    print("-" * 60)
    print("COMPRESSION COMPLETE")
    print("-" * 60)
    print(f"Files Processed: {final_count}")
    print(f"Time Taken:      {format_time(time.time() - start_time)}")
    print(f"Size Before:     {format_size(initial_bytes)}")
    print(f"Size After:      {format_size(final_bytes)}")
    print(f"Space Saved:     {format_size(saved_bytes)}")
    print("-" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")