import os
import tkinter as tk
from tkinter import messagebox

from config import SHORTCUTS, VIDEO_EXTENSIONS, VIDEO_FOLDER_PATH
from video_player import DISPLAY_H, DISPLAY_W, VideoPlayer
from PIL import ImageTk


class FlatButton(tk.Frame):
    """Custom button that respects colors on macOS."""
    def __init__(self, parent, text, command, bg, fg,
                 hover_bg, font=("Helvetica", 11), padx=14, pady=6, **kwargs):
        super().__init__(parent, bg=bg, cursor="hand2", **kwargs)
        self._bg = bg
        self._hover_bg = hover_bg
        self._command = command
        self._lbl = tk.Label(self, text=text, bg=bg, fg=fg,
                             font=font, padx=padx, pady=pady)
        self._lbl.pack(fill="both", expand=True)
        for w in (self, self._lbl):
            w.bind("<Button-1>", lambda _: command())
            w.bind("<Enter>",    lambda _: self._set_bg(self._hover_bg))
            w.bind("<Leave>",    lambda _: self._set_bg(self._bg))

    def _set_bg(self, color):
        self.config(bg=color)
        self._lbl.config(bg=color)

    def set_text(self, text):
        self._lbl.config(text=text)

PHASE_ORDER = [
    "swing_start",
    "unit_turn",
    "backswing",
    "forward_swing",
    "follow_through",
    "swing_end",
]

PHASE_LABELS = {
    "swing_start":    "Swing Start",
    "unit_turn":      "Unit Turn",
    "backswing":      "Backswing",
    "forward_swing":  "Forward Swing",
    "follow_through": "Follow Through",
    "swing_end":      "Swing End",
}

PHASE_COLORS = {
    "swing_start":    "#888888",
    "unit_turn":      "#4a90d9",
    "backswing":      "#e67e22",
    "forward_swing":  "#27ae60",
    "follow_through": "#8e44ad",
    "swing_end":      "#e74c3c",
}

REQUIRED_PHASES = {"unit_turn", "backswing", "forward_swing", "follow_through", "swing_end"}

SKIPPED_FILE = "skipped.txt"
ERRORS_FILE = "errors.txt"

TIMELINE_H = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_video_list() -> list[str]:
    skipped = _load_skipped()
    videos = []
    for f in sorted(os.listdir(VIDEO_FOLDER_PATH)):
        if any(f.endswith(ext) for ext in VIDEO_EXTENSIONS):
            if f not in skipped:
                videos.append(os.path.join(VIDEO_FOLDER_PATH, f))
    return videos


def _load_skipped() -> set[str]:
    if not os.path.exists(SKIPPED_FILE):
        return set()
    with open(SKIPPED_FILE) as f:
        return {line.strip() for line in f if line.strip()}


def _append_skipped(filename: str):
    with open(SKIPPED_FILE, "a") as f:
        f.write(filename + "\n")


def _log_error(filepath: str, reason: str):
    with open(ERRORS_FILE, "a") as f:
        f.write(f"{filepath}\t{reason}\n")


def _fmt_time(frame: int, fps: float) -> str:
    secs = int(frame / fps)
    return f"{secs // 60:02d}:{secs % 60:02d}"


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

class Labeler:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Shotty Labeler")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a1a")

        self.video_list: list[str] = _load_video_list()
        self.video_index: int = 0
        self.player: VideoPlayer | None = None
        self.target_frame: int = 0
        self.displayed_frame: int = -1
        self.marks: dict[str, int | None] = {p: None for p in PHASE_ORDER}
        self.playing: bool = False
        self.play_timer_id = None

        self._build_ui()
        self._bind_keys()
        self._load_video(0)
        self._render_loop()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self):
        # Status bar
        self.status_var = tk.StringVar(value="Loading...")
        tk.Label(self.root, textvariable=self.status_var, anchor="w",
                 bg="#222", fg="#ccc", padx=8, pady=3).pack(fill="x")

        # Video frame
        self.video_label = tk.Label(self.root, bg="black",
                                    width=DISPLAY_W, height=DISPLAY_H)
        self.video_label.pack()

        # Timeline canvas
        self.timeline = tk.Canvas(self.root, width=DISPLAY_W, height=TIMELINE_H,
                                  bg="#333", highlightthickness=0)
        self.timeline.pack()
        self.timeline.bind("<Button-1>", self._on_timeline_click)
        self.timeline.bind("<B1-Motion>", self._on_timeline_click)

        # Frame info bar
        info_bar = tk.Frame(self.root, bg="#1a1a1a")
        info_bar.pack(fill="x", padx=8, pady=(4, 0))
        self.frame_info_var = tk.StringVar(value="Frame: 000 / 000   FPS: --   00:00 / 00:00")
        tk.Label(info_bar, textvariable=self.frame_info_var,
                 bg="#1a1a1a", fg="#ddd", font=("Courier", 11)).pack(side="left")

        # Playback controls
        ctrl = tk.Frame(self.root, bg="#1a1a1a", pady=4)
        ctrl.pack()
        nav_kw = {"bg": "#2c2c2c", "fg": "#e0e0e0", "hover_bg": "#3d3d3d",
                  "padx": 12, "pady": 4}
        FlatButton(ctrl, "◀◀", lambda: self._seek(self.target_frame - 5), **nav_kw).pack(side="left", padx=2)
        FlatButton(ctrl, "◀",  lambda: self._seek(self.target_frame - 1), **nav_kw).pack(side="left", padx=2)
        self.play_btn = FlatButton(ctrl, "▶  Play", self._toggle_play,
                                   bg="#1a4f99", fg="white", hover_bg="#2563b8",
                                   font=("Helvetica", 11, "bold"), padx=16, pady=4)
        self.play_btn.pack(side="left", padx=2)
        FlatButton(ctrl, "▶",  lambda: self._seek(self.target_frame + 1), **nav_kw).pack(side="left", padx=2)
        FlatButton(ctrl, "▶▶", lambda: self._seek(self.target_frame + 5), **nav_kw).pack(side="left", padx=2)

        # Phase panel
        phase_frame = tk.Frame(self.root, bg="#1a1a1a")
        phase_frame.pack(fill="x", padx=12, pady=(4, 0))
        tk.Label(phase_frame, text="PHASES MARKED:", bg="#1a1a1a",
                 fg="#aaa", font=("Helvetica", 10, "bold")).grid(row=0, column=0,
                 columnspan=3, sticky="w", pady=(0, 2))

        self.phase_labels: dict[str, tk.Label] = {}
        for i, phase in enumerate(PHASE_ORDER):
            key = SHORTCUTS[phase]
            color = PHASE_COLORS[phase]
            tk.Label(phase_frame, text=f"[{key}] {PHASE_LABELS[phase]}:",
                     bg="#1a1a1a", fg=color, width=22, anchor="w",
                     font=("Helvetica", 10)).grid(row=i + 1, column=0, sticky="w")
            lbl = tk.Label(phase_frame, text="--", bg="#1a1a1a",
                           fg="#555", width=16, anchor="w", font=("Courier", 10))
            lbl.grid(row=i + 1, column=1, sticky="w")
            self.phase_labels[phase] = lbl

        # Action buttons
        action = tk.Frame(self.root, bg="#1a1a1a", pady=6)
        action.pack(fill="x", padx=12)
        FlatButton(action, "[X]  Skip", self._skip,
                   bg="#2c2c2c", fg="#e05555", hover_bg="#3a2020",
                   padx=12, pady=5).pack(side="left")
        FlatButton(action, "[N]  Save & Next  →", self._save_and_next,
                   bg="#145a32", fg="white", hover_bg="#1e7d48",
                   font=("Helvetica", 11, "bold"), padx=12, pady=5).pack(side="right")

    # -----------------------------------------------------------------------
    # Key bindings
    # -----------------------------------------------------------------------

    def _bind_keys(self):
        self.root.bind("<Right>",       lambda _: self._seek(self.target_frame + 1))
        self.root.bind("<Left>",        lambda _: self._seek(self.target_frame - 1))
        self.root.bind("<Shift-Right>", lambda _: self._seek(self.target_frame + 5))
        self.root.bind("<Shift-Left>",  lambda _: self._seek(self.target_frame - 5))
        self.root.bind("<space>",       lambda _: self._toggle_play())
        self.root.bind("n",             lambda _: self._save_and_next())
        self.root.bind("x",             lambda _: self._skip())

        for phase in PHASE_ORDER:
            key = SHORTCUTS[phase]
            self.root.bind(key, lambda _, p=phase: self._mark_phase(p))

    # -----------------------------------------------------------------------
    # Video loading
    # -----------------------------------------------------------------------

    def _load_video(self, index: int):
        if self.player:
            self.player.close()
            self.player = None

        self._stop_play()
        self.marks = {p: None for p in PHASE_ORDER}
        self._refresh_phase_panel()

        if index >= len(self.video_list):
            messagebox.showinfo("Done", "All videos labeled!")
            self.root.quit()
            return

        self.video_index = index
        filepath = self.video_list[index]

        try:
            self.player = VideoPlayer(filepath)
        except IOError:
            _log_error(filepath, "unreadable")
            self._load_video(index + 1)
            return

        self.target_frame = 0
        self.displayed_frame = -1

        total = len(self.video_list)
        remaining = total - index
        name = os.path.basename(filepath)
        self.status_var.set(f"Video {index + 1} of {total} — {remaining} remaining   |   {name}")
        self._update_frame_info()
        self._draw_timeline()

    # -----------------------------------------------------------------------
    # Seeking & playback
    # -----------------------------------------------------------------------

    def _seek(self, n: int):
        if not self.player:
            return
        self.target_frame = max(0, min(n, self.player.total_frames - 1))
        self._update_frame_info()
        self._draw_timeline()

    def _toggle_play(self):
        if self.playing:
            self._stop_play()
        else:
            self._start_play()

    def _start_play(self):
        self.playing = True
        self.play_btn.set_text("⏸  Pause")
        self._play_tick()

    def _stop_play(self):
        self.playing = False
        if hasattr(self, "play_btn"):
            self.play_btn.set_text("▶  Play")
        if self.play_timer_id:
            self.root.after_cancel(self.play_timer_id)
            self.play_timer_id = None

    def _play_tick(self):
        if not self.playing or not self.player:
            return
        next_frame = self.target_frame + 1
        if next_frame >= self.player.total_frames:
            self._stop_play()
            return
        self._seek(next_frame)
        delay = max(1, int(1000 / self.player.fps))
        self.play_timer_id = self.root.after(delay, self._play_tick)

    # -----------------------------------------------------------------------
    # Render loop (decoupled from input)
    # -----------------------------------------------------------------------

    def _render_loop(self):
        if self.player and self.target_frame != self.displayed_frame:
            img = self.player.get_frame(self.target_frame)
            if img:
                ph = ImageTk.PhotoImage(img)
                self.video_label.config(image=ph)
                self.video_label.image = ph
                self.displayed_frame = self.target_frame
        self.root.after(33, self._render_loop)

    # -----------------------------------------------------------------------
    # Timeline
    # -----------------------------------------------------------------------

    def _draw_timeline(self):
        if not self.player:
            return
        self.timeline.delete("all")
        total = self.player.total_frames
        w = DISPLAY_W

        # Cursor
        x = int(self.target_frame / max(total - 1, 1) * w)
        self.timeline.create_rectangle(x - 2, 0, x + 2, TIMELINE_H, fill="white", outline="")

        # Phase ticks
        for phase, frame in self.marks.items():
            if frame is not None:
                tx = int(frame / max(total - 1, 1) * w)
                self.timeline.create_rectangle(tx - 1, 0, tx + 1, TIMELINE_H,
                                               fill=PHASE_COLORS[phase], outline="")

    def _on_timeline_click(self, event):
        if not self.player:
            return
        frac = event.x / DISPLAY_W
        frame = int(frac * self.player.total_frames)
        self._seek(frame)

    # -----------------------------------------------------------------------
    # Phase marking
    # -----------------------------------------------------------------------

    def _mark_phase(self, phase: str):
        if not self.player:
            return
        self.marks[phase] = self.target_frame
        self._refresh_phase_panel()
        self._draw_timeline()

    def _refresh_phase_panel(self):
        for phase, lbl in self.phase_labels.items():
            frame = self.marks[phase]
            if frame is not None:
                lbl.config(text=f"frame {frame:04d}  ✓", fg=PHASE_COLORS[phase])
            else:
                lbl.config(text="--", fg="#555")

    # -----------------------------------------------------------------------
    # Frame info bar
    # -----------------------------------------------------------------------

    def _update_frame_info(self):
        if not self.player:
            return
        f = self.target_frame
        total = self.player.total_frames
        fps = self.player.fps
        self.frame_info_var.set(
            f"Frame: {f:04d} / {total - 1:04d}   "
            f"FPS: {fps:.0f}   "
            f"{_fmt_time(f, fps)} / {_fmt_time(total - 1, fps)}"
        )

    # -----------------------------------------------------------------------
    # Save & skip
    # -----------------------------------------------------------------------

    def _save_and_next(self):
        if not self.player:
            return

        missing = [PHASE_LABELS[p] for p in REQUIRED_PHASES if self.marks[p] is None]
        if missing:
            names = ", ".join(missing)
            proceed = messagebox.askyesno(
                "Missing phases",
                f"{names} not marked. Save anyway?"
            )
            if not proceed:
                return

        # Stubbed — will connect to sheets.py in Step 5
        print(f"[stub] Would save: {os.path.basename(self.video_list[self.video_index])}")
        print(f"[stub] Marks: {self.marks}")
        print(f"[stub] FPS: {self.player.fps}  Total frames: {self.player.total_frames}")

        self._load_video(self.video_index + 1)

    def _skip(self):
        if not self.player:
            return
        filename = os.path.basename(self.video_list[self.video_index])
        _append_skipped(filename)
        self._load_video(self.video_index + 1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = Labeler(root)
    root.mainloop()
