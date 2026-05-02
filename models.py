from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str
    is_borrowed: bool
    current_reader: Optional[str] = None
    borrow_date: Optional[str] = None


@dataclass(frozen=True)
class Borrowing:
    id: int
    book_id: int
    title: str
    author: str
    user_name: str
    borrow_date: str
    return_date: Optional[str] = None
