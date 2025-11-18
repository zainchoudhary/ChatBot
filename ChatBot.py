import streamlit as st
import google.generativeai as genai
import sqlite3
import datetime
import uuid
import html
import os
import io
import tempfile
from fpdf import FPDF
from docx import Document
from rag_pipeline import add_file_to_rag, query_rag

# -------------------- CONFIG --------------------
DB_PATH = "chatbot.db"
genai.configure(api_key="AIzaSyCnKIaRkU4yPHfqaaCYLdKIJ7ePj7zdR58")
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

# -------------------- DATABASE --------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            message TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_message(role, message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (user_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
        (st.session_state.user_id, role, message, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def load_messages():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chat_history WHERE user_id=?", (st.session_state.user_id,))
        messages = cursor.fetchall()
        conn.close()
        return [{"role": row[2], "content": row[3]} for row in messages]
    except Exception as e:
        print("Error loading messages:", e)
        return []

def clear_chat_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    conn.close()
    st.session_state.messages = []
    st.success("Chat and uploaded file cleared!")
    st.rerun()

# -------------------- RESPONSIVE STYLES --------------------
def set_custom_styles():
    st.markdown("""
        <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background-color: #000000 !important;
            color: #fff;
        }

        .chat-title {
            background: linear-gradient(270deg, #00dbde, #fc00ff, #ff6a00);
            color:white;
            text-align:center;
            padding:20px;
            border-radius:18px;
            font-size:2.3em;
            font-weight:900;
            letter-spacing:1.3px;
            text-transform:uppercase;
            margin-bottom:20px;
        }

        .file-upload-container {
            background: linear-gradient(135deg, rgba(72,61,139,0.6), rgba(123,31,162,0.6));
            border: 2px solid rgba(255, 255, 255, 0.3); 
            border-radius: 15px;
            box-shadow: 0 4px 25px rgba(0, 0, 0, 0.3); 
            padding: 25px; 
            text-align: center;
            backdrop-filter: blur(12px); 
            margin-bottom: 25px;
            width: 90%;
            max-width: 800px;
            margin-left:auto;
            margin-right:auto;
        }

        .chat-bubble-user {
            display: flex; 
            justify-content: flex-end; 
            margin: 10px 0;
        }
        .chat-bubble-user div {
            background-color: #C7C7C7; 
            color:black; 
            padding:10px 15px;
            border-radius:15px; 
            max-width:80%; 
            word-wrap:break-word;
        }

        .chat-bubble-ai {
            display: flex; 
            justify-content: flex-start; 
            margin: 10px 0;
        }
        .chat-bubble-ai div {
            background-color: #3E494D; 
            color:white; 
            padding:10px 15px;
            border-radius:15px; 
            max-width:80%; 
            word-wrap:break-word;
        }

        .export-container {
            display:flex; 
            justify-content:flex-end; 
            margin-top:10px;
            flex-wrap: wrap;
        }

        @media (max-width: 768px) {
            .chat-title { font-size: 1.8em; padding: 15px; }
            .file-upload-container { width: 95%; padding: 15px; }
            .chat-bubble-user div, .chat-bubble-ai div { max-width: 95%; font-size: 0.9em; padding: 8px 12px; }
            .export-container { justify-content: center; }
        }

        @media (max-width: 480px) {
            .chat-title { font-size: 1.5em; padding: 12px; }
            .chat-bubble-user div, .chat-bubble-ai div { font-size: 0.85em; padding: 6px 10px; }
        }
        </style>
    """, unsafe_allow_html=True)

# -------------------- RENDERING SECTIONS --------------------
def render_title():
    st.markdown('<div class="chat-title">🤖 ChatBot with File Uploader</div>', unsafe_allow_html=True)

def render_file_upload_section():
    st.markdown('<div class="file-upload-container">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:1.4em;font-weight:700;color:white;">📂 Upload Your File (PDF or DOCX)</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_chat_messages(messages):
    for msg in messages:
        safe_text = html.escape(msg["content"])
        if msg["role"] == "user":
            st.markdown(f"""
                <div class="chat-bubble-user">
                    <div>{safe_text}</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="chat-bubble-ai">
                    <div>{safe_text}</div>
                </div>
            """, unsafe_allow_html=True)

# -------------------- CHAT LOGIC --------------------
def init_chat():
    if "chat" not in st.session_state:
        st.session_state.chat = model.start_chat()
        st.session_state.chat.send_message("You are a helpful assistant.")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "file_context" not in st.session_state:
        st.session_state.file_context = ""
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None

def show_typing_animation():
    placeholder = st.empty()
    typing_html = """
    <div class="chat-bubble-ai"><div>...</div></div>
    """
    placeholder.markdown(typing_html, unsafe_allow_html=True)
    return placeholder

def handle_user_input():
    user_input = st.chat_input("💬 Ask anything...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_message("user", user_input)
        last_msg = st.session_state.messages[-1]

        typing_placeholder = show_typing_animation()
        context = ""
        if st.session_state.get("uploaded_file"):
            documents_list = query_rag(last_msg["content"], n_results=5)
            if documents_list:
                context = "\n\n".join(documents_list)

        # Build prompt
        if context:
            prompt = f"""
            You are an intelligent assistant.
            Answer based on context from the uploaded document. If unrelated, answer normally.
            Context:
            ``` 
            {context}
            ```
            User question:
            ```
            {last_msg['content']}
            ```
            """
        else:
            prompt = last_msg['content']

        response = st.session_state.chat.send_message(prompt)
        llm_reply = response.text
        typing_placeholder.empty()
        st.session_state.messages.append({"role": "ai", "content": llm_reply})
        save_message("ai", llm_reply)
        st.rerun()

# -------------------- EXPORT CHAT --------------------
def export_chat_button():
    if "show_export_options" not in st.session_state:
        st.session_state.show_export_options = False

    if st.button("📤 Export Chat", key="export_chat_btn"):
        st.session_state.show_export_options = True
        if not st.session_state.messages:
            placeholder = st.empty()
            placeholder.warning("No chat to export")
            st.session_state.show_export_options = False

    if st.session_state.show_export_options and st.session_state.messages:
        st.markdown('<div class="export-container">', unsafe_allow_html=True)
        format_choice = st.radio("Select export format:", ["PDF", "Word"], key="export_format", horizontal=True)

        if st.button("Confirm Export", key="export_confirm_btn"):
            if format_choice == "PDF":
                pdf = FPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_font("Arial", size=12)
                for msg in st.session_state.messages:
                    role = "User" if msg["role"] == "user" else "AI"
                    pdf.multi_cell(0, 8, f"{role}: {msg['content']}\n")
                    pdf.ln(1)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    pdf.output(tmp_file.name)
                    tmp_file.seek(0)
                    pdf_bytes = tmp_file.read()
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name="chat_history.pdf",
                    mime="application/pdf"
                )
            else:
                doc = Document()
                for msg in st.session_state.messages:
                    role = "User" if msg["role"] == "user" else "AI"
                    doc.add_paragraph(f"{role}: {msg['content']}")
                doc_buffer = io.BytesIO()
                doc.save(doc_buffer)
                doc_buffer.seek(0)
                st.download_button(
                    label="Download Word",
                    data=doc_buffer,
                    file_name="chat_history.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------- USER SESSION --------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# -------------------- INITIALIZATION --------------------
init_db()
set_custom_styles()
render_title()
render_file_upload_section()
init_chat()

uploaded_file = st.file_uploader("Upload File", type=["pdf", "docx"], key="file_upload")
if uploaded_file:
    st.session_state.uploaded_file = uploaded_file
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = os.path.join("temp_uploads", uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())
    add_file_to_rag(temp_path)
    st.success("File content loaded successfully!")
    st.info("You can now ask questions based on the uploaded file.")
else:
    st.session_state.uploaded_file = False

if st.button("🧹 Clear Chat History"):
    clear_chat_history()

export_chat_button()
render_chat_messages(st.session_state.messages)
handle_user_input()
