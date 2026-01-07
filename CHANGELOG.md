# Changelog

All notable changes to the Linux Port of Auto-Boost-Av1an will be documented in this file.

## [1.0.0-linux] - 2026-01-07

### Added
- **Linux Support**: Full port of the Auto-Boost-Av1an suite to Linux (Ubuntu/Debian).
- **Automated Installer**: `install_deps_ubuntu.sh` script to set up the entire environment:
    - Installs system dependencies (FFmpeg, MKVToolNix, etc.).
    - Compiles **VapourSynth** and **FFMS2** plugin from source.
    - Compiles **SVT-AV1-PSY** (5fish fork) with Clang, PGO, and LTO optimizations.
    - Compiles **WWXD** (Scene Detection) with math library linking fix.
    - Compiles **VSZIP** (Metrics) using the official `build.sh` script (auto-fetches Zig).
    - Installs **Av1an** via Cargo.
- **Run Scripts**:
    - `run_linux.sh`: Standard run script (equivalent to `batch.bat`).
    - `run_linux_hq.sh`: High Quality mode (Tune 3, Slower).
    - `run_linux_bt709.sh`: Force BT.709 color signaling.
    - `run_linux_hq_bt709.sh`: Combined HQ + BT.709.
- **Cleanup Script**: `cleanup_install.sh` to remove all installed components.
- **Documentation**: `README_LINUX.md` and `DEPENDENCIES.md` detailing the setup and versions.

### Changed
- **Python Scripts**:
    - Updated `Auto-Boost-Av1an.py` shebang to `#!/usr/bin/env python3`.
    - Replaced Windows-hardcoded paths with `shutil.which` to find `av1an`, `mkvmerge`, etc. in system PATH.
    - Fixed `subprocess.run` calls to avoid `shell=True` on Linux (prevents quoting issues).
    - Modified `tag.py` to detect `sh-used-*.txt` marker files for correct batch name tagging on Linux.
- **VSZIP Integration**:
    - Removed `--ssimu2` flag from Linux shell scripts to force purely VapourSynth-based metric calculation (using `vszip` plugin) instead of relying on a missing `fssimu2` binary.
    - Updated `install_deps_ubuntu.sh` to use the repository's `build.sh` for VSZIP, ensuring the correct Zig compiler version is always used.

### Fixed
- **WWXD Compilation**: Fixed "undefined symbol: pow" verification error by manually linking `-lm` during compilation.
- **Metrics Fallback**: Ensured `Auto-Boost-Av1an.py` correctly falls back to `core.vszip.XPSNR` when `fssimu2` is not provided.
- **Python Conflicts**: Adjusted installer order to install `pip` packages *before* compiling VapourSynth source to avoid overwriting the source-built Python module with a generic pip version.
- **Worker Count**: Removed pre-generated `workercount-config.txt` to allow auto-detection on the user's hardware.

