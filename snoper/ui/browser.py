"""Search & playback browser over the recordings index.

Tkinter window: search transcripts, list matching recordings (time, duration,
snippet), and play / open / reveal the selected file. Read-only over the SQLite
index produced by transcription + the writer.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..config import Settings
from ..storage.index import RecordingIndex


def _play(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def open_browser_window(settings: Settings) -> None:
    import tkinter as tk
    from tkinter import ttk

    index = RecordingIndex(settings.recordings_dir)

    root = tk.Tk()
    root.title("Snoper — Recordings")
    root.geometry("760x460")

    top = ttk.Frame(root)
    top.pack(fill="x", padx=8, pady=6)
    ttk.Label(top, text="Search:").pack(side="left")
    query_var = tk.StringVar()
    entry = ttk.Entry(top, textvariable=query_var, width=40)
    entry.pack(side="left", padx=6)

    cols = ("started", "duration", "snippet")
    tree = ttk.Treeview(root, columns=cols, show="headings")
    tree.heading("started", text="Started")
    tree.heading("duration", text="Dur (s)")
    tree.heading("snippet", text="Transcript")
    tree.column("started", width=160, anchor="w")
    tree.column("duration", width=70, anchor="e")
    tree.column("snippet", width=500, anchor="w")
    tree.pack(fill="both", expand=True, padx=8, pady=4)

    path_by_item: dict = {}

    def refresh(*_):
        tree.delete(*tree.get_children())
        path_by_item.clear()
        q = query_var.get().strip()
        rows = index.search(q) if q else index.all()
        for r in rows:
            snippet = (r.get("transcript") or "")[:120]
            item = tree.insert(
                "", "end",
                values=(r.get("started_at", ""), round(r.get("duration_s") or 0, 1), snippet),
            )
            path_by_item[item] = r["path"]

    def play_selected(*_):
        sel = tree.selection()
        if sel:
            p = path_by_item.get(sel[0])
            if p and Path(p).exists():
                _play(p)

    def reveal_folder():
        _play(settings.recordings_dir)

    entry.bind("<Return>", refresh)
    tree.bind("<Double-1>", play_selected)

    bottom = ttk.Frame(root)
    bottom.pack(fill="x", padx=8, pady=6)
    ttk.Button(bottom, text="Search", command=refresh).pack(side="left")
    ttk.Button(bottom, text="Play", command=play_selected).pack(side="left", padx=6)
    ttk.Button(bottom, text="Open folder", command=reveal_folder).pack(side="left")
    ttk.Label(bottom, text="(double-click a row to play)").pack(side="right")

    refresh()
    root.mainloop()
