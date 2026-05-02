import logging
from collections.abc import Sequence

from config import LOG_PATH
from models import Book, Borrowing


def setup_logging() -> None:
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        encoding="utf-8",
    )


def prompt_required(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("Значение не может быть пустым.")


def prompt_int(label: str) -> int:
    while True:
        value = input(f"{label}: ").strip()
        try:
            return int(value)
        except ValueError:
            print("Введите целое число.")


def print_books(books: Sequence[Book]) -> None:
    rows = []
    for book in books:
        if book.is_borrowed:
            status = f"выдана: {book.current_reader} с {book.borrow_date}"
        else:
            status = "доступна"
        rows.append([book.id, book.title, book.author, status])
    print_table(["ID", "Название", "Автор", "Статус"], rows, "Каталог пуст.")


def print_borrowings(items: Sequence[Borrowing], empty_message: str = "Нет выданных книг.") -> None:
    rows = [
        [
            item.id,
            item.book_id,
            item.title,
            item.author,
            item.user_name,
            item.borrow_date,
            item.return_date or "не возвращена",
        ]
        for item in items
    ]
    print_table(
        ["ID выдачи", "ID книги", "Название", "Автор", "Читатель", "Выдана", "Возврат"],
        rows,
        empty_message,
    )


def print_table(headers: Sequence[str], rows: Sequence[Sequence[object]], empty_message: str) -> None:
    if not rows:
        print(empty_message)
        return

    prepared_rows = [[str(cell) for cell in row] for row in rows]
    widths = [
        max(len(str(header)), *(len(row[index]) for row in prepared_rows))
        for index, header in enumerate(headers)
    ]
    line = " | ".join(str(header).ljust(widths[index]) for index, header in enumerate(headers))
    separator = "-+-".join("-" * width for width in widths)
    print(line)
    print(separator)
    for row in prepared_rows:
        print(" | ".join(row[index].ljust(widths[index]) for index in range(len(headers))))
