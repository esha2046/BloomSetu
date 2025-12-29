from config import model, API_avai
import streamlit as st
import hashlib
import time
import json
from curriculum import get_keywords_for_bloom, get_question_type_info
import pickle
from pathlib import Path
from config import MAX_CACHE_AGE_HOURS


CACHE_FILE = Path("question_cache.pkl")

def load_cache():
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    except:
        pass

def generate_questions(content, curriculum_info):
    if API_avai:
        return generate_with_api(content, curriculum_info)
    else:
        st.info("API unavailable. Using demo mode")
        return generate_demo(curriculum_info)

def generate_with_api(content, info):
    cache_key = hashlib.md5(
        f"{content[:200]}{info['board']}{info['class']}{info['subject']}"
        f"{info['chapter']}{info['num_questions']}{info['question_type']}"
        f"{info['bloom_level']}".encode()
    ).hexdigest()
    
    # Load persistent cache
    cache = load_cache()
    
    # Check cache with expiry
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        age_hours = (time.time() - timestamp) / 3600
        if age_hours < MAX_CACHE_AGE_HOURS:
            st.info("✓ Using cached questions (saves API calls)")
            return cached_data
    
    prompt = build_prompt(content, info)
    
    for attempt in range(2):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.3,
                    'max_output_tokens': 2048
                }
            )
            
            text = extract_text(response)
            questions = parse_json(text)
            
            if questions:
                for q in questions:
                    q.update({
                        'board': info['board'],
                        'class': info['class'],
                        'subject': info['subject'],
                        'chapter': info['chapter'],
                        'bloom_level': info['bloom_level']
                    })
                
                result = questions[:info['num_questions']]
                
                # Save to persistent cache
                cache[cache_key] = (result, time.time())
                save_cache(cache)
                
                return result
        
        except Exception as e:
            st.error(f"Generation error: {e}")
            if attempt == 0:
                time.sleep(2)
    
    return generate_demo(info)

def build_prompt(content, info):
    q_type_info = get_question_type_info(info['question_type'])
    keywords = get_keywords_for_bloom(info['bloom_level'])
    
    base = f"""You are creating questions for {info['board']} Board, Class {info['class']}, {info['subject']} exam.
Chapter: {info['chapter'] if info['chapter'] else 'General'}

STRICT REQUIREMENTS:
- Follow NCERT/CBSE pattern exactly
- Use Indian exam terminology: {', '.join(keywords[:4])}
- Return ONLY valid JSON, no explanations
- Questions must be based ONLY on the content provided
- Use proper Indian English (colour, favour, etc.)

CONTENT TO USE:
{content}

Question Details:
- Type: {q_type_info['name']}
- Marks per question: {q_type_info['marks']}
- Bloom's Level: {info['bloom_level']}
"""

    if info['question_type'] == 'MCQ':
        return base + f"""
Create exactly {info['num_questions']} multiple choice questions.

JSON FORMAT:
[
  {{
    "question": "Question text here?",
    "options": {{"A": "First option", "B": "Second option", "C": "Third option", "D": "Fourth option"}},
    "correct_answer": "A",
    "explanation": "Why this answer is correct",
    "marks": {q_type_info['marks']}
  }}
]
"""
    else:
        return base + f"""
- Word Limit: {q_type_info['word_limit']}

Create exactly {info['num_questions']} descriptive questions.

JSON FORMAT:
[
  {{
    "question": "Question text here?",
    "marks": {q_type_info['marks']},
    "word_limit": "{q_type_info['word_limit']}",
    "model_answer": "Complete answer following NCERT pattern",
    "key_points": ["First key concept", "Second key concept", "Third key concept"],
    "marking_scheme": ["Award 1 mark for concept", "Award 1 mark for explanation", "Award 1 mark for example"]
  }}
]
"""

def extract_text(response):
    try:
        return response.text.strip()
    except:
        if hasattr(response, 'candidates') and response.candidates:
            parts = response.candidates[0].content.parts
            return " ".join([p.text for p in parts if hasattr(p, 'text')])
    return ""

def parse_json(text):

    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except:
        pass
    
    s = text.find('[')
    e = text.rfind(']')
    if s!=-1 and e!=-1:
        try:
            return json.loads(text[s:e+1])
        except:
            pass
    return []

def generate_demo(info):
    time.sleep(1)
    q_type_info = get_question_type_info(info['question_type'])
    questions = []
    
    for i in range(info['num_questions']):
        if info['question_type'] == 'MCQ':
            q = {
                "question": f"Sample {info['subject']} MCQ {i+1} ({info['bloom_level']} level)",
                "options": {"A": f"Option A about {info['chapter']}", "B": "Option B", "C": "Option C", "D": "Option D"},
                "correct_answer": "A",
                "explanation": "This demonstrates the key concept",
                "marks": q_type_info['marks']
            }
        else:
            q = {
                "question": f"Sample {info['question_type']} question {i+1} on {info['chapter']}",
                "marks": q_type_info['marks'],
                "word_limit": q_type_info['word_limit'],
                "model_answer": f"Detailed answer for {info['subject']} as per NCERT.",
                "key_points": ["Main concept", "Supporting explanation", "Example"],
                "marking_scheme": ["1 mark for concept", "1 mark for explanation", "1 mark for example"]
            }
        
        q.update({
            'board': info['board'], 'class': info['class'],
            'subject': info['subject'], 'chapter': info['chapter'],
            'bloom_level': info['bloom_level']
        })
        questions.append(q)
    
    return questions