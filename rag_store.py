import sqlite3
import numpy as np
from typing import List
import google.generativeai as genai


DB_NAME = "rag_store.db"
genai.configure(api_key="AIzaSyC59fJluw0VU9RQFnbj0nBzqvKy6j9Mtvo")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            embedding BLOB
        )
    """)
    conn.commit()
    conn.close()


# ---------------- EMBEDDINGS ----------------
def get_embedding(text : str) -> np.ndarray:
    from google import genai
    client = genai.Client()
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents="What is the meaning of life?")
    print(result.embeddings)


# ---------------- STORE ----------------
def add_document(content: str):
    embedding = get_embedding(content)  # use the fixed function
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (content, embedding) VALUES (?, ?)",
        (content, embedding.tobytes())
    )
    conn.commit()
    conn.close()
# ---------------- RETRIEVAL ----------------
def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-10)

def search_documents(query: str, top_k: int = 3) -> List[str]:
    query_vec = get_embedding(query)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT content, embedding FROM documents")
    rows = cursor.fetchall()
    conn.close()

    scored_docs = []
    for content, emb_bytes in rows:
        emb = np.frombuffer(emb_bytes, dtype=np.float32)
        score = cosine_similarity(query_vec, emb)
        scored_docs.append((score, content))
    scored_docs.sort(reverse=True, key=lambda x: x[0])
    return [doc for _, doc in scored_docs[:top_k]]

# ---------------- USAGE ----------------
if __name__ == "__main__":
    init_db()
    add_document("This is a sample document for testing RAG.")
    results = search_documents("sample")
    print(results)
