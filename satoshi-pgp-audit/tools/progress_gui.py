#!/usr/bin/env python3
"""Live progress window for a Kangaroo run (Windows/macOS/Linux, stdlib only).

Reads the status JSON the solver writes (spa.lab.kangaroo.solve_checkpointed with
status_path=..., or point it at JeanLucPons Kangaroo's work file via a small
adapter) and shows rate, distinguished points, % of expected work, ETA, and a big
SOLVED banner if the key is found.

Run on your desktop:
    python tools/progress_gui.py --status status.json
No display in a headless server - this is for your Windows box.
"""

import argparse
import json
import os
import time
import tkinter as tk
from tkinter import font


def human_rate(r):
    for unit in ("", "K", "M", "G"):
        if r < 1000:
            return "%.2f %skeys/s" % (r, unit)
        r /= 1000
    return "%.2f Tkeys/s" % r


def eta_years(pct, rate, bits):
    if rate <= 0 or pct <= 0:
        return "—"
    expected = 2 * (2 ** (bits / 2))
    remaining = max(expected * (1 - pct / 100), 0)
    secs = remaining / rate
    yr = secs / 3.156e7
    return "%.0f days" % (secs / 86400) if yr < 1 else "%.2e years" % yr


class Dashboard:
    def __init__(self, root, status_path, refresh_ms=1000):
        self.status_path = status_path
        self.refresh_ms = refresh_ms
        root.title("Kangaroo — puzzle progress")
        root.configure(bg="#0b0f14")
        big = font.Font(size=22, weight="bold")
        med = font.Font(size=13)
        self.rows = {}
        self.left = {}
        for i, label in enumerate(["Puzzle", "Rate", "Distinguished pts",
                                   "Ops", "% of expected", "ETA", "Updated"]):
            lbl = tk.Label(root, text=label, fg="#8aa0b4", bg="#0b0f14", font=med,
                           anchor="w")
            lbl.grid(row=i, column=0, sticky="w", padx=12, pady=4)
            v = tk.Label(root, text="—", fg="#e6edf3", bg="#0b0f14", font=med,
                         anchor="w")
            v.grid(row=i, column=1, sticky="w", padx=12, pady=4)
            self.rows[label] = v
            self.left[label] = lbl
        self.banner = tk.Label(root, text="scanning…", fg="#7ee787", bg="#0b0f14",
                               font=big)
        self.banner.grid(row=8, column=0, columnspan=2, pady=16)
        self.root = root
        self.tick()

    def tick(self):
        try:
            with open(self.status_path) as fh:
                s = json.load(fh)
            if "mode" in s and "sweep" in s.get("mode", ""):
                self._tick_sweep(s)
            else:
                self._tick_kangaroo(s)
        except FileNotFoundError:
            self.banner.config(text="waiting for status file…", fg="#8aa0b4")
        except Exception as exc:
            self.banner.config(text="status error: %s" % exc, fg="#f85149")
        self.root.after(self.refresh_ms, self.tick)

    def _tick_sweep(self, s):
        """Brute-force sweep: ETA is the solver's own honest remaining/rate string."""
        for k, v in (("Puzzle", "Target"), ("Distinguished pts", "Keys scanned"),
                     ("Ops", "Cursor"), ("% of expected", "% of range")):
            self.left[k].config(text=v)
        self.rows["Puzzle"].config(text=s.get("label", "—"))
        self.rows["Rate"].config(text=human_rate(s.get("rate_per_sec", 0)))
        self.rows["Distinguished pts"].config(
            text="{:,}".format(s.get("keys_scanned", 0)))
        self.rows["Ops"].config(text="0x" + (s.get("cursor_hex") or "?"))
        self.rows["% of expected"].config(text="%.6f%%" % s.get("percent", 0))
        self.rows["ETA"].config(text=s.get("eta", "—"))       # honest remaining/rate
        self.rows["Updated"].config(text="%.0fs ago" % (time.time() - s.get("updated", 0)))
        if s.get("solved"):
            self.banner.config(text="SOLVED!", fg="#ffd33d")
            self.rows["Ops"].config(text="key: " + (s.get("private_key_hex") or ""))
        elif time.time() - s.get("updated", 0) > 120:
            self.banner.config(text="stalled? (no update >2m)", fg="#f85149")
        else:
            self.banner.config(text="scanning…", fg="#7ee787")

    def _tick_kangaroo(self, s):
        bits = s.get("puzzle_bits", 0)
        for k in ("Puzzle", "Distinguished pts", "Ops", "% of expected"):
            self.left[k].config(text=k)          # restore Kangaroo labels
        self.rows["Puzzle"].config(text="#%s" % bits)
        self.rows["Rate"].config(text=human_rate(s.get("rate_per_sec", 0)))
        self.rows["Distinguished pts"].config(
            text="{:,}".format(s.get("distinguished_points", 0)))
        self.rows["Ops"].config(text="{:,}".format(s.get("ops", 0)))
        pct = s.get("percent_of_expected", 0)
        self.rows["% of expected"].config(text="%.4f%%" % pct)
        self.rows["ETA"].config(text=eta_years(pct, s.get("rate_per_sec", 0), bits))
        age = time.time() - s.get("updated", 0)
        self.rows["Updated"].config(text="%.0fs ago" % age)
        if s.get("solved"):
            self.banner.config(text="SOLVED!", fg="#ffd33d")
            self.rows["Ops"].config(text="key: " + (s.get("private_key_hex") or ""))
        elif age > 120:
            self.banner.config(text="stalled? (no update >2m)", fg="#f85149")
        else:
            self.banner.config(text="scanning…", fg="#7ee787")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", default="status.json")
    ap.add_argument("--refresh-ms", type=int, default=1000)
    args = ap.parse_args()
    root = tk.Tk()
    Dashboard(root, args.status, args.refresh_ms)
    root.mainloop()


if __name__ == "__main__":
    main()
