from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOCAL_IMAGE_DIR = BASE_DIR / "bilder"

APP_DIR = BASE_DIR
DB_PATH = BASE_DIR / "rezeptfinder.sqlite3"
IMAGE_DIR = BASE_DIR / "bilder"

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".bmp"]

DAYS = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]