# tennis-labeler

A GUI tool for frame-level annotation of tennis forehand swing phases in video. Labels are saved directly to a shared Google Sheet, with automatic CSV fallback if the connection is unavailable.

## What it does

Load videos from a Google Drive folder, navigate frame-by-frame, and mark 6 phases of each forehand swing using keyboard shortcuts. Labels (frame numbers, FPS, total frames, labeler initials) are appended to a shared Google Sheet so multiple annotators can collaborate without conflicts.

**Swing phases labeled:**
1. Swing Start
2. Unit Turn
3. Backswing
4. Forward Swing
5. Follow Through
6. Swing End

---

## Prerequisites

- Python 3.9+
- [Google Drive Desktop](https://www.google.com/drive/download/) installed and synced
- `credentials.json` service account key — ask the project owner

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-org/tennis-labeler.git
cd tennis-labeler
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add credentials

Place the `credentials.json` service account key in the project root. Ask the project owner for this file — it is gitignored and should never be committed.

### 5. Configure

Copy the example config and fill in your values:

```bash
cp config.example.py config.py
```

Edit `config.py`:

| Variable | What to set |
|---|---|
| `VIDEO_FOLDER_PATH` | Local path to the Google Drive video folder (see note below) |
| `SPREADSHEET_ID` | Google Sheet ID — ask the project owner |
| `LABELER_NAME` | Your initials, written to the sheet with every label |

> **Finding `VIDEO_FOLDER_PATH` on Mac:** Open Google Drive Desktop and locate the shared folder. If the folder isn't owned by you, add a Google Drive shortcut to your main drive first. The local path will look like:
> `/Users/<you>/Library/CloudStorage/GoogleDrive-<email>/.shortcut-targets-by-id/<id>/Forehand_data/videos`

---

## Usage

```bash
source venv/bin/activate   # if not already active
python labeler.py
```

The app loads the next unlabeled video automatically. Videos already in the Google Sheet or marked as skipped are skipped.

### Keyboard shortcuts

| Key | Action |
|---|---|
| `←` / `→` | Previous / next frame |
| `Shift+←` / `Shift+→` | Jump back / forward 5 frames |
| `Space` | Play / pause |
| `1` | Mark Swing Start |
| `2` | Mark Unit Turn |
| `3` | Mark Backswing |
| `4` | Mark Forward Swing |
| `5` | Mark Follow Through |
| `6` | Mark Swing End |
| `n` | Save labels and advance to next video |
| `x` | Skip current video |

You can also click the timeline to jump to a frame.

---

## Output

Labels are written to the configured Google Sheet with one row per video:

`video_name | labeler | swing_start | unit_turn | backswing | forward_swing | follow_through | swing_end | fps | total_frames`

If the sheet is unreachable, labels fall back to `backup_labels.csv` in the project root.
