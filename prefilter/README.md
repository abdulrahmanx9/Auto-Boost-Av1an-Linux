# Auto-Boost-Av1an Prefilter Scripts (Linux)

This folder contains prefiltering scripts for applying deband and denoise filters 
before encoding with Auto-Boost-Av1an.

## Available Scripts

### NVIDIA GPU (requires NVEncC)
- **nvidia-deband.sh**: Apply libplacebo deband filter using NVEncC

### CPU (VapourSynth + x265)
- **x265-lossless-deband.sh**: Apply placebo deband filter using VapourSynth and x265

## Configuration

Edit `settings.txt` to customize filter settings. Each section controls a different script:

- `[NVIDIA_DEBAND]`: Settings for nvidia-deband.sh
- `[x265_DEBAND]`: Settings for x265-lossless-deband.sh

## Usage

1. Place your `.mkv` files in this folder
2. Run the appropriate script: `./nvidia-deband.sh` or `./x265-lossless-deband.sh`
3. Output files will be created with `-deband` suffix

## Requirements

### For NVIDIA scripts:
- NVEncC installed and in PATH (https://github.com/rigaya/NVEnc)
- FFmpeg installed (`sudo apt install ffmpeg`)
- NVIDIA GPU with NVENC support

### For x265 scripts:
- VapourSynth installed with FFMS2 and placebo plugins
- x265 installed (`sudo apt install x265`)
- FFmpeg installed (`sudo apt install ffmpeg`)
