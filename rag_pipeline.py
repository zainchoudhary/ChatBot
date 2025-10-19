from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredWordDocumentLoader, PyPDFLoader
from sentence_transformers import SentenceTransformer
import chromadb
import uuid
import os

chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_or_create_collection(name="rag_collection")

model = SentenceTransformer("all-MiniLM-L6-v2")

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext in [".docx", ".doc"]:
        loader = UnstructuredWordDocumentLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader.load()

def split_text(documents: List[str], chunk_size=300, chunk_overlap=50):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(documents)

def add_file_to_rag(file_path):
    docs = extract_text(file_path)
    print("After Extraction : ",docs)
    chunks = split_text(docs)
    print("The Chunks That Splited From Extracted Document : ",chunks)


    texts, metadatas, ids = [], [], []
    for i, chunk in enumerate(chunks):
        content = getattr(chunk, "page_content", "")
        if not content:
            continue
        content = str(content).strip()
        if content:
            texts.append(content)
            metadatas.append({"source": f"{os.path.basename(file_path)}_chunk_{i}"})
            ids.append(str(uuid.uuid4()))

    if not texts:
        print(f"No valid text found in {file_path}")
        return

    MAX_CHUNK_LENGTH = 2000
    texts = [t[:MAX_CHUNK_LENGTH] for t in texts]

    valid_texts, valid_metadatas, valid_ids, embeddings = [], [], [], []
    for t, m, id_ in zip(texts, metadatas, ids):
        try:
            emb = model.encode(t, convert_to_numpy=True).tolist()
            embeddings.append(emb)
            valid_texts.append(t)
            valid_metadatas.append(m)
            valid_ids.append(id_)
        except Exception as e:
            print("Skipping a chunk due to encoding error:", e)
            continue

    if not embeddings:
        print(f"No valid embeddings for {file_path}")
        return

    collection.add(
        documents=valid_texts,
        metadatas=valid_metadatas,
        ids=valid_ids,
        embeddings=embeddings
    )

    print(f"Added {len(valid_texts)} chunks from {file_path} to ChromaDB")

def query_rag(query, n_results=8):
    query_embedding = model.encode([query], convert_to_numpy=True).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )
    all_chunks = results.get('documents', [])[0]

    print("Retrieved chunks:", all_chunks)
    print("Number of chunks returned:", len(all_chunks))  # ✅
    return all_chunks
