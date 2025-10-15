import google.generativeai as genai
import PyPDF2
import docx
import chromadb

# ✅ Configure Gemini API Key
genai.configure(api_key="YOUR_GEMINI_API_KEY")


# ✅ Extract text from PDF
def extract_text_from_pdfd(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


# ✅ Extract text from DOCX
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text


# ✅ Detect file format and extract text
def extract_text(file_path):
    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdfd(file_path)
    elif file_path.lower().endswith(".docx"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file type. Use PDF or DOCX.")


# ✅ Split text into chunks
def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


# ✅ Create embeddings using Gemini
def create_embeddings(chunks):
    embeddings = []
    for chunk in chunks:
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=chunk
        )
        embeddings.append(response["embedding"])
    return embeddings


# ✅ Store in ChromaDB
def store_in_chromadb(chunks, embeddings, collection_name="rag_collection"):
    client = chromadb.Client()

    # Create or get a collection
    collection = client.get_or_create_collection(name=collection_name)

    # Prepare unique IDs
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    # Add to Chroma
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings
    )

    print(f"✅ Stored {len(chunks)} chunks in ChromaDB.")
    return collection


# ✅ Full pipeline
def build_rag_with_chroma(file_path):
    print("📄 Extracting text...")
    text = extract_text(file_path)

    print("✂️ Splitting into chunks...")
    chunks = chunk_text(text, chunk_size=300)

    print("🧠 Creating embeddings with Gemini...")
    embeddings = create_embeddings(chunks)

    print("💾 Storing in ChromaDB...")
    collection = store_in_chromadb(chunks, embeddings)

    return collection


# ✅ Search in ChromaDB
def search_chroma(query, collection, top_k=3):
    response = genai.embed_content(
        model="models/text-embedding-004",
        content=query
    )
    query_embedding = response["embedding"]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return results


# ✅ Example usage
if __name__ == "__main__":
    file_path = "your_file.pdf"  # You can use .docx also
    collection = build_rag_with_chroma(file_path)

    # Test search
    query_text = "Write your question here"
    search_results = search_chroma(query_text, collection)

    print("\n🔍 Top Results:")
    for doc in search_results["documents"][0]:
        print("\n", doc[:200], "...")
