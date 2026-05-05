import csv
import os

import gspread
from google.auth.exceptions import GoogleAuthError

from config import CREDENTIALS_PATH, GOOGLE_SHEET_NAME, LABELER_NAME, WORKSHEET_NAME

BACKUP_CSV = "backup_labels.csv"

COLUMNS = [
    "video_name",
    "labeler",
    "swing_start_frame",
    "unit_turn_frame",
    "backswing_frame",
    "forward_swing_frame",
    "follow_through_frame",
    "swing_end_frame",
    "fps",
    "total_frames",
]

_worksheet = None


def _connect():
    global _worksheet
    if _worksheet is not None:
        return _worksheet
    gc = gspread.service_account(filename=CREDENTIALS_PATH)
    sh = gc.open(GOOGLE_SHEET_NAME)
    _worksheet = sh.worksheet(WORKSHEET_NAME)
    return _worksheet


def get_labeled_filenames() -> set[str]:
    """Return the set of video_name values already in the sheet."""
    try:
        ws = _connect()
        values = ws.col_values(1)
        # Skip header row if present
        if values and values[0].lower() == "video_name":
            values = values[1:]
        return set(values)
    except Exception as e:
        print(f"[sheets] Could not fetch labeled filenames: {e}")
        return set()


def append_label(
    video_name: str,
    marks: dict,
    fps: float,
    total_frames: int,
) -> bool:
    """
    Write one label row to the sheet.
    marks: dict mapping phase name -> frame number (or None if not marked).
    Returns True on success, False if fell back to CSV.
    """
    row = [
        video_name,
        LABELER_NAME,
        marks.get("swing_start", ""),
        marks.get("unit_turn", ""),
        marks.get("backswing", ""),
        marks.get("forward_swing", ""),
        marks.get("follow_through", ""),
        marks.get("swing_end", ""),
        round(fps, 3),
        total_frames,
    ]

    try:
        ws = _connect()
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except (GoogleAuthError, gspread.exceptions.GSpreadException, Exception) as e:
        print(f"[sheets] Sheet write failed, saving to {BACKUP_CSV}: {e}")
        _write_backup(row)
        return False


def _write_backup(row: list):
    write_header = not os.path.exists(BACKUP_CSV) or os.path.getsize(BACKUP_CSV) == 0
    with open(BACKUP_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(COLUMNS)
        writer.writerow(row)


if __name__ == "__main__":
    # Quick smoke test — prints already-labeled filenames then appends a test row
    import sys

    print("Fetching labeled filenames...")
    labeled = get_labeled_filenames()
    print(f"  Already labeled: {labeled or '(none)'}")

    test_marks = {
        "swing_start": 10,
        "unit_turn": 20,
        "backswing": 35,
        "forward_swing": 50,
        "follow_through": 70,
    }
    video = "__test_smoke__.mp4"
    print(f"\nAppending test row for '{video}'...")
    ok = append_label(video, test_marks, fps=30.0, total_frames=120)
    if ok:
        print("  Written to sheet successfully.")
    else:
        print(f"  Fell back to {BACKUP_CSV}.")

    sys.exit(0)
