import os
import subprocess
import glob
import sys
import shutil


def mux_files():
    output_dir = "Output"
    input_dir = "Input"

    # Fallback to current dir if no Output folder found
    if not os.path.exists(output_dir):
        output_dir = "."
        input_dir = "."

    print(f"Scanning {output_dir} for AV1 files...")

    av1_files = glob.glob(os.path.join(output_dir, "*-av1.mkv"))

    if not av1_files:
        print("No *-av1.mkv files found to mux.")
        return

    print(f"Found {len(av1_files)} '-av1.mkv' files.\n")

    mkvmerge = shutil.which("mkvmerge") or "mkvmerge"

    for av1_file in av1_files:
        filename = os.path.basename(av1_file)
        base_name = filename.replace("-av1.mkv", "")

        # Search for source video in Input folder
        candidates = [
            os.path.join(input_dir, f"{base_name}.mkv"),
            os.path.join(input_dir, f"{base_name}-source.mkv"),
        ]

        source_mkv = None
        for c in candidates:
            if os.path.exists(c):
                source_mkv = c
                break

        if not source_mkv:
            print(f"[SKIP] Source video not found for: {filename}")
            continue

        final_output = os.path.join(output_dir, f"{base_name}-output.mkv")
        temp_audio = os.path.join(output_dir, f"{base_name}_temp_extract.mkv")

        # Avoid muxing if output exists? (No, overwrite logic or user deletes)

        print(f"Muxing: {base_name}...")
        try:
            # Step 1: Extract Audio/Subs from source (--no-video)
            subprocess.run(
                [mkvmerge, "-o", temp_audio, "--no-video", source_mkv],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Step 2: Merge AV1 video + Extracted Audio
            subprocess.run(
                [mkvmerge, "-o", final_output, av1_file, temp_audio],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            print(f"  -> Done: {final_output}")

            # Cleanup temp extract
            if os.path.exists(temp_audio):
                os.remove(temp_audio)

        except Exception as e:
            print(f"  [ERROR] Mux failed: {e}")


if __name__ == "__main__":
    mux_files()
