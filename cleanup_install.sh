#!/bin/bash

echo "=========================================================="
echo "   Auto-Boost-Av1an Deep Cleanup Script"
echo "=========================================================="
echo "This script wipes ALL dependencies installed by install_deps_ubuntu.sh"
echo "Including VapourSynth, Av1an, SVT-AV1, FFMS2, fssimu2, Zig, and Python Libs."
echo "USE WITH CAUTION."
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo ./cleanup_install.sh)"
    exit 1
fi

read -p "Are you sure you want to WIPEOUT all these tools? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "Cleaning up..."

# 1. Binaries
echo "- Removing Binaries..."
rm -vf /usr/local/bin/av1an
rm -vf /usr/local/bin/SvtAv1EncApp
rm -vf /usr/local/bin/vspipe
rm -vf /usr/local/bin/llvm-profdata
rm -vf /usr/local/bin/fssimu2
rm -vf /usr/local/bin/zig

# 2. Libraries
echo "- Removing Libraries..."
rm -vf /usr/local/lib/libvapoursynth*
rm -vf /usr/local/lib/libSvtAv1Enc*
rm -vf /usr/local/lib/libffms2*
rm -vf /usr/local/lib/libssimu2*
rm -vf /usr/local/lib/vapoursynth.so

# 3. Headers
echo "- Removing Headers..."
rm -rf /usr/local/include/vapoursynth
rm -rf /usr/local/include/svt-av1
rm -rf /usr/local/include/ffms2
rm -rf /usr/local/include/ssimu2.h

# 4. Zig Installation
echo "- Removing Zig..."
rm -rf /usr/local/lib/zig

# 5. VapourSynth Plugins
echo "- Removing VapourSynth Plugins..."
rm -rf /usr/local/lib/vapoursynth
rm -rf /usr/lib/x86_64-linux-gnu/vapoursynth

# 6. Python Module Symlink (Manual Install)
rm -vf /usr/lib/python3/dist-packages/vapoursynth.so

# 7. PkgConfig
echo "- Removing PkgConfig files..."
rm -vf /usr/local/lib/pkgconfig/vapoursynth.pc
rm -vf /usr/local/lib/pkgconfig/SvtAv1Enc.pc
rm -vf /usr/local/lib/pkgconfig/ffms2.pc

# 8. Python Libraries
echo "- Uninstalling Python Libraries..."
pip3 uninstall -y vapoursynth vsjetpack numpy rich vstools psutil --break-system-packages 2>/dev/null

# 9. Build Directory
if [ -d "build_tmp" ]; then
    echo "- Removing build_tmp..."
    rm -rf build_tmp
fi

# 10. Worker Config Files (Optional Cleanup)
echo "- Removing worker config files..."
rm -f tools/workercount-config.txt
rm -f tools/workercount-ssimu2.txt

# 11. Refresh Cache
ldconfig

echo ""
echo "=========================================================="
echo "                    Cleanup Complete"
echo "=========================================================="
echo ""
echo "Additional Manual Cleanup (if desired):"
echo "  - Remove Rust completely:     rustup self uninstall"
echo "  - Remove Av1an from cargo:    cargo uninstall av1an"
echo "  - Remove apt packages:        sudo apt remove ffmpeg mkvtoolnix libjpeg-turbo8-dev libwebp-dev libavif-dev"
echo ""
echo "System should be clean for a fresh run of install_deps_ubuntu.sh"
