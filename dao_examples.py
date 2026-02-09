#!/usr/bin/env python3
"""
Examples of using DAOs instead of raw SQL.
"""
from dao import BookDAO, ChapterDAO, ChunkDAO, SearchDAO
from sentence_transformers import SentenceTransformer

def example_book_operations():
    """Demonstrate book DAO operations."""
    print("=" * 80)
    print("BOOK OPERATIONS")
    print("=" * 80)

    # Get all books
    books = BookDAO.get_all()
    print(f"\n1. All books ({len(books)} total):")
    for book in books[:5]:
        print(f"   [{book.id}] {book.title[:50]}")
        print(f"       Author: {book.author or 'Unknown'}")
        print(f"       Chapters: {book.chapter_count}, Chunks: {book.chunk_count}")

    # Search by title
    print("\n2. Search for 'Agile' books:")
    agile_books = BookDAO.search_by_title("Agile")
    for book in agile_books:
        print(f"   - {book.title} ({book.chunk_count} chunks)")

    # Search by author
    print("\n3. Books by 'Voss':")
    voss_books = BookDAO.search_by_author("Voss")
    for book in voss_books:
        print(f"   - {book.title}")

    # Get specific book
    print("\n4. Get book by ID (1):")
    book = BookDAO.get_by_id(1)
    if book:
        print(f"   Title: {book.title}")
        print(f"   Chapters: {book.chapter_count}")
        print(f"   Chunks: {book.chunk_count}")

    # Database stats
    print("\n5. Database statistics:")
    stats = BookDAO.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value:,}")


def example_chapter_operations():
    """Demonstrate chapter DAO operations."""
    print("\n" + "=" * 80)
    print("CHAPTER OPERATIONS")
    print("=" * 80)

    # Get chapters for a book
    print("\n1. Chapters for book ID 1:")
    chapters = ChapterDAO.get_by_book(1)
    for chapter in chapters[:5]:
        print(f"   Ch {chapter.chapter_number}: {chapter.chapter_title} ({chapter.chunk_count} chunks)")


def example_chunk_operations():
    """Demonstrate chunk DAO operations."""
    print("\n" + "=" * 80)
    print("CHUNK OPERATIONS")
    print("=" * 80)

    # Get chunks for a chapter
    print("\n1. First 3 chunks from chapter 1:")
    chunks = ChunkDAO.get_by_chapter(1)
    for chunk in chunks[:3]:
        print(f"   Chunk {chunk.chunk_index}:")
        print(f"   {chunk.chunk_text[:100]}...")

    # Get surrounding chunks
    print("\n2. Surrounding chunks (chunk ID 100, ±1):")
    surrounding = ChunkDAO.get_surrounding(100, context_size=1)
    for chunk in surrounding:
        print(f"   Chunk {chunk.chunk_index}: {chunk.chunk_text[:80]}...")


def example_search_operations():
    """Demonstrate semantic search with DAO."""
    print("\n" + "=" * 80)
    print("SEMANTIC SEARCH")
    print("=" * 80)

    # Load model
    print("\nLoading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Perform search
    query = "building discipline and focus"
    print(f"\nSearching for: '{query}'")

    query_embedding = model.encode([query])[0]
    results = SearchDAO.semantic_search(query_embedding, top_k=3, min_similarity=0.4)

    print(f"\nFound {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"[{i}] Similarity: {result.similarity:.3f}")
        print(f"    Book: {result.book_title}")
        if result.book_author:
            print(f"    Author: {result.book_author}")
        print(f"    Chapter {result.chapter_number}: {result.chapter_title}")
        print(f"    Text: {result.chunk_text[:150]}...")
        print()


if __name__ == "__main__":
    example_book_operations()
    example_chapter_operations()
    example_chunk_operations()
    example_search_operations()

    print("\n" + "=" * 80)
    print("DAO layer provides clean, type-safe interface to database!")
    print("No more raw SQL in application code.")
    print("=" * 80)
