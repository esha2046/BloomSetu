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
    },
    "IMAGE": {
        "name": "Image-based Question",
        "marks": 3,
        "description": "Question about an image/diagram"
    },
    "DIAGRAM": {
        "name": "Diagram Labeling",
        "marks": 3,
        "description": "Label parts of a diagram"
    },
    "CASE_STUDY": {
        "name": "Case Study",
        "marks": 5,
        "word_limit": "150-200 words",
        "description": "Scenario-based question"
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

#chapter mapping for ncert
NCERT_CHAPTERS = {
    # Class 6
    "Science_6": ["Food", "Materials", "World of Living", "Moving Things", "Natural Phenomena", "Natural Resources"],
    "Mathematics_6": ["Knowing Numbers", "Whole Numbers", "Playing with Numbers", "Basic Geometry", "Fractions", "Decimals", "Data Handling", "Mensuration", "Algebra", "Ratio and Proportion", "Symmetry"],
    "History_6": ["What Where How and When", "Earliest Societies", "First Farmers", "First Cities", "Kingdoms", "New Questions"],
    "Geography_6": ["Earth in Solar System", "Globe", "Maps", "Major Domains of Earth", "Landforms", "Our Country India"],
    "Civics_6": ["Understanding Diversity", "What is Government", "Key Elements of Democracy", "Panchayati Raj", "Rural Administration", "Urban Administration"],
    
    # Class 7
    "Science_7": ["Nutrition in Plants", "Nutrition in Animals", "Heat", "Acids Bases Salts", "Weather Climate", "Motion and Time", "Electric Current", "Light", "Forests", "Wastewater Story"],
    "Mathematics_7": ["Integers", "Fractions and Decimals", "Data Handling", "Simple Equations", "Lines and Angles", "Triangles", "Rational Numbers", "Perimeter and Area", "Algebraic Expressions", "Symmetry"],
    "History_7": ["Tracing Changes", "New Kings and Kingdoms", "Delhi Sultans", "Mughal Empire", "Towns Traders", "Devotional Paths", "18th Century"],
    "Geography_7": ["Environment", "Inside Earth", "Air", "Water", "Natural Vegetation", "Human Environment", "Life in Deserts"],
    "Civics_7": ["On Equality", "Role of Government", "How State Government Works", "Understanding Media", "Markets Around Us"],
    
    # Class 8
    "Science_8": ["Crop Production", "Microorganisms", "Synthetic Fibres", "Materials Metals", "Coal and Petroleum", "Cell Structure", "Reproduction in Animals", "Force and Pressure", "Friction", "Sound", "Light", "Pollution of Air and Water"],
    "Mathematics_8": ["Rational Numbers", "Linear Equations", "Understanding Quadrilaterals", "Data Handling", "Squares and Square Roots", "Cubes and Cube Roots", "Comparing Quantities", "Mensuration", "Factorisation", "Graphs"],
    "History_8": ["How When Where", "From Trade to Territory", "Ruling the Countryside", "When People Rebel", "Weavers Iron Smelters", "National Movement", "India After Independence"],
    "Geography_8": ["Resources", "Land Soil Water", "Mineral and Power Resources", "Agriculture", "Industries", "Human Resources"],
    "Civics_8": ["Indian Constitution", "Understanding Secularism", "Parliament", "Judiciary", "Marginalization", "Public Facilities"],
    
    # Class 9
    "Physics_9": ["Motion", "Force and Laws of Motion", "Gravitation", "Work and Energy", "Sound"],
    "Chemistry_9": ["Matter in Our Surroundings", "Is Matter Pure", "Atoms and Molecules", "Structure of Atom"],
    "Biology_9": ["The Fundamental Unit of Life", "Tissues", "Diversity in Living Organisms", "Why Do We Fall Ill", "Natural Resources", "Improvement in Food Resources"],
    "Mathematics_9": ["Number Systems", "Polynomials", "Coordinate Geometry", "Linear Equations in Two Variables", "Lines and Angles", "Triangles", "Quadrilaterals", "Circles", "Surface Areas and Volumes", "Statistics", "Probability"],
    "History_9": ["French Revolution", "Socialism in Europe", "Nazism", "Forest Society", "Pastoralists"],
    "Geography_9": ["India Size and Location", "Physical Features of India", "Drainage", "Climate", "Natural Vegetation", "Population"],
    "Civics_9": ["What is Democracy", "Constitutional Design", "Electoral Politics", "Working of Institutions", "Democratic Rights"],
    "Economics_9": ["Story of Village Palampur", "People as Resource", "Poverty as Challenge", "Food Security in India"],
    
    # Class 10
    "Physics_10": ["Light Reflection and Refraction", "Human Eye", "Electricity", "Magnetic Effects of Electric Current", "Sources of Energy"],
    "Chemistry_10": ["Chemical Reactions and Equations", "Acids Bases and Salts", "Metals and Non-metals", "Carbon and its Compounds", "Periodic Classification of Elements"],
    "Biology_10": ["Life Processes", "Control and Coordination", "How Do Organisms Reproduce", "Heredity and Evolution", "Our Environment", "Management of Natural Resources"],
    "Mathematics_10": ["Real Numbers", "Polynomials", "Pair of Linear Equations", "Quadratic Equations", "Arithmetic Progressions", "Triangles", "Coordinate Geometry", "Trigonometry", "Circles", "Surface Areas and Volumes", "Statistics", "Probability"],
    "History_10": ["Rise of Nationalism in Europe", "Nationalism in India", "Making of Global World", "Age of Industrialisation", "Print Culture"],
    "Geography_10": ["Resources and Development", "Forest and Wildlife", "Water Resources", "Agriculture", "Minerals and Energy Resources", "Manufacturing Industries", "Lifelines of National Economy"],
    "Civics_10": ["Power Sharing", "Federalism", "Democracy and Diversity", "Gender Religion and Caste", "Political Parties", "Outcomes of Democracy"],
    "Economics_10": ["Development", "Sectors of Indian Economy", "Money and Credit", "Globalisation", "Consumer Rights"],
    
    # Class 11
    "Physics_11": ["Physical World", "Units and Measurements", "Motion in a Straight Line", "Motion in a Plane", "Laws of Motion", "Work Energy and Power", "System of Particles", "Gravitation", "Mechanical Properties of Solids", "Mechanical Properties of Fluids", "Thermal Properties of Matter", "Thermodynamics", "Kinetic Theory", "Oscillations", "Waves"],
    "Chemistry_11": ["Some Basic Concepts of Chemistry", "Structure of Atom", "Classification of Elements", "Chemical Bonding", "States of Matter", "Thermodynamics", "Equilibrium", "Redox Reactions", "Hydrogen", "s-Block Elements", "p-Block Elements", "Organic Chemistry Basics", "Hydrocarbons", "Environmental Chemistry"],
    "Biology_11": ["The Living World", "Biological Classification", "Plant Kingdom", "Animal Kingdom", "Morphology of Flowering Plants", "Anatomy of Flowering Plants", "Structural Organisation in Animals", "Cell The Unit of Life", "Biomolecules", "Cell Cycle and Division", "Transport in Plants", "Mineral Nutrition", "Photosynthesis", "Respiration in Plants", "Plant Growth and Development", "Digestion and Absorption", "Breathing and Exchange of Gases", "Body Fluids and Circulation", "Excretory Products", "Locomotion and Movement", "Neural Control", "Chemical Coordination"],
    "Mathematics_11": ["Sets", "Relations and Functions", "Trigonometric Functions", "Mathematical Induction", "Complex Numbers", "Linear Inequalities", "Permutations and Combinations", "Binomial Theorem", "Sequences and Series", "Straight Lines", "Conic Sections", "3D Geometry", "Limits and Derivatives", "Mathematical Reasoning", "Statistics", "Probability"],
    
    # Class 12
    "Physics_12": ["Electric Charges and Fields", "Electrostatic Potential", "Current Electricity", "Moving Charges and Magnetism", "Magnetism and Matter", "Electromagnetic Induction", "Alternating Current", "Electromagnetic Waves", "Ray Optics", "Wave Optics", "Dual Nature of Radiation", "Atoms", "Nuclei", "Semiconductor Electronics", "Communication Systems"],
    "Chemistry_12": ["The Solid State", "Solutions", "Electrochemistry", "Chemical Kinetics", "Surface Chemistry", "Isolation of Elements", "p-Block Elements", "d and f Block Elements", "Coordination Compounds", "Haloalkanes and Haloarenes", "Alcohols Phenols and Ethers", "Aldehydes Ketones", "Carboxylic Acids", "Amines", "Biomolecules", "Polymers", "Chemistry in Everyday Life"],
    "Biology_12": ["Reproduction in Organisms", "Sexual Reproduction in Flowering Plants", "Human Reproduction", "Reproductive Health", "Principles of Inheritance", "Molecular Basis of Inheritance", "Evolution", "Human Health and Disease", "Food Production", "Microbes in Human Welfare", "Biotechnology Principles", "Biotechnology Applications", "Organisms and Populations", "Ecosystem", "Biodiversity and Conservation", "Environmental Issues"],
    "Mathematics_12": ["Relations and Functions", "Inverse Trigonometric Functions", "Matrices", "Determinants", "Continuity and Differentiability", "Applications of Derivatives", "Integrals", "Applications of Integrals", "Differential Equations", "Vector Algebra", "Three Dimensional Geometry", "Linear Programming", "Probability"],
    "History_12": ["Bricks Beads and Bones", "Kings Farmers and Towns", "Kinship Caste and Class", "Thinkers Beliefs and Buildings", "Through the Eyes of Travellers", "Bhakti-Sufi Traditions", "An Imperial Capital Vijayanagara", "Peasants Zamindars and the State", "Kings and Chronicles", "Colonialism and the Countryside", "Rebels and the Raj", "Colonial Cities", "Mahatma Gandhi", "Framing the Constitution", "Understanding Partition"],
    "Geography_12": ["Population Distribution", "Migration", "Human Development", "Primary Activities", "Secondary Activities", "Tertiary Activities", "Transport and Communication", "International Trade", "Human Settlements"],
    "Civics_12": ["The Cold War Era", "End of Bipolarity", "US Hegemony", "Alternative Centres of Power", "Contemporary South Asia", "International Organisations", "Security in Contemporary World", "Environment and Natural Resources", "Globalisation"],
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