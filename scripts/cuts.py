#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""cuts.py — measure rhythm instead of guessing it.

  python cuts.py scene  <video> [threshold]     where the reference picture cuts
  python cuts.py onsets <audio|video>           where the drums / accents hit
  python cuts.py plan   <audio|video> [--n 12] [--start 0.8] [--end 15.1]
                                                propose a CUTS array you can paste
                                                straight into film.html

Why: this style only reads as "expensive" when the picture changes on the music.
Uniform 0.8s cards on a track that breathes will look wrong no matter how good
the typography is.
"""
import subprocess, sys, os, math, array, wave, tempfile

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, errors="ignore")

def scene(path, thr=0.12):
    r = run(["ffmpeg", "-v", "error", "-i", path, "-filter_complex",
             f"select='gt(scene,{thr})',metadata=print:file=-", "-an", "-f", "null", "-"])
    ts = []
    for line in (r.stdout + r.stderr).splitlines():
        if "pts_time:" in line:
            try:
                ts.append(float(line.split("pts_time:")[1].split()[0]))
            except ValueError:
                pass
    out = []
    for t in sorted(ts):
        if not out or t - out[-1] > 0.06:      # collapse the 2-3 frames of one cut
            out.append(round(t, 3))
    return out

def to_wav(src):
    tmp = os.path.join(tempfile.gettempdir(), "_cuts_probe.wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "48000", tmp])
    return tmp

def onsets(src, k=0.16, merge=0.06):
    w = wave.open(to_wav(src), "rb")
    sr, n = w.getframerate(), w.getnframes()
    a = array.array("h"); a.frombytes(w.readframes(n))
    hop = int(sr * 0.005)
    env = []
    for i in range(0, len(a) - hop, hop):
        seg = a[i:i + hop]
        env.append(math.sqrt(sum(x * x for x in seg) / hop))
    flux = [max(0.0, env[i] - env[i - 1]) for i in range(1, len(env))]
    mx = max(flux) or 1.0
    peaks = []
    for i in range(2, len(flux) - 2):
        if flux[i] > mx * k and flux[i] == max(flux[max(0, i - 3):i + 4]):
            peaks.append((i + 1) * 0.005)
    out = []
    for p in peaks:
        if not out or p - out[-1] > merge:
            out.append(round(p, 3))
    return out

def plan(src, n=12, start=0.8, end=15.1, tail=3.9):
    """tail = seconds after the last card reserved for the grid + end lockup."""
    on = onsets(src)
    card_end = end - tail
    bounds = [round(start, 3)]
    for i in range(1, n):
        want = start + (card_end - start) * i / n
        cand = [o for o in on if o > bounds[-1] + 0.35 and o < card_end - 0.15]
        pick = min(cand, key=lambda o: abs(o - want)) if cand else want
        bounds.append(round(pick, 3))
    bounds.append(round(card_end, 3))
    bounds.append(round(end, 3))
    gaps = [round(bounds[i + 1] - bounds[i], 3) for i in range(len(bounds) - 1)]
    return bounds, gaps

def main():
    if len(sys.argv) < 3:
        print(__doc__); return 1
    mode, src = sys.argv[1], sys.argv[2]
    if mode == "scene":
        thr = float(sys.argv[3]) if len(sys.argv) > 3 else 0.12
        ts = scene(src, thr)
        print(f"{len(ts)} cuts")
        print("  ".join(f"{t:.2f}" for t in ts))
    elif mode == "onsets":
        ts = onsets(src)
        print(f"{len(ts)} onsets")
        print("  ".join(f"{t:.2f}" for t in ts))
    elif mode == "plan":
        n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 12
        st = float(sys.argv[sys.argv.index("--start") + 1]) if "--start" in sys.argv else 0.8
        en = float(sys.argv[sys.argv.index("--end") + 1]) if "--end" in sys.argv else 15.1
        tl = float(sys.argv[sys.argv.index("--tail") + 1]) if "--tail" in sys.argv else 3.9
        b, g = plan(src, n, st, en, tl)
        print("// paste into film.html, right above const TL")
        print("const CUTS=[" + ",".join(f"{x:.2f}" for x in b[:n + 1]) + "];")
        print("// card lengths: " + " / ".join(f"{x:.2f}" for x in g[:n]))
        print(f"// then: TL grid=[{b[n]:.2f},{b[n] + (tl * 0.51):.2f}] final=[{b[n] + (tl * 0.51):.2f},{b[n + 1]:.2f}]")
    else:
        print(__doc__); return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
