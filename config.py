from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "library.sqlite3"
LOG_PATH = BASE_DIR / "library.log"
CSV_DEFAULT_PATH = BASE_DIR / "borrowed_books.csv"
OVERDUE_DAYS = 14
