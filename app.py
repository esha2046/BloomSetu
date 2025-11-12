import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import PyPDF2
from docx import Document
import io
from datetime import datetime
import time
import hashlib

# Load environment variables
load_dotenv()

# Try to configure API, but don't fail if not available
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        API_AVAILABLE = True
    else:
        API_AVAILABLE = False
except:
    API_AVAILABLE = False

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'student_answers' not in st.session_state:
    st.session_state.student_answers = {}
if 'results' not in st.session_state:
    st.session_state.results = None
if 'student_history' not in st.session_state:
    st.session_state.student_history = []
if 'last_request_time' not in st.session_state:
    st.session_state.last_request_time = 0
if 'question_type' not in st.session_state:
    st.session_state.question_type = 'MCQ'
if 'extracted_content' not in st.session_state:
    st.session_state.extracted_content = ""

# Helper Functions
def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file with character limit"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages[:5]:  # Limit to first 5 pages
            text += page.extract_text()
        return text[:3000]  # Limit to 3000 characters
    except Exception as e:
        st.error(f"Error extracting PDF: {str(e)}")
        return ""

def extract_text_from_docx(docx_file):
    """Extract text from DOCX file with character limit"""
    try:
        doc = Document(docx_file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text[:3000]  # Limit to 3000 characters
    except Exception as e:
        st.error(f"Error extracting DOCX: {str(e)}")
        return ""

def chunk_content(content, max_chars=1500):
    """Split content into manageable chunks"""
    if len(content) <= max_chars:
        return content
    
    words = content.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += len(word) + 1
        if current_length > max_chars:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks[0] if chunks else content

def generate_demo_questions(content, num_questions, difficulty, question_type):
    """Generate demo questions based on content for demonstration"""
    
    # Simulate API delay
    time.sleep(2)
    
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    
    if question_type == "MCQ":
        questions = []
        topics = ["concept", "principle", "application", "theory", "process"]
        
        for i in range(num_questions):
            questions.append({
                "question": f"Based on the provided content, which statement best describes the {topics[i % len(topics)]} discussed in section {i+1}?",
                "options": {
                    "A": f"Option A related to the content (ID: {content_hash[:4]})",
                    "B": f"Option B explaining a key concept from the material",
                    "C": f"Option C providing an alternative interpretation",
                    "D": f"Option D offering a different perspective"
                },
                "correct_answer": ["A", "B", "C"][i % 3],
                "explanation": f"This answer correctly identifies the main point discussed in the content regarding {topics[i % len(topics)]}. The material emphasizes this aspect at the {difficulty} level of understanding.",
                "difficulty": difficulty
            })
        return questions
    
    else:  # Short Answer
        questions = []
        aspects = ["main concept", "key principle", "important application", "core theory", "critical process"]
        
        for i in range(num_questions):
            questions.append({
                "question": f"Explain the {aspects[i % len(aspects)]} presented in the content and discuss its significance.",
                "model_answer": f"The {aspects[i % len(aspects)]} discussed in the provided material relates to the fundamental understanding of the topic. It demonstrates how theoretical concepts apply in practical scenarios and connects to broader themes in the subject area. This understanding is crucial for {difficulty}-level comprehension.",
                "key_points": [
                    f"Identifies the {aspects[i % len(aspects)]}",
                    "Explains the relationship to broader concepts",
                    "Discusses practical implications"
                ],
                "difficulty": difficulty
            })
        return questions

def generate_questions_api(content, num_questions, difficulty, question_type):
    """Generate questions using Gemini API with retry logic"""
    
    content_chunk = chunk_content(content, max_chars=1500)
    
    if question_type == "MCQ":
        prompt = f"""
Based on the following content, generate exactly {num_questions} multiple-choice questions 
at the "{difficulty}" level of Bloom's Taxonomy.

Content: {content_chunk}

Requirements:
1. Each question should test understanding at the {difficulty} cognitive level
2. Provide 4 options (A, B, C, D) with only ONE correct answer
3. Include a brief explanation for the correct answer
4. Make distractors plausible but clearly incorrect

Return ONLY a valid JSON array in this exact format (no markdown, no extra text):
[
  {{
    "question": "Question text here?",
    "options": {{
      "A": "First option",
      "B": "Second option",
      "C": "Third option",
      "D": "Fourth option"
    }},
    "correct_answer": "A",
    "explanation": "Explanation of why this is correct",
    "difficulty": "{difficulty}"
  }}
]
"""
    else:  # Short Answer
        prompt = f"""
Based on the following content, generate exactly {num_questions} short answer questions 
at the "{difficulty}" level of Bloom's Taxonomy.

Content: {content_chunk}

Requirements:
1. Questions should require 2-4 sentence answers
2. Test deeper understanding at {difficulty} level
3. Provide model answers for comparison

Return ONLY a valid JSON array in this exact format:
[
  {{
    "question": "Question text here?",
    "model_answer": "Expected answer here",
    "key_points": ["point1", "point2", "point3"],
    "difficulty": "{difficulty}"
  }}
]
"""
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 2048,
                }
            )
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            questions = json.loads(text)
            
            if not isinstance(questions, list):
                raise ValueError("Invalid response format")
                
            return questions
            
        except Exception as e:
            error_msg = str(e)
            
            if "429" in error_msg or "quota exceeded" in error_msg.lower():
                if attempt < max_retries - 1:
                    wait_time = 25
                    st.warning(f"⏳ Rate limit hit. Switching to demo mode...")
                    time.sleep(2)
                    return generate_demo_questions(content, num_questions, difficulty, question_type)
                else:
                    st.warning("⚠️ API limit reached. Using demo mode for this session.")
                    return generate_demo_questions(content, num_questions, difficulty, question_type)
            else:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    st.warning(f"⚠️ API error. Using demo mode. Error: {str(e)[:100]}")
                    return generate_demo_questions(content, num_questions, difficulty, question_type)
    
    return generate_demo_questions(content, num_questions, difficulty, question_type)

def generate_questions(content, num_questions=5, difficulty="Apply", question_type="MCQ"):
    """Main function to generate questions"""
    if API_AVAILABLE:
        return generate_questions_api(content, num_questions, difficulty, question_type)
    else:
        st.info("ℹ️ Running in demo mode (API key not configured)")
        return generate_demo_questions(content, num_questions, difficulty, question_type)

def evaluate_mcq_answer(question, student_answer):
    """Evaluate MCQ answer"""
    correct = student_answer == question['correct_answer']
    return {
        'correct': correct,
        'score': 10 if correct else 0,
        'feedback': question['explanation'] if not correct else "Correct! " + question['explanation']
    }

def evaluate_short_answer(question, student_answer):
    """Evaluate short answer - demo version"""
    
    if not student_answer or len(student_answer.strip()) < 10:
        return {
            'score': 0,
            'matched_points': [],
            'missing_points': question['key_points'],
            'feedback': "Answer is too short or empty. Please provide a more detailed response."
        }
    
    # Simple keyword matching for demo
    answer_lower = student_answer.lower()
    matched = []
    missing = []
    
    for point in question['key_points']:
        # Check if key words from the point are in the answer
        key_words = [w.lower() for w in point.split() if len(w) > 4]
        if any(word in answer_lower for word in key_words):
            matched.append(point)
        else:
            missing.append(point)
    
    # Score based on matched points
    score = int((len(matched) / len(question['key_points'])) * 10)
    
    # Add bonus points for length
    if len(student_answer.split()) > 30:
        score = min(10, score + 2)
    
    feedback = f"Your answer covers {len(matched)} out of {len(question['key_points'])} key points. "
    if score >= 7:
        feedback += "Good understanding demonstrated!"
    elif score >= 4:
        feedback += "Partial understanding shown. Review the missing points."
    else:
        feedback += "Please review the model answer and try to include more key concepts."
    
    return {
        'score': score,
        'matched_points': matched if matched else ["Partial credit for attempt"],
        'missing_points': missing,
        'feedback': feedback
    }

# Streamlit UI
st.set_page_config(page_title="AI Question Generator", layout="wide", page_icon="📚")

st.title("📚 Automated Question Generation & Assessment System")
st.markdown("*Using Large Language Models for Curriculum-Based Education*")

# Sidebar for role selection
with st.sidebar:
    st.header("🎯 Select Role")
    role = st.radio("I am a:", ["Teacher/Educator", "Student"])
    
    st.divider()
    
    # Mode indicator
    if API_AVAILABLE:
        st.success("✅ API Connected")
    else:
        st.info("📝 Demo Mode Active")
    
    st.divider()
    st.markdown("### 📊 System Stats")
    st.metric("Questions Generated", len(st.session_state.questions))
    st.metric("Quizzes Taken", len(st.session_state.student_history))

# Teacher Interface
if role == "Teacher/Educator":
    st.header("👨‍🏫 Educator Panel")
    
    tab1, tab2 = st.tabs(["📚 Generate Questions", "📊 Analytics"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Content Input")
            input_method = st.radio("Choose input method:", 
                                   ["Text Input", "Upload File (PDF/DOCX)"])
            
            content = ""
            if input_method == "Text Input":
                content = st.text_area("Paste your content here:", 
                                      height=200,
                                      value=st.session_state.extracted_content,
                                      placeholder="Enter textbook chapter, lecture notes, or any educational content...")
            else:
                uploaded_file = st.file_uploader("Upload PDF or DOCX (First 5 pages, max 3000 chars)", 
                                                type=['pdf', 'docx'])
                if uploaded_file:
                    with st.spinner("Extracting text from file..."):
                        if uploaded_file.name.endswith('.pdf'):
                            content = extract_text_from_pdf(uploaded_file)
                        else:
                            content = extract_text_from_docx(uploaded_file)
                    
                    if content:
                        st.session_state.extracted_content = content
                        with st.expander("📄 Preview Extracted Text"):
                            st.text(content[:1000] + "..." if len(content) > 1000 else content)
                        
                        st.success(f"✅ Extracted {len(content)} characters from file")
                    else:
                        st.error("❌ Failed to extract text. Please try a different file.")
        
        with col2:
            st.subheader("Configuration")
            question_type = st.selectbox("Question Type:", 
                                        ["MCQ", "Short Answer"])
            
            num_questions = st.slider("Number of Questions:", 
                                     min_value=1, max_value=10, value=3)
            
            difficulty = st.selectbox("Bloom's Taxonomy Level:", 
                                     ["Remember", "Understand", "Apply", 
                                      "Analyze", "Evaluate", "Create"])
            
            st.info(f"**{difficulty}** Level:\n" + 
                   {"Remember": "Recall facts",
                    "Understand": "Explain concepts",
                    "Apply": "Use in new situations",
                    "Analyze": "Break down & examine",
                    "Evaluate": "Make judgments",
                    "Create": "Generate new ideas"}[difficulty])
        
        if st.button("🎯 Generate Questions", type="primary", use_container_width=True):
            if content:
                if len(content) < 50:
                    st.warning("⚠️ Content is too short. Please provide at least 50 characters.")
                else:
                    # Check rate limit
                    time_since_last = time.time() - st.session_state.last_request_time
                    
                    if time_since_last < 3:
                        st.warning(f"⏳ Please wait {3 - int(time_since_last)} seconds before generating again.")
                    else:
                        with st.spinner("🤖 Generating questions using AI... Please wait..."):
                            try:
                                st.session_state.last_request_time = time.time()
                                questions = generate_questions(content, num_questions, 
                                                              difficulty, question_type)
                                
                                if questions and len(questions) > 0:
                                    st.session_state.questions = questions
                                    st.session_state.question_type = question_type
                                    st.session_state.student_answers = {}  # Reset answers
                                    st.session_state.results = None  # Reset results
                                    st.success(f"✅ Successfully generated {len(questions)} questions!")
                                    st.balloons()
                                else:
                                    st.error("❌ Failed to generate questions. Please try again.")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                                st.info("💡 Try reducing the number of questions or using shorter content.")
            else:
                st.warning("⚠️ Please provide content first!")
        
        # Display generated questions
        if st.session_state.questions:
            st.divider()
            st.subheader("📋 Generated Questions Preview")
            
            for idx, q in enumerate(st.session_state.questions, 1):
                with st.expander(f"Question {idx}: {q['question'][:60]}...", expanded=(idx==1)):
                    st.markdown(f"**Q{idx}:** {q['question']}")
                    
                    if 'options' in q:  # MCQ
                        for key, value in q['options'].items():
                            prefix = "✅ " if key == q['correct_answer'] else "   "
                            st.markdown(f"{prefix}**{key})** {value}")
                        st.info(f"**Explanation:** {q['explanation']}")
                    else:  # Short Answer
                        st.markdown(f"**Model Answer:** {q['model_answer']}")
                        st.markdown(f"**Key Points:**")
                        for point in q['key_points']:
                            st.markdown(f"  • {point}")
    
    with tab2:
        st.subheader("📈 Student Performance Analytics")
        
        if st.session_state.student_history:
            total_attempts = len(st.session_state.student_history)
            avg_score = sum(h['score'] for h in st.session_state.student_history) / total_attempts
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Attempts", total_attempts)
            col2.metric("Average Score", f"{avg_score:.1f}%")
            col3.metric("Last Score", f"{st.session_state.student_history[-1]['score']:.1f}%")
            
            st.divider()
            st.markdown("### Recent Attempts")
            for idx, history in enumerate(reversed(st.session_state.student_history[-10:]), 1):
                with st.expander(f"Attempt {total_attempts - idx + 1} - Score: {history['score']:.1f}%"):
                    st.write(f"**Date:** {history['timestamp']}")
                    st.write(f"**Questions:** {history['num_questions']}")
                    st.write(f"**Score:** {history['score']:.1f}%")
        else:
            st.info("📊 No student attempts yet. Students need to take quizzes first!")
            st.markdown("""
            **How it works:**
            1. Generate questions in the 'Generate Questions' tab
            2. Switch to 'Student' role in the sidebar
            3. Students take the quiz
            4. View analytics here after submission
            """)

# Student Interface
else:
    st.header("🎓 Student Panel")
    
    if not st.session_state.questions:
        st.warning("⚠️ No quiz available yet. Ask your teacher to generate questions!")
        st.info("💡 **For Demo:** Switch to 'Teacher/Educator' role in the sidebar to create a quiz first.")
    else:
        tab1, tab2 = st.tabs(["📝 Take Quiz", "📊 My Results"])
        
        with tab1:
            st.subheader(f"📖 Quiz: {len(st.session_state.questions)} Questions")
            st.markdown(f"**Type:** {st.session_state.question_type} | **Total Points:** {len(st.session_state.questions) * 10}")
            
            st.divider()
            
            question_type = st.session_state.get('question_type', 'MCQ')
            
            # Display questions
            for idx, question in enumerate(st.session_state.questions, 1):
                st.markdown(f"### Question {idx}")
                st.markdown(f"**{question['question']}**")
                st.caption(f"Difficulty: {question.get('difficulty', 'N/A')} | Points: 10")
                
                if question_type == "MCQ":
                    # Get current answer if exists
                    current_answer = st.session_state.student_answers.get(idx, None)
                    
                    answer = st.radio(
                        "Select your answer:",
                        options=list(question['options'].keys()),
                        format_func=lambda x: f"{x}) {question['options'][x]}",
                        key=f"q_{idx}",
                        index=list(question['options'].keys()).index(current_answer) if current_answer else 0
                    )
                    st.session_state.student_answers[idx] = answer
                else:
                    # Get current answer if exists
                    current_answer = st.session_state.student_answers.get(idx, "")
                    
                    answer = st.text_area(
                        "Your answer:",
                        key=f"q_{idx}",
                        value=current_answer,
                        height=120,
                        placeholder="Write your answer here (2-4 sentences recommended)..."
                    )
                    st.session_state.student_answers[idx] = answer
                
                st.divider()
            
            # Check if all questions are answered
            all_answered = len(st.session_state.student_answers) == len(st.session_state.questions)
            if not all_answered:
                st.info(f"📝 Please answer all questions before submitting. ({len(st.session_state.student_answers)}/{len(st.session_state.questions)} answered)")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("✅ Submit Quiz", type="primary", use_container_width=True, disabled=not all_answered):
                    # Evaluate all answers
                    results = []
                    total_score = 0
                    
                    with st.spinner("📊 Evaluating your answers..."):
                        for idx, question in enumerate(st.session_state.questions, 1):
                            student_answer = st.session_state.student_answers.get(idx, "")
                            
                            if question_type == "MCQ":
                                evaluation = evaluate_mcq_answer(question, student_answer)
                            else:
                                evaluation = evaluate_short_answer(question, student_answer)
                            
                            results.append({
                                'question_num': idx,
                                'question': question['question'],
                                'student_answer': student_answer,
                                'evaluation': evaluation
                            })
                            total_score += evaluation['score']
                    
                    # Calculate percentage
                    max_score = len(st.session_state.questions) * 10
                    percentage = (total_score / max_score) * 100
                    
                    st.session_state.results = {
                        'results': results,
                        'total_score': total_score,
                        'max_score': max_score,
                        'percentage': percentage
                    }
                    
                    # Save to history
                    st.session_state.student_history.append({
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'score': percentage,
                        'num_questions': len(st.session_state.questions)
                    })
                    
                    st.success("✅ Quiz submitted successfully!")
                    time.sleep(1)
                    st.rerun()
        
        with tab2:
            if st.session_state.results:
                results_data = st.session_state.results
                
                # Score display
                st.markdown("## 🎯 Your Results")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Score", 
                          f"{results_data['total_score']}/{results_data['max_score']}")
                col2.metric("Percentage", f"{results_data['percentage']:.1f}%")
                
                # Grade
                grade = "A+" if results_data['percentage'] >= 90 else \
                       "A" if results_data['percentage'] >= 80 else \
                       "B" if results_data['percentage'] >= 70 else \
                       "C" if results_data['percentage'] >= 60 else \
                       "D" if results_data['percentage'] >= 50 else "F"
                col3.metric("Grade", grade)
                
                # Performance indicator
                if results_data['percentage'] >= 80:
                    st.success("🎉 Excellent work! You have a strong understanding of the material.")
                elif results_data['percentage'] >= 60:
                    st.info("👍 Good effort! Review the feedback below to improve further.")
                else:
                    st.warning("📚 Keep practicing! Check the explanations carefully and try again.")
                
                st.divider()
                
                # Detailed feedback
                st.subheader("📋 Detailed Feedback")
                
                for result in results_data['results']:
                    eval_data = result['evaluation']
                    is_correct = eval_data.get('correct', eval_data['score'] >= 7)
                    
                    with st.expander(
                        f"{'✅' if is_correct else '❌'} Question {result['question_num']} - "
                        f"Score: {eval_data['score']}/10",
                        expanded=(eval_data['score'] < 7)
                    ):
                        st.markdown(f"**Question:** {result['question']}")
                        st.markdown(f"**Your Answer:** {result['student_answer']}")
                        
                        if 'matched_points' in eval_data:
                            if eval_data['matched_points']:
                                st.markdown("**✅ Points Covered:**")
                                for point in eval_data['matched_points']:
                                    st.markdown(f"  • {point}")
                            
                            if eval_data['missing_points']:
                                st.markdown("**❌ Points Missed:**")
                                for point in eval_data['missing_points']:
                                    st.markdown(f"  • {point}")
                        
                        st.info(f"**💡 Feedback:** {eval_data['feedback']}")
                
                st.divider()
                
                # Options
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Take Another Quiz", use_container_width=True):
                        st.session_state.results = None
                        st.session_state.student_answers = {}
                        st.rerun()
                
                with col2:
                    if st.button("📊 View All Attempts", use_container_width=True):
                        st.info(f"Total quizzes taken: {len(st.session_state.student_history)}")
                        for idx, h in enumerate(st.session_state.student_history, 1):
                            st.write(f"{idx}. {h['timestamp']} - Score: {h['score']:.1f}%")
            else:
                st.info("📝 Complete the quiz in the 'Take Quiz' tab to see your results here!")
                st.markdown("""
                **Instructions:**
                1. Answer all questions in the quiz
                2. Click 'Submit Quiz' button
                3. View detailed results and feedback here
                """)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>🤖 Powered by Google Gemini AI | 📚 Bloom's Taxonomy Aligned</p>
    <p>Built for Curriculum-Based Automated Assessment</p>
</div>
""", unsafe_allow_html=True)