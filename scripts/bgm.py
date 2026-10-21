import sys, os
# -*- coding: utf-8 -*-
"""KANVIS STUDIO · 剪辑工作台 · 15.2s / 150 BPM 卡点 BGM（纯 numpy/scipy 合成，无版权素材）"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100
BPM = 150.0
BEAT = 60.0 / BPM            # 0.4s
BAR = BEAT * 4               # 1.6s
DUR = 15.2
N = int(SR * DUR)
rng = np.random.default_rng(20261021)
t = np.arange(N) / SR


def lowpass(x, cutoff, order=2):
    sos = butter(order, cutoff / (SR / 2), btype="low", output="sos")
    return sosfilt(sos, x)


def highpass(x, cutoff, order=2):
    sos = butter(order, cutoff / (SR / 2), btype="high", output="sos")
    return sosfilt(sos, x)


def bandpass(x, lo, hi, order=2):
    sos = butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band", output="sos")
    return sosfilt(sos, x)


def note(freq, dur, amp=0.1, kind="sine", detune=0.0, attack=0.01, decay=0.2, release=0.1):
    n = max(8, int(dur * SR))
    tt = np.arange(n) / SR
    if kind == "sine":
        w = np.sin(2 * np.pi * freq * tt)
        if detune:
            w = 0.6 * w + 0.4 * np.sin(2 * np.pi * (freq * (1 + detune)) * tt)
    elif kind == "saw":
        w = 2 * ((freq * tt) % 1) - 1
        if detune:
            w = 0.5 * w + 0.5 * (2 * ((freq * (1 + detune) * tt) % 1) - 1)
        w = lowpass(w, 2400)
    else:
        w = np.zeros(n)
    a_n = max(1, int(attack * SR))
    d_n = max(1, int(decay * SR))
    r_n = max(1, int(release * SR))
    e = np.ones(n)
    i = 0
    seg = min(a_n, n); e[:seg] = np.linspace(0, 1, seg); i = seg
    seg = min(d_n, n - i); e[i:i + seg] *= np.linspace(1, 0.62, seg); i += seg
    seg = min(r_n, n - i); e[i:i + seg] *= np.linspace(1, 0, seg)
    return amp * w * e


bus = np.zeros((N, 2))


def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N or i < 0:
        return
    n = min(len(sig), N - i)
    bus[i:i + n, 0] += sig[:n] * gain * (1 - max(0.0, pan))
    bus[i:i + n, 1] += sig[:n] * gain * (1 + min(0.0, pan))


CH = {
    "Am": [110.00, 164.81, 220.00, 261.63],
    "F":  [87.31, 130.81, 174.61, 220.00],
    "C":  [130.81, 196.00, 261.63, 329.63],
    "G":  [98.00, 146.83, 196.00, 246.94],
}
PROG = ["Am", "F", "C", "G", "Am", "F", "C", "G", "Am", "F"]

# ---------- pad ----------
for bar_i, name in enumerate(PROG):
    at = bar_i * BAR
    if at > DUR:
        break
    chord = CH[name]
    for k, f in enumerate(chord[:3]):
        add(note(f, BAR + 0.4, amp=0.040 / (1 + 0.35 * k), kind="saw", detune=0.004,
                 attack=0.18, decay=0.25, release=0.35), at, pan=(-0.22 + 0.22 * k))
    add(note(chord[3] * 2, BAR, amp=0.008, kind="sine", attack=0.3, decay=0.3, release=0.3),
        at, pan=0.2)

# ---------- bass 8ths ----------
for bar_i, name in enumerate(PROG):
    root = CH[name][0] / 2
    for s in range(8):
        at = bar_i * BAR + s * BEAT / 2
        if at > DUR - 0.05:
            break
        if at < 0.75:
            continue
        add(note(root, BEAT * 0.42, amp=0.085, kind="sine", attack=0.005, decay=0.12, release=0.08), at)

# ---------- arp 16ths ----------
pat = [0, 2, 1, 3, 2, 1, 3, 0]
for bar_i, name in enumerate(PROG):
    chord = CH[name]
    for s in range(16):
        at = bar_i * BAR + s * BEAT / 4
        if at > DUR - 0.08 or at < 0.78:
            continue
        f = chord[pat[s % 8]] * 2
        amp = 0.020 if bar_i < 2 else 0.028
        add(note(f, BEAT * 0.5, amp=amp, kind="sine", attack=0.003, decay=0.07, release=0.06),
            at, pan=0.28 if s % 2 else -0.28)


# ---------- drums ----------
def kick(amp=0.5):
    n = int(0.34 * SR)
    tt = np.arange(n) / SR
    f = 132 * np.exp(-tt * 30) + 50
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-tt * 9)
    click = rng.normal(0, 1, n) * np.exp(-tt * 260) * 0.22
    return amp * (body + click)


def hat(amp=0.10, dur=0.045):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return amp * bandpass(rng.normal(0, 1, n), 7000, 14000) * np.exp(-tt * 70)


def clap(amp=0.13):
    n = int(0.16 * SR)
    tt = np.arange(n) / SR
    nz = bandpass(rng.normal(0, 1, n), 1400, 6000)
    return amp * nz * np.exp(-tt * 26)


def tick(amp=0.06):
    n = int(0.05 * SR)
    tt = np.arange(n) / SR
    return amp * bandpass(rng.normal(0, 1, n), 2600, 9000) * np.exp(-tt * 120)


for b in range(int(DUR / BEAT)):
    at = b * BEAT
    if at < 0.40:
        continue
    e = 1.0 if at >= 0.80 else 0.55
    add(kick(0.46 * e), at)
    add(hat(0.052 * e), at + BEAT * 0.5, pan=0.3)
    add(hat(0.030 * e), at + BEAT * 0.25, pan=-0.25)
    add(hat(0.030 * e), at + BEAT * 0.75, pan=0.25)
    if b % 4 in (1, 3) and at >= 2.4:
        add(clap(0.10 * e), at, pan=0.05)

# 每张卡的切点给一声 tick（12 张卡 × 0.8s）
for i in range(12):
    at = 0.8 + i * 0.8
    add(tick(0.055), at, pan=-0.1 if i % 2 else 0.1)


# ---------- risers & impacts ----------
def riser(dur=1.4, amp=0.09):
    n = int(dur * SR)
    nz = rng.normal(0, 1, n)
    out = np.zeros(n)
    seg = 2048
    for i in range(0, n, seg):
        k = i / n
        c = 500 + 8000 * (k ** 2)
        chunk = nz[i:i + seg]
        if len(chunk) < 32:
            break
        out[i:i + seg] = bandpass(chunk, c * 0.6, min(c * 1.7, 18000))
    return amp * out * (np.linspace(0, 1, n) ** 2)


def impact(amp=0.34):
    n = int(1.2 * SR)
    tt = np.arange(n) / SR
    f = 96 * np.exp(-tt * 4) + 40
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-tt * 3)
    nz = lowpass(rng.normal(0, 1, n), 2000) * np.exp(-tt * 5) * 0.3
    return amp * (body + nz)


add(riser(0.75, 0.10), 10.4 - 0.75)     # into the contact sheet
add(riser(0.60, 0.08), 12.8 - 0.60)     # into the end card
add(impact(0.34), 0.40)                 # title hit
add(impact(0.26), 12.80)                # end card hit

# ---------- mix ----------
mix = np.stack([lowpass(bus[:, 0], 13000), lowpass(bus[:, 1], 13000)], axis=1)

duck = np.ones(N)
for b in range(int(DUR / BEAT)):
    at = b * BEAT
    i = int(at * SR)
    n = int(0.22 * SR)
    if i >= N:
        continue
    n = min(n, N - i)
    duck[i:i + n] *= 1 - 0.20 * np.exp(-np.arange(n) / (0.08 * SR))
mix[:, 0] *= duck
mix[:, 1] *= duck

fi = int(0.25 * SR)
mix[:fi] *= np.linspace(0, 1, fi)[:, None]
fo = int(0.55 * SR)
mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.4

peak = np.max(np.abs(mix))
mix = mix / peak * 0.92
mix = np.tanh(mix * 1.12) * 0.90

out = sys.argv[1] if len(sys.argv) > 1 else "out/bgm.wav"
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
wavfile.write(out, SR, (mix * 32767).astype(np.int16))
print("written", out, "len_s", round(N / SR, 3), "peak", float(np.max(np.abs(mix))))
