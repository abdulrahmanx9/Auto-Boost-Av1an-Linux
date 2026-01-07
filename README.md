# Auto-Boost-Av1an for Ubuntu

This guide explains how to set up and run Auto-Boost-Av1an on Ubuntu.

## Prerequisites

### Automatic Installation

We have provided a script to automatically install all dependencies on Ubuntu/Debian.
This script needs to be run as root.

```bash
chmod +x install_deps_ubuntu.sh
sudo ./install_deps_ubuntu.sh
```

**Cleanup:**
If the installation fails or you want to undo the manual compilations (SVT-AV1, WWXD), you can run:
```bash
chmod +x cleanup_install.sh
sudo ./cleanup_install.sh
```

If you prefer to install manually, follow the steps below.

### 1. System Packages

Install basic tools, FFmpeg, and x264 (required for scene detection):

```bash
sudo apt update
sudo apt install -y ffmpeg x264 mkvtoolnix mkvtoolnix-gui python3 python3-pip git curl
```

### 2. VapourSynth

Install VapourSynth and its Python bindings.
For Ubuntu, you might need to add the `vs-repo` or use the default repositories if available (Ubuntu 24.04+ has newer versions).

```bash
sudo apt install -y vapoursynth libvapoursynth-dev python3-vapoursynth
```

### 3. Python Dependencies

Install the required Python packages:

```bash
pip3 install vsjetpack numpy rich vstools psutil
```

### 4. Av1an

The automatic installer uses the latest version from Git for feature parity.
Manual install:
```bash
cargo install --git https://github.com/rust-av/Av1an.git
```

### 5. SVT-AV1

The automatic installer compiles **SVT-AV1-PSY** (Psycho-visual fork) with Clang and PGO/LTO optimizations for best quality and speed on Linux.
Manual install (using defaults):
```bash
git clone https://github.com/5fish/svt-av1-psy
cd svt-av1-psy/Build/linux
./build.sh --native --static --release --enable-lto --enable-pgo
sudo cp ../../Bin/Release/SvtAv1EncApp /usr/local/bin/
```
Ensure `SvtAv1EncApp` is in your PATH.

### 6. VapourSynth Plugins

The script relies on the following plugins:
1.  **FFMS2**: For video loading.
2.  **WWXD**: For scene detection (required by `Progressive-Scene-Detection.py`).
3.  **VSZIP**: For metrics calculation (fallback if `fssimu2` is missing).

Install FFMS2:
```bash
sudo apt install -y libffms2-4 libffms2-dev
```

**Install WWXD:**
You typically need to compile this plugin or find it in a PPA.
[GitHub: WWXD](https://github.com/dubhater/vapoursynth-wwxd)

**Install VSZIP (SSIMULACRA2):**
Required for metrics if you don't use `fssimu2`.
[GitHub: vs-zip](https://github.com/dnjulek/vapoursynth-zip)

*Alternatively, you can install the `fssimu2` binary and place it in your PATH to avoid needing `vszip`.*

## Usage

1.  Place your source files (e.g., `yourfile-source.mkv`) in the project folder.
2.  Make the script executable:
    ```bash
    chmod +x run_linux.sh
    ```
3.  Run the script:
    ```bash
    ./run_linux.sh
    ```

The script will:
1.  Calculate optimal worker count.
2.  Rename files to standard format.
3.  Run Scene Detection.
4.  Run Auto-Boost-Av1an (Fast Pass -> Metrics -> Zones -> Final Encode).
5.  Mux audio/subtitles back.
6.  Tag the output file.
7.  Cleanup temporary files.

## Verification

To verify that the installation was successful, run the following commands:

```bash
# Check Core Tools
ffmpeg -version | head -n 1
mkvmerge --version
python3 --version

# Check VapourSynth
vspipe --version
python3 -c "import vapoursynth; print(f'VapourSynth Core: {vapoursynth.core.version()}')"

# Check Encoders
av1an --version
SvtAv1EncApp --help | grep "SVT"
```

## Troubleshooting

-   **Missing Tools**: Ensure `av1an`, `SvtAv1EncApp`, `ffmpeg`, `mkvmerge`, `mkvpropedit` are in your PATH.
-   **VapourSynth Errors**: Ensure you have the required plugins (`ffms2`) installed and accessible to VapourSynth.
-   **Permissions**: Ensure you have write permissions in the folder.

## Files Required

If you are moving this project to a Linux machine, you only need the following files. You can ignore the `VapourSynth` folder and the `.exe` files in `tools/`.

**Root Directory:**
-   `Auto-Boost-Av1an.py`
-   `run_linux.sh`
-   `README_LINUX.md`

**Tools Directory (`tools/`):**
-   `tools/Progressive-Scene-Detection.py`
-   `tools/cleanup.py`
-   `tools/mux.py`
-   `tools/rename.py`
-   `tools/tag.py`
-   `tools/workercount.py`
-   `tools/sample.mkv`
-   `tools/iso200-grain.tbl`

*Note: The Windows binaries (av1an.exe, mkvmerge.exe, etc.) and the VapourSynth folder are NOT needed on Linux.*

## Code Modification Log

To support Linux, the following changes were made to the original codebase:
- **Automated Installer**: `install_deps_ubuntu.sh` automates the entire setup (System packages, VapourSynth, Av1an, SVT-AV1-PSY, WWXD, VSZIP).
    - *Note*: **VSZIP** (VapourSynth-ZIP) plugin and its dependency (Zig compiler) are now **automatically downloaded and installed** by the script.
- **Code Adaptation**: Python scripts were modified to use `shutil.which` for finding executables (`av1an`, `mkvmerge`, etc.) instead of hardcoded Windows paths.
- **Path Handling**: Windows-style paths (backslashes) were replaced or handled using Python's cross-platform `pathlib` or `os.path` where necessary.

### 1. `Auto-Boost-Av1an.py`
-   **Tool Path Resolution**: Modified to use `platform.system()` to detect the OS.
    -   **Windows**: Continues to use relative paths to the portable `tools\` folder (e.g., `tools\av1an\av1an.exe`).
    -   **Linux**: Uses `shutil.which()` to find `av1an` and `fssimu2` in the system PATH.

### 2. `tools/mux.py` & `tools/tag.py`
-   **MKVToolNix Paths**: Modified to use `platform.system()` and `shutil.which()`.
    -   **Windows**: Uses bundled `tools\MKVToolNix\mkvmerge.exe` and `mkvpropedit.exe`.
    -   **Linux**: Expects `mkvmerge` and `mkvpropedit` to be installed and available in the system PATH.
-   **Batch Detection (`tag.py`)**: Updated `get_active_batch_filename` to detect the new `sh-used-run.sh.txt` marker file created by the Linux shell script.

### 3. New Files
-   **`run_linux.sh`**: A Bash script created to verify worker count, rename files, run scene detection, execute the main Python script, and perform muxing/tagging/cleanup. This replaces `batch.bat` on Linux.
-   **`README_LINUX.md`**: This documentation file.
