import streamlit as st
import requests
import json
import os
import uuid
from datetime import datetime
import nltk
from nltk import pos_tag, word_tokenize
from pathlib import Path

# ===========================
# 🔒 Secure Setup
# ===========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ADMIN_PASS = os.getenv("ADMIN_PASS", None)
DATA_DIR = Path("chat_data")
DATA_DIR.mkdir(exist_ok=True)

nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)

# === Hide Streamlit default UI (menu, footer, GitHub, etc.) ===
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp a[href*='github'], .stApp a[href*='streamlit.io'] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

# ===========================
# 🧩 Free Models
# ===========================
FREE_MODELS = [
    "nvidia/nemotron-nano-9b-v2:free",
    "meta-llama/llama-3.3-8b-instruct:free",
    "minimax/minimax-m2:free"
]

# ===========================
# 🧠 Bloom’s Taxonomy
# ===========================
BLOOMS_LEVELS = {
    "Knowledge": ["define", "list", "name", "recall", "identify", "label", "state"],
    "Comprehension": ["describe", "explain", "summarize", "paraphrase", "classify", "discuss"],
    "Application": ["apply", "demonstrate", "solve", "use", "illustrate", "show"],
    "Analysis": ["analyze", "compare", "contrast", "differentiate", "examine", "categorize"],
    "Synthesis": ["create", "design", "develop", "construct", "compose", "formulate"],
    "Evaluation": ["evaluate", "judge", "critique", "assess", "justify", "appraise"],
}

def classify_blooms_level(text):
    tokens = word_tokenize(text.lower())
    tagged = pos_tag(tokens)
    verbs = [word for word, tag in tagged if tag.startswith("VB")]
    matched = []
    for level, verbs_list in BLOOMS_LEVELS.items():
        for verb in verbs:
            if verb in verbs_list:
                matched.append(level)
    return max(set(matched), key=matched.count) if matched else "Not Classified"

# ===========================
# 🔑 Admin Authentication
# ===========================
def is_admin():
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if st.session_state.admin_authenticated:
        return True

    with st.sidebar:
        st.subheader("🔒 Admin Login")
        password = st.text_input("Enter admin password:", type="password")
        if password and password == ADMIN_PASS:
            st.session_state.admin_authenticated = True
            st.success("✅ Admin access granted")
            return True
        elif password and password != ADMIN_PASS:
            st.error("❌ Incorrect password")
    return False

# ===========================
# 🧠 Send Message to OpenRouter
# ===========================
def send_openrouter_message(message, model_name):
    if not OPENROUTER_API_KEY:
        return "⚠️ Missing API key. Please add OPENROUTER_API_KEY in Secrets."
    paid_keywords = ["pro", "openai", "anthropic", "google", "gpt"]
    if any(k in model_name.lower() for k in paid_keywords):
        return f"🚫 '{model_name}' blocked — paid model not allowed."
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": model_name,
                "messages": [{"role": "user", "content": message}]
            }),
            timeout=40
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ===========================
# 💾 File Operations (Persistence)
# ===========================
def save_history(session_id, data):
    with open(DATA_DIR / f"{session_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_history(session_id):
    file_path = DATA_DIR / f"{session_id}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ===========================
# 🎨 UI Setup
# ===========================
st.set_page_config(page_title="EduChat AI | Student Learning Assistant", page_icon="🎓", layout="centered")

st.markdown("<h1 style='text-align:center; color:#1f2937;'>🎓 EduChat AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#4b5563;'>AI-based student assistant with Bloom’s Taxonomy and multi-model learning.</p>", unsafe_allow_html=True)

# ===========================
# 🧠 Session Management
# ===========================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history(st.session_state.session_id)
if "votes" not in st.session_state:
    st.session_state.votes = {}

# ===========================
# ⚙️ Admin Panel
# ===========================
if is_admin():
    with st.sidebar:
        st.header("⚙️ Admin Settings")
        st.caption(f"🆔 Session: `{st.session_state.session_id}`")
        st.markdown("---")

# ===========================
# 📜 History Section
# ===========================
st.sidebar.header("📚 Chat History")
all_histories = [f.name.replace(".json", "") for f in DATA_DIR.glob("*.json")]
selected_history = st.sidebar.selectbox("Select a previous session to view:", ["(Current Session)"] + all_histories)

if selected_history != "(Current Session)":
    old_data = load_history(selected_history)
    st.sidebar.markdown("### 🧠 Previous Chat")
    for chat in old_data[-3:]:
        st.sidebar.write(f"💬 {chat.get('user_question')}")
    if st.sidebar.button("Load Selected Chat"):
        st.session_state.chat_history = old_data
        st.sidebar.success("✅ Loaded selected session successfully!")

if st.sidebar.button("➕ Start New Chat"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.votes = {}
    st.experimental_rerun()

# ===========================
# 💬 Chat Input
# ===========================
question = st.text_area("💬 Ask your question:")

selected_models = st.multiselect(
    "🧠 Choose models to compare:",
    FREE_MODELS,
    default=["minimax/minimax-m2:free"]
)

if st.button("🚀 Get Answers"):
    if not question.strip():
        st.warning("Please enter a valid question.")
    else:
        blooms_level = classify_blooms_level(question)
        st.markdown(f"🧩 **Bloom’s Cognitive Level:** `{blooms_level}`")
        st.write("---")

        answers = {}
        for model in selected_models:
            with st.spinner(f"Fetching response from {model}..."):
                response = send_openrouter_message(question, model)
                st.markdown(f"### 🤖 {model}")
                st.write(response)
                answers[model] = response
                st.markdown("---")

        # Vote option
        best_model = st.radio("Which model gave the best answer?", selected_models, key=str(uuid.uuid4()))
        st.session_state.votes[question] = best_model
        st.success(f"✅ You chose: **{best_model}**")

        # Save chat persistently
        chat_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_question": question,
            "bloom_level": blooms_level,
            "answers": answers,
            "best_model": best_model
        }
        st.session_state.chat_history.append(chat_entry)
        save_history(st.session_state.session_id, st.session_state.chat_history)

# ===========================
# 💾 Download Option (with confirmation)
# ===========================
if st.session_state.chat_history:
    if st.checkbox("📦 Download Chat History"):
        confirm = st.radio("Are you sure you want to download this session?", ("No", "Yes"))
        if confirm == "Yes":
            st.download_button(
                label="⬇️ Download (.json)",
                data=json.dumps(st.session_state.chat_history, indent=4, ensure_ascii=False),
                file_name=f"EduChat_Session_{st.session_state.session_id}.json",
                mime="application/json"
            )

# ===========================
# 📘 Footer
# ===========================
st.markdown("---")
st.markdown(
    """
    <div style='text-align:center; color:#6b7280; font-size:14px;'>
    🧠 <b>EduChat AI</b> — Smart Learning Assistant.<br>
    Developed by Faizal | Powered by <a href='https://openrouter.ai' target='_blank'>OpenRouter.ai</a>.
    </div>
    """,
    unsafe_allow_html=True
)
