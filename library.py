import argparse
import logging
import sys
from pathlib import Path

from config import CSV_DEFAULT_PATH, DB_PATH, OVERDUE_DAYS
from database import (
    LibraryError,
    add_book,
    borrow_book,
    connect,
    delete_book,
    export_borrowed_to_csv,
    init_db,
    list_books,
    list_borrowed_books,
    overdue_books,
    reader_history,
    return_book,
    search_books_by_author,
)
from utils import print_books, print_borrowings, prompt_int, prompt_required, setup_logging


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with connect(args.db) as connection:
            init_db(connection)
            if args.command is None:
                interactive_menu(connection)
            else:
                run_command(connection, args)
    except LibraryError as exc:
        logging.warning("Ошибка: %s", exc)
        print(f"Ошибка: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nРабота завершена.")
        return 130
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Учёт книг библиотеки №7")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="путь к SQLite-файлу")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add-book", help="добавить книгу")
    add_parser.add_argument("--title", help="название книги")
    add_parser.add_argument("--author", help="автор книги")

    subparsers.add_parser("list", help="показать каталог")

    borrow_parser = subparsers.add_parser("borrow", help="выдать книгу")
    borrow_parser.add_argument("book_id", type=int, help="ID книги")
    borrow_parser.add_argument("--user", help="имя читателя")
    borrow_parser.add_argument("--date", help="дата выдачи в формате ГГГГ-ММ-ДД")

    return_parser = subparsers.add_parser("return", help="вернуть книгу")
    return_parser.add_argument("book_id", type=int, help="ID книги")
    return_parser.add_argument("--date", help="дата возврата в формате ГГГГ-ММ-ДД")

    subparsers.add_parser("borrowed", help="показать все выданные книги")

    delete_parser = subparsers.add_parser("delete-book", help="удалить книгу из каталога")
    delete_parser.add_argument("book_id", type=int, help="ID книги")

    search_parser = subparsers.add_parser("search-author", help="найти книги по автору")
    search_parser.add_argument("query", help="фамилия или часть имени автора")

    history_parser = subparsers.add_parser("history", help="история читателя")
    history_parser.add_argument("user_name", help="имя читателя")

    overdue_parser = subparsers.add_parser("overdue", help="показать просроченные книги")
    overdue_parser.add_argument("--days", type=int, default=OVERDUE_DAYS, help="срок выдачи в днях")

    export_parser = subparsers.add_parser("export-csv", help="экспортировать выданные книги в CSV")
    export_parser.add_argument("path", nargs="?", type=Path, default=CSV_DEFAULT_PATH, help="путь к CSV-файлу")

    subparsers.add_parser("init-db", help="создать таблицы базы данных")
    return parser


def run_command(connection, args: argparse.Namespace) -> None:
    command = args.command
    if command == "add-book":
        title = args.title or prompt_required("Название")
        author = args.author or prompt_required("Автор")
        book_id = add_book(connection, title, author)
        logging.info("Добавлена книга id=%s title=%r author=%r", book_id, title, author)
        print(f"Книга добавлена. ID: {book_id}")
    elif command == "list":
        books = list_books(connection)
        logging.info("Просмотр каталога")
        print_books(books)
    elif command == "borrow":
        user_name = args.user or prompt_required("Имя читателя")
        borrowing_id = borrow_book(connection, args.book_id, user_name, args.date)
        logging.info("Выдана книга book_id=%s borrowing_id=%s user=%r", args.book_id, borrowing_id, user_name)
        print(f"Книга выдана. ID выдачи: {borrowing_id}")
    elif command == "return":
        return_book(connection, args.book_id, args.date)
        logging.info("Возвращена книга book_id=%s", args.book_id)
        print("Книга возвращена.")
    elif command == "borrowed":
        items = list_borrowed_books(connection)
        logging.info("Просмотр выданных книг")
        print_borrowings(items)
    elif command == "delete-book":
        delete_book(connection, args.book_id)
        logging.info("Удалена из каталога книга book_id=%s", args.book_id)
        print("Книга удалена из каталога.")
    elif command == "search-author":
        books = search_books_by_author(connection, args.query)
        logging.info("Поиск по автору query=%r", args.query)
        print_books(books)
    elif command == "history":
        items = reader_history(connection, args.user_name)
        logging.info("Просмотр истории читателя user=%r", args.user_name)
        print_borrowings(items, "История читателя пуста.")
    elif command == "overdue":
        items = overdue_books(connection, args.days)
        logging.info("Просмотр просроченных книг days=%s", args.days)
        print_borrowings(items, "Просроченных книг нет.")
    elif command == "export-csv":
        count = export_borrowed_to_csv(connection, args.path)
        logging.info("Экспорт CSV path=%s rows=%s", args.path, count)
        print(f"CSV-файл создан: {args.path}. Записей: {count}")
    elif command == "init-db":
        logging.info("Инициализация базы данных")
        print("База данных готова.")
    else:
        raise LibraryError(f"Неизвестная команда: {command}")


def interactive_menu(connection) -> None:
    while True:
        print(
            "\n== Библиотека №7 ===\n"
            "1. Добавить книгу\n"
            "2. Просмотреть каталог\n"
            "3. Выдать книгу\n"
            "4. Вернуть книгу\n"
            "5. Просмотреть выданные книги\n"
            "6. Удалить книгу\n"
            "7. Поиск по автору\n"
            "8. История читателя\n"
            "9. Просроченные книги\n"
            "10. Экспорт выданных книг в CSV\n"
            "0. Выход"
        )
        choice = input("Выберите действие: ").strip()
        try:
            if choice == "1":
                handle_add_book(connection)
            elif choice == "2":
                logging.info("Просмотр каталога из меню")
                print_books(list_books(connection))
            elif choice == "3":
                handle_borrow(connection)
            elif choice == "4":
                handle_return(connection)
            elif choice == "5":
                logging.info("Просмотр выданных книг из меню")
                print_borrowings(list_borrowed_books(connection))
            elif choice == "6":
                handle_delete(connection)
            elif choice == "7":
                query = prompt_required("Автор")
                logging.info("Поиск по автору из меню query=%r", query)
                print_books(search_books_by_author(connection, query))
            elif choice == "8":
                user_name = prompt_required("Имя читателя")
                logging.info("История читателя из меню user=%r", user_name)
                print_borrowings(reader_history(connection, user_name), "История читателя пуста.")
            elif choice == "9":
                logging.info("Просмотр просроченных книг из меню")
                print_borrowings(overdue_books(connection), "Просроченных книг нет.")
            elif choice == "10":
                raw_path = input(f"Путь [{CSV_DEFAULT_PATH}]: ").strip()
                path = Path(raw_path) if raw_path else CSV_DEFAULT_PATH
                count = export_borrowed_to_csv(connection, path)
                logging.info("Экспорт CSV из меню path=%s rows=%s", path, count)
                print(f"CSV-файл создан: {path}. Записей: {count}")
            elif choice == "0":
                logging.info("Выход из меню")
                print("До свидания.")
                return
            else:
                print("Выберите пункт меню от 0 до 10.")
        except LibraryError as exc:
            logging.warning("Ошибка меню: %s", exc)
            print(f"Ошибка: {exc}")


def handle_add_book(connection) -> None:
    title = prompt_required("Название")
    author = prompt_required("Автор")
    book_id = add_book(connection, title, author)
    logging.info("Добавлена книга из меню id=%s title=%r author=%r", book_id, title, author)
    print(f"Книга добавлена. ID: {book_id}")


def handle_borrow(connection) -> None:
    book_id = prompt_int("ID книги")
    user_name = prompt_required("Имя читателя")
    borrowing_id = borrow_book(connection, book_id, user_name)
    logging.info("Выдана книга из меню book_id=%s borrowing_id=%s user=%r", book_id, borrowing_id, user_name)
    print(f"Книга выдана. ID выдачи: {borrowing_id}")


def handle_return(connection) -> None:
    book_id = prompt_int("ID книги")
    return_book(connection, book_id)
    logging.info("Возвращена книга из меню book_id=%s", book_id)
    print("Книга возвращена.")


def handle_delete(connection) -> None:
    book_id = prompt_int("ID книги")
    delete_book(connection, book_id)
    logging.info("Удалена из каталога книга из меню book_id=%s", book_id)
    print("Книга удалена из каталога.")


if __name__ == "__main__":
    sys.exit(main())
