INSERT INTO books (title, author) VALUES ('Мастер и Маргарита', 'Михаил Булгаков');
INSERT INTO books (title, author) VALUES ('Война и мир', 'Лев Толстой');
INSERT INTO books (title, author) VALUES ('Преступление и наказание', 'Фёдор Достоевский');
INSERT INTO books (title, author) VALUES ('Евгений Онегин', 'Александр Пушкин');
INSERT INTO books (title, author) VALUES ('Анна Каренина', 'Лев Толстой');
INSERT INTO books (title, author) VALUES ('Мёртвые души', 'Николай Гоголь');
INSERT INTO books (title, author) VALUES ('Идиот', 'Фёдор Достоевский');
INSERT INTO books (title, author) VALUES ('Собачье сердце', 'Михаил Булгаков');

INSERT INTO borrowings (book_id, user_name, borrow_date)
VALUES (1, 'Егор', '2026-04-20');

INSERT INTO borrowings (book_id, user_name, borrow_date)
VALUES (3, 'Анастасия', '2026-04-25');

UPDATE books SET is_borrowed = 1 WHERE id IN (1, 3);
