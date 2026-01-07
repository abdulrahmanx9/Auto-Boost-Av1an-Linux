import os
import sys
import time
import subprocess
import threading
import queue
import json
import re
from pathlib import Path
import psutil  # Required

# ================= CONFIGURATION =================
# Detect CPU threads and leave 1 free for system responsiveness
TOTAL_THREADS = psutil.cpu_count(logical=True)
PARALLELISM = max(1, TOTAL_THREADS - 1)

IGNORE_EXTS = set() # Add extensions to ignore if needed, e.g., {'.wav'}
# =================================================

# Global Queues and Locks
slot_status = ["Idle"] * PARALLELISM
files_queue = queue.Queue()
stop_display = threading.Event()

# Regex for FFMPEG progress parsing
re_ffmpeg = re.compile(r"time=\s*(\S+).*bitrate=\s*(\S+).*speed=\s*(\S+)")

# --- PATH SETUP (Relative to this script) ---
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent 

FFMPEG_EXE = ROOT_DIR / "tools" / "av1an" / "ffmpeg.exe"
OPUSENC_EXE = ROOT_DIR / "tools" / "opus" / "opusenc.exe"
MKV_DIR = ROOT_DIR / "tools" / "MKVToolNix"
MKVMERGE_EXE = MKV_DIR / "mkvmerge.exe"
MKVEXTRACT_EXE = MKV_DIR / "mkvextract.exe"

# Add MKVToolNix to PATH
os.environ["PATH"] += os.pathsep + str(MKV_DIR)

# --- HELPER FUNCTIONS ---

def run_command(cmd, capture_output=False):
    """Run a subprocess command safely without bleeding stderr to console."""
    try:
        cmd_str = [str(c) for c in cmd]
        if capture_output:
            # Capture both stdout and stderr to prevent red text leaks
            return subprocess.check_output(cmd_str, stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
        
        # Suppress all output for standard runs
        subprocess.run(cmd_str, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def get_track_title_string(lang_code):
    """Maps ISO 639-2 codes to Display Names."""
    lookup = {
        "jpn": "Japanese", "eng": "English", "chi": "Chinese", "zho": "Chinese",
        "ger": "German", "deu": "German", "fra": "French", "fre": "French",
        "ita": "Italian", "spa": "Spanish", "kor": "Korean", "rus": "Russian",
        "por": "Portuguese", "hin": "Hindi", "und": ""
    }
    return lookup.get(lang_code.lower(), "")

# --- PHASE 1: EXTRACTION ---

def get_mkv_tracks(mkv_path):
    cmd = [MKVMERGE_EXE, '-J', str(mkv_path)]
    try:
        res = run_command(cmd, capture_output=True)
        data = json.loads(res)
        return [t for t in data.get('tracks', []) if t['type'] == 'audio']
    except:
        return []

def extract_tracks():
    mkvs = list(Path('.').glob('*.mkv'))
    if not mkvs:
        print("No .mkv files found in the current directory.")
        return []

    print(f"Found {len(mkvs)} MKV files. Analyzing tracks with {PARALLELISM} parallel workers...")
    extracted_files = []
    
    for mkv in mkvs:
        tracks = get_mkv_tracks(mkv)
        extract_cmds = []
        
        for track in tracks:
            tid = track['id']
            lang = track['properties'].get('language', 'und')
            
            # Determine extension
            codec_id = track['properties'].get('codec_id', '')
            codec_name = track.get('codec', '') 
            full_codec_info = (codec_id + codec_name).upper()

            ext = ".unknown"
            if 'AAC' in full_codec_info: ext = '.aac'
            elif 'AC-3' in full_codec_info or 'E-AC-3' in full_codec_info: ext = '.ac3'
            elif 'DTS-HD' in full_codec_info: ext = '.dtshd'
            elif 'DTS' in full_codec_info: ext = '.dts'
            elif 'TRUEHD' in full_codec_info: ext = '.thd'
            elif 'FLAC' in full_codec_info: ext = '.flac'
            elif 'VORBIS' in full_codec_info: ext = '.ogg'
            elif 'OPUS' in full_codec_info: ext = '.opus'
            elif 'PCM' in full_codec_info: ext = '.wav'
            
            if ext in IGNORE_EXTS: continue

            out_name = f"{mkv.stem}_track{tid}_{lang}{ext}"
            
            if not Path(out_name).exists():
                extract_cmds.extend([f"{tid}:{out_name}"])
            
            extracted_files.append(Path(out_name))

        if extract_cmds:
            print(f"Extracting from {mkv.name}...")
            cmd = [MKVEXTRACT_EXE, 'tracks', str(mkv)] + extract_cmds
            run_command(cmd)
        else:
             print(f"Skipping extraction for {mkv.name} (files exist).")

    return extracted_files

# --- PHASE 2: DISPLAY ---

def display_loop():
    # Only write to STDOUT to avoid stderr red coloring
    sys.stdout.write("\n" * PARALLELISM)
    while not stop_display.is_set():
        sys.stdout.write(f"\033[{PARALLELISM}A")
        for i in range(PARALLELISM):
            line = slot_status[i]
            clean_line = line[:110].ljust(110)
            sys.stdout.write(f"\r{clean_line}\n")
        sys.stdout.flush()
        time.sleep(0.1)

# --- PHASE 3: WORKERS ---

def get_audio_channels(filepath):
    cmd = [FFMPEG_EXE, '-v', 'error', '-select_streams', 'a:0', 
           '-show_entries', 'stream=channels', '-of', 'csv=p=0', str(filepath)]
    try:
        # Capture stderr to DEVNULL prevents red text leaks
        return subprocess.check_output([str(c) for c in cmd], stderr=subprocess.DEVNULL, text=True).strip()
    except:
        return "2"

def worker_flac(slot_id):
    """Converts source audio to FLAC (Intermediate)."""
    while True:
        try:
            input_file = files_queue.get_nowait()
        except queue.Empty:
            break
        
        output_file = input_file.with_suffix('.flac')
        fname = input_file.name[:25]
        slot_status[slot_id] = f"{slot_id+1}: [FLAC] {fname}.. Starting"
        
        cmd = [FFMPEG_EXE, '-y', '-i', str(input_file), '-c:a', 'flac', 
               '-sample_fmt', 's16', '-compression_level', '0', str(output_file)]
        
        try:
            # PIPE stderr so we can read progress without it hitting the console
            proc = subprocess.Popen(
                [str(c) for c in cmd], 
                stderr=subprocess.PIPE, 
                stdout=subprocess.DEVNULL, 
                text=True, 
                bufsize=1, 
                encoding='utf-8'
            )
            while True:
                chunk = proc.stderr.read(256)
                if not chunk and proc.poll() is not None:
                    break
                if chunk:
                    match = re_ffmpeg.search(chunk)
                    if match:
                        t, b, s = match.groups()
                        slot_status[slot_id] = f"{slot_id+1}: [FLAC] {fname}.. T:{t} Spd:{s}"
        except Exception as e:
             slot_status[slot_id] = f"{slot_id+1}: [Err] {str(e)[:20]}"
             continue

        files_queue.task_done()
    slot_status[slot_id] = f"{slot_id+1}: Idle"

def worker_opus(slot_id):
    """Encodes FLAC to Opus."""
    while True:
        try:
            input_file = files_queue.get_nowait()
        except queue.Empty:
            break
        
        output_file = input_file.with_suffix('.opus')
        fname = input_file.name[:25]
        
        slot_status[slot_id] = f"{slot_id+1}: [OPUS] {fname}.. Probing"
        channels = get_audio_channels(input_file)
        
        # Bitrate Strategy
        bitrate = "128"
        try:
            ch_int = int(channels)
            if ch_int >= 8: bitrate = "320"
            elif ch_int >= 6: bitrate = "256"
            elif ch_int >= 2: bitrate = "128"
            else: bitrate = "96"
        except:
            bitrate = "128"
        
        slot_status[slot_id] = f"{slot_id+1}: [OPUS] {fname}.. Init ({channels}ch @ {bitrate}k)"

        cmd = [OPUSENC_EXE, '--bitrate', bitrate, str(input_file), str(output_file)]
        
        try:
            # IMPORTANT: Capture stderr. Opusenc writes progress to stderr.
            # If we don't capture it, PowerShell makes it red.
            proc = subprocess.Popen(
                [str(c) for c in cmd], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                bufsize=1, 
                encoding='utf-8'
            )
            
            while True:
                chunk = proc.stderr.read(10)
                if not chunk and proc.poll() is not None:
                    break
                
                if chunk:
                    match = re.search(r"(\d+)%", chunk)
                    if match:
                        pct = match.group(1)
                        slot_status[slot_id] = f"{slot_id+1}: [OPUS] {fname}.. {pct}% ({channels}ch)"
                        
        except Exception as e:
             slot_status[slot_id] = f"{slot_id+1}: [Err] {str(e)[:20]}"
             continue

        files_queue.task_done()
    slot_status[slot_id] = f"{slot_id+1}: Idle"

def run_phase(files, worker_func, name):
    if not files: return
    print(f"\n--- Starting {name} ({len(files)} files) ---")
    
    for f in files: files_queue.put(f)
    for i in range(PARALLELISM): slot_status[i] = "Waiting..."

    stop_display.clear()
    d_thread = threading.Thread(target=display_loop, daemon=True)
    d_thread.start()
    
    threads = []
    for i in range(PARALLELISM):
        t = threading.Thread(target=worker_func, args=(i,))
        t.start()
        threads.append(t)
        
    files_queue.join()
    stop_display.set()
    d_thread.join()
    for t in threads: t.join()
    
    sys.stdout.write(f"\033[{PARALLELISM}B")
    print(f"{name} Complete.")

# --- PHASE 4: MUXING ---

def mux_final_files():
    current_dir = Path.cwd()
    output_dir = current_dir / "opus-output"
    output_dir.mkdir(exist_ok=True)

    print(f"\n--- Starting Muxing Phase ---")
    files_processed = 0

    for mkv_path in current_dir.glob("*.mkv"):
        audio_pattern = re.compile(re.escape(mkv_path.stem) + r"_track(\d+)_([a-zA-Z0-9]+)\.opus$")
        found_audio_tracks = []

        for audio_file in current_dir.glob("*.opus"):
            match = audio_pattern.match(audio_file.name)
            if match:
                track_num = int(match.group(1)) 
                lang_code = match.group(2)
                found_audio_tracks.append({
                    "path": audio_file,
                    "track_num": track_num,
                    "lang": lang_code,
                    "title": get_track_title_string(lang_code)
                })

        if not found_audio_tracks:
            continue

        found_audio_tracks.sort(key=lambda x: x["track_num"])
        output_file = output_dir / mkv_path.name

        print(f"Muxing: {mkv_path.name}")

        subtitle_flags = []
        try:
            cmd = [MKVMERGE_EXE, "-J", str(mkv_path)]
            res = run_command(cmd, capture_output=True)
            file_info = json.loads(res)
            for track in file_info.get("tracks", []):
                if track.get("type") == "subtitles":
                    tid = track.get("id")
                    subtitle_flags.extend(["--compression", f"{tid}:zlib"])
        except:
            pass

        cmd = [MKVMERGE_EXE, "-o", str(output_file)]
        cmd.extend(subtitle_flags) 
        cmd.append("--no-audio")
        cmd.append(str(mkv_path))

        for track in found_audio_tracks:
            title_flag = track['title'] if track['title'] else track['lang']
            print(f"  + Track: {title_flag} ({track['path'].name})")
            cmd.extend([
                "--language", f"0:{track['lang']}",
                "--track-name", f"0:{title_flag}",
                str(track['path'])
            ])

        if run_command(cmd):
            files_processed += 1
        else:
            print("  > Error during muxing (check logs).")

    print(f"\nAll done. Processed {files_processed} videos into 'opus-output'.")

# --- MAIN ENTRY ---

def main():
    try:
        extracted = extract_tracks()
        
        to_flac = [f for f in extracted if f.suffix != '.flac' and f.suffix != '.opus']
        to_opus = [f for f in extracted if f.suffix == '.flac']
        
        if to_flac:
            run_phase(to_flac, worker_flac, "Converting to Intermediate FLAC")
            for f in to_flac:
                to_opus.append(f.with_suffix('.flac'))
        
        if to_opus:
            valid_opus_inputs = [f for f in to_opus if f.exists()]
            run_phase(valid_opus_inputs, worker_opus, "Encoding to Opus")

        mux_final_files()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting safely.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nAn unexpected error occurred: {e}")
        # Prevent red traceback dump
        sys.exit(1)

if __name__ == "__main__":
    # Enable ANSI escape codes for Windows, but don't force colors
    if os.name == 'nt': os.system('')
    main()