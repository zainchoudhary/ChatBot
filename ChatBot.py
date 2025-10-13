import streamlit as st
import google.generativeai as genai
import PyPDF2
import docx
import sqlite3
import datetime
import uuid
import threading

# ---------------- CONFIG ----------------
genai.configure(api_key="AIzaSyC59fJluw0VU9RQFnbj0nBzqvKy6j9Mtvo")
DB_NAME = "chatbot.db"
db_lock = threading.Lock()  # For thread-safe DB access

# ---------------- DATABASE ----------------
def init_db():
    with db_lock:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
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

def migrate_db():
    """Add user_id column if it doesn't exist and assign 'default' to old messages"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(chat_history)")
        columns = [col[1] for col in cursor.fetchall()]
        if "user_id" not in columns:
            cursor.execute("ALTER TABLE chat_history ADD COLUMN user_id TEXT")
            cursor.execute("UPDATE chat_history SET user_id='default'")
            conn.commit()
        conn.close()

def save_message(role, message):
    try:
        with db_lock:
            conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (user_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
                (st.session_state.user_id, role, message, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
    except Exception as e:
        st.error(f"Database error (save_message): {e}")

def load_messages():
    try:
        with db_lock:
            conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            cursor = conn.cursor()
            # Load messages for this user + old default messages
            cursor.execute(
                "SELECT role, message FROM chat_history WHERE user_id=? OR user_id='default' ORDER BY id ASC",
                (st.session_state.user_id,)
            )
            messages = cursor.fetchall()
            conn.close()
            return [{"role": role, "content": msg} for role, msg in messages]
    except Exception as e:
        st.error(f"Database error (load_messages): {e}")
        return []

def clear_chat_history():
    try:
        with db_lock:
            conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM chat_history WHERE user_id=?",
                (st.session_state.user_id,)
            )
            conn.commit()
            conn.close()
        st.session_state.messages = []
        st.session_state.file_context = ""
        st.success("Your chat history has been cleared!")
        st.rerun()
    except Exception as e:
        st.error(f"Database error (clear_chat_history): {e}")

# ---------------- FILE HANDLING ----------------
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    return "".join(page.extract_text() for page in pdf_reader.pages)

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def handle_file_upload():
    uploaded_file = st.file_uploader("", type=["pdf", "docx"])
    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            return extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return extract_text_from_docx(uploaded_file)
        else:
            st.warning("Unsupported file type.")
    return ""

# ---------------- STYLING ----------------
def set_custom_styles():
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            background-color: black !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_title():
    st.markdown(
        """
        <div style="background: linear-gradient(270deg, #00dbde, #fc00ff, #ff6a00);
                    color:white;text-align:center;padding:20px;border-radius:18px;
                    font-size:2.3em;font-weight:900;letter-spacing:1.3px;
                    text-transform:uppercase;margin-bottom:20px;">
            🤖 ChatBot with File Uploader
        </div>
        """,
        unsafe_allow_html=True
    )

def render_file_upload_section():
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, rgba(72,61,139,0.6), rgba(123,31,162,0.6));
                    border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 15px;
                    box-shadow: 0 4px 25px rgba(0, 0, 0, 0.3); padding: 25px; text-align: center;
                    backdrop-filter: blur(12px); margin-bottom: 25px;">
            <div style="font-size:1.4em;font-weight:700;color:white;">
                📂 Upload Your File (PDF or DOCX)
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------- CHAT ----------------
def render_chat_messages(messages):
    for msg in messages:
        if msg["role"] == "user":
            st.markdown(
                f"""
                <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                    <div style="background-color: #C7C7C7; color:black; padding:10px 15px;
                                border-radius:15px; max-width:60%; word-wrap:break-word;">
                        {msg['content']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
                    <div style="background-color: #3E494D; color:white; padding:10px 15px;
                                border-radius:15px; max-width:60%; word-wrap:break-word;">
                        {msg['content']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

def init_chat():
    # Assign unique ID per user session
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())

    # Initialize chat model
    if "chat" not in st.session_state:
        st.session_state.chat = model.start_chat()
        st.session_state.chat.send_message("You are a helpful assistant.")

    # Load this user's messages from database
    if "messages" not in st.session_state:
        st.session_state.messages = load_messages()

    # File context per user
    if "file_context" not in st.session_state:
        st.session_state.file_context = ""

def show_typing_animation():
    placeholder = st.empty()
    typing_html = """
    <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
        <div style="
            display: inline-flex;
            align-items: center;
            background-color: #3E494D;
            color: white;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 60%;
            word-wrap: break-word;
        ">
            <div class="typing-indicator" style="display: flex; gap: 4px;">
                <span style="width: 8px; height: 8px; background-color: #ccc; border-radius: 50%; display: inline-block; animation: blink 1s infinite 0s;"></span>
                <span style="width: 8px; height: 8px; background-color: #ccc; border-radius: 50%; display: inline-block; animation: blink 1s infinite 0.2s;"></span>
                <span style="width: 8px; height: 8px; background-color: #ccc; border-radius: 50%; display: inline-block; animation: blink 1s infinite 0.4s;"></span>
            </div>
        </div>
    </div>

    <style>
    @keyframes blink {0% { opacity: 0.2; } 20% { opacity: 1; } 100% { opacity: 0.2; }}
    </style>
    """
    placeholder.markdown(typing_html, unsafe_allow_html=True)
    return placeholder

def handle_user_input():
    user_input = st.chat_input("💬 Ask anything...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_message("user", user_input)

        render_chat_messages([{"role": "user", "content": user_input}])
        typing_placeholder = show_typing_animation()

        response = st.session_state.chat.send_message(user_input)
        llm_reply = response.text

        typing_placeholder.empty()
        st.session_state.messages.append({"role": "ai", "content": llm_reply})
        save_message("ai", llm_reply)
        render_chat_messages([{"role": "ai", "content": llm_reply}])

# ----------------- MAIN -----------------
init_db()
migrate_db()  # Migrate old DB safely
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

set_custom_styles()
render_title()
render_file_upload_section()
init_chat()

file_text = handle_file_upload()
if file_text:
    st.session_state.file_context = file_text
    st.session_state.chat.send_message("Here is a document the user uploaded:\n\n" + file_text[:8000])
    st.success("File content loaded successfully!")
    st.info("Now you can ask questions based on the uploaded file.")

if st.button("🧹 Clear Chat History"):
    clear_chat_history()

render_chat_messages(st.session_state.messages)
handle_user_input()
