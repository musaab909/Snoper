"""Minimal Tkinter settings window.

Exposes the knobs a user actually touches: recording mode, VOX threshold and
silence timeout, input device, transcription toggle/model, and autostart. Saving
persists to the config file; autostart changes are applied immediately on Windows.
"""

from __future__ import annotations

from ..config import VALID_MODES, Settings


def open_settings_window(settings: Settings) -> None:
    import tkinter as tk
    from tkinter import messagebox, ttk

    from ..audio.capture import list_input_devices

    root = tk.Tk()
    root.title("Snoper — Settings")
    root.resizable(False, False)

    pad = {"padx": 8, "pady": 4}
    row = 0

    def add_label(text):
        nonlocal row
        ttk.Label(root, text=text).grid(column=0, row=row, sticky="w", **pad)

    # Mode
    add_label("Recording mode")
    mode_var = tk.StringVar(value=settings.mode)
    ttk.Combobox(root, textvariable=mode_var, values=list(VALID_MODES), state="readonly").grid(
        column=1, row=row, **pad
    )
    row += 1

    # VOX threshold
    add_label("VOX threshold (0–1)")
    thr_var = tk.DoubleVar(value=settings.vox_threshold)
    ttk.Entry(root, textvariable=thr_var, width=10).grid(column=1, row=row, sticky="w", **pad)
    row += 1

    # Auto-calibrate
    add_label("Auto-calibrate threshold")
    cal_var = tk.BooleanVar(value=settings.auto_calibrate)
    ttk.Checkbutton(root, variable=cal_var).grid(column=1, row=row, sticky="w", **pad)
    row += 1

    # Silence timeout
    add_label("Silence timeout (s)")
    sil_var = tk.DoubleVar(value=settings.silence_timeout_s)
    ttk.Entry(root, textvariable=sil_var, width=10).grid(column=1, row=row, sticky="w", **pad)
    row += 1

    # Input device
    add_label("Input device")
    devices = list_input_devices()
    dev_labels = ["System default"] + [f'{d["index"]}: {d["name"]}' for d in devices]
    dev_var = tk.StringVar(
        value=next(
            (lbl for lbl in dev_labels if lbl.startswith(f"{settings.input_device}:")),
            "System default",
        )
    )
    ttk.Combobox(root, textvariable=dev_var, values=dev_labels, state="readonly", width=30).grid(
        column=1, row=row, **pad
    )
    row += 1

    # System audio
    add_label("Capture system audio (Windows)")
    sys_var = tk.BooleanVar(value=settings.capture_system_audio)
    ttk.Checkbutton(root, variable=sys_var).grid(column=1, row=row, sticky="w", **pad)
    row += 1

    # Transcription
    add_label("Transcribe (Whisper)")
    tr_var = tk.BooleanVar(value=settings.transcribe)
    ttk.Checkbutton(root, variable=tr_var).grid(column=1, row=row, sticky="w", **pad)
    row += 1

    add_label("Whisper model")
    model_var = tk.StringVar(value=settings.whisper_model)
    ttk.Combobox(
        root, textvariable=model_var,
        values=["tiny", "base", "small", "medium", "large"], state="readonly",
    ).grid(column=1, row=row, **pad)
    row += 1

    # Autostart
    add_label("Start on Windows boot")
    auto_var = tk.BooleanVar(value=settings.autostart)
    ttk.Checkbutton(root, variable=auto_var).grid(column=1, row=row, sticky="w", **pad)
    row += 1

    def save():
        try:
            settings.mode = mode_var.get()
            settings.vox_threshold = float(thr_var.get())
            settings.auto_calibrate = bool(cal_var.get())
            settings.silence_timeout_s = float(sil_var.get())
            sel = dev_var.get()
            settings.input_device = None if sel == "System default" else int(sel.split(":")[0])
            settings.capture_system_audio = bool(sys_var.get())
            settings.transcribe = bool(tr_var.get())
            settings.whisper_model = model_var.get()
            settings.autostart = bool(auto_var.get())
            settings.save()
            try:
                from ..platform.autostart_win import apply as apply_autostart

                apply_autostart(settings.autostart)
            except Exception as e:
                messagebox.showwarning("Autostart", f"Could not update autostart: {e}")
            messagebox.showinfo("Snoper", "Settings saved. Restart recording to apply.")
            root.destroy()
        except (ValueError, Exception) as e:
            messagebox.showerror("Snoper", f"Invalid settings: {e}")

    ttk.Button(root, text="Save", command=save).grid(column=0, row=row, **pad)
    ttk.Button(root, text="Cancel", command=root.destroy).grid(column=1, row=row, sticky="w", **pad)

    root.mainloop()
