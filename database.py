import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from config import DB_PATH
from models import Book, Borrowing


class LibraryError(Exception):
    pass


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            is_borrowed INTEGER NOT NULL DEFAULT 0,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS borrowings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            borrow_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
        CREATE INDEX IF NOT EXISTS idx_books_deleted ON books(is_deleted);
        CREATE INDEX IF NOT EXISTS idx_borrowings_book_id ON borrowings(book_id);
        CREATE INDEX IF NOT EXISTS idx_borrowings_user_name ON borrowings(user_name);
        CREATE INDEX IF NOT EXISTS idx_borrowings_return_date ON borrowings(return_date);
        """
    )
    _ensure_column(connection, "books", "is_deleted", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "books", "created_at", "TEXT")
    connection.execute(
        "UPDATE books SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL OR created_at = ''"
    )
    connection.commit()


def add_book(connection: sqlite3.Connection, title: str, author: str) -> int:
    title = _required(title, "Название книги")
    author = _required(author, "Автор")
    cursor = connection.execute(
        "INSERT INTO books (title, author) VALUES (?, ?)",
        (title, author),
    )
    connection.commit()
    return int(cursor.lastrowid)


def list_books(connection: sqlite3.Connection) -> list[Book]:
    rows = connection.execute(
        """
        SELECT
            b.id,
            b.title,
            b.author,
            b.is_borrowed,
            br.user_name AS current_reader,
            br.borrow_date
        FROM books b
        LEFT JOIN borrowings br
            ON br.book_id = b.id AND br.return_date IS NULL
        WHERE b.is_deleted = 0
        ORDER BY b.id
        """
    ).fetchall()
    return [_book_from_row(row) for row in rows]


def search_books_by_author(connection: sqlite3.Connection, query: str) -> list[Book]:
    query = _required(query, "Фамилия или часть имени автора")
    rows = connection.execute(
        """
        SELECT
            b.id,
            b.title,
            b.author,
            b.is_borrowed,
            br.user_name AS current_reader,
            br.borrow_date
        FROM books b
        LEFT JOIN borrowings br
            ON br.book_id = b.id AND br.return_date IS NULL
        WHERE b.is_deleted = 0 AND LOWER(b.author) LIKE LOWER(?)
        ORDER BY b.author, b.title
        """,
        (f"%{query}%",),
    ).fetchall()
    return [_book_from_row(row) for row in rows]


def borrow_book(
    connection: sqlite3.Connection,
    book_id: int,
    user_name: str,
    borrow_date: Optional[str] = None,
) -> int:
    user_name = _required(user_name, "Имя читателя")
    borrow_date = borrow_date or date.today().isoformat()
    _validate_date(borrow_date, "Дата выдачи")

    try:
        connection.execute("BEGIN")
        book = _get_active_book(connection, book_id)
        if book is None:
            raise LibraryError(f"Книга с ID {book_id} не найдена.")
        if book["is_borrowed"]:
            raise LibraryError(f"Книга с ID {book_id} уже выдана.")

        cursor = connection.execute(
            """
            INSERT INTO borrowings (book_id, user_name, borrow_date)
            VALUES (?, ?, ?)
            """,
            (book_id, user_name, borrow_date),
        )
        connection.execute(
            "UPDATE books SET is_borrowed = 1 WHERE id = ?",
            (book_id,),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise


def return_book(
    connection: sqlite3.Connection,
    book_id: int,
    return_date: Optional[str] = None,
) -> None:
    return_date = return_date or date.today().isoformat()
    _validate_date(return_date, "Дата возврата")

    try:
        connection.execute("BEGIN")
        book = _get_active_book(connection, book_id)
        if book is None:
            raise LibraryError(f"Книга с ID {book_id} не найдена.")
        if not book["is_borrowed"]:
            raise LibraryError(f"Книга с ID {book_id} не выдавалась.")

        borrowing = connection.execute(
            """
            SELECT id, borrow_date
            FROM borrowings
            WHERE book_id = ? AND return_date IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (book_id,),
        ).fetchone()
        if borrowing is None:
            raise LibraryError(f"Активная выдача для книги с ID {book_id} не найдена.")
        if return_date < borrowing["borrow_date"]:
            raise LibraryError("Дата возврата не может быть раньше даты выдачи.")

        connection.execute(
            "UPDATE borrowings SET return_date = ? WHERE id = ?",
            (return_date, borrowing["id"]),
        )
        connection.execute(
            "UPDATE books SET is_borrowed = 0 WHERE id = ?",
            (book_id,),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def list_borrowed_books(connection: sqlite3.Connection) -> list[Borrowing]:
    rows = connection.execute(
        """
        SELECT
            br.id,
            br.book_id,
            b.title,
            b.author,
            br.user_name,
            br.borrow_date,
            br.return_date
        FROM borrowings br
        JOIN books b ON b.id = br.book_id
        WHERE br.return_date IS NULL
        ORDER BY br.borrow_date, br.id
        """
    ).fetchall()
    return [_borrowing_from_row(row) for row in rows]


def delete_book(connection: sqlite3.Connection, book_id: int) -> None:
    book = _get_active_book(connection, book_id)
    if book is None:
        raise LibraryError(f"Книга с ID {book_id} не найдена.")
    if book["is_borrowed"]:
        raise LibraryError("Нельзя удалить книгу, которая сейчас выдана.")

    connection.execute(
        "UPDATE books SET is_deleted = 1 WHERE id = ?",
        (book_id,),
    )
    connection.commit()


def reader_history(connection: sqlite3.Connection, user_name: str) -> list[Borrowing]:
    user_name = _required(user_name, "Имя читателя")
    rows = connection.execute(
        """
        SELECT
            br.id,
            br.book_id,
            b.title,
            b.author,
            br.user_name,
            br.borrow_date,
            br.return_date
        FROM borrowings br
        JOIN books b ON b.id = br.book_id
        WHERE LOWER(br.user_name) = LOWER(?)
        ORDER BY br.borrow_date DESC, br.id DESC
        """,
        (user_name,),
    ).fetchall()
    return [_borrowing_from_row(row) for row in rows]


def overdue_books(connection: sqlite3.Connection, days: int = 14) -> list[Borrowing]:
    if days < 1:
        raise LibraryError("Количество дней должно быть положительным.")
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = connection.execute(
        """
        SELECT
            br.id,
            br.book_id,
            b.title,
            b.author,
            br.user_name,
            br.borrow_date,
            br.return_date
        FROM borrowings br
        JOIN books b ON b.id = br.book_id
        WHERE br.return_date IS NULL AND br.borrow_date < ?
        ORDER BY br.borrow_date, br.id
        """,
        (cutoff,),
    ).fetchall()
    return [_borrowing_from_row(row) for row in rows]


def export_borrowed_to_csv(connection: sqlite3.Connection, path: Path | str) -> int:
    import csv

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    borrowed = list_borrowed_books(connection)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["ID выдачи", "ID книги", "Название", "Автор", "Читатель", "Дата выдачи"])
        for item in borrowed:
            writer.writerow([item.id, item.book_id, item.title, item.author, item.user_name, item.borrow_date])
    return len(borrowed)


def _get_active_book(connection: sqlite3.Connection, book_id: int) -> Optional[sqlite3.Row]:
    return connection.execute(
        "SELECT * FROM books WHERE id = ? AND is_deleted = 0",
        (book_id,),
    ).fetchone()


def _book_from_row(row: sqlite3.Row) -> Book:
    return Book(
        id=row["id"],
        title=row["title"],
        author=row["author"],
        is_borrowed=bool(row["is_borrowed"]),
        current_reader=row["current_reader"],
        borrow_date=row["borrow_date"],
    )


def _borrowing_from_row(row: sqlite3.Row) -> Borrowing:
    return Borrowing(
        id=row["id"],
        book_id=row["book_id"],
        title=row["title"],
        author=row["author"],
        user_name=row["user_name"],
        borrow_date=row["borrow_date"],
        return_date=row["return_date"],
    )


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _required(value: str, label: str) -> str:
    value = (value or "").strip()
    if not value:
        raise LibraryError(f"{label} не может быть пустым.")
    return value


def _validate_date(value: str, label: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise LibraryError(f"{label} должна быть в формате ГГГГ-ММ-ДД.") from exc
