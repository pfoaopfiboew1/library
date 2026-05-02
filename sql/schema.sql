-- ============================================
-- Библиотека №7 — Создание таблиц
-- ============================================

-- Таблица книг
CREATE TABLE IF NOT EXISTS books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    author      TEXT    NOT NULL,
    is_borrowed INTEGER NOT NULL DEFAULT 0,
    is_deleted  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Таблица выдач
CREATE TABLE IF NOT EXISTS borrowings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL,
    user_name   TEXT    NOT NULL,
    borrow_date TEXT    NOT NULL,
    return_date TEXT,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT
);

-- Индексы для ускорения запросов
CREATE INDEX IF NOT EXISTS idx_books_author          ON books(author);
CREATE INDEX IF NOT EXISTS idx_books_deleted          ON books(is_deleted);
CREATE INDEX IF NOT EXISTS idx_borrowings_book_id     ON borrowings(book_id);
CREATE INDEX IF NOT EXISTS idx_borrowings_user_name   ON borrowings(user_name);
CREATE INDEX IF NOT EXISTS idx_borrowings_return_date ON borrowings(return_date);
