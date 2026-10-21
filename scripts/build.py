#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""build.py — one command from film.html + music to finished mp4 (both ratios).

  python build.py --html film.html --audio music.wav --name MyFilm
  python build.py --html film.html --audio music.wav --name MyFilm --res both --dur 15.1

Outputs, inside --out (default ./out):
  MyFilm_1920x1080.mp4 / MyFilm_1080x1920.mp4
  cover_wide.jpg / cover_vertical.jpg
  still_grid.jpg / contact_sheet.jpg
  frames_h/ frames_v/            (intermediates, safe to delete)

Needs: node + puppeteer-core + headless Edge/Chrome (env BROWSER), ffmpeg on PATH.
"""
import argparse, os, subprocess, sys, shutil, glob

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(os.path.dirname(HERE), "templates")

def which_node():
    for p in [os.environ.get("NODE"), "node"]:
        if not p:
            continue
        if os.path.isabs(p) and os.path.exists(p):
            return p
        if not os.path.isabs(p) and shutil.which(p):
            return p
    sys.exit("node not found — install Node >= 18 or set NODE=<path to node.exe>")

def call(cmd, quiet=False):
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print("FAILED:", " ".join(str(c) for c in cmd)[:200])
        print((r.stdout or "")[-1500:]); print((r.stderr or "")[-1500:])
        sys.exit(1)
    if not quiet and r.stdout.strip():
        print("   " + r.stdout.strip().splitlines()[-1])
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--audio", default="")
    ap.add_argument("--dur", type=float, default=15.1)
    ap.add_argument("--name", default="card_film")
    ap.add_argument("--out", default="out")
    ap.add_argument("--res", default="both", choices=["both", "h", "v"])
    ap.add_argument("--fps", type=int, default=60)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    node = which_node()
    render = os.path.join(TPL, "render.js")
    N = round(a.dur * a.fps)
    targets = ["h", "v"] if a.res == "both" else [a.res]

    for res in targets:
        print(f"[1/3] render {res.upper()}")
        call([node, render, a.html, os.path.join(a.out, f"frames_{res}"), res,
              str(a.dur), str(a.fps)])

    for res in targets:
        size = "1080x1920" if res == "v" else "1920x1080"
        print(f"[2/3] encode {size}")
        cmd = ["ffmpeg", "-y", "-v", "error",
               "-framerate", str(a.fps), "-i", os.path.join(a.out, f"frames_{res}", "f_%04d.jpg")]
        if a.audio:
            cmd += ["-i", a.audio, "-af", "apad",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "16",
                "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
                "-frames:v", str(N), "-t", f"{a.dur:.3f}", "-movflags", "+faststart",
                os.path.join(a.out, f"{a.name}_{size}.mp4")]
        call(cmd)

    print("[3/3] stills")
    mp4 = {res: os.path.join(a.out, f"{a.name}_{'1080x1920' if res=='v' else '1920x1080'}.mp4")
           for res in targets}
    if "h" in mp4:
        call(["ffmpeg", "-y", "-v", "error", "-ss", f"{a.dur-0.2:.2f}", "-i", mp4["h"],
              "-frames:v", "1", "-q:v", "2", os.path.join(a.out, "cover_wide.jpg")], True)
        call(["ffmpeg", "-y", "-v", "error", "-i", mp4["h"],
              "-vf", "fps=2,scale=384:-1,tile=6x5", "-frames:v", "1",
              os.path.join(a.out, "contact_sheet.jpg")], True)
    if "v" in mp4:
        call(["ffmpeg", "-y", "-v", "error", "-ss", f"{a.dur-0.2:.2f}", "-i", mp4["v"],
              "-frames:v", "1", "-q:v", "2", os.path.join(a.out, "cover_vertical.jpg")], True)

    print("\nDONE")
    for f in sorted(glob.glob(os.path.join(a.out, "*.mp4")) + glob.glob(os.path.join(a.out, "*.jpg"))):
        print(f"  {os.path.getsize(f)/1048576:6.2f} MB  {f}")

if __name__ == "__main__":
    main()
