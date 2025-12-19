import os 
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

API_avai = False
model = None

if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        API_avai = True
    except Exception:
        pass


MIN_CONTENT_LENGTH = 50
MAX_CONTENT_LENGTH = 3000 #max char for chunking
MAX_PDF_PAGES = 5 
REQUEST_COOLDOWN = 10 #seconds duh