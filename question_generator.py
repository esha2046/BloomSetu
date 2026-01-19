from config import model, API_avai, OPTIMAL_CONTENT_LENGTH, ENABLE_CONTENT_OPTIMIZATION, MAX_IMAGES_PER_REQUEST
import streamlit as st
import hashlib
import time
import json
import re
from curriculum import get_keywords_for_bloom, get_question_type_info
from ncert_references import get_ncert_reference
import pickle
from pathlib import Path
from config import MAX_CACHE_AGE_HOURS
from PIL import Image
import io
from functools import lru_cache
from typing import Optional, List, Dict, Any


CACHE_FILE = Path("question_cache.pkl")
IMAGE_HASH_CACHE = {}  # In-memory cache for image hashes
_cache_data = None  # Lazy-loaded cache data
_cache_loaded = False  # Track if cache has been loaded

def optimize_content(content: str, chapter: Optional[str] = None, max_length: int = OPTIMAL_CONTENT_LENGTH) -> str:
    """Optimize content length for API efficiency with improved text extraction"""
    if not ENABLE_CONTENT_OPTIMIZATION or len(content) <= max_length:
        return content
    
    # If chapter specified, try to extract relevant paragraphs first
    if chapter:
        chapter_lower = chapter.lower()
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # Score paragraphs by relevance (exact match > partial match)
        scored_paragraphs = []
        for p in paragraphs:
            p_lower = p.lower()
            if chapter_lower in p_lower:
                score = 2 if chapter_lower == p_lower[:len(chapter_lower)] else 1
                scored_paragraphs.append((score, p))
        
        if scored_paragraphs:
            # Sort by relevance and take top paragraphs
            scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
            relevant = [p for _, p in scored_paragraphs]
            optimized = '\n\n'.join(relevant)
            
            # If optimized content fits, return it
            if len(optimized) <= max_length:
                return optimized
            
            # Otherwise, use optimized content for further truncation
            content = optimized
    
    # Smart truncation: preserve complete sentences and paragraphs
    if len(content) > max_length:
        # Try to find a good break point at sentence boundaries
        target_length = int(max_length * 0.95)  # Use 95% to leave buffer
        truncated = content[:target_length]
        
        # Find the last complete sentence
        sentence_endings = ['.', '!', '?', '।']  # Include Hindi full stop
        best_cut = -1
        
        for ending in sentence_endings:
            last_pos = truncated.rfind(ending)
            if last_pos > target_length * 0.7:  # Only if we keep at least 70%
                best_cut = max(best_cut, last_pos)
        
        # Also check for paragraph breaks
        last_para = truncated.rfind('\n\n')
        if last_para > target_length * 0.7:
            best_cut = max(best_cut, last_para)
        
        if best_cut > target_length * 0.7:
            content = content[:best_cut + 1].strip()
        else:
            # Fallback: truncate at word boundary
            last_space = truncated.rfind(' ')
            if last_space > target_length * 0.8:
                content = content[:last_space].strip()
            else:
                content = truncated.strip()
    
    return content

def get_image_hash(images: Optional[List[Image.Image]]) -> str:
    """Generate hash for images with caching to avoid reprocessing"""
    if not images:
        return ""
    
    try:
        # Use image id as cache key (PIL images have unique ids)
        image_ids = tuple(id(img) for img in images[:MAX_IMAGES_PER_REQUEST])
        
        # Check cache first
        if image_ids in IMAGE_HASH_CACHE:
            return IMAGE_HASH_CACHE[image_ids]
        
        # Generate hashes
        hashes = []
        for img in images[:MAX_IMAGES_PER_REQUEST]:
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=85, optimize=True)
            img_hash = hashlib.md5(img_bytes.getvalue()).hexdigest()
            hashes.append(img_hash)
        
        result = "_".join(hashes)
        
        # Cache the result (limit cache size to prevent memory issues)
        if len(IMAGE_HASH_CACHE) < 100:  # Limit to 100 entries
            IMAGE_HASH_CACHE[image_ids] = result
        
        return result
    except Exception:
        return ""

def load_cache() -> Dict[str, tuple]:
    """Lazy load cache - only load when needed"""
    global _cache_data, _cache_loaded
    
    if _cache_loaded:
        return _cache_data if _cache_data is not None else {}
    
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'rb') as f:
                _cache_data = pickle.load(f)
                _cache_loaded = True
                return _cache_data if _cache_data is not None else {}
        except Exception:
            _cache_data = {}
            _cache_loaded = True
            return {}
    
    _cache_data = {}
    _cache_loaded = True
    return {}

def save_cache(cache: Dict[str, tuple], incremental: bool = True):
    """Save cache with optional incremental updates"""
    global _cache_data
    
    try:
        # If incremental and we have existing cache, merge
        if incremental and _cache_data:
            cache = {**_cache_data, **cache}
        
        _cache_data = cache
        
        # Use atomic write to prevent corruption
        temp_file = CACHE_FILE.with_suffix('.tmp')
        with open(temp_file, 'wb') as f:
            pickle.dump(cache, f)
        temp_file.replace(CACHE_FILE)  # Atomic rename
    except Exception:
        pass

def cleanup_expired_cache():
    """Remove expired entries from cache"""
    global _cache_data
    if not _cache_data:
        return
    
    current_time = time.time()
    expired_keys = [
        key for key, (_, timestamp) in _cache_data.items()
        if (current_time - timestamp) / 3600 >= MAX_CACHE_AGE_HOURS
    ]
    
    for key in expired_keys:
        del _cache_data[key]
    
    if expired_keys:
        save_cache(_cache_data, incremental=False)

def generate_questions(content, curriculum_info, images=None):
    if API_avai:
        return generate_with_api(content, curriculum_info, images)
    else:
        st.info("API unavailable. Using demo mode")
        return generate_demo(curriculum_info, images)

def generate_with_api(content: str, info: Dict[str, Any], images: Optional[List[Image.Image]] = None) -> List[Dict[str, Any]]:
    """Generate questions with API, optimized for performance"""
    # Optimize content before processing
    optimized_content = optimize_content(content, info.get('chapter'), OPTIMAL_CONTENT_LENGTH)
    if len(optimized_content) < len(content) and ENABLE_CONTENT_OPTIMIZATION:
        reduction = len(content) - len(optimized_content)
        st.info(f"✓ Content optimized: Reduced by {reduction} characters for API efficiency")
    
    # Generate cache key efficiently (use more content for better cache hits)
    image_hash = get_image_hash(images) if images else ""
    # Use first 500 chars instead of 200 for better cache key uniqueness
    content_sample = optimized_content[:500] if len(optimized_content) > 500 else optimized_content
    cache_key_data = (
        f"{content_sample}{info['board']}{info['class']}{info['subject']}"
        f"{info['chapter']}{info['num_questions']}{info['question_type']}"
        f"{info['bloom_level']}{image_hash}"
    )
    cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()
    
    # Load cache (lazy loading)
    cache = load_cache()
    
    # Check cache with expiry
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        age_hours = (time.time() - timestamp) / 3600
        if age_hours < MAX_CACHE_AGE_HOURS:
            st.info("✓ Using cached questions (saves API calls)")
            return cached_data
        else:
            # Remove expired entry
            del cache[cache_key]
    
    # Only send images if question type requires them (early exit optimization)
    images_to_send = None
    requires_images = info['question_type'] in ['IMAGE', 'DIAGRAM']
    if images and requires_images:
        images_to_send = images[:MAX_IMAGES_PER_REQUEST]
    
    # Build prompt (cached internally)
    prompt = build_prompt(optimized_content, info, images_to_send)
    
    # Pre-compute values used in loop
    ncert_ref = get_ncert_reference(info['subject'], info['class'], info['chapter'])
    num_questions_needed = info['num_questions']
    question_type = info['question_type']
    
    # Exponential backoff retry logic
    max_attempts = 2
    base_delay = 1
    
    for attempt in range(max_attempts):
        try:
            # Prepare content parts efficiently
            content_parts = [prompt]
            if images_to_send:
                content_parts.extend(images_to_send)  # More efficient than loop
            
            # Adjust temperature for retries (lower = more consistent)
            temperature = 0.2 if attempt > 0 else 0.3
            
            response = model.generate_content(
                content_parts,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': 4096  # Increased to handle longer case study questions
                }
            )
            
            text = extract_text(response)
            
            # Early validation
            if not text or len(text.strip()) < 10:
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    st.warning(f"API returned empty response. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                break
            
            questions = parse_json(text)
            
            # Validate parsed questions and their structure
            if not questions or not isinstance(questions, list) or len(questions) == 0:
                # On retry, try a simpler prompt structure
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    st.warning(f"No valid questions parsed. Retrying with stricter prompt in {delay}s...")
                    time.sleep(delay)
                    
                    # Modify prompt for retry - be more explicit about JSON
                    if attempt == 1:
                        # Add more explicit JSON instructions
                        prompt = build_prompt(optimized_content, info, images_to_send)
                        prompt += "\n\nCRITICAL: Return ONLY valid JSON array. No markdown, no explanations, no code blocks. Start with [ and end with ]. Ensure all strings are properly closed with quotes."
                        content_parts = [prompt]
                        if images_to_send:
                            content_parts.extend(images_to_send)
                    continue
                else:
                    # Last attempt failed - show helpful error
                    if len(text) > 100:
                        # Response seems long, might be truncated
                        st.error(f"Failed to parse questions after {max_attempts} attempts. The response may be incomplete or malformed.")
                    else:
                        st.error(f"Failed to parse questions. Response was too short or invalid.")
                break
            
            # Validate question structure and check for placeholders
            valid_questions = []
            for q in questions:
                if not isinstance(q, dict):
                    continue
                
                # Check for required fields based on question type
                if question_type == 'MCQ':
                    required_fields = ['question', 'options', 'correct_answer', 'explanation']
                elif question_type in ['IMAGE', 'DIAGRAM']:
                    required_fields = ['question', 'model_answer', 'key_points']
                else:
                    required_fields = ['question', 'model_answer', 'key_points']
                
                # Check if all required fields exist
                if all(field in q for field in required_fields):
                    # Check for placeholder text
                    question_text = q.get('question', '').lower()
                    if question_text and len(question_text) >= 20:
                        if 'sample' not in question_text and 'placeholder' not in question_text:
                            valid_questions.append(q)
            
            # If we lost questions due to validation, warn but continue if we have some
            if len(valid_questions) < len(questions):
                st.warning(f"⚠️ Filtered out {len(questions) - len(valid_questions)} invalid questions")
            
            # If no valid questions after filtering, retry
            if len(valid_questions) == 0:
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    st.warning(f"No valid questions after validation. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    st.error("⚠️ Could not generate valid questions after validation")
                    break
            
            questions = valid_questions
            
            # Check first question for placeholder (additional check)
            first_q = questions[0]
            question_text = first_q.get('question', '').lower()
            is_placeholder = (
                'sample' in question_text or 
                'placeholder' in question_text or 
                len(question_text) < 20
            )
            
            if is_placeholder and len(questions) == 1:
                # Only retry if this is the only question and it's a placeholder
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    st.warning(f"Generated questions appear to be placeholders. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    st.warning("⚠️ Generated questions may contain placeholders")
            
            # Enrich questions with metadata (batch operation)
            metadata = {
                'board': info['board'],
                'class': info['class'],
                'subject': info['subject'],
                'chapter': info['chapter'],
                'bloom_level': info['bloom_level'],
                'ncert_reference': ncert_ref
            }
            
            for idx, q in enumerate(questions):
                q.update(metadata)
                # Attach image if available and question type requires it
                if images and requires_images:
                    img_idx = idx % len(images) if len(images) > 0 else 0
                    q['image_index'] = img_idx
                    q['has_image'] = True
            
            result = questions[:num_questions_needed]
            
            # Save to cache incrementally
            cache[cache_key] = (result, time.time())
            save_cache({cache_key: cache[cache_key]}, incremental=True)
            
            return result
        
        except Exception as e:
            error_msg = str(e).lower()
            st.error(f"Generation error: {str(e)}")
            
            # Handle specific error types
            if "quota" in error_msg or "limit" in error_msg:
                st.warning("API quota may be exceeded. Using demo mode.")
                break
            elif attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                st.info(f"Retrying API call in {delay}s...")
                time.sleep(delay)
            else:
                st.warning("API call failed after retries. Falling back to demo mode.")
    
    # Only use demo if API is unavailable or all attempts failed
    if not API_avai:
        return generate_demo(info, images)
    else:
        # Try one more time with a simpler approach or return demo
        st.warning("⚠️ Could not generate questions from API. Using demo questions.")
        return generate_demo(info, images)

# Cache prompt templates to avoid repeated string operations
@lru_cache(maxsize=32)
def _get_cached_keywords(bloom_level: str) -> tuple:
    """Cache keywords for bloom level"""
    return tuple(get_keywords_for_bloom(bloom_level)[:4])

@lru_cache(maxsize=16)
def _get_cached_q_type_info(question_type: str) -> tuple:
    """Cache question type info"""
    info = get_question_type_info(question_type)
    return (info.get('name', ''), info.get('marks', 1), info.get('word_limit', 'As required'))

def build_prompt(content: str, info: Dict[str, Any], images: Optional[List] = None) -> str:
    """Build prompt efficiently with cached lookups"""
    # Use cached lookups
    q_type_info_tuple = _get_cached_q_type_info(info['question_type'])
    q_type_name, q_type_marks, q_type_word_limit = q_type_info_tuple
    
    keywords_tuple = _get_cached_keywords(info['bloom_level'])
    keywords_str = ', '.join(keywords_tuple)
    
    chapter = info['chapter'] if info['chapter'] else 'General'
    
    # Build base prompt efficiently
    base = f"""You are creating questions for {info['board']} Board, Class {info['class']}, {info['subject']} exam.
Chapter: {chapter}

CRITICAL REQUIREMENTS:
- Generate REAL, SPECIFIC questions based on the content provided below
- DO NOT use placeholder text like "Sample question" or "Question text here"
- Questions must be directly related to the content provided
- Follow NCERT/CBSE pattern exactly
- Use Indian exam terminology: {keywords_str}
- Return ONLY valid JSON array, no explanations or markdown
- Use proper Indian English (colour, favour, etc.)
- Each question must be unique and specific to the content

CONTENT TO USE FOR GENERATING QUESTIONS:
{content}

Question Details:
- Type: {q_type_name}
- Marks per question: {q_type_marks}
- Bloom's Taxonomy Level: {info['bloom_level']}
- Number of questions needed: {info['num_questions']}

IMPORTANT: Generate actual questions based on the content above. Do not use placeholder text.
"""

    # Build type-specific prompt efficiently
    question_type = info['question_type']
    num_questions = info['num_questions']
    bloom_level = info['bloom_level']
    
    if question_type == 'MCQ':
        return base + f"""
Generate exactly {num_questions} multiple choice questions based on the content provided above.

Each question must:
1. Be a specific question directly related to the content
2. Test understanding at {bloom_level} level
3. Have 4 distinct options where only one is correct
4. Include a clear explanation

CRITICAL JSON FORMAT REQUIREMENTS:
- Return ONLY a valid JSON array
- Start with [ and end with ]
- No markdown code blocks (no ```json or ```)
- No explanations before or after the JSON
- Escape all quotes properly in strings
- Use double quotes for all strings

JSON FORMAT:
[
  {{
    "question": "Write a specific question based on the content above?",
    "options": {{"A": "Option based on content", "B": "Another option", "C": "Third option", "D": "Fourth option"}},
    "correct_answer": "A",
    "explanation": "Explanation why this answer is correct based on the content",
    "marks": {q_type_marks}
  }}
]

Remember: Generate REAL questions based on the content. Return ONLY the JSON array, nothing else.
"""
    elif question_type == 'IMAGE':
        return base + f"""
Create exactly {num_questions} image-based questions. Questions should ask about diagrams, figures, or visual content.

JSON FORMAT:
[
  {{
    "question": "Question about the image/diagram shown?",
    "marks": {q_type_marks},
    "model_answer": "Answer describing what is shown in the image",
    "key_points": ["First observation", "Second observation", "Third observation"],
    "has_image": true
  }}
]
"""
    elif question_type == 'DIAGRAM':
        return base + f"""
Create exactly {num_questions} diagram labeling questions. Ask students to label parts of a diagram.

JSON FORMAT:
[
  {{
    "question": "Label the parts of the diagram shown:",
    "marks": {q_type_marks},
    "labels": {{"1": "Part name 1", "2": "Part name 2", "3": "Part name 3"}},
    "model_answer": "Complete labeled diagram explanation",
    "key_points": ["Label 1 description", "Label 2 description", "Label 3 description"],
    "has_image": true
  }}
]
"""
    elif question_type == 'CASE_STUDY':
        return base + f"""
Create exactly {num_questions} case study questions. Present a scenario and ask analytical questions.

JSON FORMAT:
[
  {{
    "question": "Case study scenario: [Describe situation]. Based on this, answer: [Question]?",
    "marks": {q_type_marks},
    "word_limit": "{q_type_word_limit}",
    "model_answer": "Complete answer analyzing the case study",
    "key_points": ["First analysis point", "Second analysis point", "Third analysis point"],
    "marking_scheme": ["Award marks for identifying key factors", "Award marks for analysis", "Award marks for conclusion"]
  }}
]
"""
    else:
        return base + f"""
- Word Limit: {q_type_word_limit}

Generate exactly {num_questions} descriptive questions based on the content provided above.

Each question must:
1. Be a complete, specific question related to the content
2. Test understanding at {bloom_level} level
3. Have a detailed model answer based on the content
4. Include specific key points from the content

CRITICAL JSON FORMAT REQUIREMENTS:
- Return ONLY a valid JSON array
- Start with [ and end with ]
- No markdown code blocks (no ```json or ```)
- No explanations before or after the JSON
- Escape all quotes properly in strings
- Use double quotes for all strings

JSON FORMAT:
[
  {{
    "question": "Write a specific question based on the content provided above?",
    "marks": {q_type_marks},
    "word_limit": "{q_type_word_limit}",
    "model_answer": "Detailed answer based on the content, following NCERT pattern",
    "key_points": ["Specific concept from content", "Another specific point from content", "Third specific point"],
    "marking_scheme": ["Award marks for first concept", "Award marks for second concept", "Award marks for third concept"]
  }}
]

Remember: Generate REAL questions based on the content. Return ONLY the JSON array, nothing else.
"""

def extract_text(response):
    try:
        return response.text.strip()
    except:
        if hasattr(response, 'candidates') and response.candidates:
            parts = response.candidates[0].content.parts
            return " ".join([p.text for p in parts if hasattr(p, 'text')])
    return ""

def parse_json(text: str) -> List[Dict[str, Any]]:
    """Parse JSON from API response with robust error handling and incomplete JSON recovery"""
    if not text or len(text.strip()) < 5:
        return []
    
    original_text = text
    text = text.strip()
    
    # Remove markdown code blocks efficiently
    if text.startswith("```json"):
        text = text[7:].strip()
    elif text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    
    # Try direct JSON parsing first (fastest path)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
        elif isinstance(parsed, dict) and 'questions' in parsed:
            questions = parsed.get('questions', [])
            if isinstance(questions, list) and len(questions) > 0:
                return questions
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON array from text (common case)
    start_idx = text.find('[')
    end_idx = text.rfind(']')
    
    if start_idx != -1:
        # If we found start but no end, try to complete it
        if end_idx == -1 or end_idx <= start_idx:
            # Try to find where the last complete object ends
            # Look for closing braces to estimate where array should end
            brace_count = 0
            last_brace_pos = -1
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_brace_pos = i
            # If we found complete objects, try adding closing bracket
            if last_brace_pos > start_idx:
                # Check if there are multiple objects (comma separated)
                potential_json = text[start_idx:last_brace_pos+1]
                # Count how many complete question objects we have
                question_objects = re.findall(r'\{[^{}]*"question"[^{}]*\}', potential_json)
                if not question_objects:
                    # Try a more lenient approach - extract everything up to last complete brace
                    potential_json = text[start_idx:last_brace_pos+1] + ']'
                    try:
                        parsed = json.loads(potential_json)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            return parsed
                    except:
                        pass
        
        # Normal case: we have both brackets
        if end_idx != -1 and end_idx > start_idx:
            try:
                json_str = text[start_idx:end_idx+1]
                parsed = json.loads(json_str)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed
            except json.JSONDecodeError:
                pass
    
    # Enhanced JSON fixing: handle more edge cases
    try:
        if '[' in text and ('"question"' in text or '"options"' in text):
            fixed_text = text
            
            # Remove trailing commas
            fixed_text = re.sub(r',\s*}', '}', fixed_text)
            fixed_text = re.sub(r',\s*]', ']', fixed_text)
            
            # Fix newlines in strings (but preserve structure)
            fixed_text = re.sub(r'(?<!\\)\n', '\\n', fixed_text)
            fixed_text = re.sub(r'\r', '', fixed_text)
            
            # Try to extract JSON array
            start_idx = fixed_text.find('[')
            end_idx = fixed_text.rfind(']')
            
            # If no closing bracket, try to add one
            if start_idx != -1:
                if end_idx == -1 or end_idx <= start_idx:
                    # Find last complete object
                    brace_level = 0
                    last_complete_pos = -1
                    in_string = False
                    escape_next = False
                    
                    for i in range(start_idx, len(fixed_text)):
                        char = fixed_text[i]
                        if escape_next:
                            escape_next = False
                            continue
                        if char == '\\':
                            escape_next = True
                            continue
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                        if not in_string:
                            if char == '{':
                                brace_level += 1
                            elif char == '}':
                                brace_level -= 1
                                if brace_level == 0:
                                    last_complete_pos = i
                    
                    if last_complete_pos > start_idx:
                        # Extract up to last complete object and close array
                        json_str = fixed_text[start_idx:last_complete_pos+1] + ']'
                        try:
                            parsed = json.loads(json_str)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                return parsed
                        except:
                            pass
                else:
                    json_str = fixed_text[start_idx:end_idx+1]
                    try:
                        parsed = json.loads(json_str)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            return parsed
                    except json.JSONDecodeError:
                        # Try cleaning and retrying
                        json_str = json_str.replace('\n', ' ').replace('\t', ' ')
                        json_str = ''.join(char if char.isprintable() or char in ['\n', '\t'] else ' ' for char in json_str)
                        try:
                            parsed = json.loads(json_str)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                return parsed
                        except:
                            pass
    except Exception:
        pass
    
    # Last resort: extract complete question objects using regex (for truncated responses)
    try:
        questions = []
        # Pattern to find complete question objects
        # Look for { "question": "...", ... } patterns
        pattern = r'\{\s*"question"\s*:\s*"([^"]*(?:\\.[^"]*)*)"[^}]*\}'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in matches:
            obj_start = match.start()
            obj_text = match.group(0)
            # Try to parse this object
            try:
                # Complete the object if needed
                if not obj_text.strip().endswith('}'):
                    # Try to find where object should end
                    brace_count = obj_text.count('{') - obj_text.count('}')
                    if brace_count > 0:
                        # Look ahead for closing brace
                        remaining = text[obj_start + len(obj_text):obj_start + len(obj_text) + 500]
                        for i, char in enumerate(remaining):
                            if char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    obj_text = text[obj_start:obj_start + len(obj_text) + i + 1]
                                    break
                
                parsed_obj = json.loads(obj_text)
                if isinstance(parsed_obj, dict) and 'question' in parsed_obj:
                    questions.append(parsed_obj)
            except:
                continue
        
        if len(questions) > 0:
            return questions
    except Exception:
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