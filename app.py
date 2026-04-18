import io
import uuid
from datetime import datetime

import streamlit as st
import pandas as pd

from elevenlabs.client import ElevenLabs
from huggingface_hub import HfApi, hf_hub_download, HfFolder

# -----------------------------
# STREAMLIT SECRETS (FIXED)
# -----------------------------
ELEVENLABS_API_KEY = st.secrets.get("ELEVENLABS_API_KEY")
HF_TOKEN = st.secrets.get("HF_TOKEN")
HF_DATASET_REPO = st.secrets.get("HF_DATASET_REPO")
HF_DATASET_PATH = st.secrets.get("HF_DATASET_PATH", "responses.csv")

# -----------------------------
# VALIDATION (SAFE STOP)
# -----------------------------
if not ELEVENLABS_API_KEY:
    st.error("Missing ELEVENLABS_API_KEY in Streamlit secrets")
    st.stop()

if not HF_TOKEN:
    st.error("Missing HF_TOKEN in Streamlit secrets")
    st.stop()

if not HF_DATASET_REPO:
    st.error("Missing HF_DATASET_REPO in Streamlit secrets")
    st.stop()

# -----------------------------
# INIT CLIENTS
# -----------------------------
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
hf_api = HfApi()
HfFolder.save_token(HF_TOKEN)

st.set_page_config(
    page_title="Empathetic vs. Neutral AI Voice Study",
    page_icon="🎙",
    layout="centered"
)

# -----------------------------
# SAFE VOICE LOADER (FIXED CRASH)
# -----------------------------
@st.cache_data
def load_voices():
    try:
        return client.voices.get_all().voices
    except Exception as e:
        st.error("Failed to load ElevenLabs voices. Check API key or account.")
        return []

# -----------------------------
# TEXT TO SPEECH
# -----------------------------
def play_voice(text: str, voice_name: str):
    try:
        voices = load_voices()
        voice_map = {v.name: v for v in voices}

        if voice_name not in voice_map:
            st.error("Voice not found.")
            return

        audio = client.text_to_speech.convert(
            voice_id=voice_map[voice_name].voice_id,
            model_id="eleven_flash_v2_5",
            text=text,
            output_format="mp3_22050_32"
        )

        audio_bytes = b"".join(audio)
        st.audio(io.BytesIO(audio_bytes), format="audio/mpeg")

    except Exception as e:
        st.error(f"Voice generation failed: {e}")

# -----------------------------
# HF DATA HELPERS
# -----------------------------
def load_existing_hf_csv(repo_id, path):
    try:
        local_path = hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            filename=path,
            token=HF_TOKEN
        )
        return pd.read_csv(local_path)
    except Exception:
        return pd.DataFrame()

def upload_csv_to_hf(df, repo_id, path):
    tmp_path = "responses_tmp.csv"
    df.to_csv(tmp_path, index=False)

    hf_api.upload_file(
        path_or_fileobj=tmp_path,
        path_in_repo=path,
        repo_id=repo_id,
        repo_type="dataset",
        token=HF_TOKEN
    )

# -----------------------------
# SESSION STATE INIT
# -----------------------------
def init_state():
    if "step" not in st.session_state:
        st.session_state["step"] = "consent"

init_state()

# -----------------------------
# VOICES (GLOBAL CACHE)
# -----------------------------
default_voice_metadata = {
    "Rachel": {"gender": "Female", "accent": "American", "description": "Casual"},
    "River": {"gender": "Neutral", "accent": "American", "description": "Calm"},
}

voices = load_voices()

# -----------------------------
# UI
# -----------------------------
st.title("Empathetic vs Neutral AI Voice Study")

# -----------------------------
# CONSENT
# -----------------------------
if st.session_state["step"] == "consent":
    st.write("Consent page...")

    if st.button("Continue"):
        st.session_state["step"] = "demographics"
        st.rerun()

# -----------------------------
# DEMO
# -----------------------------
elif st.session_state["step"] == "demographics":
    st.write("Demographics page...")

    if st.button("Next"):
        st.session_state["step"] = "session_emp"
        st.rerun()

# -----------------------------
# EMPATHETIC
# -----------------------------
elif st.session_state["step"] == "session_emp":
    st.header("Empathetic Voice Session")

    voice_labels = {
        f"{v.name}": v for v in voices
    }

    emp_voice = st.selectbox("Select voice", list(voice_labels.keys()))

    script = st.text_area("Script", "Hello, take a deep breath.")

    if st.button("Play Empathetic Voice"):
        play_voice(script, emp_voice)

    if st.button("Next"):
        st.session_state["step"] = "session_neu"
        st.rerun()

# -----------------------------
# NEUTRAL
# -----------------------------
elif st.session_state["step"] == "session_neu":
    st.header("Neutral Voice Session")

    voice_labels = {v.name: v for v in voices}

    neu_voice = st.selectbox("Select voice", list(voice_labels.keys()))

    script = st.text_area("Script", "Please continue the study.")

    if st.button("Play Neutral Voice"):
        play_voice(script, neu_voice)

    if st.button("Next"):
        st.session_state["step"] = "open"
        st.rerun()

# -----------------------------
# OPEN
# -----------------------------
elif st.session_state["step"] == "open":
    st.write("Open-ended questions...")

    if st.button("Next"):
        st.session_state["step"] = "review"
        st.rerun()

# -----------------------------
# REVIEW
# -----------------------------
elif st.session_state["step"] == "review":
    st.write("Review page")

    if st.button("Submit"):
        st.success("Submitted!")
