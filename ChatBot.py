import streamlit as st
import google.generativeai as genai
import sqlite3
import datetime
import uuid
import html
import os
from rag_pipeline import add_file_to_rag, query_rag

DB_PATH = "chatbot.db"

# -------------------- GEMINI SETUP --------------------
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
        cursor.execute("SELECT role, message FROM chat_history WHERE user_id=? ORDER BY id ASC", (st.session_state.user_id,))
        messages = cursor.fetchall()
        conn.close()
        return [{"role": row[0], "content": row[1]} for row in messages]
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
    st.success("Chat cleared!")
    st.rerun()

# -------------------- STYLE --------------------
def set_custom_styles():
    st.markdown("""
        <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background-color: black !important;
        }
        </style>
    """, unsafe_allow_html=True)

def render_title():
    st.markdown("""
        <div style="background: linear-gradient(270deg, #00dbde, #fc00ff, #ff6a00);
                    color:white;text-align:center;padding:20px;border-radius:18px;
                    font-size:2.3em;font-weight:900;letter-spacing:1.3px;
                    text-transform:uppercase;margin-bottom:20px;">
            🤖 ChatBot with File Uploader
        </div>
    """, unsafe_allow_html=True)

def render_file_upload_section():
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(72,61,139,0.6), rgba(123,31,162,0.6));
                    border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 15px;
                    box-shadow: 0 4px 25px rgba(0, 0, 0, 0.3); padding: 25px; text-align: center;
                    backdrop-filter: blur(12px); margin-bottom: 25px;">
            <div style="font-size:1.4em;font-weight:700;color:white;">
                📂 Upload Your File (PDF or DOCX)
            </div>
        </div>
    """, unsafe_allow_html=True)

# -------------------- CHAT --------------------
def render_chat_messages(messages):
    for msg in messages:
        safe_text = html.escape(msg["content"])
        if msg["role"] == "user":
            st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                    <div style="background-color: #C7C7C7; color:black; padding:10px 15px;
                                border-radius:15px; max-width:60%; word-wrap:break-word;">
                        {safe_text}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
                    <div style="background-color: #3E494D; color:white; padding:10px 15px;
                                border-radius:15px; max-width:60%; word-wrap:break-word;">
                        {safe_text}
                    </div>
                </div>
            """, unsafe_allow_html=True)

def init_chat():
    if "chat" not in st.session_state:
        st.session_state.chat = model.start_chat()
        st.session_state.chat.send_message("You are a helpful assistant.")

    if "messages" not in st.session_state:
        db_messages = load_messages()
        st.session_state.messages = db_messages if db_messages else []

    if "file_context" not in st.session_state:
        st.session_state.file_context = ""

    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None

def show_typing_animation():
    placeholder = st.empty()
    typing_html = """
    <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
        <div style="display: inline-flex; align-items: center; background-color: #3E494D;
                    color: white; padding: 10px 15px; border-radius: 15px;">
            <span>...</span>
        </div>
    </div>
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

        if context:
            prompt = f"""
            You are an intelligent assistant.
            If the question relates to the document, answer from it.
            If not, provide a general relevant answer.

            Context:
            ``` 
            {context}
            ```

            Question:
            ```
            {last_msg['content']}
            ```
            """
        else:
            prompt = last_msg["content"]

        response = st.session_state.chat.send_message(prompt)
        llm_reply = response.text

        typing_placeholder.empty()
        st.session_state.messages.append({"role": "ai", "content": llm_reply})
        save_message("ai", llm_reply)
        st.rerun()

# -------------------- USER ID PERSISTENCE --------------------
@st.cache_data
def get_persistent_user_id():
    """Persist user_id across reloads"""
    return str(uuid.uuid4())

if "user_id" not in st.session_state:
    st.session_state.user_id = get_persistent_user_id()

# -------------------- INITIALIZATION --------------------
init_db()
set_custom_styles()
render_title()
render_file_upload_section()
init_chat()

# -------------------- FILE UPLOAD --------------------
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

# -------------------- CLEAR CHAT --------------------
if st.button("🧹 Clear Chat History"):
    clear_chat_history()

# -------------------- CHAT DISPLAY --------------------
render_chat_messages(st.session_state.messages)
handle_user_input()
