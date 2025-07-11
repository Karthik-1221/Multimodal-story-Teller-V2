# app.py

import streamlit as st
import google.generativeai as genai
import requests
import json
from PIL import Image
import io
import os
from dotenv import load_dotenv
import streamlit.components.v1 as components
import base64 # Needed for Stability.ai's API response

# --- 1. Configuration and Setup ---

st.set_page_config(layout="wide", page_title="The Multimodal Storyteller", page_icon="🪶")
load_dotenv()

def load_api_keys():
    """Loads API keys securely from Streamlit secrets or a .env file."""
    try:
        google_api_key = st.secrets["GOOGLE_API_KEY"]
        stability_api_key = st.secrets["STABILITY_API_KEY"]
    except (KeyError, st.errors.StreamlitAPIException):
        google_api_key = os.getenv("GOOGLE_API_KEY")
        stability_api_key = os.getenv("STABILITY_API_KEY")
    return google_api_key, stability_api_key

GOOGLE_API_KEY, STABILITY_API_KEY = load_api_keys()

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    st.error("Google API Key not found. Please set it in your secrets.")
    st.stop()

# --- 2. AI and Helper Functions ---

def generate_world_bible(theme, archetype, contradiction):
    """Generates the story's core rules and tone using Gemini."""
    prompt = f"""
    You are a world-building AI. Create a 'World Bible' for a new story. This document should be a rich, one-page summary establishing the world's history, main conflicts, character motivations, and tone. It must be consistent and creative.

    Core Theme: {theme}
    Protagonist Archetype: {archetype}
    The World's Core Contradiction: {contradiction}

    Generate the World Bible based on these inputs.
    """
    with st.spinner("Generating the core of your universe..."):
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text

def generate_story_chapter(story_context, world_bible, user_choice):
    """Generates the next narrative chapter, choices, and image prompt."""
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    generation_config = genai.types.GenerationConfig(temperature=0.9)
    prompt = f"""
    You are a multi-persona Storytelling Engine. Follow these steps precisely.
    The user's choice for the last chapter was: "{user_choice}".
    The full story context so far is: "{story_context}".
    The secret World Bible for this universe is: "{world_bible}".

    Step 1: Act as a Literary Artist. Write a rich, descriptive paragraph expanding on the user's choice.
    Step 2: Act as a Plot Theorist. Based on the new paragraph, generate three distinct, single-sentence plot choices for the user. One must be a 'Wildcard'.
    Step 3: Act as an Art Director. Based on the paragraph from Step 1, write a concise, descriptive prompt for an AI image generator (comma-separated keywords).
    Step 4: Format your entire response as a single, raw JSON object with NO markdown formatting, using these exact keys: "narrative_chapter", "next_choices", and "image_prompt".
    """
    with st.spinner("The Storyteller is weaving the next chapter..."):
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            cleaned_json_string = response.text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_json_string)
            return data
        except Exception as e:
            st.error(f"Error processing AI response: {e}. The AI may have returned an unexpected format.")
            st.code(response.text) # Show the raw response for debugging
            return None

def generate_image_stability(prompt):
    """Generates an image using the Stability.ai API with a credit-friendly model."""
    if not STABILITY_API_KEY:
        st.warning("Stability API Key not found. Image generation is disabled.")
        return None

    # We are using the Stable Diffusion v1.6 model via the Stability.ai API
    API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {STABILITY_API_KEY}",
    }

    payload = {
        "text_prompts": [{"text": f"cinematic, epic, high detail, masterpiece, {prompt}"}],
        "cfg_scale": 7,
        "height": 768,
        "width": 1024,
        "samples": 1,
        "steps": 30,
    }

    with st.spinner("The Stability artist is painting the scene..."):
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            image_b64 = data["artifacts"][0]["base64"]
            return Image.open(io.BytesIO(base64.b64decode(image_b64)))
        except requests.exceptions.HTTPError as e:
            st.error(f"HTTP error with Stability API: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            st.error(f"An error occurred with the Stability API: {e}")
            return None

def text_to_speech_player(text):
    """Generates a silent autoplaying HTML5 audio player for narration."""
    safe_text = text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ").strip()
    components.html(f"""
        <script>
            const synth = window.speechSynthesis;
            if (synth.speaking) {{ synth.cancel(); }}
            const utterance = new SpeechSynthesisUtterance("{safe_text}");
            utterance.pitch = 1;
            utterance.rate = 0.9;
            synth.speak(utterance);
        </script>
    """, height=0)

# --- 3. Streamlit Application UI and Logic ---

st.title("The Multimodal Storyteller 🪶")
st.markdown("Co-create a unique saga with AI. Forge a world, make choices, and bring your story to life with generated art and audio.")

if 'app_stage' not in st.session_state:
    st.session_state.app_stage = "world_forge"
    st.session_state.world_bible = None
    st.session_state.story_chapters = []
    st.session_state.latest_choices = []

if st.session_state.app_stage == "world_forge":
    with st.form("world_forge_form"):
        st.header("Step 1: Forge Your World")
        theme = st.selectbox("Choose a Core Theme:", ["Revenge", "Discovery", "Betrayal", "Survival", "Redemption"])
        archetype = st.selectbox("Choose a Protagonist Archetype:", ["The Outcast", "The Reluctant Hero", "The Idealist", "The Trickster"])
        contradiction = st.text_input("What is a strange contradiction in this world?", "A city of high magic where everyone is profoundly bored.")
        
        if st.form_submit_button("Set the Stage"):
            st.session_state.world_bible = generate_world_bible(theme, archetype, contradiction)
            st.session_state.app_stage = "story_start"
            st.rerun()

elif st.session_state.app_stage == "story_start":
    st.header("Step 2: Begin Your Saga")
    st.info("Your world has been created. Start your story with a single, compelling sentence.")
    
    with st.form("start_story_form"):
        initial_prompt = st.text_area("Your opening sentence:", "The last starship captain woke from cryo-sleep to the sound of a ticking clock.")
        if st.form_submit_button("Start the Saga") and initial_prompt:
            st.session_state.story_chapters.append({"text": initial_prompt, "image": None})
            st.session_state.latest_choices = [initial_prompt] 
            st.session_state.app_stage = "story_cycle"
            st.rerun()

elif st.session_state.app_stage == "story_cycle":
    st.header("Your Saga Unfolds...")
    for chapter in st.session_state.story_chapters:
        if chapter["image"]: st.image(chapter["image"], use_column_width=True)
        st.markdown(f"*{chapter['text']}*")
        st.markdown("---")
        
    if st.session_state.story_chapters:
        full_story_text = " ".join([ch['text'] for ch in st.session_state.story_chapters])
        col1, col2, col3 = st.columns([2,1,1])
        if col1.button("🔊 Narrate Story"): text_to_speech_player(full_story_text)
        if col2.button("⏸ Pause"): components.html("<script>window.speechSynthesis.pause();</script>", height=0)
        if col3.button("⏹ Stop"): components.html("<script>window.speechSynthesis.cancel();</script>", height=0)

    st.header("What Happens Next?")
    
    if st.session_state.latest_choices:
        choice_made = st.radio("Choose a path:", st.session_state.latest_choices, key="choice_radio")
        if st.button("Weave Next Chapter"):
            story_so_far = " ".join([ch['text'] for ch in st.session_state.story_chapters])
            ai_response = generate_story_chapter(story_so_far, st.session_state.world_bible, choice_made)
            
            if ai_response:
                new_image = generate_image_stability(ai_response["image_prompt"])
                st.session_state.story_chapters.append({"text": ai_response["narrative_chapter"], "image": new_image})
                st.session_state.latest_choices = ai_response["next_choices"]
                st.rerun()

st.markdown("---")
if st.session_state.app_stage != "world_forge":
    if st.button("Start a New Saga (Restart)"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

st.markdown("""
<div style="text-align: center; padding: 10px;">
    <p>Created by <b>Karthik</b></p>
</div>
""", unsafe_allow_html=True)