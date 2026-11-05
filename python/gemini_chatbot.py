
import os
import streamlit as st
import google.generativeai as genai

# Fetch API key safely from Streamlit secrets or environment variables
api_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None

def ask_gemini(prompt):
    if not model:
        return "⚠️ Gemini API key is missing. Please configure GEMINI_API_KEY in Streamlit App Secrets."
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return """
    ⚠️ Gemini API quota exceeded.

    You have reached the free-tier request limit.

    Options:
    • Wait a few minutes and try again
    • Use a new Gemini API key
    • Upgrade your Gemini API plan

    The Diet Recommendation System will continue working normally.
    """
        else:
            return f"Error: {str(e)}"

        

