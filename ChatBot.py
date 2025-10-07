import streamlit as st
import google.generativeai as genai
import PyPDF2
import docx

st.markdown(
    """
    <style>
    body {
        background-color: #1E1E2F;  /* Change this to any color you like */
        color: black;
            }
    </style>
    """,
    unsafe_allow_html=True
)

genai.configure(api_key="AIzaSyC59fJluw0VU9RQFnbj0nBzqvKy6j9Mtvo")
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat()
    st.session_state.chat.send_message("You are a helpful assistant.")

if "file_context" not in st.session_state:
    st.session_state.file_context = ""

if "messages" not in st.session_state:
    st.session_state.messages = []  # store full conversation history

st.markdown(
    """
    <style>
    @keyframes gradientFlow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .chatbot-title {
        background: linear-gradient(270deg, #00dbde, #fc00ff, #ff6a00);
        background-size: 600% 600%;
        animation: gradientFlow 8s ease infinite;
        color: white;
        text-align: center;
        padding: 20px;
        border-radius: 18px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(12px);
        font-size: 2.3em;
        font-weight: 900;
        letter-spacing: 1.3px;
        text-transform: uppercase;
        text-shadow: 0 0 10px rgba(255,255,255,0.6);
        margin-bottom: 20px;
        border: 2px solid rgba(255,255,255,0.25);
        transition: all 0.4s ease;
    }

    .chatbot-title:hover {
        transform: scale(1.04);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
        border-color: rgba(255,255,255,0.6);
    }
    </style>

    <div class="chatbot-title">
        🤖 ChatBot with File Uploader
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
    .file-upload-box {
        background: linear-gradient(135deg, rgba(72,61,139,0.6), rgba(123,31,162,0.6));
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 15px;
        box-shadow: 0 4px 25px rgba(0, 0, 0, 0.3);
        padding: 25px;
        text-align: center;
        backdrop-filter: blur(12px);
        margin-bottom: 25px;
        transition: all 0.4s ease;
    }
    .file-upload-box:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 30px rgba(0, 0, 0, 0.5);
        border-color: rgba(255, 255, 255, 0.6);
    }
    .file-upload-title {
        font-size: 1.4em;
        font-weight: 700;
        color: white;
        text-shadow: 0 0 10px rgba(255,255,255,0.4);
        margin-bottom: 12px;
    }
    </style>

    <div class="file-upload-box">
        <div class="file-upload-title">📂 Upload Your File (PDF or DOCX)</div>
    </div>
    """,
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader("", type=["pdf", "docx"])

if uploaded_file:
    if uploaded_file.type == "application/pdf":
        file_text = extract_text_from_pdf(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        file_text = extract_text_from_docx(uploaded_file)
    else:
        st.warning("Unsupported file type.")
        file_text = ""

    if file_text:
        st.session_state.file_context = file_text
        st.success("File content loaded successfully!")
        st.session_state.chat.send_message("Here is a document the user uploaded:\n\n" + file_text[:8000])
        st.info("Now you can ask questions based on the uploaded file.")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"""
            <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                <div style="background-color: #e0e0e0; padding: 10px 15px; border-radius: 15px; max-width: 60%; word-wrap: break-word;">
                    {msg['content']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="display: flex; justify-content: flex-start; align-items: flex-start; margin: 10px 0;">
                <div style="font-size: 24px; margin-right: 8px;">🤖</div>
                <div style="color: white; background-color: #3E494D; padding: 10px 15px; border-radius: 15px; max-width: 60%; word-wrap: break-word;">
                    {msg['content']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

user_input = st.chat_input("Ask anything about the file...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    response = st.session_state.chat.send_message(user_input)
    llm_reply = response.text
    st.session_state.messages.append({"role": "ai", "content": llm_reply})
    st.rerun()  # refresh page to show the new message without losing history