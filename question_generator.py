from config import model , API_avai
import streamlit as st
import hashlib
import time
import json

def generate_ques(content,num=5,difficulty="Apply",ques_type="MCQ"):
    if API_avai:
        return ques_with_api(content,num,difficulty,ques_type)
    else:
        st.info("Couldn't connect to API")
        return ques_demo(content,num,difficulty,ques_type) #fallback func


def chunk_content(content,size=600,overlap=100):
    chunks = []
    start = 0
    length = len(content)
    
    while start<length:
        end = start + size
        chunks.append(content[start:end])
        start = end-overlap #we do this so that each chunk can preserve content of the previous chunk
    
    return chunks


def ques_with_api(content,num,difficulty,ques_type):
    chunk = chunk_content(content) #can change limit
    curr_chunk = chunk[:2] #can change no. of chunks
    context = "\n\n".join(curr_chunk)

    cache_key = hashlib.md5((context + str(num) + difficulty + ques_type).encode()).hexdigest() #cache chunk to prevent repeated api calls

    if 'question_cache' not in st.session_state:
        st.session_state.question_cache = {}

    if cache_key in st.session_state.question_cache:
        return st.session_state.question_cache[cache_key]
    
    prompt = build_prompt(content,num,difficulty,ques_type)

    for attempt in range(2):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature' : 0.3, #factual data for mcqs
                    'max_output_tokens' : 2048
                }
            )

            
            text = extract_response(response)
            questions = parse_response(text)

            st.write(f"Response text: {text[:200]}")
            st.write(f"Parsed questions: {questions}")

            if questions:
                st.session_state.question_cache[cache_key] = questions[:num]
                return questions[:num]

        except Exception as e:
            st.error(f"Error: {e}")
            if attempt ==0:
                st.info("Retrying...")
                time.sleep(2)
            
    return ques_demo(content, num, difficulty, ques_type)

def build_prompt(content, num, difficulty, ques_type):
    """
    Builds a strict JSON-only prompt.
    Prevents Gemini from wasting tokens on explanations.
    """
    if ques_type == "MCQ":
        return f"""
Create exactly {num} multiple-choice questions based ONLY on the content below.

CONTENT:
{content}

Difficulty Level: {difficulty}

IMPORTANT:
- Do NOT summarize the content
- Do NOT repeat the content
- Return ONLY valid JSON

FORMAT:
[
  {{
    "question": "Question text?",
    "options": {{
      "A": "Option A",
      "B": "Option B",
      "C": "Option C",
      "D": "Option D"
    }},
    "correct_answer": "A",
    "explanation": "Brief explanation",
    "difficulty": "{difficulty}"
  }}
]
"""
    else:
        return f"""
Create exactly {num} short-answer questions based ONLY on the content below.

CONTENT:
{content}

Difficulty Level: {difficulty}

IMPORTANT:
- Do NOT summarize the content
- Do NOT repeat the content
- Return ONLY valid JSON

FORMAT:
[
  {{
    "question": "Question text?",
    "model_answer": "Model answer",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "difficulty": "{difficulty}"
  }}
]
"""

def extract_response(response):
    try:
        return response.text.strip()
    except:
        if hasattr(response, 'candidates') and response.candidates:
            parts = response.candidates[0].content.parts #return first candidate
            return " ".join([p.text for p in parts if hasattr(p, 'text')]) 
    return ""

def parse_response(text):
    text = text.strip()

    #removing markdown apparently

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    s = text.find('[')
    e = text.rfind(']')

    try:
        return json.loads(text)
    except:
        pass

    if s != -1 and e != -1:
        try:
            return json.loads(text[s:e+1])
        except:
            pass

    return []
    

#chatgpted idc
def ques_demo(content, num, difficulty, ques_type):
    """
    Generates mock questions when API is unavailable.
    Useful for demos and testing.
    """
    time.sleep(1)

    content_id = hashlib.md5(content.encode()).hexdigest()[:8]

    if ques_type == "MCQ":
        topics = ["concept", "principle", "application", "theory", "process"]
        return [{
            "question": f"Which statement best explains the {topics[i % len(topics)]}?",
            "options": {
                "A": f"Option A (ID {content_id[:4]})",
                "B": "Option B describing a key idea",
                "C": "Option C offering interpretation",
                "D": "Option D giving perspective"
            },
            "correct_answer": ["A", "B", "C"][i % 3],
            "explanation": f"This option best represents the {topics[i % len(topics)]}.",
            "difficulty": difficulty
        } for i in range(num)]
    else:
        aspects = ["main concept", "key principle", "application", "theory", "process"]
        return [{
            "question": f"Explain the {aspects[i % len(aspects)]}.",
            "model_answer": f"The {aspects[i % len(aspects)]} is fundamental to understanding the topic.",
            "key_points": [
                f"Identifies the {aspects[i % len(aspects)]}",
                "Explains relevance",
                "Mentions practical importance"
            ],
            "difficulty": difficulty
        } for i in range(num)]