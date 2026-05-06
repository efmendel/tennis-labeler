# Copy this file to config.py and fill in your values.
# config.py is gitignored — never commit it.

# Local path to the Google Drive folder containing videos.
# On Mac with Google Drive Desktop, this looks like:
# /Users/<you>/Library/CloudStorage/GoogleDrive-<email>/.shortcut-targets-by-id/<id>/Forehand_data/videos
VIDEO_FOLDER_PATH = "/path/to/your/videos"

# Google Sheets identifiers — ask the project owner for these.
SPREADSHEET_ID = "your-spreadsheet-id"
WORKSHEET_NAME = "Sheet1"
CREDENTIALS_PATH = "credentials.json"

# Your initials — written to the sheet with every saved label.
LABELER_NAME = "XX"

VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".MOV", ".MP4"]

SHORTCUTS = {
    "swing_start": "1",
    "unit_turn": "2",
    "backswing": "3",
    "forward_swing": "4",
    "follow_through": "5",
    "swing_end": "6",
    "next_frame": "Right",
    "prev_frame": "Left",
    "jump_forward": "shift-Right",
    "jump_back": "shift-Left",
    "save_and_next": "n",
    "skip_video": "x",
    "play_pause": "space",
}
