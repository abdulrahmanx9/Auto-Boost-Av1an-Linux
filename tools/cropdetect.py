#!/usr/bin/env python3
"""
robust_autocrop.py

Batch-detect crop values for many videos using ffmpeg cropdetect in a robust way.
Modified for Auto-Boost-Av1an integration with settings.txt support.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CROP_RE = re.compile(r"\bcrop=(\d+):(\d+):(\d+):(\d+)\b")

VIDEO_DEFAULT_EXTS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".m4v",
    ".webm",
    ".avi",
    ".mpg",
    ".mpeg",
    ".ts",
    ".m2ts",
    ".wmv",
}


@dataclass
class VideoInfo:
    path: Path
    width: int
    height: int
    duration: float  # seconds (may be 0/unknown for some files)


@dataclass
class CropResult:
    crop: str  # "W:H:X:Y"
    w: int
    h: int
    x: int
    y: int
    confidence: float  # 0..1
    samples: int  # number of frames/segments observed
    chosen_from_limits: List[float]  # which cropdetect limits produced this crop
    notes: str


def run_cmd(cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def ffprobe_info(path: Path) -> Optional[VideoInfo]:
    # Pull width/height/duration for the first video stream
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height:format=duration",
        "-of",
        "json",
        str(path),
    ]
    p = run_cmd(cmd, timeout=60)
    if p.returncode != 0:
        return None

    try:
        data = json.loads(p.stdout)
        streams = data.get("streams", [])
        if not streams:
            return None
        w = int(streams[0].get("width", 0) or 0)
        h = int(streams[0].get("height", 0) or 0)
        dur = float(data.get("format", {}).get("duration", 0) or 0.0)
        if w <= 0 or h <= 0:
            return None
        return VideoInfo(path=path, width=w, height=h, duration=dur)
    except Exception:
        return None


def sample_timestamps(duration: float, n: int) -> List[float]:
    """
    Pick timestamps spread across the video, avoiding very beginning/end.
    If duration is unknown/zero, fall back to a few early timestamps.
    """
    if duration and duration > 10:
        start = max(0.5, duration * 0.05)
        end = max(start + 1.0, duration * 0.95)
        if end <= start:
            return [start]
        return [start + (end - start) * (i / (n - 1)) for i in range(n)]
    # unknown duration
    return [0.5, 3.0, 8.0, 15.0][: max(1, min(n, 4))]


def run_cropdetect_segment(
    video: Path,
    ss: float,
    seg: float,
    fps: float,
    limit: float,
    round_to: int,
) -> List[Tuple[int, int, int, int]]:
    """
    Run ffmpeg cropdetect on a short segment and return all detected crops.
    """
    vf = f"fps={fps},format=yuv444p,cropdetect=limit={limit}:round={round_to}:reset=0"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-ss",
        f"{ss:.3f}",
        "-i",
        str(video),
        "-t",
        f"{seg:.3f}",
        "-vf",
        vf,
        "-an",
        "-sn",
        "-dn",
        "-f",
        "null",
        "-",
    ]
    p = run_cmd(cmd, timeout=max(60, int(seg * 10) + 30))
    text = (p.stderr or "") + "\n" + (p.stdout or "")
    crops: List[Tuple[int, int, int, int]] = []
    for m in CROP_RE.finditer(text):
        w, h, x, y = map(int, m.groups())
        crops.append((w, h, x, y))
    return crops


def area(w: int, h: int) -> int:
    return w * h


def choose_best_crop(
    vi: VideoInfo,
    observed: Counter,
    crop_to_limits: Dict[str, set],
) -> Optional[CropResult]:
    """
    Choose best crop among observed crops:
    - prefer stability (high count)
    - avoid overcropping: among similar counts, prefer larger area
    - prefer crops supported by multiple limits
    """
    if not observed:
        return None

    full_area = area(vi.width, vi.height)

    # Score: stability + mild preference for larger area + support across limits
    best = None
    best_score = -1e18

    total = sum(observed.values())

    for crop_str, count in observed.items():
        w, h, x, y = map(int, crop_str.split(":"))
        a = area(w, h)
        if a <= 0 or a > full_area:
            continue

        # Fraction of frames/samples that reported this crop
        freq = count / max(1, total)

        # Area ratio: closer to 1 = less cropping (safer)
        ar = a / full_area

        # Limits support: more independent thresholds agreeing = good sign
        lim_support = len(crop_to_limits.get(crop_str, set()))

        # Heuristic score (tuned for "robust but not reckless"):
        # - frequency dominates
        # - larger area breaks ties (avoid overcropping)
        # - multi-limit agreement boosts confidence
        score = (freq * 1000.0) + (ar * 50.0) + (lim_support * 15.0)

        # Slight penalty if crop is exactly full frame (still valid, but less "found bars")
        if w == vi.width and h == vi.height and x == 0 and y == 0:
            score -= 5.0

        if score > best_score:
            best_score = score
            best = (crop_str, w, h, x, y, freq, total, lim_support)

    if best is None:
        return None

    crop_str, w, h, x, y, freq, total, lim_support = best
    limits = sorted(crop_to_limits.get(crop_str, set()))
    notes = []
    if lim_support >= 3:
        notes.append("strong multi-threshold agreement")
    elif lim_support == 2:
        notes.append("moderate multi-threshold agreement")
    else:
        notes.append("single-threshold pick (still may be correct)")

    return CropResult(
        crop=crop_str,
        w=w,
        h=h,
        x=x,
        y=y,
        confidence=float(freq),
        samples=int(total),
        chosen_from_limits=[float(v) for v in limits],
        notes="; ".join(notes),
    )


def find_videos(paths: List[str], recursive: bool, exts: set) -> List[Path]:
    vids: List[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            if recursive:
                for f in pp.rglob("*"):
                    if f.is_file() and f.suffix.lower() in exts:
                        vids.append(f)
            else:
                for f in pp.iterdir():
                    if f.is_file() and f.suffix.lower() in exts:
                        vids.append(f)
        else:
            if pp.is_file():
                vids.append(pp)
    # de-dupe while preserving order
    seen = set()
    out = []
    for v in vids:
        r = v.resolve()
        if r not in seen:
            seen.add(r)
            out.append(v)
    return out


def detect_crop_for_video(
    vi: VideoInfo,
    sample_count: int,
    segment_len: float,
    fps: float,
    limits: List[float],
    round_to: int,
    progress_mode: bool = False,
) -> Optional[CropResult]:
    timestamps = sample_timestamps(vi.duration, sample_count)

    observed: Counter = Counter()
    crop_to_limits: Dict[str, set] = defaultdict(set)

    total_steps = len(limits) * len(timestamps)
    current_step = 0

    for lim in limits:
        for ts in timestamps:
            crops = run_cropdetect_segment(
                video=vi.path,
                ss=ts,
                seg=segment_len,
                fps=fps,
                limit=lim,
                round_to=round_to,
            )
            for w, h, x, y in crops:
                crop_str = f"{w}:{h}:{x}:{y}"
                observed[crop_str] += 1
                crop_to_limits[crop_str].add(lim)

            # Emit progress for parent process
            if progress_mode:
                current_step += 1
                percent = int((current_step / total_steps) * 100)
                # Flush to ensure parent reads it immediately
                print(f"PROGRESS:{percent}", flush=True)

    return choose_best_crop(vi, observed, crop_to_limits)


def load_settings() -> dict:
    """
    Attempts to load settings.txt from the script's directory
    or the parent directory.
    """
    script_dir = Path(__file__).parent.resolve()

    # Check current directory and parent directory
    possible_paths = [script_dir / "settings.txt", script_dir.parent / "settings.txt"]

    settings = {}

    target_file = None
    for p in possible_paths:
        if p.is_file():
            target_file = p
            break

    if target_file:
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        settings[key.strip().lower()] = val.strip()
        except Exception as e:
            print(f"Warning: Failed to read {target_file}: {e}", file=sys.stderr)

    return settings


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Robust batch crop detection using ffmpeg cropdetect."
    )
    ap.add_argument("inputs", nargs="+", help="Video files and/or directories.")
    ap.add_argument(
        "--recursive", action="store_true", help="Recurse into directories."
    )
    ap.add_argument(
        "--extensions",
        default=",".join(sorted(e.lstrip(".") for e in VIDEO_DEFAULT_EXTS)),
        help="Comma-separated extensions to include (default: common video types).",
    )

    ap.add_argument(
        "--samples",
        type=int,
        default=15,
        help="Number of timestamps to sample per video.",
    )
    ap.add_argument(
        "--segment", type=float, default=2.5, help="Seconds per sample segment."
    )
    ap.add_argument(
        "--fps", type=float, default=3.0, help="Analysis FPS within each segment."
    )

    ap.add_argument(
        "--round",
        dest="round_to",
        type=int,
        default=2,
        help="Round crop values to this multiple (2 recommended for yuv420).",
    )

    ap.add_argument(
        "--aggressive",
        action="store_true",
        help="Use a wider range of cropdetect limits (better for gray bars; higher risk in very dark content).",
    )

    ap.add_argument("--out", default="crops.csv", help="CSV output path.")
    ap.add_argument(
        "--json-out", default="", help="Optional JSON output path (in addition to CSV)."
    )

    # Internal flag for UI integration (suppresses standard stdout, emits machine-readable progress)
    ap.add_argument("--progress-mode", action="store_true", help=argparse.SUPPRESS)

    args = ap.parse_args()

    # --- Load Settings ---
    settings = load_settings()
    crop_mode = settings.get("crop", "auto").lower()

    manual_crop_vals = {"top": 0, "bottom": 0, "left": 0, "right": 0}
    if crop_mode == "manual":
        for k in manual_crop_vals:
            try:
                manual_crop_vals[k] = int(settings.get(k, 0))
            except ValueError:
                manual_crop_vals[k] = 0

    if not args.progress_mode:
        print(f"Crop Mode: {crop_mode}")
        if crop_mode == "manual":
            print(f"Manual values: {manual_crop_vals}")

    exts = {
        ("." + e.strip().lower().lstrip("."))
        for e in args.extensions.split(",")
        if e.strip()
    }
    videos = find_videos(args.inputs, args.recursive, exts)

    if not videos:
        print("No videos found with the specified inputs/extensions.", file=sys.stderr)
        return 2

    # Multi-pass cropdetect thresholds.
    if args.aggressive:
        limits = [0.04, 0.06, 0.08, 0.12, 0.18, 0.25, 0.32, 0.40, 0.50]
    else:
        limits = [0.06, 0.08, 0.12, 0.18, 0.25, 0.35]

    results_rows = []
    json_results = []

    for idx, vp in enumerate(videos, 1):
        vi = ffprobe_info(vp)
        if not vi:
            if not args.progress_mode:
                print(
                    f"[{idx}/{len(videos)}] SKIP (ffprobe failed): {vp}",
                    file=sys.stderr,
                )
            continue

        if not args.progress_mode:
            print(f"[{idx}/{len(videos)}] Analyze: {vp}")

        res = None

        # --- Decision: Manual vs Auto ---
        if crop_mode == "manual":
            # Calculate manual crop based on settings.txt
            m_top = manual_crop_vals["top"]
            m_bot = manual_crop_vals["bottom"]
            m_left = manual_crop_vals["left"]
            m_right = manual_crop_vals["right"]

            # Calculate width/height
            target_w = vi.width - m_left - m_right
            target_h = vi.height - m_top - m_bot

            # Basic validation to prevent negative dimensions
            if target_w <= 0 or target_h <= 0:
                if not args.progress_mode:
                    print(
                        f"WARNING: Manual crop results in invalid dimensions ({target_w}x{target_h}). Reverting to full frame."
                    )
                target_w = vi.width
                target_h = vi.height
                m_left = 0
                m_top = 0

            target_x = m_left
            target_y = m_top
            crop_str = f"{target_w}:{target_h}:{target_x}:{target_y}"

            res = CropResult(
                crop=crop_str,
                w=target_w,
                h=target_h,
                x=target_x,
                y=target_y,
                confidence=1.0,
                samples=1,
                chosen_from_limits=[],
                notes="Manual crop via settings.txt",
            )
            # Emit 100% progress for UI
            if args.progress_mode:
                print(f"PROGRESS:100", flush=True)

        else:
            # Original Auto Logic
            res = detect_crop_for_video(
                vi=vi,
                sample_count=args.samples,
                segment_len=args.segment,
                fps=args.fps,
                limits=limits,
                round_to=args.round_to,
                progress_mode=args.progress_mode,
            )

        if not res:
            crop_str = f"{vi.width}:{vi.height}:0:0"
            res = CropResult(
                crop=crop_str,
                w=vi.width,
                h=vi.height,
                x=0,
                y=0,
                confidence=0.0,
                samples=0,
                chosen_from_limits=[],
                notes="NO cropdetect hits; falling back to full-frame",
            )

        ffmpeg_apply = f'-vf "crop={res.crop}"'
        row = {
            "file": str(vp),
            "width": vi.width,
            "height": vi.height,
            "duration_sec": round(vi.duration, 3),
            "crop": res.crop,
            "crop_w": res.w,
            "crop_h": res.h,
            "crop_x": res.x,
            "crop_y": res.y,
            "confidence": round(res.confidence, 4),
            "samples_seen": res.samples,
            "limits_agreed": ",".join(f"{x:.2f}" for x in res.chosen_from_limits),
            "notes": res.notes,
            "ffmpeg_apply": ffmpeg_apply,
        }
        results_rows.append(row)
        json_results.append(row)

        if not args.progress_mode:
            print(
                f"  -> crop={res.crop}  confidence={row['confidence']}  limits=[{row['limits_agreed']}]"
            )

    # Write CSV
    out_csv = Path(args.out)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "file",
        "width",
        "height",
        "duration_sec",
        "crop",
        "crop_w",
        "crop_h",
        "crop_x",
        "crop_y",
        "confidence",
        "samples_seen",
        "limits_agreed",
        "notes",
        "ffmpeg_apply",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results_rows:
            w.writerow(r)

    if args.json_out:
        out_json = Path(args.json_out)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(json_results, indent=2), encoding="utf-8")

    if not args.progress_mode:
        print(f"\nDone. Wrote: {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
