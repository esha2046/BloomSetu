import PyPDF2
from docx import Document
import streamlit as st
from PIL import Image
import io
from config import MAX_IMAGE_SIZE_KB, MAX_IMAGE_DIMENSIONS, IMAGE_QUALITY, ENABLE_IMAGE_OPTIMIZATION

def optimize_image(img):
    """Optimize image: resize, compress to reduce API usage"""
    if not ENABLE_IMAGE_OPTIMIZATION:
        return img
    
    try:
        # Resize if too large
        if img.size[0] > MAX_IMAGE_DIMENSIONS[0] or img.size[1] > MAX_IMAGE_DIMENSIONS[1]:
            img.thumbnail(MAX_IMAGE_DIMENSIONS, Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed (for JPEG)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Compress to target size
        output = io.BytesIO()
        quality = IMAGE_QUALITY
        img.save(output, format='JPEG', quality=quality, optimize=True)
        size_kb = len(output.getvalue()) / 1024
        
        # Reduce quality if still too large
        while size_kb > MAX_IMAGE_SIZE_KB and quality > 50:
            quality -= 5
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            size_kb = len(output.getvalue()) / 1024
        
        # Reload optimized image
        output.seek(0)
        return Image.open(output)
    except:
        return img

def extract_pdf(pdf_file,max_pages=5,max_chars=3000):
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        images = []
        for page_num, page in enumerate(reader.pages[:max_pages]):
            text += page.extract_text()
            # Extract images from page
            try:
                if '/Resources' in page and '/XObject' in page['/Resources']:
                    xObject = page['/Resources']['/XObject'].get_object()
                    for obj in xObject:
                        if '/Subtype' in xObject[obj] and xObject[obj]['/Subtype'] == '/Image':
                            try:
                                img_data = xObject[obj].get_data()
                                img = Image.open(io.BytesIO(img_data))
                                optimized_img = optimize_image(img)
                                images.append(optimized_img)
                                if len(images) >= 3:
                                    break
                            except:
                                pass
            except:
                pass
        return text[:max_chars], images[:3]  # Return text and up to 3 images
    except Exception as e:
        st.error(f"Error extracting PDF:{str(e)}")
        return "", []
    
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