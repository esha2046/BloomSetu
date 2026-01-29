# BloomSetu

An AI-powered educational assessment platform for Indian curriculum (CBSE, ICSE, State Board). Teachers can generate questions from study materials, and students can take assessments with automated evaluation.

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_api_key_here
```

### 3. Run the App
```bash
streamlit run app.py
```

## How It Works

1. **Teachers**: Upload study materials (PDFs, docs, images) → AI generates questions
2. **Students**: Take assessments → Submit answers → Get automated evaluation with detailed feedback
3. **AI Evaluation**: Uses Google Gemini API and semantic similarity models to grade answers accurately

## Features

- Multi-format support (PDF, DOCX, images)
- Indian curriculum-aligned questions
- Automated grading with partial credit
- Detailed feedback for students
- Rate limiting and caching for efficiency

---

*For detailed methodology, see METHODOLOGY.md and ML_METHODOLOGY.md*
