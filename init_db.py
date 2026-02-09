#!/usr/bin/env python3
"""
Initialize the book knowledge database with proper schema.
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "books.db"

def init_database():
    """Create database schema with books, chapters, sections, and chunks."""

    if DB_PATH.exists():
        response = input(f"Database {DB_PATH} already exists. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Books table
    cursor.execute("""
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            isbn TEXT,
            publication_year INTEGER,
            file_path TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Chapters table
    cursor.execute("""
        CREATE TABLE chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            chapter_number INTEGER NOT NULL,
            chapter_title TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)

    # Sections table
    cursor.execute("""
        CREATE TABLE sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id INTEGER NOT NULL,
            section_order INTEGER NOT NULL,
            section_title TEXT,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        )
    """)

    # Chunks table
    cursor.execute("""
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            chapter_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            page_start INTEGER,
            page_end INTEGER,
            embedding BLOB,
            embedding_model TEXT,
            FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)

    # Indexes for common queries
    cursor.execute("CREATE INDEX idx_chunks_book ON chunks(book_id)")
    cursor.execute("CREATE INDEX idx_chunks_chapter ON chunks(chapter_id)")
    cursor.execute("CREATE INDEX idx_chunks_section ON chunks(section_id)")
    cursor.execute("CREATE INDEX idx_chapters_book ON chapters(book_id)")
    cursor.execute("CREATE INDEX idx_sections_chapter ON sections(chapter_id)")

    # Views for easier querying

    # View: book_stats - books with chapter/chunk counts
    cursor.execute("""
        CREATE VIEW book_stats AS
        SELECT
            b.id,
            b.title,
            b.author,
            b.isbn,
            b.publication_year,
            b.file_path,
            b.date_added,
            (SELECT COUNT(*) FROM chapters WHERE book_id = b.id) as chapter_count,
            (SELECT COUNT(*) FROM chunks WHERE book_id = b.id) as chunk_count
        FROM books b
    """)

    # View: chunk_context - chunks with full book/chapter context
    cursor.execute("""
        CREATE VIEW chunk_context AS
        SELECT
            c.id as chunk_id,
            c.chunk_text,
            c.chunk_index,
            c.page_start,
            c.page_end,
            b.id as book_id,
            b.title as book_title,
            b.author as book_author,
            ch.id as chapter_id,
            ch.chapter_number,
            ch.chapter_title,
            s.id as section_id,
            s.section_title
        FROM chunks c
        JOIN books b ON c.book_id = b.id
        JOIN chapters ch ON c.chapter_id = ch.id
        LEFT JOIN sections s ON c.section_id = s.id
    """)

    # View: chapter_stats - chapters with chunk counts
    cursor.execute("""
        CREATE VIEW chapter_stats AS
        SELECT
            ch.id as chapter_id,
            ch.chapter_number,
            ch.chapter_title,
            b.id as book_id,
            b.title as book_title,
            (SELECT COUNT(*) FROM chunks WHERE chapter_id = ch.id) as chunk_count
        FROM chapters ch
        JOIN books b ON ch.book_id = b.id
    """)

    conn.commit()
    conn.close()

    print(f"✓ Database initialized: {DB_PATH}")
    print("✓ Tables created: books, chapters, sections, chunks")
    print("✓ Indexes created for efficient querying")
    print("✓ Views created: book_stats, chunk_context, chapter_stats")

if __name__ == "__main__":
    init_database()
