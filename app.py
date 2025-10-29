import streamlit as st
import requests
import json
import os

# ===========================
# 🔒 Safety & Setup
# ===========================
# Never hardcode API keys — use Streamlit Secrets instead!
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def send_openrouter_message(message, model_name):
    """
    Send a message to OpenRouter using only free models.
    Blocks paid models automatically.
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ API key missing! Please set OPENROUTER_API_KEY in Streamlit Cloud Secrets."

    # Safety check — block paid models
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
                "X-Title": "Free AI Chatbot",
            },
            data=json.dumps({
                "model": model_name,
                "messages": [{"role": "user", "content": message}],
            }),
            timeout=40
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


# ===========================
# 🎨 Streamlit Web UI
# ===========================
st.set_page_config(page_title="Free AI Model Comparator", page_icon="🤖", layout="centered")

st.title("🤖 AI Model Comparator (Free via OpenRouter)")
st.markdown("Compare responses from multiple **free-tier AI models** in one place.")

# User input
user_question = st.text_area("💬 Enter your question:", "What is Artificial Intelligence?")

# Model selection
available_models = [
    "nvidia/nemotron-nano-9b-v2:free",
    "meta-llama/llama-3.3-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free"
]
selected_models = st.multiselect(
    "🧠 Choose models to compare:",
    available_models,
    default=available_models  # all selected by default
)

# Submit button
if st.button("🚀 Compare Responses"):
    if not user_question.strip():
        st.warning("Please enter a valid question first.")
    else:
        for model in selected_models:
            with st.spinner(f"Fetching response from {model}..."):
                answer = send_openrouter_message(user_question, model)
                st.markdown(f"### 🟢 Model: `{model}`")
                st.write(answer)
                st.markdown("---")

st.caption("Powered by [OpenRouter.ai](https://openrouter.ai) | Free-tier models only 🟢")
