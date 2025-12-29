import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path("shared_questions.json")
HISTORY_FILE = Path("student_history.json")

def save_questions(questions):
    """Teacher saves generated questions"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({
                'questions': questions,
                'timestamp': datetime.now().isoformat()
            }, f)
        return True
    except:
        return False

def load_questions():
    """Student loads questions"""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                return data.get('questions', [])
        except:
            pass
    return []

def save_student_result(result):
    """Save student assessment result"""
    history = load_student_history()
    history.append(result)
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    except:
        pass

def load_student_history():
    """Load all student results"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return []

def clear_questions():
    """Clear current assessment"""
    if DATA_FILE.exists():
        DATA_FILE.unlink()