#!/usr/bin/env python3
"""
Ingest books into the knowledge database using DAO layer.
Supports: PDF, EPUB, DOCX, TXT files.
Chunks text intelligently and generates embeddings.
"""
import sys
import re
from pathlib import Path
from typing import List, Tuple, Optional
import pickle

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: sentence-transformers not installed")
    print("Install with: pip install sentence-transformers")
    sys.exit(1)

from dao import Book, Chapter, Chunk, BookDAO, ChapterDAO, ChunkDAO

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500  # words
OVERLAP_SIZE = 100  # words

def load_text_file(file_path: Path) -> str:
    """Load plain text file."""
    return file_path.read_text(encoding='utf-8')

def load_pdf(file_path: Path) -> str:
    """Load PDF file."""
    try:
        import pypdf
    except ImportError:
        print("Error: pypdf not installed")
        print("Install with: pip install pypdf")
        sys.exit(1)

    text = []
    with open(file_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            text.append(page.extract_text())
    return '\n\n'.join(text)

def load_epub(file_path: Path) -> str:
    """Load EPUB file."""
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except ImportError:
        print("Error: ebooklib and/or beautifulsoup4 not installed")
        print("Install with: pip install ebooklib beautifulsoup4")
        sys.exit(1)

    book = epub.read_epub(file_path)
    text = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        text.append(soup.get_text())

    return '\n\n'.join(text)

def load_docx(file_path: Path) -> str:
    """Load DOCX file."""
    try:
        import docx
    except ImportError:
        print("Error: python-docx not installed")
        print("Install with: pip install python-docx")
        sys.exit(1)

    doc = docx.Document(file_path)
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    return '\n\n'.join(text)

def load_book(file_path: Path) -> str:
    """Load book based on file extension."""
    suffix = file_path.suffix.lower()

    if suffix == '.txt':
        return load_text_file(file_path)
    elif suffix == '.pdf':
        return load_pdf(file_path)
    elif suffix == '.epub':
        return load_epub(file_path)
    elif suffix == '.docx':
        return load_docx(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

def detect_chapters(text: str) -> List[Tuple[int, str, str]]:
    """
    Detect chapter boundaries in text.
    Returns: [(chapter_num, chapter_title, chapter_text), ...]
    """
    # Simple heuristic: look for "Chapter N" or "CHAPTER N" patterns
    chapter_pattern = re.compile(r'^(Chapter\s+(\d+|[IVX]+)[:\s]+(.*)?)$', re.MULTILINE | re.IGNORECASE)

    chapters = []
    matches = list(chapter_pattern.finditer(text))

    if not matches:
        # No chapters detected, treat whole book as one chapter
        return [(1, "Full Text", text)]

    for i, match in enumerate(matches):
        chapter_start = match.start()
        chapter_header = match.group(1).strip()

        # Extract chapter number (try numeric first, then roman numerals)
        num_match = re.search(r'\d+', chapter_header)
        chapter_num = int(num_match.group()) if num_match else i + 1

        # Extract chapter title (text after "Chapter N:")
        title_match = re.search(r'Chapter\s+\d+[:\s]+(.*)', chapter_header, re.IGNORECASE)
        chapter_title = title_match.group(1).strip() if title_match else chapter_header

        # Get chapter text (from this match to next match or end)
        chapter_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapter_text = text[chapter_start:chapter_end].strip()

        chapters.append((chapter_num, chapter_title, chapter_text))

    return chapters

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP_SIZE) -> List[str]:
    """
    Chunk text into overlapping segments, respecting paragraph boundaries.
    """
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    chunks = []
    current_chunk = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())

        # If single paragraph exceeds chunk size, split it by sentences
        if para_words > chunk_size:
            sentences = re.split(r'([.!?]+\s+)', para)
            for i in range(0, len(sentences), 2):
                sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
                current_chunk.append(sentence)
                current_words += len(sentence.split())

                if current_words >= chunk_size:
                    chunks.append(' '.join(current_chunk))
                    # Keep overlap
                    overlap_text = ' '.join(current_chunk)
                    overlap_words = overlap_text.split()[-overlap:]
                    current_chunk = [' '.join(overlap_words)]
                    current_words = len(overlap_words)
        else:
            # Add paragraph to current chunk
            if current_words + para_words > chunk_size and current_chunk:
                # Finish current chunk
                chunks.append(' '.join(current_chunk))
                # Start new chunk with overlap
                overlap_text = ' '.join(current_chunk)
                overlap_words = overlap_text.split()[-overlap:]
                current_chunk = [' '.join(overlap_words), para]
                current_words = len(overlap_words) + para_words
            else:
                current_chunk.append(para)
                current_words += para_words

    # Add final chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def ingest_book(file_path: Path, title: Optional[str] = None, author: Optional[str] = None):
    """Ingest a book into the database using DAO layer."""

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"Loading book: {file_path}")
    text = load_book(file_path)

    print(f"Loaded {len(text):,} characters")
    print("Detecting chapters...")
    chapters_data = detect_chapters(text)
    print(f"Found {len(chapters_data)} chapter(s)")

    # Use filename as title if not provided
    if not title:
        title = file_path.stem

    # Create book via DAO
    book = Book(
        title=title,
        author=author,
        file_path=str(file_path)
    )
    book_id = BookDAO.create(book)
    print(f"✓ Book added: {title} (ID: {book_id})")

    # Load embedding model
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Process each chapter
    total_chunks = 0
    for chapter_num, chapter_title, chapter_text in chapters_data:
        # Create chapter via DAO
        chapter = Chapter(
            book_id=book_id,
            chapter_number=chapter_num,
            chapter_title=chapter_title
        )
        chapter_id = ChapterDAO.create(chapter)

        # Chunk chapter text
        chunks_text = chunk_text(chapter_text)
        print(f"  Chapter {chapter_num}: {len(chunks_text)} chunks")

        # Generate embeddings for all chunks at once (faster)
        embeddings = model.encode(chunks_text, show_progress_bar=False)

        # Insert chunks via DAO
        for idx, (chunk_txt, embedding) in enumerate(zip(chunks_text, embeddings), 1):
            embedding_blob = pickle.dumps(embedding)
            chunk = Chunk(
                book_id=book_id,
                chapter_id=chapter_id,
                chunk_index=idx,
                chunk_text=chunk_txt,
                embedding=embedding_blob,
                embedding_model=EMBEDDING_MODEL
            )
            ChunkDAO.create(chunk)

        total_chunks += len(chunks_text)

    print(f"\n✓ Ingestion complete!")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Average chunk size: {len(text) // total_chunks:,} characters")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_book.py <book_file> [--title 'Book Title'] [--author 'Author Name']")
        print("\nSupported formats: .txt, .pdf, .epub, .docx")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    # Parse optional arguments
    title = None
    author = None
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--title' and i + 1 < len(sys.argv):
            title = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--author' and i + 1 < len(sys.argv):
            author = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    ingest_book(file_path, title, author)
