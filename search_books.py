#!/usr/bin/env python3
"""
Semantic search through book knowledge database using DAO layer.
"""
import sys
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install sentence-transformers scikit-learn")
    sys.exit(1)

from dao import BookDAO, ChunkDAO, SearchDAO

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def search_books(query: str, top_k: int = 5, min_similarity: float = 0.3, show_context: bool = False):
    """
    Search books using semantic similarity.

    Args:
        query: Search query
        top_k: Number of results to return
        min_similarity: Minimum cosine similarity threshold
        show_context: If True, also show surrounding chunks
    """
    # Load embedding model
    print(f"Loading model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Load all chunks via DAO
    print("Loading chunks from database...")
    chunks = ChunkDAO.get_all_with_embeddings()

    if not chunks:
        print("Error: No chunks found in database. Run ingest_book.py first.")
        sys.exit(1)

    print(f"Loaded {len(chunks)} chunks")

    # Encode query
    print(f"\nSearching for: '{query}'")
    query_embedding = model.encode([query])[0]

    # Perform search via DAO
    results = SearchDAO.semantic_search(query_embedding, top_k, min_similarity)

    # Display results
    print(f"\nFound {len(results)} result(s):\n")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\n[{i}] Similarity: {result.similarity:.3f}")
        print(f"Book: {result.book_title}")
        if result.book_author:
            print(f"Author: {result.book_author}")
        print(f"Chapter {result.chapter_number}: {result.chapter_title}")
        print(f"Chunk: {result.chunk_index}")
        print(f"\n{result.chunk_text[:500]}...")

        if show_context:
            print("\n--- Context (surrounding chunks) ---")
            show_surrounding_chunks(result.chunk_id)

        print("\n" + "=" * 80)

def show_surrounding_chunks(chunk_id: int, context_size: int = 1):
    """Show chunks before and after the matched chunk."""
    surrounding = ChunkDAO.get_surrounding(chunk_id, context_size)

    # Get the target chunk to know its index
    target = ChunkDAO.get_by_id(chunk_id)
    if not target:
        return

    for chunk in surrounding:
        if chunk.id == chunk_id:
            continue
        position = "before" if chunk.chunk_index < target.chunk_index else "after"
        print(f"\nChunk {chunk.chunk_index} ({position}):")
        print(f"{chunk.chunk_text[:300]}...")

def list_books():
    """List all books in the database using DAO."""
    books = BookDAO.get_all()
    stats = BookDAO.get_stats()

    print("Books in database:\n")
    print("=" * 80)

    for book in books:
        print(f"\nID: {book.id}")
        print(f"Title: {book.title}")
        if book.author:
            print(f"Author: {book.author}")
        print(f"Chapters: {book.chapter_count}, Chunks: {book.chunk_count}")

    print("\n" + "=" * 80)
    print(f"\nTotal: {stats['total_books']} books, {stats['total_chunks']} chunks")
    print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Search:     python search_books.py 'your query' [--top 10] [--context]")
        print("  List books: python search_books.py --list")
        print("\nOptions:")
        print("  --top N       Number of results (default: 5)")
        print("  --context     Show surrounding chunks for context")
        print("  --min SCORE   Minimum similarity score (default: 0.3)")
        sys.exit(1)

    if sys.argv[1] == '--list':
        list_books()
        sys.exit(0)

    query = sys.argv[1]
    top_k = 5
    show_context = False
    min_similarity = 0.3

    # Parse options
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--top' and i + 1 < len(sys.argv):
            top_k = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--context':
            show_context = True
            i += 1
        elif sys.argv[i] == '--min' and i + 1 < len(sys.argv):
            min_similarity = float(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    search_books(query, top_k, min_similarity, show_context)
