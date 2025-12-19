def eval_mcq(ques,ans):
    correct = (ans==ques['correct_answer'])
    return {
        'correct': correct,
        'score': 10 if correct else 0,
        'feedback': ques['explanation'] if not correct else f"Correct! {ques['explanation']}"
    }

def eval_shortans(ques,ans):
    if not ans or len(ans.strip())<10:
        return{
            'score':0,
            'matched_points': [],
            'missing_points': ques['key_points'],
            'feedback': "Answer too short. Please provide more detail."
        }
    
    ans_lower = ans.lower()
    matched = []
    missing = []

    for point in ques['key_points']:
        keywords = [w.lower() for w in point.split() if len(w) > 4] #we only keep meaningful words from sentence
        if any(word in ans_lower for word in keywords):
            matched.append(point)
        else:
            missing.append(point)

    score = int((len(matched)/len(ques['key_points'])) * 10)

    if len(ans.split()) >30:
        score = min(10,score+2)

    if score >= 7:
        feedback = f"Great job! You covered {len(matched)}/{len(ques['key_points'])} key points."
    elif score >= 4:
        feedback = f"Good! You covered {len(matched)}/{len(ques['key_points'])} points. Please review missing points."
    else:
        feedback = "Uh oh! Please review the model answer and study the key concepts."

    return {
        'score': score,
        'matched_points': matched or ["Partial credit for attempt"],
        'missing_points': missing,
        'feedback': feedback
    }
    

