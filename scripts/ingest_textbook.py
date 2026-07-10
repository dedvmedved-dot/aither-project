#!/usr/bin/env python3
"""
Chunk textbook .md files, embed with multilingual model, load into ChromaDB.

Usage: python3 ingest_textbook.py [--reset]
  --reset  : drop existing collection before loading
"""

import os, re, sys, hashlib
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────
TEXTBOOK_DIR = "/root/aither-project/docs/training-manual"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "textbook"
CHUNK_SIZE = 1000       # target chars per chunk
CHUNK_OVERLAP = 200     # overlap between chunks
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Files to process (skip TOC-only files)
SKIP_FILES = {
    "00-master-toc.md", "01-part1-theory-toc.md", "02-part2-deployment-toc.md",
    "03-part3-development-toc.md", "04-appendices-labs-toc.md",
    "05-part4-production-toc.md", "TOC.md", "TOC-detailed.md",
}

# ── Helpers ───────────────────────────────────────────────────────────────

def clean_markdown(text: str) -> str:
    """Strip DOT blocks, excessive whitespace, but keep structure."""
    # Replace DOT code blocks with placeholder
    text = re.sub(r'```dot\n.*?```', '[ДИАГРАММА]', text, flags=re.DOTALL)
    # Replace other code blocks with placeholder  
    text = re.sub(r'```.*?```', '[КОД]', text, flags=re.DOTALL)
    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_by_sections(markdown: str, source_file: str, chapter_title: str) -> list[dict]:
    """
    Split markdown by ## and ### headers into chunks.
    Returns list of {id, text, metadata}.
    """
    chunks = []
    lines = markdown.split('\n')
    
    current_section = chapter_title
    current_lines = []
    
    for line in lines:
        if line.startswith('## ') or line.startswith('### '):
            # Save current chunk
            if current_lines:
                text = '\n'.join(current_lines).strip()
                if len(text) > 100:  # skip tiny sections
                    chunk_id = hashlib.md5(text.encode()).hexdigest()[:16]
                    chunks.append({
                        "id": f"{source_file}_{chunk_id}",
                        "text": text,
                        "metadata": {
                            "source": source_file,
                            "chapter": chapter_title,
                            "section": current_section,
                            "chars": len(text),
                        }
                    })
            current_section = line.lstrip('#').strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    
    # Last section
    if current_lines:
        text = '\n'.join(current_lines).strip()
        if len(text) > 100:
            chunk_id = hashlib.md5(text.encode()).hexdigest()[:16]
            chunks.append({
                "id": f"{source_file}_{chunk_id}",
                "text": text,
                "metadata": {
                    "source": source_file,
                    "chapter": chapter_title,
                    "section": current_section,
                    "chars": len(text),
                }
            })
    
    # Split large chunks (>2000 chars) into smaller pieces
    final_chunks = []
    for ch in chunks:
        if len(ch["text"]) <= 2000:
            final_chunks.append(ch)
        else:
            # Split by paragraphs
            paras = ch["text"].split('\n\n')
            sub_text = ""
            sub_idx = 0
            for para in paras:
                if len(sub_text) + len(para) < CHUNK_SIZE:
                    sub_text += para + '\n\n'
                else:
                    if sub_text.strip():
                        final_chunks.append({
                            "id": f"{ch['id']}_p{sub_idx}",
                            "text": sub_text.strip(),
                            "metadata": {**ch["metadata"], "sub_chunk": sub_idx},
                        })
                        sub_idx += 1
                    sub_text = para + '\n\n'
            if sub_text.strip():
                final_chunks.append({
                    "id": f"{ch['id']}_p{sub_idx}",
                    "text": sub_text.strip(),
                    "metadata": {**ch["metadata"], "sub_chunk": sub_idx},
                })
    
    return final_chunks


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    reset = "--reset" in sys.argv
    
    print("🔧 Loading embedding model...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    print(f"   Model: {MODEL_NAME}, dim={model.get_sentence_embedding_dimension()}")
    
    print("📚 Connecting to ChromaDB...")
    import chromadb
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"   Dropped existing collection '{COLLECTION_NAME}'")
        except Exception:
            pass
    
    coll = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Учебник Aither: 24 главы", "model": MODEL_NAME}
    )
    
    # Phase 1: chunk all files
    print("📄 Chunking textbook...")
    all_chunks = []
    
    for md_file in sorted(Path(TEXTBOOK_DIR).glob("*.md")):
        fname = md_file.name
        if fname in SKIP_FILES:
            continue
        
        with open(md_file) as f:
            content = f.read()
        
        # Extract chapter title from first # heading
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        chapter_title = title_match.group(1) if title_match else fname
        
        content = clean_markdown(content)
        chunks = chunk_by_sections(content, fname, chapter_title)
        all_chunks.extend(chunks)
        print(f"   {fname}: {len(chunks)} chunks (chapter: {chapter_title[:60]})")
    
    print(f"\n   Total chunks: {len(all_chunks)}")
    
    # Phase 2: embed and load in batches
    print("\n🧮 Embedding and loading into ChromaDB...")
    
    BATCH = 50
    for i in range(0, len(all_chunks), BATCH):
        batch = all_chunks[i:i+BATCH]
        ids = [c["id"] for c in batch]
        texts = [c["text"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        
        embeddings = model.encode(texts, show_progress_bar=False).tolist()
        
        coll.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        
        pct = min(100, (i + BATCH) * 100 // len(all_chunks))
        print(f"   {pct}% — {i+len(batch)}/{len(all_chunks)} chunks loaded")
    
    print(f"\n✅ Done! {coll.count()} documents in ChromaDB collection '{COLLECTION_NAME}'")


if __name__ == "__main__":
    main()
