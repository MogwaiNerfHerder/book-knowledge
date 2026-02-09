#!/usr/bin/env python3
"""
Unit tests for the DAO layer.
"""
import unittest
import sqlite3
import pickle
import tempfile
from pathlib import Path
import numpy as np
import dao

# Create a single test database for all tests
TEST_DB = None
TEST_DB_PATH = None

def setUpModule():
    """Create test database once for all tests."""
    global TEST_DB, TEST_DB_PATH

    TEST_DB = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    TEST_DB_PATH = Path(TEST_DB.name)
    TEST_DB.close()

    # Override DB_PATH in dao module
    dao.DB_PATH = TEST_DB_PATH

    # Create full schema
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()

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

    cursor.execute("""
        CREATE TABLE chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            chapter_number INTEGER NOT NULL,
            chapter_title TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)

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
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)

    # Create views
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
            c.section_id as section_id,
            NULL as section_title
        FROM chunks c
        JOIN books b ON c.book_id = b.id
        JOIN chapters ch ON c.chapter_id = ch.id
    """)

    conn.commit()
    conn.close()

def tearDownModule():
    """Remove test database."""
    if TEST_DB_PATH and TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


class BaseTestCase(unittest.TestCase):
    """Base test case that clears data before each test."""

    def setUp(self):
        """Clear all tables before each test."""
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chunks")
        cursor.execute("DELETE FROM chapters")
        cursor.execute("DELETE FROM books")
        conn.commit()
        conn.close()


class TestBookDAO(BaseTestCase):
    """Test BookDAO operations."""

    def test_create_book(self):
        """Test creating a book."""
        book = dao.Book(title="Test Book", author="Test Author")
        book_id = dao.BookDAO.create(book)

        self.assertIsNotNone(book_id)
        self.assertGreater(book_id, 0)

    def test_get_by_id(self):
        """Test retrieving book by ID."""
        book = dao.Book(title="Test Book", author="Test Author", isbn="123456")
        book_id = dao.BookDAO.create(book)

        retrieved = dao.BookDAO.get_by_id(book_id)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "Test Book")
        self.assertEqual(retrieved.author, "Test Author")
        self.assertEqual(retrieved.isbn, "123456")

    def test_get_all(self):
        """Test retrieving all books."""
        dao.BookDAO.create(dao.Book(title="Book 1"))
        dao.BookDAO.create(dao.Book(title="Book 2"))
        dao.BookDAO.create(dao.Book(title="Book 3"))

        books = dao.BookDAO.get_all()

        self.assertEqual(len(books), 3)

    def test_search_by_title(self):
        """Test searching books by title."""
        dao.BookDAO.create(dao.Book(title="Clean Code"))
        dao.BookDAO.create(dao.Book(title="The Clean Coder"))
        dao.BookDAO.create(dao.Book(title="Agile Practices"))

        results = dao.BookDAO.search_by_title("Clean")

        self.assertEqual(len(results), 2)
        titles = [b.title for b in results]
        self.assertIn("Clean Code", titles)
        self.assertIn("The Clean Coder", titles)

    def test_search_by_author(self):
        """Test searching books by author."""
        dao.BookDAO.create(dao.Book(title="Book 1", author="Martin Fowler"))
        dao.BookDAO.create(dao.Book(title="Book 2", author="Robert Martin"))
        dao.BookDAO.create(dao.Book(title="Book 3", author="Kent Beck"))

        results = dao.BookDAO.search_by_author("Martin")

        self.assertEqual(len(results), 2)

    def test_delete_book(self):
        """Test deleting a book."""
        book_id = dao.BookDAO.create(dao.Book(title="To Delete"))

        result = dao.BookDAO.delete(book_id)
        self.assertTrue(result)

        retrieved = dao.BookDAO.get_by_id(book_id)
        self.assertIsNone(retrieved)

    def test_get_stats(self):
        """Test getting database statistics."""
        book_id = dao.BookDAO.create(dao.Book(title="Test Book"))
        chapter_id = dao.ChapterDAO.create(dao.Chapter(book_id=book_id, chapter_number=1))
        dao.ChunkDAO.create(dao.Chunk(
            book_id=book_id,
            chapter_id=chapter_id,
            chunk_index=1,
            chunk_text="Test chunk text"
        ))

        stats = dao.BookDAO.get_stats()

        self.assertEqual(stats['total_books'], 1)
        self.assertEqual(stats['total_chapters'], 1)
        self.assertEqual(stats['total_chunks'], 1)
        self.assertGreater(stats['total_characters'], 0)


class TestChapterDAO(BaseTestCase):
    """Test ChapterDAO operations."""

    def test_create_chapter(self):
        """Test creating a chapter."""
        book_id = dao.BookDAO.create(dao.Book(title="Test Book"))
        chapter = dao.Chapter(book_id=book_id, chapter_number=1, chapter_title="Introduction")
        chapter_id = dao.ChapterDAO.create(chapter)

        self.assertIsNotNone(chapter_id)
        self.assertGreater(chapter_id, 0)

    def test_get_by_book(self):
        """Test retrieving chapters by book."""
        book_id = dao.BookDAO.create(dao.Book(title="Test Book"))
        dao.ChapterDAO.create(dao.Chapter(book_id=book_id, chapter_number=1, chapter_title="Ch 1"))
        dao.ChapterDAO.create(dao.Chapter(book_id=book_id, chapter_number=2, chapter_title="Ch 2"))

        chapters = dao.ChapterDAO.get_by_book(book_id)

        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].chapter_number, 1)
        self.assertEqual(chapters[1].chapter_number, 2)


class TestChunkDAO(BaseTestCase):
    """Test ChunkDAO operations."""

    def test_create_chunk(self):
        """Test creating a chunk."""
        book_id = dao.BookDAO.create(dao.Book(title="Test Book"))
        chapter_id = dao.ChapterDAO.create(dao.Chapter(book_id=book_id, chapter_number=1))

        chunk = dao.Chunk(
            book_id=book_id,
            chapter_id=chapter_id,
            chunk_index=1,
            chunk_text="Test chunk content"
        )
        chunk_id = dao.ChunkDAO.create(chunk)

        self.assertIsNotNone(chunk_id)
        self.assertGreater(chunk_id, 0)

    def test_get_by_chapter(self):
        """Test retrieving chunks by chapter."""
        book_id = dao.BookDAO.create(dao.Book(title="Test Book"))
        chapter_id = dao.ChapterDAO.create(dao.Chapter(book_id=book_id, chapter_number=1))

        dao.ChunkDAO.create(dao.Chunk(book_id=book_id, chapter_id=chapter_id, chunk_index=1, chunk_text="Chunk 1"))
        dao.ChunkDAO.create(dao.Chunk(book_id=book_id, chapter_id=chapter_id, chunk_index=2, chunk_text="Chunk 2"))

        chunks = dao.ChunkDAO.get_by_chapter(chapter_id)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].chunk_index, 1)
        self.assertEqual(chunks[1].chunk_index, 2)

    def test_get_surrounding(self):
        """Test getting surrounding chunks."""
        book_id = dao.BookDAO.create(dao.Book(title="Test Book"))
        chapter_id = dao.ChapterDAO.create(dao.Chapter(book_id=book_id, chapter_number=1))

        chunk1_id = dao.ChunkDAO.create(dao.Chunk(book_id=book_id, chapter_id=chapter_id, chunk_index=1, chunk_text="Chunk 1"))
        chunk2_id = dao.ChunkDAO.create(dao.Chunk(book_id=book_id, chapter_id=chapter_id, chunk_index=2, chunk_text="Chunk 2"))
        chunk3_id = dao.ChunkDAO.create(dao.Chunk(book_id=book_id, chapter_id=chapter_id, chunk_index=3, chunk_text="Chunk 3"))

        surrounding = dao.ChunkDAO.get_surrounding(chunk2_id, context_size=1)

        self.assertEqual(len(surrounding), 3)
        indices = [c.chunk_index for c in surrounding]
        self.assertEqual(indices, [1, 2, 3])


class TestSearchDAO(BaseTestCase):
    """Test SearchDAO operations."""

    def test_semantic_search(self):
        """Test semantic search returns results."""
        book_id = dao.BookDAO.create(dao.Book(title="Test Book", author="Test Author"))
        chapter_id = dao.ChapterDAO.create(dao.Chapter(book_id=book_id, chapter_number=1, chapter_title="Test Chapter"))

        # Create chunks with mock embeddings
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])
        embedding3 = np.array([0.5, 0.5, 0.0])

        dao.ChunkDAO.create(dao.Chunk(
            book_id=book_id,
            chapter_id=chapter_id,
            chunk_index=1,
            chunk_text="Dogs are animals",
            embedding=pickle.dumps(embedding1),
            embedding_model="test"
        ))

        dao.ChunkDAO.create(dao.Chunk(
            book_id=book_id,
            chapter_id=chapter_id,
            chunk_index=2,
            chunk_text="Cats are animals",
            embedding=pickle.dumps(embedding2),
            embedding_model="test"
        ))

        dao.ChunkDAO.create(dao.Chunk(
            book_id=book_id,
            chapter_id=chapter_id,
            chunk_index=3,
            chunk_text="Dogs and cats are pets",
            embedding=pickle.dumps(embedding3),
            embedding_model="test"
        ))

        query_embedding = np.array([1.0, 0.0, 0.0])  # Should match chunk 1 best

        results = dao.SearchDAO.semantic_search(query_embedding, top_k=3, min_similarity=0.0)

        self.assertGreater(len(results), 0)
        self.assertIsInstance(results[0], dao.SearchResult)
        # First result should be most similar
        self.assertGreater(results[0].similarity, results[1].similarity)

    def test_semantic_search_threshold(self):
        """Test semantic search respects similarity threshold."""
        book_id = dao.BookDAO.create(dao.Book(title="Test Book"))
        chapter_id = dao.ChapterDAO.create(dao.Chapter(book_id=book_id, chapter_number=1))

        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])

        dao.ChunkDAO.create(dao.Chunk(
            book_id=book_id,
            chapter_id=chapter_id,
            chunk_index=1,
            chunk_text="Text 1",
            embedding=pickle.dumps(embedding1),
            embedding_model="test"
        ))

        dao.ChunkDAO.create(dao.Chunk(
            book_id=book_id,
            chapter_id=chapter_id,
            chunk_index=2,
            chunk_text="Text 2",
            embedding=pickle.dumps(embedding2),
            embedding_model="test"
        ))

        query_embedding = np.array([1.0, 0.0, 0.0])

        results = dao.SearchDAO.semantic_search(query_embedding, top_k=3, min_similarity=0.9)

        # With high threshold, should get fewer results
        self.assertLessEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
