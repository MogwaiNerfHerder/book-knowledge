#!/usr/bin/env python3
"""
Data Access Objects (DAOs) for the book knowledge database.
Provides clean interface for all database operations.
"""
import sqlite3
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

DB_PATH = Path(__file__).parent / "books.db"

@dataclass
class Book:
    """Book entity."""
    id: Optional[int] = None
    title: str = ""
    author: Optional[str] = None
    isbn: Optional[str] = None
    publication_year: Optional[int] = None
    file_path: Optional[str] = None
    date_added: Optional[datetime] = None
    chapter_count: Optional[int] = None
    chunk_count: Optional[int] = None

@dataclass
class Chapter:
    """Chapter entity."""
    id: Optional[int] = None
    book_id: int = 0
    chapter_number: int = 0
    chapter_title: Optional[str] = None
    chunk_count: Optional[int] = None

@dataclass
class Chunk:
    """Chunk entity."""
    id: Optional[int] = None
    section_id: Optional[int] = None
    chapter_id: int = 0
    book_id: int = 0
    chunk_index: int = 0
    chunk_text: str = ""
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    embedding: Optional[bytes] = None
    embedding_model: Optional[str] = None

@dataclass
class SearchResult:
    """Search result with full context."""
    chunk_id: int
    similarity: float
    chunk_text: str
    chunk_index: int
    book_id: int
    book_title: str
    book_author: Optional[str]
    chapter_id: int
    chapter_number: int
    chapter_title: Optional[str]


class DatabaseConnection:
    """Context manager for database connections."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        self.conn.close()


class BookDAO:
    """Data access object for books."""

    @staticmethod
    def create(book: Book) -> int:
        """Create a new book, returns book_id."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                INSERT INTO books (title, author, isbn, publication_year, file_path)
                VALUES (?, ?, ?, ?, ?)
            """, (book.title, book.author, book.isbn, book.publication_year, book.file_path))
            return cursor.lastrowid

    @staticmethod
    def get_by_id(book_id: int) -> Optional[Book]:
        """Get book by ID with stats."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT id, title, author, isbn, publication_year, file_path,
                       date_added, chapter_count, chunk_count
                FROM book_stats
                WHERE id = ?
            """, (book_id,))
            row = cursor.fetchone()
            if row:
                return Book(*row)
        return None

    @staticmethod
    def get_all() -> List[Book]:
        """Get all books with stats."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT id, title, author, isbn, publication_year, file_path,
                       date_added, chapter_count, chunk_count
                FROM book_stats
                ORDER BY date_added DESC
            """)
            return [Book(*row) for row in cursor.fetchall()]

    @staticmethod
    def search_by_title(title_pattern: str) -> List[Book]:
        """Search books by title pattern."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT id, title, author, isbn, publication_year, file_path,
                       date_added, chapter_count, chunk_count
                FROM book_stats
                WHERE title LIKE ?
                ORDER BY title
            """, (f"%{title_pattern}%",))
            return [Book(*row) for row in cursor.fetchall()]

    @staticmethod
    def search_by_author(author_pattern: str) -> List[Book]:
        """Search books by author pattern."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT id, title, author, isbn, publication_year, file_path,
                       date_added, chapter_count, chunk_count
                FROM book_stats
                WHERE author LIKE ?
                ORDER BY title
            """, (f"%{author_pattern}%",))
            return [Book(*row) for row in cursor.fetchall()]

    @staticmethod
    def delete(book_id: int) -> bool:
        """Delete a book (cascades to chapters/chunks)."""
        with DatabaseConnection() as cursor:
            cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

    @staticmethod
    def get_stats() -> Dict[str, int]:
        """Get overall database statistics."""
        with DatabaseConnection() as cursor:
            cursor.execute("SELECT COUNT(*) FROM books")
            total_books = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM chapters")
            total_chapters = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM chunks")
            total_chunks = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(LENGTH(chunk_text)) FROM chunks")
            total_chars = cursor.fetchone()[0] or 0

            return {
                'total_books': total_books,
                'total_chapters': total_chapters,
                'total_chunks': total_chunks,
                'total_characters': total_chars,
                'total_words': total_chars // 5
            }


class ChapterDAO:
    """Data access object for chapters."""

    @staticmethod
    def create(chapter: Chapter) -> int:
        """Create a new chapter, returns chapter_id."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                INSERT INTO chapters (book_id, chapter_number, chapter_title)
                VALUES (?, ?, ?)
            """, (chapter.book_id, chapter.chapter_number, chapter.chapter_title))
            return cursor.lastrowid

    @staticmethod
    def get_by_id(chapter_id: int) -> Optional[Chapter]:
        """Get chapter by ID with stats."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT chapter_id, book_id, chapter_number, chapter_title,
                       book_title, chunk_count
                FROM chapter_stats
                WHERE chapter_id = ?
            """, (chapter_id,))
            row = cursor.fetchone()
            if row:
                return Chapter(id=row[0], book_id=row[1], chapter_number=row[2],
                             chapter_title=row[3], chunk_count=row[5])
        return None

    @staticmethod
    def get_by_book(book_id: int) -> List[Chapter]:
        """Get all chapters for a book."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT chapter_id, book_id, chapter_number, chapter_title, chunk_count
                FROM chapter_stats
                WHERE book_id = ?
                ORDER BY chapter_number
            """, (book_id,))
            return [Chapter(id=row[0], book_id=row[1], chapter_number=row[2],
                          chapter_title=row[3], chunk_count=row[4])
                   for row in cursor.fetchall()]


class ChunkDAO:
    """Data access object for chunks."""

    @staticmethod
    def create(chunk: Chunk) -> int:
        """Create a new chunk, returns chunk_id."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                INSERT INTO chunks (
                    section_id, chapter_id, book_id, chunk_index, chunk_text,
                    page_start, page_end, embedding, embedding_model
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (chunk.section_id, chunk.chapter_id, chunk.book_id, chunk.chunk_index,
                  chunk.chunk_text, chunk.page_start, chunk.page_end,
                  chunk.embedding, chunk.embedding_model))
            return cursor.lastrowid

    @staticmethod
    def get_by_id(chunk_id: int) -> Optional[Chunk]:
        """Get chunk by ID with full context."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT chunk_id, section_id, chapter_id, book_id, chunk_index,
                       chunk_text, page_start, page_end
                FROM chunk_context
                WHERE chunk_id = ?
            """, (chunk_id,))
            row = cursor.fetchone()
            if row:
                return Chunk(id=row[0], section_id=row[1], chapter_id=row[2],
                           book_id=row[3], chunk_index=row[4], chunk_text=row[5],
                           page_start=row[6], page_end=row[7])
        return None

    @staticmethod
    def get_by_chapter(chapter_id: int) -> List[Chunk]:
        """Get all chunks for a chapter."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT chunk_id, section_id, chapter_id, book_id, chunk_index,
                       chunk_text, page_start, page_end
                FROM chunk_context
                WHERE chapter_id = ?
                ORDER BY chunk_index
            """, (chapter_id,))
            return [Chunk(id=row[0], section_id=row[1], chapter_id=row[2],
                        book_id=row[3], chunk_index=row[4], chunk_text=row[5],
                        page_start=row[6], page_end=row[7])
                   for row in cursor.fetchall()]

    @staticmethod
    def get_surrounding(chunk_id: int, context_size: int = 1) -> List[Chunk]:
        """Get chunks surrounding a given chunk."""
        with DatabaseConnection() as cursor:
            # Get the target chunk's position
            cursor.execute("""
                SELECT chapter_id, chunk_index
                FROM chunks
                WHERE id = ?
            """, (chunk_id,))
            chapter_id, chunk_index = cursor.fetchone()

            # Get surrounding chunks
            cursor.execute("""
                SELECT id, section_id, chapter_id, book_id, chunk_index,
                       chunk_text, page_start, page_end
                FROM chunks
                WHERE chapter_id = ?
                AND chunk_index BETWEEN ? AND ?
                ORDER BY chunk_index
            """, (chapter_id, chunk_index - context_size, chunk_index + context_size))

            return [Chunk(id=row[0], section_id=row[1], chapter_id=row[2],
                        book_id=row[3], chunk_index=row[4], chunk_text=row[5],
                        page_start=row[6], page_end=row[7])
                   for row in cursor.fetchall()]

    @staticmethod
    def get_all_with_embeddings() -> List[Tuple]:
        """Get all chunks with embeddings for search."""
        with DatabaseConnection() as cursor:
            cursor.execute("""
                SELECT
                    cc.chunk_id,
                    cc.chunk_text,
                    c.embedding,
                    cc.chunk_index,
                    cc.book_id,
                    cc.book_title,
                    cc.book_author,
                    cc.chapter_id,
                    cc.chapter_number,
                    cc.chapter_title
                FROM chunk_context cc
                JOIN chunks c ON cc.chunk_id = c.id
                WHERE c.embedding IS NOT NULL
                ORDER BY cc.book_id, cc.chapter_number, cc.chunk_index
            """)
            return cursor.fetchall()


class SearchDAO:
    """Data access object for semantic search operations."""

    @staticmethod
    def semantic_search(query_embedding, top_k: int = 5,
                       min_similarity: float = 0.3) -> List[SearchResult]:
        """
        Perform semantic search using pre-computed embeddings.

        Args:
            query_embedding: The embedding vector for the search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of SearchResult objects
        """
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        # Load all chunks with embeddings
        chunks = ChunkDAO.get_all_with_embeddings()

        if not chunks:
            return []

        # Extract embeddings
        embeddings = []
        for chunk in chunks:
            embedding_blob = chunk[2]
            embedding = pickle.loads(embedding_blob)
            embeddings.append(embedding)

        embeddings_matrix = np.array(embeddings)

        # Calculate similarities
        similarities = cosine_similarity([query_embedding], embeddings_matrix)[0]

        # Get top matches
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            similarity = similarities[idx]
            if similarity < min_similarity:
                continue

            chunk_data = chunks[idx]
            results.append(SearchResult(
                chunk_id=chunk_data[0],
                similarity=similarity,
                chunk_text=chunk_data[1],
                chunk_index=chunk_data[3],
                book_id=chunk_data[4],
                book_title=chunk_data[5],
                book_author=chunk_data[6],
                chapter_id=chunk_data[7],
                chapter_number=chunk_data[8],
                chapter_title=chunk_data[9]
            ))

        return results


if __name__ == "__main__":
    # Example usage
    print("=== Book Knowledge DAO Examples ===\n")

    # Get all books
    books = BookDAO.get_all()
    print(f"Total books: {len(books)}")
    if books:
        print(f"Latest: {books[0].title} ({books[0].chunk_count} chunks)")

    # Get stats
    stats = BookDAO.get_stats()
    print(f"\nDatabase stats:")
    for key, value in stats.items():
        print(f"  {key}: {value:,}")

    # Search by author
    voss_books = BookDAO.search_by_author("Voss")
    print(f"\nBooks by Voss: {len(voss_books)}")
    for book in voss_books:
        print(f"  - {book.title}")

    # Get chapters for first book
    if books:
        chapters = ChapterDAO.get_by_book(books[0].id)
        print(f"\nChapters in '{books[0].title}': {len(chapters)}")
