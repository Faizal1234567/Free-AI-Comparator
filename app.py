# Create the .streamlit directory
!mkdir -p .streamlit

# Create the secrets.toml file and add your secrets
# Replace "YOUR_OPENROUTER_API_KEY" and "YOUR_ADMIN_PASSWORD" with your actual values
secrets_content = """
OPENROUTER_API_KEY = "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"
ADMIN_PASS = "P@ssword2025"
"""

with open(".streamlit/secrets.toml", "w") as f:
    f.write(secrets_content)

print("Created .streamlit/secrets.toml with placeholder values. Please replace them with your actual secrets.")


# app.py - Robust EduChat AI (fixed)
import streamlit as st
import requests
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

# ---------- Use st.secrets for secure config ----------
OPENROUTER_API_KEY = st.secrets.get("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")
ADMIN_PASS = st.secrets.get("P@ssword2025")

# ---------- Requirements check: show admin-friendly error if missing libs ----------
MISSING_PKGS = []
try:
    import nltk
    from nltk import pos_tag, word_tokenize
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except Exception as e:
    MISSING_PKGS.append("nltk")

# ---------- Data directory ----------
DATA_DIR = Path("chat_data")
DATA_DIR.mkdir(exist_ok=True)

# ---------- Hide default Streamlit menu/footer/GitHub links ----------
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp a[href*='github'], .stApp a[href*='streamlit.io'] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

# ---------- Free models ----------
FREE_MODELS = [
    "nvidia/nemotron-nano-9b-v2:free",
    "meta-llama/llama-3.3-8b-instruct:free",
    "minimax/minimax-m2:free"
]

# ---------- Bloom verb lists ----------
BLOOMS_LEVELS = {
    "Knowledge": ["define", "list", "name", "recall", "identify", "label", "state"],
    "Comprehension": ["describe", "explain", "summarize", "paraphrase", "classify", "discuss"],
    "Application": ["apply", "demonstrate", "solve", "use", "illustrate", "show"],
    "Analysis": ["analyze", "compare", "contrast", "differentiate", "examine", "categorize"],
    "Synthesis": ["create", "design", "develop", "construct", "compose", "formulate"],
    "Evaluation": ["evaluate", "judge", "critique", "assess", "justify", "appraise"],
}

def classify_blooms_level(text):
    if "nltk" in MISSING_PKGS:
        return "Not Classified (nltk missing)"
    tokens = word_tokenize(text.lower())
    tagged = pos_tag(tokens)
    verbs = [word for word, tag in tagged if tag.startswith("VB")]
    matched = []
    for level, verbs_list in BLOOMS_LEVELS.items():
        for verb in verbs:
            if verb in verbs_list:
                matched.append(level)
    return max(set(matched), key=matched.count) if matched else "Not Classified"

# ---------- Admin auth ----------
def is_admin():
    # admin session flag
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    # Already authenticated
    if st.session_state.admin_authenticated:
        return True

    # Provide a small admin login widget in the sidebar
    with st.sidebar:
        st.subheader("🔒 Admin Login")
        pwd = st.text_input("Enter admin password:", type="password")
        if pwd:
            if ADMIN_PASS is None:
                st.error("ADMIN_PASS not set in Streamlit Secrets. Add ADMIN_PASS in Secrets.")
            elif pwd == ADMIN_PASS:
                st.session_state.admin_authenticated = True
                st.success("✅ Admin access granted")
                return True
            else:
                st.error("❌ Incorrect password")
    return False

# ---------- Message sending ----------
def send_openrouter_message(message, model_name):
    # Basic checks
    if OPENROUTER_API_KEY is None:
        return "⚠️ OPENROUTER_API_KEY not set in Streamlit Secrets."

    # Block accidentally using paid models
    paid_keywords = ["pro", "openai", "anthropic", "google", "gpt"]
    if any(k in model_name.lower() for k in paid_keywords):
        return f"🚫 '{model_name}' blocked — paid models not allowed."

    # Build request payload for single-turn prompt (safer)
    payload = {
        "model": model_name,
        "messages": [{"role":"user","content": message}],
        "max_tokens": 800
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=30
        )
        # If HTTP error, return readable string
        if resp.status_code != 200:
            return f"⚠️ Error {resp.status_code}: {resp.text}"
        j = resp.json()
        # Safely get content
        try:
            return j["choices"][0]["message"]["content"]
        except Exception:
            return f"⚠️ Unexpected response format: {j}"
    except Exception as e:
        return f"⚠️ Request error: {e}"

# ---------- Persistence ----------
def save_history_to_file(session_id, data):
    try:
        with open(DATA_DIR / f"{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        # Admin-only message
        st.session_state._last_save_error = str(e)
        return False

def load_history_from_file(session_id):
    p = DATA_DIR / f"{session_id}.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ---------- UI ----------
st.set_page_config(page_title="EduChat AI — Fixed", page_icon="🎓", layout="centered")
st.title("🎓 EduChat AI (Fixed)")

if MISSING_PKGS:
    st.warning(f"Missing Python packages: {', '.join(MISSING_PKGS)}. Add them to requirements.txt and redeploy. Admins see more details in sidebar.")

# Session essentials
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    # load persistent file if exists
    st.session_state.chat_history = load_history_from_file(st.session_state.session_id)
if "votes" not in st.session_state:
    st.session_state.votes = {}

# Admin sidebar (authenticated)
if is_admin():
    with st.sidebar:
        st.header("⚙️ Admin")
        st.write("Admin-only settings")
        sel_model = st.selectbox("Default model (admin-only):", FREE_MODELS, index=2)
        st.write(f"Session ID: `{st.session_state.session_id}`")
        if hasattr(st.session_state, "_last_save_error"):
            st.error(f"Last save error: {st.session_state._last_save_error}")
else:
    # hide empty sidebar area for regular users
    st.sidebar.markdown("")

# Chat input and model selection
question = st.text_area("💬 Type your question here:")
selected_models = st.multiselect("Choose model(s) to compare:", FREE_MODELS, default=[FREE_MODELS[-1]])

if st.button("Get Answers"):
    if not question.strip():
        st.warning("Please type a question.")
    else:
        blooms = classify_blooms_level(question)
        st.markdown(f"**Bloom’s level:** `{blooms}`")
        st.write("---")

        # Fetch results per model and display
        answers = {}
        for model in selected_models:
            with st.spinner(f"Querying {model}..."):
                ans = send_openrouter_message(question, model)
                st.markdown(f"### Model: `{model}`")
                st.write(ans)
                answers[model] = ans
                st.markdown("---")

        # Allow user to choose best answer (radio)
        if selected_models:
            best = st.radio("Which answer is best?", selected_models, key=str(uuid.uuid4()))
            st.success(f"You selected: **{best}**")
        else:
            best = None

        # Save entry to session history and persist to file
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "bloom": blooms,
            "answers": answers,
            "selected_best": best
        }
        st.session_state.chat_history.append(entry)
        saved = save_history_to_file(st.session_state.session_id, st.session_state.chat_history)
        if not saved:
            st.warning("Could not save chat history to file (admins see details).")

# Show chat history with ability to open previous sessions
st.markdown("## Your session history")
if st.session_state.chat_history:
    for item in st.session_state.chat_history:
        st.markdown(f"**{item['timestamp']}** — Q: {item['question']}")
        st.markdown(f"• Bloom: `{item['bloom']}`")
        for m, a in item["answers"].items():
            st.markdown(f"  - `{m}`: {a[:400]}{'...' if len(a) > 400 else ''}")
        st.markdown(f"• Best: {item.get('selected_best')}")
        st.markdown("---")
else:
    st.info("No chat entries yet. Ask a question to get started.")

# Download (ask first)
if st.session_state.chat_history:
    if st.checkbox("I want to download this session data"):
        confirm = st.radio("Confirm download?", ["No", "Yes"])
        if confirm == "Yes":
            st.download_button("Download JSON", data=json.dumps(st.session_state.chat_history, indent=2, ensure_ascii=False),
                                file_name=f"edu_chat_{st.session_state.session_id}.json", mime="application/json")

st.caption("If problems persist, open 'Manage app' → Logs on Streamlit Cloud (admins).")
