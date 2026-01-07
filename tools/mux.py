import os
import subprocess
import glob
import sys
import shutil
import platform

# Path to mkvmerge executable
if platform.system() == "Windows":
    MKVMERGE = os.path.join("tools", "MKVToolNix", "mkvmerge.exe")
else:
    MKVMERGE = shutil.which("mkvmerge") or "mkvmerge"


def run_mkvmerge(cmd, status_label):
    """
    Runs mkvmerge hidden, parsing output to update a single progress line.
    """
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )

    # Print initial status with extra spaces to reserve the line
    print(f"{status_label}: Starting...          ", end="\r")
    sys.stdout.flush()

    for line in process.stdout:
        line = line.strip()
        # mkvmerge output standard: "Progress: 10%"
        if line.startswith("Progress:"):
            percent = line.split(":")[-1].strip()
            # Update the line with the percentage + padding spaces
            print(f"{status_label}: {percent}          ", end="\r")
            sys.stdout.flush()

    process.wait()

    if process.returncode != 0:
        print(f"\n[ERROR] Command failed: {' '.join(cmd)}")
        raise subprocess.CalledProcessError(process.returncode, cmd)

    # Finalize the line with explicit spaces to overwrite "Starting..." or percentages
    print(f"{status_label}: Done.          ")


def mux_files():
    # Look for files ending in -av1.mkv
    av1_files = glob.glob("*-av1.mkv")

    if not av1_files:
        print("No *-av1.mkv files found to mux.")
        return

    print(f"Found {len(av1_files)} '-av1.mkv' files. Starting muxing process...\n")

    for av1_file in av1_files:
        # Determine base name by removing the suffix
        # e.g. "File-source-av1.mkv" -> "File-source"
        base_name = av1_file.replace("-av1.mkv", "")

        # Check for matching source file.
        # 1. Check strict match (e.g. "File-source.mkv")
        # 2. Check appended match (e.g. "File-source.mkv" if base was just "File")
        possible_sources = [f"{base_name}.mkv", f"{base_name}-source.mkv"]

        source_mkv = None
        for path in possible_sources:
            if os.path.exists(path):
                source_mkv = path
                break

        if not source_mkv:
            print(f"[SKIP] Source file not found for: {av1_file}")
            # Optional: print what we looked for to help debugging
            # print(f"       Checked: {possible_sources}")
            continue

        temp_mkv = f"{base_name}_temp_no_video.mkv"
        final_output = f"{base_name}-output.mkv"

        try:
            # Step 1: Extract Audio/Subs (No Video) from the source file
            cmd_step1 = [MKVMERGE, "-o", temp_mkv, "--no-video", source_mkv]
            run_mkvmerge(cmd_step1, f"[{base_name}] Step 1/2 (Extract)")

            # Step 2: Mux the new AV1 video file + the extracted Audio/Subs
            cmd_step2 = [MKVMERGE, "-o", final_output, av1_file, temp_mkv]
            run_mkvmerge(cmd_step2, f"[{base_name}] Step 2/2 (Merge)  ")

            # Cleanup temp file
            if os.path.exists(temp_mkv):
                os.remove(temp_mkv)

        except subprocess.CalledProcessError:
            print(f"\n[FAIL] Could not process {base_name}. Skipping.")


if __name__ == "__main__":
    mux_files()
