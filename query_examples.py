#!/usr/bin/env python3
"""
Examples of using database views for easy querying.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "books.db"

def example_queries():
    """Demonstrate easy querying with views."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("DATABASE VIEWS - EXAMPLE QUERIES")
    print("=" * 80)

    # Example 1: Get all books with stats
    print("\n1. All books with chapter/chunk counts:")
    print("-" * 80)
    cursor.execute("SELECT title, author, chapter_count, chunk_count FROM book_stats LIMIT 5")
    for title, author, chapters, chunks in cursor.fetchall():
        author_str = f" by {author}" if author else ""
        print(f"  {title[:50]}{author_str}")
        print(f"    → {chapters} chapters, {chunks} chunks")

    # Example 2: Find books with most chunks
    print("\n2. Books with most content (top 3):")
    print("-" * 80)
    cursor.execute("""
        SELECT title, chunk_count
        FROM book_stats
        ORDER BY chunk_count DESC
        LIMIT 3
    """)
    for title, chunks in cursor.fetchall():
        print(f"  {title[:50]}: {chunks} chunks")

    # Example 3: Get specific book context
    print("\n3. Sample chunks from 'Clean Code' with full context:")
    print("-" * 80)
    cursor.execute("""
        SELECT chunk_text, chapter_number, chapter_title
        FROM chunk_context
        WHERE book_title LIKE '%Clean Code%'
        LIMIT 2
    """)
    for text, ch_num, ch_title in cursor.fetchall():
        print(f"  Chapter {ch_num}: {ch_title}")
        print(f"  {text[:150]}...")
        print()

    # Example 4: Chapter statistics
    print("\n4. Chapters with most chunks (any book):")
    print("-" * 80)
    cursor.execute("""
        SELECT book_title, chapter_number, chapter_title, chunk_count
        FROM chapter_stats
        ORDER BY chunk_count DESC
        LIMIT 5
    """)
    for book, ch_num, ch_title, chunks in cursor.fetchall():
        print(f"  {book[:40]} - Ch {ch_num}: {chunks} chunks")

    # Example 5: Find all content from specific author
    print("\n5. All chunks from Chris Voss:")
    print("-" * 80)
    cursor.execute("""
        SELECT book_title, COUNT(*) as chunks
        FROM chunk_context
        WHERE book_author LIKE '%Voss%'
        GROUP BY book_title
    """)
    for book, chunks in cursor.fetchall():
        print(f"  {book}: {chunks} chunks")

    # Example 6: Books by topic (using title keywords)
    print("\n6. Agile-related books:")
    print("-" * 80)
    cursor.execute("""
        SELECT title, chunk_count
        FROM book_stats
        WHERE title LIKE '%Agile%'
    """)
    for title, chunks in cursor.fetchall():
        print(f"  {title}: {chunks} chunks")

    print("\n" + "=" * 80)

    conn.close()

if __name__ == "__main__":
    example_queries()
