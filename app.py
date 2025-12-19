import streamlit as st
import time 
from datetime import datetime

from config import API_avai, REQUEST_COOLDOWN, MIN_CONTENT_LENGTH
from extract import extract_pdf, extract_docx
from question_generator import generate_ques
from evaluate import eval_mcq, eval_shortans

def init_session_state():
    defaults = {
        'ques': [],
        'ans': {},
        'results': None,
        'student_history': [],
        'last_request_time': 0,
        'ques_type': 'MCQ',
        'extracted_content': ""
    }
    for key,value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

def can_make_request():
    #checks time elapsed
    elapsed = time.time() - st.session_state.last_request_time
    if elapsed < REQUEST_COOLDOWN:
        st.warning(f"Wait {REQUEST_COOLDOWN - elapsed:.1f}s between requests")
        return False
    st.session_state.last_request_time = time.time()
    return True


st.set_page_config(page_title="BloomSetu", layout="wide", page_icon="📚")

st.title("BloomSetu")
st.markdown("*Automated assessment using LLMs for educators*")

with st.sidebar:
    st.header("Select Role")
    role = st.radio("I am a:", ["Teacher", "Student"])
    
    st.divider()
    st.success("Connected" if API_avai else "Demo Mode")
    
    st.divider()
    st.markdown("### Stats")
    st.metric("Questions Generated", len(st.session_state.ques))
    st.metric("Quizzes Taken", len(st.session_state.student_history))

# teacher's interface
if role == "Teacher":
    st.header("Teacher Panel")
    
    tab1, tab2 = st.tabs(["Generate Questions", "Analytics"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Input content")
            input_method = st.radio("Input method:", ["Text", "File Upload"])
            
            content = ""
            if input_method == "Text":
                content = st.text_area(
                    "Paste content:", 
                    height=200,
                    value=st.session_state.extracted_content,
                    placeholder="Enter educational content..."
                )
            else:
                file = st.file_uploader("Upload PDF or DOCX", type=['pdf', 'docx'])
                if file:
                    with st.spinner("Extracting text..."):
                        if file.name.endswith('.pdf'):
                            content = extract_pdf(file)
                        else:
                            content = extract_docx(file)
                    
                    if content:
                        st.session_state.extracted_content = content
                        with st.expander("Preview"):
                            st.text(content[:1000] + ("..." if len(content) > 1000 else ""))
                        st.success(f"Extracted {len(content)} characters")
        
        with col2:
            st.subheader("Settings")
            ques_type = st.selectbox("Type:", ["MCQ", "Short Answer"])
            num = st.slider("Questions:", 1, 10, 3)
            difficulty = st.selectbox(
                "Bloom's Level:", 
                ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
            )
            
            difficulty_desc = {
                "Remember": "Recall facts",
                "Understand": "Explain concepts",
                "Apply": "Use in new situations",
                "Analyze": "Break down & examine",
                "Evaluate": "Make judgments",
                "Create": "Generate new ideas"
            }
            st.info(f"**{difficulty}**: {difficulty_desc[difficulty]}")
        
        if st.button("Generate Questions", type="primary", use_container_width=True):
            if not content:
                st.warning("Please provide content!")
            elif len(content) < MIN_CONTENT_LENGTH:
                st.warning(f"Content too short (min {MIN_CONTENT_LENGTH} chars)")
            elif not can_make_request():
                st.stop()
            else:
                with st.spinner("Generating questions..."):
                    questions = generate_ques(content, num, difficulty, ques_type)
                    
                    if questions:
                        st.session_state.ques = questions
                        st.session_state.ques_type = ques_type
                        st.session_state.ans = {}
                        st.session_state.results = None
                        st.success(f"Generated {len(questions)} questions!")
                        st.balloons()
        
    
        if st.session_state.ques:
            st.divider()
            st.subheader("Generated Questions")
            
            for idx, q in enumerate(st.session_state.ques, 1):
                with st.expander(f"Q{idx}: {q['question'][:60]}...", expanded=(idx==1)):
                    st.markdown(f"**{q['question']}**")
                    
                    if 'options' in q:
                        for key, val in q['options'].items():
                            mark = "✅" if key == q['correct_answer'] else "  "
                            st.markdown(f"{mark} **{key})** {val}")
                        st.info(f"**Explanation:** {q['explanation']}")
                    else:
                        st.markdown(f"**Model Answer:** {q['model_answer']}")
                        st.markdown("**Key Points:**")
                        for point in q['key_points']:
                            st.markdown(f"• {point}")
    
    with tab2:
        st.subheader("Performance Analytics")
        
        if st.session_state.student_history:
            history = st.session_state.student_history
            avg_score = sum(h['score'] for h in history) / len(history)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Attempts", len(history))
            col2.metric("Average Score", f"{avg_score:.1f}%")
            col3.metric("Last Score", f"{history[-1]['score']:.1f}%")
            
            st.divider()
            st.markdown("### Recent Attempts")
            for idx, h in enumerate(reversed(history[-10:]), 1):
                with st.expander(f"Attempt {len(history)-idx+1} - {h['score']:.1f}%"):
                    st.write(f"**Date:** {h['timestamp']}")
                    st.write(f"**Questions:** {h['num']}")
                    st.write(f"**Score:** {h['score']:.1f}%")
        else:
            st.info("No attempts yet. Students need to take quizzes first!")


else:
    st.header("🎓 Student Panel")
    
    if not st.session_state.ques:
        st.warning("No quiz available. Ask your teacher to generate questions!")
        st.info("Switch to 'Teacher' role to create a quiz")
    else:
        tab1, tab2 = st.tabs(["Take Quiz", "Results"])
        
        with tab1:
            st.subheader(f"📖 Quiz: {len(st.session_state.ques)} Questions")
            st.markdown(f"**Type:** {st.session_state.ques_type} | **Points:** {len(st.session_state.ques) * 10}")
            st.divider()
            
            # Display questions
            for idx, q in enumerate(st.session_state.ques, 1):
                st.markdown(f"### Question {idx}")
                st.markdown(f"**{q['question']}**")
                st.caption(f"Difficulty: {q.get('difficulty', 'N/A')} | Points: 10")
                
                if st.session_state.ques_type == "MCQ":
                    current = st.session_state.ans.get(idx)
                    answer = st.radio(
                        "Select answer:",
                        options=list(q['options'].keys()),
                        format_func=lambda x: f"{x}) {q['options'][x]}",
                        key=f"q_{idx}",
                        index=list(q['options'].keys()).index(current) if current else 0
                    )
                else:
                    current = st.session_state.ans.get(idx, "")
                    answer = st.text_area(
                        "Your answer:",
                        key=f"q_{idx}",
                        value=current,
                        height=120,
                        placeholder="Write your answer (2-4 sentences)..."
                    )
                
                st.session_state.ans[idx] = answer
                st.divider()
            
            # Submit button
            all_answered = len(st.session_state.ans) == len(st.session_state.ques)
            if not all_answered:
                st.info(f" Answer all questions ({len(st.session_state.ans)}/{len(st.session_state.ques)})")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("✅ Submit Quiz", type="primary", use_container_width=True, disabled=not all_answered):
                    results = []
                    total_score = 0
                    
                    with st.spinner(" Evaluating..."):
                        for idx, q in enumerate(st.session_state.ques, 1):
                            answer = st.session_state.ans.get(idx, "")
                            
                            if st.session_state.ques_type == "MCQ":
                                eval_result = eval_mcq(q, answer)
                            else:
                                eval_result = eval_shortans(q, answer)
                            
                            results.append({
                                'num': idx,
                                'ques': q['question'],
                                'ans': answer,
                                'evaluation': eval_result
                            })
                            total_score += eval_result['score']
                    
                    max_score = len(st.session_state.ques) * 10
                    percentage = (total_score / max_score) * 100
                    
                    st.session_state.results = {
                        'results': results,
                        'total_score': total_score,
                        'max_score': max_score,
                        'percentage': percentage
                    }
                    
                    st.session_state.student_history.append({
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'score': percentage,
                        'num': len(st.session_state.ques)
                    })
                    
                    st.success("✅ Quiz submitted!")
                    time.sleep(1)
                    st.rerun()
        
        with tab2:
            if st.session_state.results:
                data = st.session_state.results
                
                st.markdown("## Your Results")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Score", f"{data['total_score']}/{data['max_score']}")
                col2.metric("Percentage", f"{data['percentage']:.1f}%")
                
                grade = ("A+" if data['percentage'] >= 90 else
                        "A" if data['percentage'] >= 80 else
                        "B" if data['percentage'] >= 70 else
                        "C" if data['percentage'] >= 60 else
                        "D" if data['percentage'] >= 50 else "F")
                col3.metric("Grade", grade)
                
                if data['percentage'] >= 80:
                    st.success("🎉 Excellent work!")
                elif data['percentage'] >= 60:
                    st.info("👍 Good effort! Review feedback below.")
                else:
                    st.warning(" Keep practicing!")
                
                st.divider()
                st.subheader(" Detailed Feedback")
                
                for result in data['results']:
                    eval_data = result['evaluation']
                    is_correct = eval_data.get('correct', eval_data['score'] >= 7)
                    
                    with st.expander(
                        f"{'✅' if is_correct else '❌'} Q{result['num']} - {eval_data['score']}/10",
                        expanded=(eval_data['score'] < 7)
                    ):
                        st.markdown(f"**Question:** {result['ques']}")
                        st.markdown(f"**Your Answer:** {result['ans']}")
                        
                        if 'matched_points' in eval_data:
                            if eval_data['matched_points']:
                                st.markdown("**Points Covered:**")
                                for p in eval_data['matched_points']:
                                    st.markdown(f"• {p}")
                            
                            if eval_data['missing_points']:
                                st.markdown("** Points Missed:**")
                                for p in eval_data['missing_points']:
                                    st.markdown(f"• {p}")
                        
                        st.info(f"** Feedback:** {eval_data['feedback']}")
                
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Take Another Quiz", use_container_width=True):
                        st.session_state.results = None
                        st.session_state.ans = {}
                        st.rerun()
            else:
                st.info("Complete the quiz to see results!")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p> Bloom's Taxonomy and Indian Curicullum Aligned</p>
</div>
""", unsafe_allow_html=True)