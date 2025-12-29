BOARDS = ["CBSE", "ICSE", "State Board"]

CLASSES = list(range(6, 13))  

SUBJECTS = {
    "Science": ["Physics", "Chemistry", "Biology"],
    "Mathematics": ["Mathematics"],
    "Social Science": ["History", "Geography", "Civics", "Economics"],
    "Languages": ["English", "Hindi"]
}

ALL_SUBJECTS = []
for category in SUBJECTS.values():
    ALL_SUBJECTS.extend(category)


#question types info
QUESTION_TYPES = {
    "MCQ": {
        "name": "Multiple Choice",
        "marks": 1,
        "description": "Single correct answer"
    },
    "VSA": {
        "name": "Very Short Answer",
        "marks": 1,
        "word_limit": "20-30 words",
        "description": "1 mark question"
    },
    "SA": {
        "name": "Short Answer",
        "marks": 3,
        "word_limit": "50-60 words",
        "description": "3 marks question"
    },
    "LA": {
        "name": "Long Answer",
        "marks": 5,
        "word_limit": "100-150 words",
        "description": "5 marks question"
    }
}

#pattern for each board
EXAM_PATTERNS = {
    "CBSE_10": {
        "MCQ": {"count": 20, "marks": 1},
        "VSA": {"count": 6, "marks": 1},
        "SA": {"count": 6, "marks": 3},
        "LA": {"count": 3, "marks": 5}
    },
    "CBSE_12": {
        "MCQ": {"count": 16, "marks": 1},
        "VSA": {"count": 5, "marks": 1},
        "SA": {"count": 7, "marks": 3},
        "LA": {"count": 3, "marks": 5}
    },
    "ICSE": {
        "MCQ": {"count": 10, "marks": 1},
        "SA": {"count": 8, "marks": 2},
        "LA": {"count": 4, "marks": 5}
    }
}

# exam keywords
EXAM_KEYWORDS = {
    "Remember": ["Define", "State", "Name", "List", "Identify"],
    "Understand": ["Explain", "Describe", "Discuss", "Illustrate"],
    "Apply": ["Calculate", "Solve", "Demonstrate", "Apply"],
    "Analyze": ["Analyze", "Compare", "Differentiate", "Examine"],
    "Evaluate": ["Justify", "Evaluate", "Assess", "Critique"],
    "Create": ["Derive", "Design", "Formulate", "Construct"]
}

#chapter mapping for ncert for some of subjects
NCERT_CHAPTERS = {
    "Physics_11": [
        "Physical World",
        "Units and Measurements",
        "Motion in a Straight Line",
        "Motion in a Plane",
        "Laws of Motion",
        "Work, Energy and Power"
    ],
    "Chemistry_11": [
        "Some Basic Concepts of Chemistry",
        "Structure of Atom",
        "Classification of Elements",
        "Chemical Bonding"
    ],
    "Biology_11": [
        "The Living World",
        "Biological Classification",
        "Plant Kingdom",
        "Animal Kingdom"
    ],
    "Mathematics_10": [
        "Real Numbers",
        "Polynomials",
        "Linear Equations",
        "Quadratic Equations",
        "Arithmetic Progressions"
    ]
}

def get_chapters(subject, class_level):
    key = f"{subject}_{class_level}"
    return NCERT_CHAPTERS.get(key, [])

def get_exam_pattern(board, class_level):
    key = f"{board}_{class_level}"
    return EXAM_PATTERNS.get(key, EXAM_PATTERNS.get(board, {}))

def get_keywords_for_bloom(bloom_level):
    return EXAM_KEYWORDS.get(bloom_level, ["Explain", "Describe"])

def get_question_type_info(q_type):
    return QUESTION_TYPES.get(q_type, QUESTION_TYPES["MCQ"])