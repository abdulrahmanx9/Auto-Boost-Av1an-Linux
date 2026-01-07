import os
import glob
import re
import subprocess
import shutil
import platform
import tempfile


def get_script_version():
    """Extracts the latest version number from readme.txt."""
    readme_path = "readme.txt"
    version = "Unknown"
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r"v(\d+\.\d+)", content)
                if match:
                    version = "v" + match.group(1)
        except Exception as e:
            print(f"Warning: Could not read readme.txt: {e}")
    return version


def get_5fish_folder():
    """Finds the 5fish folder name in tools/av1an."""
    base_path = os.path.join("tools", "av1an")
    pattern = os.path.join(base_path, "5fish-svt-av1-psy*")
    folders = glob.glob(pattern)
    if folders:
        return os.path.basename(folders[0])
    return "5fish-svt-av1-psy_Unknown"


def get_active_batch_filename():
    """Scans tools/ folder for the marker file created by the .bat script."""
    # Look for files like tools/bat-used-batch.bat.txt or tools/sh-used-run.sh.txt
    pattern_bat = os.path.join("tools", "bat-used-*.txt")
    pattern_sh = os.path.join("tools", "sh-used-*.txt")
    files = glob.glob(pattern_bat) + glob.glob(pattern_sh)

    if not files:
        print(
            "Error: No active batch marker found in tools/. Cannot determine settings."
        )
        return None

    # Extract the batch filename from the marker filename
    # Marker format: tools\bat-used-[BATCH_FILENAME].txt
    marker_file = files[0]
    filename = os.path.basename(marker_file)  # bat-used-batch.bat.txt

    # Remove prefix "bat-used-" or "sh-used-" and suffix ".txt"
    batch_name = (
        filename.replace("bat-used-", "").replace("sh-used-", "").replace(".txt", "")
    )

    # Clean up the marker file immediately so it doesn't persist
    try:
        os.remove(marker_file)
        print(f"Detected active batch: {batch_name} (Marker removed)")
    except OSError as e:
        print(f"Warning: Could not delete marker file {marker_file}: {e}")

    return batch_name


def parse_batch_settings(batch_filename):
    """Reads the .bat file and extracts arguments from the Auto-Boost command."""
    settings = {
        "quality": "medium",  # Default
        "ssimu2": False,
        "resume": False,
        "verbose": False,
        "fast_speed": None,
        "final_speed": None,
        "photon_noise": None,
        "final_params": "",
    }

    if not os.path.exists(batch_filename):
        print(f"Error: Batch file '{batch_filename}' not found.")
        return settings

    try:
        with open(batch_filename, "r", encoding="utf-8") as f:
            for line in f:
                # FIXED: Check using lowercase to ensure case-insensitivity
                if "auto-boost-av1an.py" in line.lower():
                    # Parse this line
                    # 1. Flags
                    if "--ssimu2" in line:
                        settings["ssimu2"] = True
                    if "--resume" in line:
                        settings["resume"] = True
                    if "--verbose" in line:
                        settings["verbose"] = True

                    # 2. Values
                    q_match = re.search(r"--quality\s+(\w+)", line)
                    if q_match:
                        settings["quality"] = q_match.group(1)

                    fs_match = re.search(r"--fast-speed\s+(\d+)", line)
                    if fs_match:
                        settings["fast_speed"] = fs_match.group(1)

                    fin_s_match = re.search(r"--final-speed\s+(\d+)", line)
                    if fin_s_match:
                        settings["final_speed"] = fin_s_match.group(1)

                    pn_match = re.search(r"--photon-noise\s+(\d+)", line)
                    if pn_match:
                        settings["photon_noise"] = pn_match.group(1)

                    # 3. Final Params (Content inside quotes)
                    # This regex looks for --final-params followed by space and a quoted string
                    fp_match = re.search(r'--final-params\s+"([^"]+)"', line)
                    if fp_match:
                        settings["final_params"] = fp_match.group(1)

                    break  # Stop after finding the command
    except Exception as e:
        print(f"Error reading batch file: {e}")

    return settings


def get_crf_string(quality):
    """Maps quality string to CRF display string."""
    q = quality.lower()
    if q == "high":
        return "--crf 25(variable)"
    elif q == "low":
        return "--crf 35(variable)"
    else:
        return "--crf 30(variable)"


def apply_tag_to_file(filepath, encoding_settings):
    """Writes a temp XML and applies it to the MKV file via mkvpropedit."""
    xml_template = f"""<?xml version="1.0"?>
<Tags>
  <Tag>
    <Targets>
      <TrackUID>1</TrackUID>
    </Targets>
    <Simple>
      <Name>ENCODING_SETTINGS</Name>
      <String>{encoding_settings}</String>
    </Simple>
  </Tag>
</Tags>
"""
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".xml", mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(xml_template)
        tmp_path = tmp.name

    try:
        print(f"Applying tag to: {filepath}")
        if platform.system() == "Windows":
            mkvpropedit_exe = "tools\\MKVToolNix\\mkvpropedit.exe"
        else:
            mkvpropedit_exe = shutil.which("mkvpropedit") or "mkvpropedit"

        subprocess.run(
            [
                mkvpropedit_exe,
                filepath,
                "--tags",
                "track:v1:" + tmp_path,
            ],
            check=True,
            capture_output=True,
        )
        print("Success.")
    except subprocess.CalledProcessError as e:
        print(f"Error tagging {filepath}: {e}")
        if e.stderr:
            print(f"Details: {e.stderr.decode('utf-8')}")
    except FileNotFoundError:
        print("Error: mkvpropedit.exe not found in tools\\MKVToolNix\\")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def main():
    # 1. Identify which batch file launched this script
    batch_file = get_active_batch_filename()
    if not batch_file:
        return  # Exit if we can't find the marker

    # 2. Parse that specific batch file for settings
    args = parse_batch_settings(batch_file)

    # 3. Gather dynamic data
    script_version = get_script_version()
    fish_version = get_5fish_folder()

    # 4. Build the Info String
    info_parts = [f"Auto-Boost-Av1an {script_version}"]

    if args["quality"] != "medium":
        info_parts.append(f"--quality {args['quality']}")

    if args["ssimu2"]:
        info_parts.append("--ssimu2")
    if args["resume"]:
        info_parts.append("--resume")
    if args["verbose"]:
        info_parts.append("--verbose")
    if args["fast_speed"]:
        info_parts.append(f"--fast-speed {args['fast_speed']}")
    if args["final_speed"]:
        info_parts.append(f"--final-speed {args['final_speed']}")
    if args["photon_noise"]:
        info_parts.append(f"--photon-noise {args['photon_noise']}")

    info_parts.append(fish_version)

    # 5. Build the Settings String
    settings_parts = ["settings:"]

    if args["final_speed"]:
        settings_parts.append(f"--preset {args['final_speed']}")

    settings_parts.append(get_crf_string(args["quality"]))

    if args["final_params"]:
        settings_parts.append(args["final_params"])

    full_string = " ".join(info_parts) + " " + " ".join(settings_parts)

    print(
        "-------------------------------------------------------------------------------"
    )
    print(f"Scanned: {batch_file}")
    print(f"Generated Tag: \n{full_string}")
    print(
        "-------------------------------------------------------------------------------"
    )

    # 6. Apply to files
    found = False
    for root, _, files in os.walk("."):
        for f in files:
            if f.lower().endswith("-output.mkv"):
                found = True
                full_path = os.path.join(root, f)
                apply_tag_to_file(full_path, full_string)

    if not found:
        print("No *-output.mkv files found to tag.")


if __name__ == "__main__":
    main()
