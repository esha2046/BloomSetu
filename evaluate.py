import streamlit as st
from config import ENABLE_SEMANTIC_EVALUATION, SEMANTIC_SIMILARITY_THRESHOLD

# Lazy load semantic model
_semantic_model = None

def get_semantic_model():
    """Lazy load semantic model to avoid loading on import"""
    global _semantic_model
    if _semantic_model is None and ENABLE_SEMANTIC_EVALUATION:
        try:
            from sentence_transformers import SentenceTransformer
            _semantic_model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight, fast model
        except Exception as e:
            st.warning(f"Semantic evaluation unavailable: {e}. Using keyword matching.")
            return None
    return _semantic_model

def evaluate_answer(question, student_answer):
    if 'options' in question:
        return evaluate_mcq(question, student_answer)
    elif 'labels' in question:
        return evaluate_diagram_labeling(question, student_answer)
    else:
        return evaluate_descriptive(question, student_answer)

#simple mcq logic
def evaluate_mcq(question, student_answer):
    correct_answer = question['correct_answer']
    marks = question.get('marks', 1)
    is_correct = (student_answer == correct_answer)
    
    return {
        'correct': is_correct,
        'score': marks if is_correct else 0,
        'max_score': marks,
        'percentage': 100 if is_correct else 0,
        'feedback': (question['explanation'] if is_correct 
                    else f"Correct answer: {correct_answer}. {question['explanation']}")
    }

def evaluate_diagram_labeling(question, student_answer):
    """Evaluate diagram labeling questions"""
    if not student_answer or not isinstance(student_answer, dict):
        return {
            'score': 0,
            'max_score': question.get('marks', 3),
            'percentage': 0,
            'feedback': "No labels provided",
            'matched_labels': [],
            'missing_labels': list(question.get('labels', {}).keys())
        }
    
    correct_labels = question.get('labels', {})
    matched = []
    missing = []
    score = 0
    
    for label_key, correct_name in correct_labels.items():
        student_label = student_answer.get(label_key, "").strip().lower()
        correct_lower = correct_name.lower()
        
        # Simple matching: check if student answer contains key words
        key_words = [w for w in correct_lower.split() if len(w) > 3]
        matches = sum(1 for word in key_words if word in student_label)
        
        if matches >= len(key_words) * 0.5 or student_label in correct_lower:
            matched.append(f"{label_key}: {correct_name}")
            score += question.get('marks', 3) / len(correct_labels)
        else:
            missing.append(f"{label_key}: {correct_name} (You: {student_answer.get(label_key, 'N/A')})")
    
    score = round(score * 2) / 2  # Round to 0.5
    max_marks = question.get('marks', 3)
    percentage = (score / max_marks * 100) if max_marks > 0 else 0
    
    feedback = f"Matched {len(matched)}/{len(correct_labels)} labels. "
    if missing:
        feedback += f"Review: {', '.join(missing[:2])}"
    
    return {
        'score': min(score, max_marks),
        'max_score': max_marks,
        'percentage': percentage,
        'feedback': feedback,
        'matched_labels': matched,
        'missing_labels': missing
    }

def evaluate_descriptive(question, student_answer):
    if not student_answer or len(student_answer.strip()) < 10:
        return {
            'score': 0,
            'max_score': question.get('marks', 5),
            'percentage': 0,
            'feedback': "Answer too short or empty",
            'matched_points': [],
            'missing_points': question.get('key_points', []),
            'word_count': 0
        }
    
    max_marks = question.get('marks', 5)
    key_points = question.get('key_points', [])
    model_answer = question.get('model_answer', '')
    word_count = len(student_answer.split())
    
    # Try semantic evaluation first, fall back to keyword matching
    if ENABLE_SEMANTIC_EVALUATION:
        semantic_result = evaluate_semantic(student_answer, model_answer, key_points, max_marks, word_count, question)
        if semantic_result:
            return semantic_result
    
    # Fall back to keyword-based evaluation
    return evaluate_keyword_based(question, student_answer, key_points, max_marks, word_count)

def evaluate_semantic(student_answer, model_answer, key_points, max_marks, word_count, question):
    """Evaluate using semantic similarity"""
    try:
        model = get_semantic_model()
        if not model:
            return None
        
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        # Get embeddings
        texts_to_encode = [student_answer, model_answer] + key_points
        embeddings = model.encode(texts_to_encode, convert_to_numpy=True)
        
        student_emb = embeddings[0:1]
        model_emb = embeddings[1:2]
        key_point_embs = embeddings[2:]
        
        # Overall similarity with model answer
        overall_similarity = cosine_similarity(student_emb, model_emb)[0][0]
        
        # Similarity with each key point
        matched_points = []
        missing_points = []
        point_similarities = []
        
        for i, point in enumerate(key_points):
            point_emb = key_point_embs[i:i+1]
            similarity = cosine_similarity(student_emb, point_emb)[0][0]
            point_similarities.append(similarity)
            
            if similarity >= SEMANTIC_SIMILARITY_THRESHOLD:
                matched_points.append(point)
            else:
                missing_points.append(point)
        
        # Calculate score based on semantic similarity
        if len(key_points) > 0:
            # Use average of key point similarities and overall similarity
            avg_key_similarity = np.mean(point_similarities)
            combined_similarity = (overall_similarity * 0.4 + avg_key_similarity * 0.6)
        else:
            combined_similarity = overall_similarity
        
        # Map similarity to score (0.6 similarity = 60% of marks, 0.9+ = 90%+)
        base_score = combined_similarity * max_marks
        
        # Adjust for word limit
        word_limit = question.get('word_limit', '50-100 words')
        score = adjust_for_word_limit(base_score, word_count, word_limit, max_marks)
        score = round(score * 2) / 2
        score = max(0, min(score, max_marks))
        
        percentage = (score / max_marks * 100) if max_marks > 0 else 0
        feedback = generate_semantic_feedback(score, max_marks, matched_points, missing_points, 
                                               word_count, overall_similarity, len(key_points))
        
        return {
            'score': score,
            'max_score': max_marks,
            'percentage': percentage,
            'feedback': feedback,
            'matched_points': matched_points,
            'missing_points': missing_points,
            'word_count': word_count,
            'semantic_similarity': float(overall_similarity)
        }
    except Exception as e:
        # Fall back to keyword matching on error
        return None

def evaluate_keyword_based(question, student_answer, key_points, max_marks, word_count):
    """Original keyword-based evaluation (fallback)"""
    student_lower = student_answer.lower()
    matched_points = []
    missing_points = []
    
    for point in key_points:
        keywords = extract_keywords(point)
        matches = sum(1 for kw in keywords if kw in student_lower)
        
        if matches >= 2 or len(keywords) <= 2:
            matched_points.append(point)
        else:
            missing_points.append(point)
    
    if len(key_points) > 0:
        coverage_ratio = len(matched_points) / len(key_points)
    else:
        coverage_ratio = 0.5
    
    base_score = coverage_ratio * max_marks
    
    word_limit = question.get('word_limit', '50-100 words')
    score = adjust_for_word_limit(base_score, word_count, word_limit, max_marks)
    
    score = round(score * 2) / 2
    
    percentage = (score / max_marks * 100) if max_marks > 0 else 0
    feedback = generate_feedback(score, max_marks, matched_points, missing_points, word_count)
    
    return {
        'score': score,
        'max_score': max_marks,
        'percentage': percentage,
        'feedback': feedback,
        'matched_points': matched_points,
        'missing_points': missing_points,
        'word_count': word_count
    }

def extract_keywords(text):
    common_words = {'the', 'is', 'are', 'was', 'were', 'a', 'an', 'and', 'or', 'but', 
                   'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = text.lower().split()
    keywords = [w for w in words if w not in common_words and len(w) > 3]
    return keywords[:5]

def adjust_for_word_limit(score, word_count, word_limit, max_marks):
    if 'VSA' in str(word_limit) or '20-30' in str(word_limit):
        min_words, max_words = 15, 40
    elif 'SA' in str(word_limit) or '50' in str(word_limit):
        min_words, max_words = 40, 100
    elif 'LA' in str(word_limit) or '100' in str(word_limit):
        min_words, max_words = 80, 180
    else:
        return score
    
    if word_count < min_words:
        penalty = (min_words - word_count) / min_words * 0.3
        score = score * (1 - penalty)
    elif word_count > max_words * 1.5:
        score = score * 0.95
    
    return max(0, min(score, max_marks))

def generate_feedback(score, max_marks, matched, missing, word_count):
    percentage = (score / max_marks * 100) if max_marks > 0 else 0
    feedback_parts = []
    
    if percentage >= 90:
        feedback_parts.append("🌟 Excellent! Outstanding answer.")
    elif percentage >= 75:
        feedback_parts.append("✅ Very Good! Well-explained answer.")
    elif percentage >= 60:
        feedback_parts.append("👍 Good attempt. Answer is satisfactory.")
    elif percentage >= 40:
        feedback_parts.append("⚠️ Fair attempt. Needs more detail.")
    else:
        feedback_parts.append("❌ Weak answer. Requires significant improvement.")
    
    if matched:
        feedback_parts.append(f"Covered {len(matched)} key point(s).")
    
    if missing:
        if len(missing) <= 2:
            feedback_parts.append(f"Missing: {', '.join(missing[:2])}")
        else:
            feedback_parts.append(f"Missing {len(missing)} important points.")
    
    feedback_parts.append(f"Word count: {word_count}")
    return " ".join(feedback_parts)

def generate_semantic_feedback(score, max_marks, matched, missing, word_count, similarity, total_points):
    """Generate feedback with semantic similarity information"""
    percentage = (score / max_marks * 100) if max_marks > 0 else 0
    feedback_parts = []
    
    if percentage >= 90:
        feedback_parts.append("🌟 Excellent! Outstanding answer with high semantic match.")
    elif percentage >= 75:
        feedback_parts.append("✅ Very Good! Well-explained answer.")
    elif percentage >= 60:
        feedback_parts.append("👍 Good attempt. Answer covers main concepts.")
    elif percentage >= 40:
        feedback_parts.append("⚠️ Fair attempt. Some concepts covered but needs more detail.")
    else:
        feedback_parts.append("❌ Weak answer. Low similarity with expected answer.")
    
    if matched:
        feedback_parts.append(f"Semantically matched {len(matched)}/{total_points} key point(s).")
    
    if missing:
        if len(missing) <= 2:
            feedback_parts.append(f"Missing concepts: {', '.join(missing[:2])}")
        else:
            feedback_parts.append(f"Missing {len(missing)} important concepts.")
    
    # Add similarity score for transparency
    similarity_percent = int(similarity * 100)
    feedback_parts.append(f"Semantic similarity: {similarity_percent}% | Word count: {word_count}")
    
    return " ".join(feedback_parts)

def calculate_total_score(results):
    total = sum(r['evaluation']['score'] for r in results)
    max_total = sum(r['evaluation']['max_score'] for r in results)
    percentage = (total / max_total * 100) if max_total > 0 else 0
    
    return {
        'total_score': total,
        'max_score': max_total,
        'percentage': percentage
    }