import PyPDF2
from docx import Document
import streamlit as st

def extract_pdf(pdf_file,max_pages=5,max_chars=3000):
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages[:max_pages]:
            text += page.extract_text()
        return text[:max_chars]
    except Exception as e:
        st.error(f"Error extracting PDF:{str(e)}")
        return ""
    
def extract_docx(docx_file,max_chars=3000):
    try:
        doc = Document(docx_file)
        text = "\n"
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text[:max_chars]
    except Exception as e:
        st.error(f"Error extracting docs:{str(e)}")
        return ""