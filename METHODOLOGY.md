# BloomSetu - Step-wise Methodology

## Project Overview
BloomSetu is an AI-powered educational assessment platform designed for Indian curriculum (CBSE, ICSE, State Board). It enables teachers to generate questions from study materials and allows students to take assessments with automated evaluation and detailed feedback.

---

## Phase 1: Project Setup & Configuration

### Step 1.1: Environment Setup
1. **Create Python Virtual Environment**
   ```bash
   python -m venv quesansgen
   quesansgen\Scripts\activate  # Windows
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   - Core: `streamlit`, `google-generativeai`, `python-dotenv`
   - Document Processing: `PyPDF2`, `python-docx`, `Pillow`
   - ML Evaluation: `sentence-transformers`, `scikit-learn`, `torch`, `numpy`

3. **Configure API Keys**
   - Create `.env` file in project root
   - Add: `GEMINI_API_KEY=your_api_key_here`
   - Load via `python-dotenv` in `config.py`

### Step 1.2: Configuration Setup (`config.py`)
- **API Configuration**: Google Gemini API setup with fallback to demo mode
- **Content Limits**: 
  - `MIN_CONTENT_LENGTH = 50`
  - `MAX_CONTENT_LENGTH = 3000`
  - `OPTIMAL_CONTENT_LENGTH = 1500` (for API efficiency)
- **Rate Limiting**: 
  - `REQUEST_COOLDOWN = 10` seconds
  - `DAILY_LIMIT = 10` API calls
- **Image Optimization**:
  - `MAX_IMAGE_SIZE_KB = 200`
  - `MAX_IMAGE_DIMENSIONS = (800, 600)`
  - `MAX_IMAGES_PER_REQUEST = 1`
- **Evaluation Settings**:
  - `ENABLE_SEMANTIC_EVALUATION = True`
  - `SEMANTIC_SIMILARITY_THRESHOLD = 0.6`

---

## Phase 2: Core Module Development

### Step 2.1: Authentication System (`auth.py`)
**Purpose**: User authentication with role-based access (Teacher/Student)

**Implementation Steps**:
1. Initialize user storage (`users.json`)
2. Create login page with username/password
3. Create registration page with role selection
4. Implement session management
5. Add logout functionality
6. Password hashing (basic implementation)

**Key Features**:
- Role-based access control (Teacher vs Student)
- Session persistence using Streamlit session state
- User data stored in JSON format

### Step 2.2: Curriculum Management (`curriculum.py`)
**Purpose**: Define Indian curriculum structure and question types

**Implementation Steps**:
1. Define board types: `["CBSE", "ICSE", "State Board"]`
2. Define class levels: `range(6, 13)` (Classes 6-12)
3. Map subjects by category:
   - Science: Physics, Chemistry, Biology
   - Mathematics
   - Social Science: History, Geography, Civics, Economics
   - Languages: English, Hindi
4. Define question types with metadata:
   - MCQ (1 mark)
   - VSA - Very Short Answer (1 mark, 20-30 words)
   - SA - Short Answer (3 marks, 50-60 words)
   - LA - Long Answer (5 marks, 100-150 words)
   - IMAGE (3 marks)
   - DIAGRAM (3 marks)
   - CASE_STUDY (5 marks, 150-200 words)
5. Map NCERT chapters for each subject-class combination
6. Define Bloom's Taxonomy keywords:
   - Remember, Understand, Apply, Analyze, Evaluate, Create

### Step 2.3: Document Extraction (`extract.py`)
**Purpose**: Extract text and images from PDF/DOCX files

**Implementation Steps**:
1. **PDF Extraction**:
   - Use `PyPDF2` to read PDF files
   - Extract text from pages (limit: 5 pages, 3000 chars)
   - Extract images from PDF pages
   - Optimize images (resize, compress to <200KB)
   - Return text and image list

2. **DOCX Extraction**:
   - Use `python-docx` to read DOCX files
   - Extract text from paragraphs
   - Limit to 3000 characters
   - Return text only

3. **Image Optimization**:
   - Resize if dimensions exceed 800x600
   - Convert to RGB format
   - Compress JPEG quality (start at 85%, reduce if needed)
   - Target size: <200KB per image

---

## Phase 3: Question Generation System

### Step 3.1: Question Generator Core (`question_generator.py`)
**Purpose**: Generate questions using AI API with caching and optimization

**Implementation Steps**:

1. **Content Optimization**:
   - Check if content exceeds `OPTIMAL_CONTENT_LENGTH` (1500 chars)
   - If chapter specified, prioritize relevant paragraphs
   - Smart truncation at sentence boundaries
   - Preserve complete sentences and paragraphs

2. **Caching System**:
   - Generate cache key from: content sample + curriculum info + image hash
   - Use MD5 hash for cache key
   - Store cache in `question_cache.pkl` (pickle format)
   - Cache expiry: 48 hours (`MAX_CACHE_AGE_HOURS`)
   - Lazy loading: Load cache only when needed
   - Incremental updates: Merge new entries with existing cache

3. **Image Handling**:
   - Generate image hash using MD5 of compressed image bytes
   - In-memory cache for image hashes (limit: 100 entries)
   - Only send images if question type requires them (IMAGE, DIAGRAM)
   - Limit to 1 image per API request

4. **Prompt Building**:
   - Use `@lru_cache` for keyword and question type lookups
   - Build prompts based on:
     - Board, Class, Subject, Chapter
     - Question type and marks
     - Bloom's Taxonomy level
     - Number of questions needed
   - Include NCERT/CBSE pattern requirements
   - Add type-specific JSON format instructions

5. **API Integration**:
   - Use Google Gemini 2.5 Flash model
   - Exponential backoff retry (max 2 attempts)
   - Temperature: 0.3 (for consistent output)
   - Max output tokens: 2048
   - Handle API errors gracefully

6. **Response Parsing**:
   - Remove markdown code blocks (```json, ```)
   - Extract JSON array from response
   - Fix common JSON issues (trailing commas)
   - Validate parsed questions
   - Check for placeholder questions

7. **Question Enrichment**:
   - Add metadata: board, class, subject, chapter, bloom_level
   - Add NCERT references
   - Attach image indices for image-based questions
   - Limit to requested number of questions

8. **Demo Mode**:
   - Fallback when API unavailable
   - Generate sample questions with proper structure
   - Include all required fields

---

## Phase 4: Answer Evaluation System

### Step 4.1: Evaluation Engine (`evaluate.py`)
**Purpose**: Evaluate student answers with semantic similarity and keyword matching

**Implementation Steps**:

1. **MCQ Evaluation**:
   - Simple exact match comparison
   - Award full marks if correct, zero if incorrect
   - Return explanation from question

2. **Diagram Labeling Evaluation**:
   - Compare student labels with correct labels
   - Use keyword matching (check if key words present)
   - Partial credit: 50% match threshold
   - Score calculation: `marks / total_labels * matched_labels`
   - Round to 0.5 increments

3. **Descriptive Answer Evaluation**:
   - **Semantic Evaluation** (Primary):
     - Lazy load `SentenceTransformer` model (`all-MiniLM-L6-v2`)
     - Generate embeddings for: student answer, model answer, key points
     - Calculate cosine similarity
     - Overall similarity with model answer (40% weight)
     - Key point similarities (60% weight)
     - Map similarity to score (0.6 similarity = 60% marks)
     - Threshold: `SEMANTIC_SIMILARITY_THRESHOLD = 0.6`
   
   - **Keyword-Based Evaluation** (Fallback):
     - Extract keywords from key points (exclude common words)
     - Count keyword matches in student answer
     - Coverage ratio: `matched_points / total_points`
     - Base score: `coverage_ratio * max_marks`

4. **Word Limit Adjustment**:
   - Parse word limit from question (VSA: 15-40, SA: 40-100, LA: 80-180)
   - Penalty if below minimum words (up to 30% reduction)
   - Slight penalty if significantly over limit (5% reduction)

5. **Feedback Generation**:
   - Grade-based feedback (Excellent, Very Good, Good, Fair, Weak)
   - List matched and missing key points
   - Include word count
   - For semantic: Include similarity percentage

6. **Score Calculation**:
   - Sum individual question scores
   - Calculate percentage: `(total_score / max_score) * 100`
   - Return summary with total, max, and percentage

---

## Phase 5: User Interface Development

### Step 5.1: Main Application (`app.py`)
**Purpose**: Streamlit-based web interface for teachers and students

**Implementation Steps**:

1. **Initialization**:
   - Set page config (title: "BloomSetu", layout: "wide")
   - Initialize user system
   - Check authentication (redirect to login if not authenticated)
   - Initialize session state variables

2. **Session State Management**:
   - Questions list
   - Student answers dictionary
   - Results data
   - Extracted content and images
   - Curriculum settings (board, class, subject, chapter)
   - Question type and Bloom's level
   - Quota tracking (daily API limit)

3. **Header Section**:
   - Display role icon (👨‍🏫 Teacher / 👨‍🎓 Student)
   - Show username
   - Logout button

4. **Sidebar**:
   - Curriculum settings (Board, Class, Subject, Chapter dropdowns)
   - API status indicator
   - Statistics:
     - Teacher: Questions generated, API calls remaining, Student assessments, Class average
     - Student: Assessments taken, Average score

---

## Phase 6: Teacher Interface

### Step 6.1: Create Assessment Tab
**Implementation Steps**:

1. **Input Section**:
   - Radio buttons: "Text" or "File Upload"
   - Text area for manual content input
   - File uploader for PDF/DOCX
   - Show extracted content preview
   - Display extracted images if available

2. **Question Settings**:
   - Question type dropdown with descriptions
   - Number of questions slider (1-10)
   - Bloom's Taxonomy level selector
   - Display keywords for selected Bloom level

3. **Generation Process**:
   - Validate content (minimum length check)
   - Check request cooldown
   - Check daily quota
   - Show optimization warnings:
     - Content truncation info
     - Image compression info
     - Image count info
   - Call `generate_questions()` function
   - Increment quota counter
   - Display success message

4. **Generated Questions Display**:
   - Show curriculum info (board, class, subject, chapter)
   - Display total marks
   - Expandable sections for each question
   - Show images if question requires them
   - Display:
     - MCQ: Options, correct answer, explanation
     - Descriptive: Model answer, key points, marking scheme
     - Diagram: Labels, model answer, key points
   - Show NCERT references if available

5. **Actions**:
   - "Publish to Students" button (saves to `shared_questions.json`)
   - "Clear" button (resets questions)

### Step 6.2: Student Analytics Tab
**Implementation Steps**:
1. Load student history from `student_history.json`
2. Display metrics:
   - Total assessments
   - Class average
   - Latest score
3. Show recent submissions (last 10):
   - Username, percentage, timestamp
   - Expandable details: date, questions count, score breakdown

---

## Phase 7: Student Interface

### Step 7.1: Take Assessment Tab
**Implementation Steps**:

1. **Load Published Questions**:
   - Load from `shared_questions.json`
   - Check if assessment available
   - Show waiting message if no assessment

2. **Question Display**:
   - Show assessment info (board, class, subject, chapter, total marks)
   - For each question:
     - Display question text
     - Show images if required
     - Show NCERT references
     - Input method based on question type:
       - **MCQ**: Radio buttons with options
       - **Diagram**: Text inputs for each label
       - **Descriptive**: Text area with word limit
     - Show word count for descriptive answers

3. **Submission**:
   - Validate all questions answered
   - Disable submit if incomplete
   - On submit:
     - Call `evaluate_answer()` for each question
     - Calculate total score
     - Save result to `student_history.json`
     - Store results in session state
     - Redirect to results tab

### Step 7.2: View Results Tab
**Implementation Steps**:

1. **Score Summary**:
   - Total score (X / Y)
   - Percentage
   - Grade calculation (A+, A, B+, B, C, D)
   - Performance message based on percentage

2. **Detailed Feedback**:
   - Expandable sections for each question
   - Show question text
   - Show student answer
   - Display:
     - Matched points (✅)
     - Missing points (❌)
     - Feedback message
   - Auto-expand questions with low scores (<60%)

3. **Actions**:
   - "Retake Assessment" button (reset answers)
   - "Wait for New Assessment" button (clear current assessment)

---

## Phase 8: Data Persistence

### Step 8.1: Shared State Management (`shared_state.py`)
**Purpose**: Manage persistent data storage

**Implementation Steps**:

1. **Save Questions**:
   - Write questions to `shared_questions.json`
   - Include metadata (timestamp, curriculum info)

2. **Load Questions**:
   - Read from `shared_questions.json`
   - Return questions list or empty list

3. **Save Student Result**:
   - Append to `student_history.json`
   - Include: username, timestamp, scores, percentage

4. **Load Student History**:
   - Read from `student_history.json`
   - Return list of all attempts
   - Filter by username if needed

---

## Phase 9: Optimization & Performance

### Step 9.1: Caching Strategy
- **Question Cache**: MD5-based cache keys, 48-hour expiry
- **Image Hash Cache**: In-memory cache (100 entry limit)
- **Prompt Cache**: LRU cache for keywords and question types
- **Lazy Loading**: Load cache only when needed

### Step 9.2: API Optimization
- **Content Truncation**: Smart truncation at sentence boundaries
- **Image Optimization**: Resize, compress, limit count
- **Request Cooldown**: 10-second delay between requests
- **Daily Quota**: Limit to 10 API calls per day
- **Retry Logic**: Exponential backoff for failed requests

### Step 9.3: Error Handling
- **API Failures**: Fallback to demo mode
- **File Extraction Errors**: Show error messages, return empty content
- **JSON Parsing Errors**: Multiple parsing attempts with fixes
- **Cache Errors**: Graceful degradation, continue without cache

---

## Phase 10: Testing & Deployment

### Step 10.1: Testing Checklist
- [ ] Authentication (login, register, logout)
- [ ] PDF extraction (text + images)
- [ ] DOCX extraction
- [ ] Question generation (all types)
- [ ] MCQ evaluation
- [ ] Descriptive answer evaluation (semantic + keyword)
- [ ] Diagram labeling evaluation
- [ ] Caching system
- [ ] Image optimization
- [ ] Content optimization
- [ ] Student result saving
- [ ] Analytics display

### Step 10.2: Deployment Steps
1. **Local Deployment**:
   ```bash
   streamlit run app.py
   ```

2. **Production Considerations**:
   - Use environment variables for API keys
   - Set up proper file storage (not local JSON files)
   - Implement database for user and result storage
   - Add HTTPS for security
   - Set up proper session management
   - Configure rate limiting at server level

---

## Phase 11: Future Enhancements

### Potential Improvements:
1. **Database Integration**: Replace JSON files with SQLite/PostgreSQL
2. **User Management**: Password hashing, email verification
3. **Advanced Analytics**: Charts, performance trends, topic-wise analysis
4. **Export Features**: PDF export for assessments and results
5. **Multi-language Support**: Hindi and other regional languages
6. **Question Bank**: Save and reuse question sets
7. **Adaptive Testing**: Difficulty adjustment based on performance
8. **Real-time Collaboration**: Live assessment features
9. **Mobile App**: React Native or Flutter app
10. **API Endpoints**: REST API for third-party integrations

---

## Technical Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                 │
│  ┌──────────────┐              ┌──────────────┐         │
│  │ Teacher View │              │ Student View │         │
│  └──────┬───────┘              └──────┬───────┘         │
└─────────┼──────────────────────────────┼─────────────────┘
          │                              │
          ▼                              ▼
┌─────────────────────────────────────────────────────────┐
│              Core Modules                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Extract    │  │  Generate    │  │  Evaluate    │ │
│  │  (extract.py)│  │(question_    │  │(evaluate.py) │ │
│  │              │  │ generator.py)│  │              │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│         External Services & Storage                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Google Gemini│  │  File Cache  │  │  JSON Files  │ │
│  │     API     │  │(question_    │  │(users.json,   │ │
│  │             │  │ cache.pkl)   │  │ shared_*.json)│ │
│  └─────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Key Design Patterns Used

1. **Lazy Loading**: Cache and model loading only when needed
2. **Fallback Pattern**: Demo mode when API unavailable
3. **Caching Strategy**: Multi-level caching (file, memory, LRU)
4. **Retry Pattern**: Exponential backoff for API calls
5. **Strategy Pattern**: Different evaluation methods (semantic vs keyword)
6. **Session Management**: Streamlit session state for user data
7. **Optimization**: Content and image optimization before API calls

---

## Dependencies Flow

```
app.py
├── auth.py (authentication)
├── config.py (configuration)
├── curriculum.py (curriculum data)
├── extract.py (document extraction)
│   └── PyPDF2, python-docx, Pillow
├── question_generator.py (AI question generation)
│   ├── config.py
│   ├── curriculum.py
│   └── google-generativeai
├── evaluate.py (answer evaluation)
│   ├── config.py
│   └── sentence-transformers, scikit-learn
└── shared_state.py (data persistence)
```

---

## Conclusion

This methodology provides a comprehensive guide to understanding and implementing the BloomSetu project. Each phase builds upon the previous one, creating a robust educational assessment platform aligned with Indian curriculum standards.
