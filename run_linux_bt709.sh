#!/bin/bash
set -e

# --- STEP 0A: CREATE BATCH MARKER ---
# Create a temporary file so tag.py knows which script is running
touch "tools/sh-used-run_linux_bt709.sh.txt"

# --- STEP 0B: SET TEMP PATH ---
export PATH="$PWD/tools:$PATH"

# --- STEP 1: WORKER COUNT CHECK ---
if [ -f "tools/workercount-config.txt" ]; then
    WORKER_COUNT=$(grep "workers=" "tools/workercount-config.txt" | cut -d'=' -f2)
else
    echo ""
    echo "-------------------------------------------------------------------------------"
    echo "First Run Detected: Calculating optimal worker count..."
    echo "-------------------------------------------------------------------------------"
    python3 "tools/workercount.py"
    if [ -f "tools/workercount-config.txt" ]; then
        WORKER_COUNT=$(grep "workers=" "tools/workercount-config.txt" | cut -d'=' -f2)
    else
        WORKER_COUNT=1
    fi
fi

# --- STEP 2: RENAMING ---
echo "Starting Renaming Process..."
python3 "tools/rename.py"

# --- STEP 3: PYTHON AUTOMATION ---
echo "Starting Auto-Boost-Av1an with $WORKER_COUNT final-pass workers..."

shopt -s nullglob
for f in *-source.mkv; do
    echo ""
    echo "-------------------------------------------------------------------------------"
    echo "Detecting scenes for \"$f\"..."
    echo "-------------------------------------------------------------------------------"
    
    filename=$(basename -- "$f")
    filename_no_ext="${filename%.*}"
    
    python3 "tools/Progressive-Scene-Detection.py" -i "$f" -o "${filename_no_ext}_scenedetect.json"

    echo ""
    echo "-------------------------------------------------------------------------------"
    echo "Processing \"$f\"..."
    echo "-------------------------------------------------------------------------------"
    
    # BT.709 Params
    python3 "Auto-Boost-Av1an.py" -i "$f" --scenes "${filename_no_ext}_scenedetect.json" --photon-noise 2 --resume --workers "$WORKER_COUNT" --verbose --fast-params "--psy-rd 0.6 --color-primaries 1 --transfer-characteristics 1 --matrix-coefficients 1" --final-params "--psy-rd 0.6 --color-primaries 1 --transfer-characteristics 1 --matrix-coefficients 1 --lp 3"
done

# --- STEP 4: MUXING ---
echo "Starting Muxing Process..."
python3 "tools/mux.py"

# --- STEP 5: TAGGING ---
echo "Tagging output files..."
python3 "tools/tag.py"

echo "All tasks finished."

# --- STEP 6: CLEANUP ---
echo "Cleaning up temporary files and folders..."
python3 "tools/cleanup.py"
