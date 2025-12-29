import streamlit as st
import time
from datetime import datetime

from config import API_avai, REQUEST_COOLDOWN, MIN_CONTENT_LENGTH, DAILY_LIMIT , MAX_CACHE_AGE_HOURS
from extract import extract_pdf, extract_docx
from question_generator import generate_questions
from evaluate import evaluate_answer, calculate_total_score
from curriculum import BOARDS, CLASSES, ALL_SUBJECTS, QUESTION_TYPES, get_chapters, get_keywords_for_bloom

def init_session_state():
    defaults = {
        'questions': [],
        'student_answers': {},
        'results': None,
        'history': [],
        'last_request_time': 0,
        'extracted_content': "",
        'board': 'CBSE',
        'class_level': 10,
        'subject': 'Physics',
        'chapter': '',
        'question_type': 'MCQ',
        'bloom_level': 'Apply'
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def init_quota_tracking():
    if 'quota_data' not in st.session_state:
        st.session_state.quota_data = {
            'count': 0,
            'date': datetime.now().date()
        }
    
    today = datetime.now().date()
    if st.session_state.quota_data['date'] != today:
        st.session_state.quota_data['count'] = 0
        st.session_state.quota_data['date'] = today

def check_quota():
    if not API_avai:
        return True
    return st.session_state.quota_data['count'] < DAILY_LIMIT

def increment_quota():
    st.session_state.quota_data['count'] += 1

init_session_state()
init_session_state()
init_quota_tracking()

def can_make_request():
    elapsed = time.time() - st.session_state.last_request_time
    if elapsed < REQUEST_COOLDOWN:
        st.warning(f"Please wait {REQUEST_COOLDOWN - elapsed:.1f}s")
        return False
    st.session_state.last_request_time = time.time()
    return True

st.set_page_config(
    page_title="BloomSetu - Indian Curriculum",
    layout="wide",
    page_icon="IN"
)

st.title("BloomSetu")
st.markdown("### AI-Powered Assessment for Indian Schools and Coaching Centers")
st.caption("Aligned with CBSE, ICSE and State Boards | NCERT Pattern | Bloom's Taxonomy")

with st.sidebar:
    st.header("Select Role")
    role = st.radio("I am a:", ["Teacher", "Student"], label_visibility="collapsed")

    st.divider()

    st.markdown("### Curriculum Settings")
    board = st.selectbox("Board", BOARDS, index=BOARDS.index(st.session_state.board))
    st.session_state.board = board

    class_level = st.selectbox(
        "Class",
        CLASSES,
        index=CLASSES.index(st.session_state.class_level)
        if st.session_state.class_level in CLASSES else 4
    )
    st.session_state.class_level = class_level

    subject = st.selectbox(
        "Subject",
        ALL_SUBJECTS,
        index=ALL_SUBJECTS.index(st.session_state.subject)
        if st.session_state.subject in ALL_SUBJECTS else 0
    )
    st.session_state.subject = subject

    chapters = get_chapters(subject, class_level)
    if chapters:
        chapter_options = ["All Chapters"] + chapters
        chapter = st.selectbox("Chapter", chapter_options)
        st.session_state.chapter = "" if chapter == "All Chapters" else chapter
    else:
        chapter = st.text_input("Chapter or Topic", value=st.session_state.chapter)
        st.session_state.chapter = chapter

    st.divider()
    st.success("API Connected" if API_avai else "Demo Mode")

    st.divider()
    st.markdown("### Statistics")
    st.metric("Questions Generated", len(st.session_state.questions))
    st.metric("Assessments Taken", len(st.session_state.history))
    
    # Add this block
    if API_avai:
        remaining = DAILY_LIMIT - st.session_state.quota_data['count']
        st.metric("API Calls Today", f"{remaining}/{DAILY_LIMIT}")

    if st.session_state.history:
        avg_score = sum(h['percentage'] for h in st.session_state.history) / len(st.session_state.history)
        st.metric("Average Score", f"{avg_score:.1f}%")

if role == "Teacher":
    st.header("Teacher Dashboard")
    tab1, tab2 = st.tabs(["Create Assessment", "Analytics"])

    with tab1:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Input Study Material")
            input_method = st.radio(
                "Choose input method:",
                ["Text", "File Upload"],
                horizontal=True
            )

            content = ""
            if input_method == "Text":
                content = st.text_area(
                    "Paste study material:",
                    height=250,
                    value=st.session_state.extracted_content,
                    placeholder="Enter educational content..."
                )
            else:
                uploaded_file = st.file_uploader("Upload PDF or DOCX file", type=['pdf', 'docx'])
                if uploaded_file:
                    with st.spinner("Extracting text..."):
                        content = extract_pdf(uploaded_file) if uploaded_file.name.endswith('.pdf') else extract_docx(uploaded_file)
                    if content:
                        st.session_state.extracted_content = content
                        with st.expander("Preview"):
                            st.text(content[:1500] + ("..." if len(content) > 1500 else ""))
                        st.success(f"Extracted {len(content)} characters")

        with col2:
            st.subheader("Question Settings")
            q_type = st.selectbox(
                "Question Type",
                list(QUESTION_TYPES.keys()),
                format_func=lambda x: f"{QUESTION_TYPES[x]['name']} ({QUESTION_TYPES[x]['marks']} marks)"
            )
            st.session_state.question_type = q_type

            type_info = QUESTION_TYPES[q_type]
            st.info(type_info['description'])

            if 'word_limit' in type_info:
                st.caption(f"Word Limit: {type_info['word_limit']}")

            num_questions = st.slider("Number of Questions", 1, 10, 3)

            bloom_level = st.selectbox(
                "Bloom's Taxonomy Level",
                ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
            )
            st.session_state.bloom_level = bloom_level

            keywords = get_keywords_for_bloom(bloom_level)
            st.caption(f"Keywords: {', '.join(keywords[:3])}")

        st.divider()

        col_left, col_center, col_right = st.columns([1, 2, 1])
        with col_center:
            if st.button("Generate Assessment", type="primary", use_container_width=True):
                if not content:
                    st.error("Please provide study material")
                elif len(content) < MIN_CONTENT_LENGTH:
                    st.error(f"Content too short (minimum {MIN_CONTENT_LENGTH} characters)")
                elif not can_make_request():
                    st.stop()
                elif API_avai and not check_quota():  # Add this check
                    st.error(f"Daily limit reached ({DAILY_LIMIT} assessments). Resets at midnight. Using demo mode.")
                else:
                    curriculum_info = {
                        'board': st.session_state.board,
                        'class': st.session_state.class_level,
                        'subject': st.session_state.subject,
                        'chapter': st.session_state.chapter,
                        'num_questions': num_questions,
                        'question_type': q_type,
                        'bloom_level': bloom_level
                    }

                    with st.spinner("Generating questions..."):
                        was_using_api = API_avai and check_quota()
                        questions = generate_questions(content, curriculum_info)
                        if questions and was_using_api:
                            increment_quota()

                    if questions:
                        st.session_state.questions = questions
                        st.session_state.student_answers = {}
                        st.session_state.results = None
                        st.success(f"Generated {len(questions)} questions")

        if st.session_state.questions:
            st.divider()
            st.subheader("Generated Assessment")

            q = st.session_state.questions[0]
            st.info(
                f"{q['board']} | Class {q['class']} | {q['subject']} "
                f"{'| ' + q['chapter'] if q['chapter'] else ''}"
            )

            total_marks = sum(q.get('marks', 1) for q in st.session_state.questions)
            st.caption(f"Total Marks: {total_marks}")

            for idx, question in enumerate(st.session_state.questions, 1):
                marks = question.get('marks', 1)
                with st.expander(
                    f"Q{idx} ({marks} marks): {question['question'][:70]}...",
                    expanded=(idx == 1)
                ):
                    st.markdown(question['question'])

                    if 'options' in question:
                        for key, value in question['options'].items():
                            st.markdown(f"{key}) {value}")
                        st.success(f"Correct Answer: {question['correct_answer']}")
                        st.info(f"Explanation: {question['explanation']}")
                    else:
                        st.markdown("Model Answer")
                        st.write(question['model_answer'])

                        st.markdown("Key Points")
                        for point in question['key_points']:
                            st.markdown(f"- {point}")

                        if 'marking_scheme' in question:
                            st.markdown("Marking Scheme")
                            for scheme in question['marking_scheme']:
                                st.markdown(f"- {scheme}")

    with tab2:
        st.subheader("Student Performance Analytics")
        if st.session_state.history:
            history = st.session_state.history
            col1, col2, col3 = st.columns(3)

            avg_score = sum(h['percentage'] for h in history) / len(history)
            col1.metric("Total Assessments", len(history))
            col2.metric("Average Score", f"{avg_score:.1f}%")
            col3.metric("Latest Score", f"{history[-1]['percentage']:.1f}%")

            st.divider()
            st.markdown("Recent Assessment History")

            for idx, attempt in enumerate(reversed(history[-10:]), 1):
                with st.expander(
                    f"Assessment {len(history) - idx + 1} - {attempt['percentage']:.1f}%"
                ):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"Date: {attempt['timestamp']}")
                        st.write(f"Questions: {attempt['num_questions']}")
                    with col_b:
                        st.write(f"Score: {attempt['total_score']:.1f}/{attempt['max_score']}")
                        st.write(f"Percentage: {attempt['percentage']:.1f}%")
        else:
            st.info("No data available yet")

else:
    st.header("Student Dashboard")

    if not st.session_state.questions:
        st.warning("No assessment available")
        st.info("Ask your teacher to generate an assessment first")
        st.markdown("---")
        st.markdown("### How it works:")
        st.markdown("1. Teacher generates questions from study material")
        st.markdown("2. You attempt the assessment")
        st.markdown("3. Get instant evaluation with detailed feedback")

    else:
        tab1, tab2 = st.tabs(["Take Assessment", "View Results"])

        with tab1:
            q = st.session_state.questions[0]
            total_marks = sum(q.get('marks', 1) for q in st.session_state.questions)

            st.markdown(f"### Assessment: {len(st.session_state.questions)} Questions")
            st.info(
                f"{q['board']} | Class {q['class']} | {q['subject']} "
                f"{'| ' + q['chapter'] if q['chapter'] else ''} | Total: {total_marks} marks"
            )
            st.divider()

            for idx, question in enumerate(st.session_state.questions, 1):
                marks = question.get('marks', 1)
                st.markdown(f"### Question {idx} [{marks} marks]")
                st.markdown(f"**{question['question']}**")

                if 'options' in question:
                    current = st.session_state.student_answers.get(idx)
                    option_keys = list(question['options'].keys())
                    answer = st.radio(
                        "Select your answer:",
                        options=option_keys,
                        format_func=lambda x: f"{x}) {question['options'][x]}",
                        key=f"q_{idx}",
                        index=option_keys.index(current) if current in option_keys else 0
                    )
                    st.session_state.student_answers[idx] = answer
                else:
                    word_limit = question.get('word_limit', 'As required')
                    st.caption(f"Word Limit: {word_limit}")
                    current = st.session_state.student_answers.get(idx, "")
                    answer = st.text_area(
                        "Write your answer:",
                        value=current,
                        height=180,
                        key=f"q_{idx}",
                        placeholder=f"Write your answer here ({word_limit})"
                    )
                    st.session_state.student_answers[idx] = answer
                    if answer:
                        st.caption(f"Word count: {len(answer.split())}")

                st.divider()

            answered = len(st.session_state.student_answers)
            total_q = len(st.session_state.questions)

            if answered < total_q:
                st.warning(f"Please answer all questions ({answered}/{total_q})")

            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button(
                    "Submit Assessment",
                    type="primary",
                    use_container_width=True,
                    disabled=(answered < total_q)
                ):
                    results = []
                    with st.spinner("Evaluating your answers..."):
                        for idx, question in enumerate(st.session_state.questions, 1):
                            student_answer = st.session_state.student_answers.get(idx, "")
                            evaluation = evaluate_answer(question, student_answer)
                            results.append({
                                'question_num': idx,
                                'question': question['question'],
                                'student_answer': student_answer,
                                'evaluation': evaluation
                            })

                    score_summary = calculate_total_score(results)
                    st.session_state.results = {
                        'results': results,
                        **score_summary
                    }
                    st.session_state.history.append({
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'total_score': score_summary['total_score'],
                        'max_score': score_summary['max_score'],
                        'percentage': score_summary['percentage'],
                        'num_questions': len(st.session_state.questions)
                    })
                    st.success("Assessment submitted")
                    time.sleep(1)
                    st.rerun()

        with tab2:
            if st.session_state.results:
                results = st.session_state.results
                st.markdown("## Your Assessment Results")

                col1, col2, col3 = st.columns(3)
                col1.metric(
                    "Total Score",
                    f"{results['total_score']:.1f} / {results['max_score']}"
                )
                col2.metric(
                    "Percentage",
                    f"{results['percentage']:.1f}%"
                )

                perc = results['percentage']
                if perc >= 90:
                    grade = "A+"
                elif perc >= 80:
                    grade = "A"
                elif perc >= 70:
                    grade = "B+"
                elif perc >= 60:
                    grade = "B"
                elif perc >= 50:
                    grade = "C"
                else:
                    grade = "D"

                col3.metric("Grade", grade)

                if perc >= 80:
                    st.success("Excellent performance")
                elif perc >= 60:
                    st.info("Good work. Review feedback to improve")
                else:
                    st.warning("Keep practicing and revise concepts")

                st.divider()
                st.subheader("Detailed Question-wise Feedback")

                for result in results['results']:
                    eval_data = result['evaluation']
                    score = eval_data['score']
                    max_score = eval_data['max_score']

                    with st.expander(
                        f"Question {result['question_num']} - {score:.1f}/{max_score} marks",
                        expanded=(score < max_score * 0.6)
                    ):
                        st.markdown(f"**Question:** {result['question']}")
                        st.markdown(f"**Your Answer:** {result['student_answer']}")

                        if 'matched_points' in eval_data:
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if eval_data.get('matched_points'):
                                    st.markdown("Points Covered")
                                    for point in eval_data['matched_points']:
                                        st.markdown(f"- {point}")
                            with col_b:
                                if eval_data.get('missing_points'):
                                    st.markdown("Points Missed")
                                    for point in eval_data['missing_points']:
                                        st.markdown(f"- {point}")

                        st.info(f"Feedback: {eval_data['feedback']}")

                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Retake Assessment", use_container_width=True):
                        st.session_state.results = None
                        st.session_state.student_answers = {}
                        st.rerun()
                with col2:
                    if st.button("New Assessment", use_container_width=True):
                        st.info("Ask your teacher to generate a new assessment")
            else:
                st.info("Complete the assessment to view results")

st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p><b>BloomSetu</b> - Aligned with CBSE, ICSE and State Boards</p>
        <p style='font-size: 0.9em;'>Powered by Bloom's Taxonomy</p>
    </div>
    """,
    unsafe_allow_html=True
)
