"""
PurmaLinux - Memory Engine
Local RAG (Retrieval Augmented Generation) for semantic search

Features:
- Indexes documents, code, notes, emails
- Creates vector embeddings for semantic search
- Natural language queries: "Where did I save the contract?"
- Automatic indexing of watched directories
- Privacy-first: everything stays local
"""

import os
import json
import asyncio
import sqlite3
import hashlib
import mimetypes
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import time
import re
import subprocess

# ═══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Document:
    """Represents an indexed document"""
    id: str
    path: str
    filename: str
    file_type: str
    content: str
    summary: str = ""
    tags: List[str] = None
    embedding: List[float] = None
    file_hash: str = ""
    size_bytes: int = 0
    created_at: datetime = None
    modified_at: datetime = None
    indexed_at: datetime = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.indexed_at is None:
            self.indexed_at = datetime.now()

@dataclass
class SearchResult:
    """A search result with relevance score"""
    document: Document
    score: float
    matched_chunks: List[str]
    reason: str

@dataclass
class MemoryChunk:
    """A chunk of content with its embedding"""
    id: str
    document_id: str
    content: str
    chunk_index: int
    embedding: List[float] = None
    start_char: int = 0
    end_char: int = 0

# ═══════════════════════════════════════════════════════════════════════════════
#  Vector Storage (Simple Implementation)
# ═══════════════════════════════════════════════════════════════════════════════

class VectorStore:
    """Simple vector store using SQLite + numpy-like operations"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            data_dir = os.path.expanduser("~/.local/share/purma/memory")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "vectors.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT,
                content TEXT,
                summary TEXT,
                tags TEXT,
                file_hash TEXT,
                size_bytes INTEGER,
                created_at DATETIME,
                modified_at DATETIME,
                indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(path)
            )
        """)

        # Chunks table (for long documents)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER,
                embedding TEXT,
                start_char INTEGER,
                end_char INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        """)

        # Watched directories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watched_dirs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                recursive INTEGER DEFAULT 1,
                file_patterns TEXT DEFAULT '*',
                last_scan DATETIME,
                enabled INTEGER DEFAULT 1
            )
        """)

        # Search history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                results_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_path ON documents(path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_type ON documents(file_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id)")

        # FTS5 for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                filename, content, summary, tags,
                content='documents',
                content_rowid='rowid'
            )
        """)

        conn.commit()
        conn.close()

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def add_document(self, doc: Document) -> str:
        """Add a document to the store"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        doc_id = doc.id or self._compute_hash(doc.path + doc.content[:100])

        cursor.execute("""
            INSERT OR REPLACE INTO documents
            (id, path, filename, file_type, content, summary, tags, file_hash,
             size_bytes, created_at, modified_at, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            doc.path,
            doc.filename,
            doc.file_type,
            doc.content,
            doc.summary,
            json.dumps(doc.tags),
            doc.file_hash,
            doc.size_bytes,
            doc.created_at.isoformat() if doc.created_at else None,
            doc.modified_at.isoformat() if doc.modified_at else None,
            datetime.now().isoformat()
        ))

        # Update FTS index
        cursor.execute("""
            INSERT INTO documents_fts(rowid, filename, content, summary, tags)
            SELECT rowid, filename, content, summary, tags
            FROM documents WHERE id = ?
        """, (doc_id,))

        conn.commit()
        conn.close()

        return doc_id

    def add_chunk(self, chunk: MemoryChunk):
        """Add a chunk to the store"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        chunk_id = chunk.id or self._compute_hash(chunk.document_id + str(chunk.chunk_index))

        cursor.execute("""
            INSERT OR REPLACE INTO chunks
            (id, document_id, content, chunk_index, embedding, start_char, end_char)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk_id,
            chunk.document_id,
            chunk.content,
            chunk.chunk_index,
            json.dumps(chunk.embedding) if chunk.embedding else None,
            chunk.start_char,
            chunk.end_char
        ))

        conn.commit()
        conn.close()

    def search_fts(self, query: str, limit: int = 20) -> List[Dict]:
        """Full-text search"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clean query for FTS5
        clean_query = re.sub(r'[^\w\s]', ' ', query)
        search_terms = ' OR '.join(clean_query.split())

        cursor.execute("""
            SELECT d.id, d.path, d.filename, d.file_type, d.summary,
                   snippet(documents_fts, 1, '<mark>', '</mark>', '...', 32) as snippet,
                   bm25(documents_fts) as score
            FROM documents_fts
            JOIN documents d ON documents_fts.rowid = d.rowid
            WHERE documents_fts MATCH ?
            ORDER BY score
            LIMIT ?
        """, (search_terms, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "path": row[1],
                "filename": row[2],
                "file_type": row[3],
                "summary": row[4],
                "snippet": row[5],
                "score": abs(row[6])  # BM25 returns negative scores
            })

        conn.close()
        return results

    def search_semantic(self, query_embedding: List[float], limit: int = 10) -> List[Dict]:
        """Semantic search using embeddings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, document_id, content, embedding
            FROM chunks
            WHERE embedding IS NOT NULL
        """)

        results = []
        for row in cursor.fetchall():
            chunk_embedding = json.loads(row[3])
            score = self._cosine_similarity(query_embedding, chunk_embedding)
            if score > 0.3:  # Threshold
                results.append({
                    "chunk_id": row[0],
                    "document_id": row[1],
                    "content": row[2],
                    "score": score
                })

        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)

        # Enrich with document info
        for result in results[:limit]:
            cursor.execute("""
                SELECT path, filename, file_type, summary
                FROM documents WHERE id = ?
            """, (result["document_id"],))
            doc = cursor.fetchone()
            if doc:
                result["path"] = doc[0]
                result["filename"] = doc[1]
                result["file_type"] = doc[2]
                result["summary"] = doc[3]

        conn.close()
        return results[:limit]

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, path, filename, file_type, content, summary, tags,
                   file_hash, size_bytes, created_at, modified_at, indexed_at
            FROM documents WHERE id = ?
        """, (doc_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "path": row[1],
                "filename": row[2],
                "file_type": row[3],
                "content": row[4],
                "summary": row[5],
                "tags": json.loads(row[6]) if row[6] else [],
                "file_hash": row[7],
                "size_bytes": row[8],
                "created_at": row[9],
                "modified_at": row[10],
                "indexed_at": row[11]
            }
        return None

    def delete_document(self, doc_id: str):
        """Delete a document and its chunks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """Get storage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(size_bytes) FROM documents")
        total_size = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(DISTINCT file_type) FROM documents")
        type_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM watched_dirs WHERE enabled = 1")
        watched_count = cursor.fetchone()[0]

        conn.close()

        return {
            "documents": doc_count,
            "chunks": chunk_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": type_count,
            "watched_directories": watched_count
        }

    def add_watched_dir(self, path: str, recursive: bool = True, patterns: str = "*"):
        """Add a directory to watch for changes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO watched_dirs (path, recursive, file_patterns, enabled)
            VALUES (?, ?, ?, 1)
        """, (os.path.expanduser(path), 1 if recursive else 0, patterns))

        conn.commit()
        conn.close()

    def get_watched_dirs(self) -> List[Dict]:
        """Get all watched directories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT path, recursive, file_patterns, last_scan, enabled
            FROM watched_dirs
        """)

        results = []
        for row in cursor.fetchall():
            results.append({
                "path": row[0],
                "recursive": bool(row[1]),
                "patterns": row[2],
                "last_scan": row[3],
                "enabled": bool(row[4])
            })

        conn.close()
        return results


# ═══════════════════════════════════════════════════════════════════════════════
#  Embedding Generator
# ═══════════════════════════════════════════════════════════════════════════════

class EmbeddingGenerator:
    """Generates embeddings using Ollama or local models"""

    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model
        self.ollama_url = "http://localhost:11434"

    async def generate(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("embedding")
        except Exception as e:
            print(f"Embedding error: {e}")

        # Fallback: simple hash-based pseudo-embedding
        return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Fallback embedding using hash (not semantic, but works for exact matching)"""
        import hashlib

        # Create a deterministic but distributed embedding
        embedding = []
        for i in range(dim):
            hash_input = f"{text}_{i}".encode()
            hash_val = int(hashlib.md5(hash_input).hexdigest(), 16)
            # Normalize to [-1, 1]
            embedding.append((hash_val % 10000) / 5000 - 1)

        # Normalize vector
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    async def generate_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts"""
        return [await self.generate(text) for text in texts]


# ═══════════════════════════════════════════════════════════════════════════════
#  Document Processor
# ═══════════════════════════════════════════════════════════════════════════════

class DocumentProcessor:
    """Processes various document types for indexing"""

    SUPPORTED_TYPES = {
        ".txt": "text",
        ".md": "markdown",
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c_header",
        ".hpp": "cpp_header",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".r": "r",
        ".R": "r",
        ".lua": "lua",
        ".vim": "vim",
        ".conf": "config",
        ".ini": "config",
        ".toml": "toml",
        ".xml": "xml",
        ".csv": "csv",
        ".log": "log",
        ".env": "env",
        ".dockerfile": "dockerfile",
        ".gitignore": "gitignore",
        ".pdf": "pdf",
        ".doc": "word",
        ".docx": "word",
        ".odt": "odt",
    }

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def get_file_type(self, path: str) -> str:
        """Determine file type"""
        ext = Path(path).suffix.lower()
        return self.SUPPORTED_TYPES.get(ext, "unknown")

    def can_process(self, path: str) -> bool:
        """Check if file can be processed"""
        ext = Path(path).suffix.lower()
        return ext in self.SUPPORTED_TYPES

    def extract_content(self, path: str) -> Optional[str]:
        """Extract text content from file"""
        file_type = self.get_file_type(path)

        try:
            if file_type == "pdf":
                return self._extract_pdf(path)
            elif file_type in ("word", "odt"):
                return self._extract_office(path)
            else:
                # Plain text or code
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        except Exception as e:
            print(f"Error extracting content from {path}: {e}")
            return None

    def _extract_pdf(self, path: str) -> Optional[str]:
        """Extract text from PDF"""
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", path, "-"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        except:
            pass

        # Try with Python library
        try:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except:
            pass

        return None

    def _extract_office(self, path: str) -> Optional[str]:
        """Extract text from Office documents"""
        try:
            result = subprocess.run(
                ["pandoc", "-t", "plain", path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        except:
            pass

        return None

    def chunk_content(self, content: str) -> List[Tuple[str, int, int]]:
        """Split content into overlapping chunks"""
        chunks = []

        if len(content) <= self.chunk_size:
            return [(content, 0, len(content))]

        start = 0
        while start < len(content):
            end = start + self.chunk_size

            # Try to break at a natural boundary
            if end < len(content):
                # Look for paragraph break
                para_break = content.rfind("\n\n", start, end)
                if para_break > start + self.chunk_size // 2:
                    end = para_break

                # Or line break
                elif (line_break := content.rfind("\n", start, end)) > start + self.chunk_size // 2:
                    end = line_break

                # Or sentence break
                elif (sent_break := content.rfind(". ", start, end)) > start + self.chunk_size // 2:
                    end = sent_break + 1

            chunk = content[start:end].strip()
            if chunk:
                chunks.append((chunk, start, end))

            start = end - self.chunk_overlap

        return chunks

    def generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate a simple summary (first N characters)"""
        # Clean whitespace
        clean = " ".join(content.split())

        if len(clean) <= max_length:
            return clean

        # Try to break at sentence
        truncated = clean[:max_length]
        last_period = truncated.rfind(".")
        if last_period > max_length // 2:
            return truncated[:last_period + 1]

        return truncated + "..."

    def extract_tags(self, path: str, content: str) -> List[str]:
        """Extract automatic tags from file"""
        tags = []

        # File type tag
        file_type = self.get_file_type(path)
        if file_type != "unknown":
            tags.append(f"type:{file_type}")

        # Directory-based tags
        parts = Path(path).parts
        for part in parts[-4:-1]:  # Last 3 directory levels
            if part and not part.startswith("."):
                tags.append(f"dir:{part}")

        # Content-based tags for code
        if file_type in ("python", "javascript", "typescript"):
            if "import " in content or "from " in content:
                tags.append("has:imports")
            if "def " in content or "function " in content:
                tags.append("has:functions")
            if "class " in content:
                tags.append("has:classes")
            if "test" in path.lower() or "spec" in path.lower():
                tags.append("type:test")

        return tags


# ═══════════════════════════════════════════════════════════════════════════════
#  Memory Engine
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryEngine:
    """Main Memory engine - coordinates indexing and search"""

    def __init__(self):
        self.store = VectorStore()
        self.embedder = EmbeddingGenerator()
        self.processor = DocumentProcessor()
        self.indexing = False
        self._watch_thread = None

    async def index_file(self, path: str, generate_embeddings: bool = True) -> Optional[str]:
        """Index a single file"""
        path = os.path.expanduser(path)

        if not os.path.exists(path):
            return None

        if not self.processor.can_process(path):
            return None

        # Extract content
        content = self.processor.extract_content(path)
        if not content:
            return None

        # Get file info
        stat = os.stat(path)
        file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Create document
        doc = Document(
            id=hashlib.sha256(path.encode()).hexdigest()[:16],
            path=path,
            filename=os.path.basename(path),
            file_type=self.processor.get_file_type(path),
            content=content,
            summary=self.processor.generate_summary(content),
            tags=self.processor.extract_tags(path, content),
            file_hash=file_hash,
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime)
        )

        # Add document
        doc_id = self.store.add_document(doc)

        # Create chunks with embeddings
        if generate_embeddings:
            chunks = self.processor.chunk_content(content)

            for i, (chunk_content, start, end) in enumerate(chunks):
                embedding = await self.embedder.generate(chunk_content)

                chunk = MemoryChunk(
                    id=f"{doc_id}_{i}",
                    document_id=doc_id,
                    content=chunk_content,
                    chunk_index=i,
                    embedding=embedding,
                    start_char=start,
                    end_char=end
                )
                self.store.add_chunk(chunk)

        return doc_id

    async def index_directory(self, path: str, recursive: bool = True,
                              patterns: List[str] = None) -> Dict:
        """Index all files in a directory"""
        path = os.path.expanduser(path)

        if patterns is None:
            patterns = ["*"]

        indexed = []
        failed = []
        skipped = []

        self.indexing = True

        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for filename in files:
                if filename.startswith("."):
                    continue

                filepath = os.path.join(root, filename)

                if not self.processor.can_process(filepath):
                    skipped.append(filepath)
                    continue

                try:
                    doc_id = await self.index_file(filepath)
                    if doc_id:
                        indexed.append({"path": filepath, "id": doc_id})
                    else:
                        skipped.append(filepath)
                except Exception as e:
                    failed.append({"path": filepath, "error": str(e)})

            if not recursive:
                break

        self.indexing = False

        return {
            "indexed": len(indexed),
            "failed": len(failed),
            "skipped": len(skipped),
            "details": {
                "indexed": indexed[:10],  # First 10
                "failed": failed[:10]
            }
        }

    async def search(self, query: str, mode: str = "hybrid",
                     limit: int = 10, file_type: str = None) -> Dict:
        """Search the memory"""
        results = []

        if mode in ("fts", "hybrid"):
            # Full-text search
            fts_results = self.store.search_fts(query, limit=limit * 2)
            for r in fts_results:
                r["search_type"] = "keyword"
                results.append(r)

        if mode in ("semantic", "hybrid"):
            # Semantic search
            query_embedding = await self.embedder.generate(query)
            if query_embedding:
                sem_results = self.store.search_semantic(query_embedding, limit=limit)
                for r in sem_results:
                    r["search_type"] = "semantic"
                    # Check if already in results
                    if not any(existing.get("path") == r.get("path") for existing in results):
                        results.append(r)

        # Filter by file type
        if file_type:
            results = [r for r in results if r.get("file_type") == file_type]

        # Sort by score and deduplicate
        results.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Log search
        conn = sqlite3.connect(self.store.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO search_history (query, results_count) VALUES (?, ?)",
            (query, len(results))
        )
        conn.commit()
        conn.close()

        return {
            "query": query,
            "mode": mode,
            "total_results": len(results),
            "results": results[:limit]
        }

    async def ask(self, question: str) -> Dict:
        """Ask a question about your files (RAG)"""
        # Search for relevant context
        search_results = await self.search(question, mode="hybrid", limit=5)

        # Build context from results
        context_parts = []
        sources = []

        for result in search_results.get("results", []):
            if "content" in result:
                context_parts.append(f"From {result.get('filename', 'unknown')}:\n{result['content'][:500]}")
                sources.append({
                    "path": result.get("path"),
                    "filename": result.get("filename"),
                    "score": result.get("score")
                })
            elif "snippet" in result:
                context_parts.append(f"From {result.get('filename', 'unknown')}:\n{result['snippet']}")
                sources.append({
                    "path": result.get("path"),
                    "filename": result.get("filename"),
                    "score": result.get("score")
                })

        context = "\n\n---\n\n".join(context_parts)

        # This would be enhanced with actual LLM call
        prompt = f"""Based on the following context from the user's files, answer their question.

Context:
{context}

Question: {question}

Answer:"""

        return {
            "question": question,
            "context_used": len(context_parts),
            "sources": sources,
            "prompt_for_llm": prompt,
            "answer": None  # Would be filled by LLM
        }

    def get_status(self) -> Dict:
        """Get Memory status"""
        stats = self.store.get_stats()
        watched = self.store.get_watched_dirs()

        return {
            "indexing": self.indexing,
            "stats": stats,
            "watched_directories": watched
        }

    def add_watch(self, path: str, recursive: bool = True, patterns: str = "*"):
        """Add a directory to watch"""
        self.store.add_watched_dir(path, recursive, patterns)
        return {"status": "added", "path": path}

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a specific document"""
        return self.store.get_document(doc_id)

    def delete_document(self, doc_id: str) -> Dict:
        """Delete a document from memory"""
        self.store.delete_document(doc_id)
        return {"status": "deleted", "id": doc_id}

    def get_recent_searches(self, limit: int = 20) -> List[Dict]:
        """Get recent search queries"""
        conn = sqlite3.connect(self.store.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT query, results_count, created_at
            FROM search_history
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                "query": row[0],
                "results_count": row[1],
                "created_at": row[2]
            })

        conn.close()
        return results


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton Instance
# ═══════════════════════════════════════════════════════════════════════════════

_memory_engine = None

def get_memory_engine() -> MemoryEngine:
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = MemoryEngine()
    return _memory_engine
