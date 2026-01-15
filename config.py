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
MAX_CONTENT_LENGTH = 3000
OPTIMAL_CONTENT_LENGTH = 1500  # Target length for API calls
MAX_PDF_PAGES = 5 
REQUEST_COOLDOWN = 10

DAILY_LIMIT = 10  
MAX_CACHE_AGE_HOURS = 48  # Increased cache age

# Image optimization settings
MAX_IMAGE_SIZE_KB = 200
MAX_IMAGE_DIMENSIONS = (800, 600)
IMAGE_QUALITY = 85
MAX_IMAGES_PER_REQUEST = 1  # Only send 1 image per API call

# Content optimization
ENABLE_CONTENT_OPTIMIZATION = True
ENABLE_IMAGE_OPTIMIZATION = True

# ML Evaluation settings
ENABLE_SEMANTIC_EVALUATION = True
SEMANTIC_SIMILARITY_THRESHOLD = 0.6  # Minimum similarity for partial credit