from config import model, API_avai, OPTIMAL_CONTENT_LENGTH, ENABLE_CONTENT_OPTIMIZATION, MAX_IMAGES_PER_REQUEST
import streamlit as st
import hashlib
import time
import json
from curriculum import get_keywords_for_bloom, get_question_type_info
from ncert_references import get_ncert_reference
import pickle
from pathlib import Path
from config import MAX_CACHE_AGE_HOURS
from PIL import Image
import io


CACHE_FILE = Path("question_cache.pkl")

def optimize_content(content, chapter=None, max_length=OPTIMAL_CONTENT_LENGTH):
    """Optimize content length for API efficiency"""
    if not ENABLE_CONTENT_OPTIMIZATION or len(content) <= max_length:
        return content
    
    # If chapter specified, try to extract relevant paragraphs
    if chapter:
        paragraphs = content.split('\n\n')
        relevant = [p for p in paragraphs if chapter.lower() in p.lower()]
        if relevant:
            content = '\n\n'.join(relevant)
            if len(content) <= max_length:
                return content
    
    # Truncate to optimal length, keeping complete sentences
    if len(content) > max_length:
        truncated = content[:max_length]
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        cut_point = max(last_period, last_newline)
        if cut_point > max_length * 0.7:  # Only cut if we keep at least 70%
            content = truncated[:cut_point + 1]
        else:
            content = truncated
    
    return content

def get_image_hash(images):
    """Generate hash for images for caching"""
    if not images:
        return ""
    try:
        hashes = []
        for img in images[:MAX_IMAGES_PER_REQUEST]:
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_hash = hashlib.md5(img_bytes.getvalue()).hexdigest()
            hashes.append(img_hash)
        return "_".join(hashes)
    except:
        return ""

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

def generate_questions(content, curriculum_info, images=None):
    if API_avai:
        return generate_with_api(content, curriculum_info, images)
    else:
        st.info("API unavailable. Using demo mode")
        return generate_demo(curriculum_info, images)

def generate_with_api(content, info, images=None):
    # Optimize content before processing
    optimized_content = optimize_content(content, info.get('chapter'), OPTIMAL_CONTENT_LENGTH)
    if len(optimized_content) < len(content) and ENABLE_CONTENT_OPTIMIZATION:
        reduction = len(content) - len(optimized_content)
        st.info(f"✓ Content optimized: Reduced by {reduction} characters for API efficiency")
    
    # Generate cache key including image hashes
    image_hash = get_image_hash(images) if images else ""
    cache_key = hashlib.md5(
        f"{optimized_content[:200]}{info['board']}{info['class']}{info['subject']}"
        f"{info['chapter']}{info['num_questions']}{info['question_type']}"
        f"{info['bloom_level']}{image_hash}".encode()
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
    
    # Only send images if question type requires them
    images_to_send = None
    if images and info['question_type'] in ['IMAGE', 'DIAGRAM']:
        images_to_send = images[:MAX_IMAGES_PER_REQUEST]  # Only send 1 image
    
    prompt = build_prompt(optimized_content, info, images_to_send)
    
    for attempt in range(2):
        try:
            # Prepare content parts (text + images if needed)
            content_parts = [prompt]
            if images_to_send:
                for img in images_to_send:
                    content_parts.append(img)
            
            response = model.generate_content(
                content_parts,
                generation_config={
                    'temperature': 0.3,
                    'max_output_tokens': 2048
                }
            )
            
            text = extract_text(response)
            questions = parse_json(text)
            
            if questions:
                ncert_ref = get_ncert_reference(info['subject'], info['class'], info['chapter'])
                for idx, q in enumerate(questions):
                    q.update({
                        'board': info['board'],
                        'class': info['class'],
                        'subject': info['subject'],
                        'chapter': info['chapter'],
                        'bloom_level': info['bloom_level'],
                        'ncert_reference': ncert_ref
                    })
                    # Attach image if available and question type requires it
                    if images and (info['question_type'] in ['IMAGE', 'DIAGRAM']):
                        # Use first image for all questions, or cycle through if multiple
                        img_idx = idx % len(images) if len(images) > 0 else 0
                        q['image_index'] = img_idx
                        q['has_image'] = True
                
                result = questions[:info['num_questions']]
                
                # Save to persistent cache
                cache[cache_key] = (result, time.time())
                save_cache(cache)
                
                return result
        
        except Exception as e:
            st.error(f"Generation error: {e}")
            if attempt == 0:
                time.sleep(2)
    
    return generate_demo(info, images)

def build_prompt(content, info, images=None):
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
    elif info['question_type'] == 'IMAGE':
        return base + f"""
Create exactly {info['num_questions']} image-based questions. Questions should ask about diagrams, figures, or visual content.

JSON FORMAT:
[
  {{
    "question": "Question about the image/diagram shown?",
    "marks": {q_type_info['marks']},
    "model_answer": "Answer describing what is shown in the image",
    "key_points": ["First observation", "Second observation", "Third observation"],
    "has_image": true
  }}
]
"""
    elif info['question_type'] == 'DIAGRAM':
        return base + f"""
Create exactly {info['num_questions']} diagram labeling questions. Ask students to label parts of a diagram.

JSON FORMAT:
[
  {{
    "question": "Label the parts of the diagram shown:",
    "marks": {q_type_info['marks']},
    "labels": {{"1": "Part name 1", "2": "Part name 2", "3": "Part name 3"}},
    "model_answer": "Complete labeled diagram explanation",
    "key_points": ["Label 1 description", "Label 2 description", "Label 3 description"],
    "has_image": true
  }}
]
"""
    elif info['question_type'] == 'CASE_STUDY':
        return base + f"""
Create exactly {info['num_questions']} case study questions. Present a scenario and ask analytical questions.

JSON FORMAT:
[
  {{
    "question": "Case study scenario: [Describe situation]. Based on this, answer: [Question]?",
    "marks": {q_type_info['marks']},
    "word_limit": "{q_type_info['word_limit']}",
    "model_answer": "Complete answer analyzing the case study",
    "key_points": ["First analysis point", "Second analysis point", "Third analysis point"],
    "marking_scheme": ["Award marks for identifying key factors", "Award marks for analysis", "Award marks for conclusion"]
  }}
]
"""
    else:
        return base + f"""
- Word Limit: {q_type_info.get('word_limit', 'As required')}

Create exactly {info['num_questions']} descriptive questions.

JSON FORMAT:
[
  {{
    "question": "Question text here?",
    "marks": {q_type_info['marks']},
    "word_limit": "{q_type_info.get('word_limit', 'As required')}",
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

def generate_demo(info, images=None):
    time.sleep(1)
    q_type_info = get_question_type_info(info['question_type'])
    ncert_ref = get_ncert_reference(info['subject'], info['class'], info['chapter'])
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
        elif info['question_type'] == 'IMAGE':
            img_idx = i % len(images) if images and len(images) > 0 else 0
            q = {
                "question": f"Observe the image/diagram. What does it show about {info['chapter']}?",
                "marks": q_type_info['marks'],
                "model_answer": f"Answer describing the image content related to {info['subject']}",
                "key_points": ["Visual element 1", "Visual element 2", "Visual element 3"],
                "has_image": True,
                "image_index": img_idx if images else 0
            }
        elif info['question_type'] == 'DIAGRAM':
            img_idx = i % len(images) if images and len(images) > 0 else 0
            q = {
                "question": f"Label the parts of the diagram shown:",
                "marks": q_type_info['marks'],
                "labels": {"1": "Part A", "2": "Part B", "3": "Part C"},
                "model_answer": f"Complete labeled diagram for {info['chapter']}",
                "key_points": ["Label 1: Description", "Label 2: Description", "Label 3: Description"],
                "has_image": True,
                "image_index": img_idx if images else 0
            }
        elif info['question_type'] == 'CASE_STUDY':
            q = {
                "question": f"Case Study: A scenario involving {info['chapter']}. Analyze and explain.",
                "marks": q_type_info['marks'],
                "word_limit": q_type_info.get('word_limit', '150-200 words'),
                "model_answer": f"Case study analysis for {info['subject']}",
                "key_points": ["Analysis point 1", "Analysis point 2", "Analysis point 3"],
                "marking_scheme": ["1 mark for identification", "1 mark for analysis", "1 mark for conclusion"]
            }
        else:
            q = {
                "question": f"Sample {info['question_type']} question {i+1} on {info['chapter']}",
                "marks": q_type_info['marks'],
                "word_limit": q_type_info.get('word_limit', '50-100 words'),
                "model_answer": f"Detailed answer for {info['subject']} as per NCERT.",
                "key_points": ["Main concept", "Supporting explanation", "Example"],
                "marking_scheme": ["1 mark for concept", "1 mark for explanation", "1 mark for example"]
            }
        
        q.update({
            'board': info['board'], 'class': info['class'],
            'subject': info['subject'], 'chapter': info['chapter'],
            'bloom_level': info['bloom_level'],
            'ncert_reference': ncert_ref
        })
        if images and (info['question_type'] in ['IMAGE', 'DIAGRAM']) and i < len(images):
            q['image_index'] = i
        questions.append(q)
    
    return questions