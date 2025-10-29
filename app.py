import streamlit as st
import requests
import json
import os
import uuid
from datetime import datetime

# ===========================
# 🔒 Secure Setup
# ===========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# === Allowed Free Models ===
FREE_MODELS = [
    "nvidia/nemotron-nano-9b-v2:free",
    "meta-llama/llama-3.3-8b-instruct:free",
    "minimax/minimax-m2:free"
]

# ===========================
# 💬 Message Sending Function
# ===========================
def send_openrouter_message(message, model_name="minimax/minimax-m2:free"):
    if not OPENROUTER_API_KEY:
        return "⚠️ Missing API key. Please set OPENROUTER_API_KEY in Secrets."

    # Safety: block paid models
    paid_keywords = ["pro", "openai", "anthropic", "google", "gpt"]
    if any(k in model_name.lower() for k in paid_keywords):
        return f"🚫 '{model_name}' blocked — paid model not allowed."

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://streamlit.io/",
                "X-Title": "EduChat AI",
            },
            data=json.dumps({
                "model": model_name,
                "messages": st.session_state.chat_history
            }),
            timeout=40
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


# ===========================
# 🎨 Page Configuration
# ===========================
st.set_page_config(
    page_title="EduChat AI | Student Learning Assistant",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        body { background-color: #f9fafb; }
        .stApp { 
            background: linear-gradient(to right, #f3f4f6, #e5e7eb);
        }
        .main-title {
            text-align: center;
            color: #1f2937;
            font-family: 'Helvetica Neue', sans-serif;
        }
        .subtitle {
            text-align: center;
            color: #4b5563;
            font-size: 16px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<h1 class='main-title'>🎓 EduChat AI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>An intelligent learning assistant for students and educators — powered by free OpenRouter models.</p>", unsafe_allow_html=True)
st.write("")

# ===========================
# 🧠 Initialize Session
# ===========================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())  # Unique user session
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "minimax/minimax-m2:free"

# Sidebar (Admin)
with st.sidebar:
    st.header("⚙️ Admin Settings")
    st.info("Visible to admin only (not users).")
    st.session_state.selected_model = st.selectbox(
        "Choose Model",
        FREE_MODELS,
        index=2
    )
    st.markdown("---")
    st.caption(f"🆔 Current Session ID: `{st.session_state.session_id}`")

# ===========================
# 💬 Chat Input
# ===========================
user_message = st.chat_input("💬 Ask me anything related to your studies...")

if user_message:
    st.session_state.chat_history.append({"role": "user", "content": user_message})
    with st.spinner("🤖 Thinking..."):
        bot_response = send_openrouter_message(user_message, st.session_state.selected_model)
        st.session_state.chat_history.append({"role": "assistant", "content": bot_response})

    # ✅ Auto-save per user session
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"chat_{st.session_state.session_id}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(st.session_state.chat_history, f, indent=4, ensure_ascii=False)

# ===========================
# 🧾 Display Chat
# ===========================
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# ===========================
# 💾 Download Chat
# ===========================
if st.session_state.chat_history:
    chat_text = "\n\n".join(
        [f"👩‍🎓 User: {m['content']}" if m['role'] == 'user' else f"🤖 EduChat: {m['content']}" for m in st.session_state.chat_history]
    )
    st.download_button(
        label="⬇️ Download Chat (.txt)",
        data=chat_text,
        file_name=f"EduChat_{st.session_state.session_id}.txt",
        mime="text/plain"
    )
    st.download_button(
        label="⬇️ Download Chat (.json)",
        data=json.dumps(st.session_state.chat_history, indent=4, ensure_ascii=False),
        file_name=f"EduChat_{st.session_state.session_id}.json",
        mime="application/json"
    )

# ===========================
# 📘 Footer
# ===========================
st.markdown("---")
st.markdown(
    """
    <div style='text-align:center; color:#6b7280; font-size:14px;'>
    🧠 <b>EduChat AI</b> — your personal academic assistant.<br>
    Built with ❤️ for students by Faizal, powered by <a href='https://openrouter.ai' target='_blank'>OpenRouter.ai</a>.
    </div>
    """,
    unsafe_allow_html=True
)

