import tkinter as tk

import cv2
from PIL import Image, ImageTk

DISPLAY_W = 800
DISPLAY_H = 450


class VideoPlayer:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.cap = cv2.VideoCapture(filepath)
        if not self.cap.isOpened():
            raise IOError(f"Cannot open video: {filepath}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def get_frame(self, n: int) -> Image.Image | None:
        n = max(0, min(n, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, n)
        ok, frame = self.cap.read()
        if not ok:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return _letterbox(rgb, DISPLAY_W, DISPLAY_H)

    def close(self):
        self.cap.release()


def _letterbox(rgb_array, target_w: int, target_h: int) -> Image.Image:
    src = Image.fromarray(rgb_array)
    src_w, src_h = src.size
    scale = min(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    resized = src.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python video_player.py <path_to_video>")
        sys.exit(1)

    path = sys.argv[1]
    player = VideoPlayer(path)
    print(f"Opened: {path}")
    print(f"  FPS: {player.fps}  Frames: {player.total_frames}  Size: {player.width}x{player.height}")

    root = tk.Tk()
    root.title("video_player.py — frame test")

    frame_img = player.get_frame(0)
    photo = ImageTk.PhotoImage(frame_img)
    label = tk.Label(root, image=photo)
    label.pack()

    current = tk.IntVar(value=0)

    def show(n):
        img = player.get_frame(n)
        if img:
            ph = ImageTk.PhotoImage(img)
            label.config(image=ph)
            label.image = ph
            current.set(n)
            info.config(text=f"Frame {n} / {player.total_frames - 1}")

    info = tk.Label(root, text=f"Frame 0 / {player.total_frames - 1}")
    info.pack()

    btn_frame = tk.Frame(root)
    btn_frame.pack()
    tk.Button(btn_frame, text="◀", command=lambda: show(current.get() - 1)).pack(side="left")
    tk.Button(btn_frame, text="▶", command=lambda: show(current.get() + 1)).pack(side="left")

    root.bind("<Left>", lambda _: show(current.get() - 1))
    root.bind("<Right>", lambda _: show(current.get() + 1))
    root.bind("<Shift-Left>", lambda _: show(current.get() - 5))
    root.bind("<Shift-Right>", lambda _: show(current.get() + 5))

    root.mainloop()
    player.close()
