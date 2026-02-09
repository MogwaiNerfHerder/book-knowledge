# Book Knowledge Database

Semantic search through your book library using AI embeddings.

## Setup

### 1. Install Dependencies

```bash
pip install sentence-transformers scikit-learn pypdf ebooklib beautifulsoup4
```

### 2. Initialize Database

```bash
python init_db.py
```

Creates `books.db` with proper schema (books → chapters → sections → chunks).

## Usage

### Add Books

```bash
# Basic (uses filename as title)
python ingest_book.py path/to/book.pdf

# With metadata
python ingest_book.py book.pdf --title "Switch" --author "Chip Heath"

# Supports: .txt, .pdf, .epub
```

**What it does:**
- Extracts text from book
- Detects chapter boundaries
- Chunks text (500 words, 100-word overlap, paragraph-aware)
- Generates semantic embeddings for each chunk
- Stores with full hierarchical metadata

### Search Books

```bash
# Basic search
python search_books.py "resistance to change"

# More results
python search_books.py "leadership" --top 10

# Show surrounding chunks for context
python search_books.py "decision making" --context

# Higher similarity threshold
python search_books.py "innovation" --min 0.5
```

**Returns:**
- Similarity score
- Book title & author
- Chapter number & title
- Matched text chunk
- Optional: surrounding chunks for context

### List Books

```bash
python search_books.py --list
```

Shows all books with chapter/chunk counts.

## Architecture

### Database Schema

```
books (id, title, author, isbn, file_path, date_added)
  ↓
chapters (id, book_id, chapter_number, chapter_title)
  ↓
sections (id, chapter_id, section_order, section_title)
  ↓
chunks (id, book_id, chapter_id, section_id, chunk_index,
        chunk_text, page_start, page_end, embedding, embedding_model)
```

### Views (for easy querying)

**book_stats**
- Books with chapter/chunk counts
- Usage: `SELECT * FROM book_stats WHERE chunk_count > 100`

**chunk_context**
- Chunks with full book/chapter/section context
- Usage: `SELECT * FROM chunk_context WHERE book_author LIKE '%Voss%'`

**chapter_stats**
- Chapters with chunk counts per book
- Usage: `SELECT * FROM chapter_stats ORDER BY chunk_count DESC`

See `query_examples.py` for more examples.

### Chunking Strategy

1. **Detect chapters**: Pattern matching for "Chapter N" headers
2. **Chunk by paragraphs**: Keep paragraphs intact when possible
3. **Overlap**: 100-word overlap between chunks (preserves context)
4. **Size**: ~500 words per chunk (balances context vs. precision)
5. **Fallback**: If paragraph > 500 words, split by sentences

### Search Method

1. Encode query using `all-MiniLM-L6-v2` (same model as chunks)
2. Calculate cosine similarity between query and all chunk embeddings
3. Return top-K matches above similarity threshold
4. Include full metadata (book, chapter, position) for each match

## Examples

### Adding Books

```bash
python ingest_book.py ~/Documents/switch.pdf --title "Switch" --author "Chip Heath"
```

Output:
```
Loading book: switch.pdf
Loaded 234,567 characters
Detecting chapters...
Found 11 chapters
✓ Book added: Switch (ID: 1)
Loading embedding model: all-MiniLM-L6-v2
  Chapter 1: 23 chunks
  Chapter 2: 31 chunks
  ...
✓ Ingestion complete!
  Total chunks: 287
  Average chunk size: 817 characters
```

### Searching

```bash
python search_books.py "people resist change"
```

Output:
```
Found 3 result(s):

[1] Similarity: 0.847
Book: Switch
Author: Chip Heath
Chapter 2: Direct the Rider
Chunk: 15

People don't resist change, they resist loss. When you frame
change as gain rather than loss, resistance drops dramatically...
```

## Performance

- **Ingestion**: ~2-5 minutes per book (depends on size)
- **Search**: ~1-2 seconds for 10,000 chunks
- **Storage**: ~2KB per chunk (text + embedding)

## Notes

- First run downloads embedding model (~80MB)
- Embeddings are 384-dimensional vectors
- Database uses foreign keys for referential integrity
- Indexes on book_id, chapter_id for fast queries
