import streamlit as st
import hashlib
import json
from pathlib import Path
from time import time

USERS_FILE = Path("users.json")

# change later 
DEFAULT_USERS = {
    "teacher": {"password": "teacher123", "role": "teacher"},
    "student": {"password": "student123", "role": "student"}
}

def init_users():
    if not USERS_FILE.exists():
        save_users(DEFAULT_USERS)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_USERS

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    users = load_users()
    if username in users:
        stored = users[username]['password']
        # Simple check (in production, compare hashed passwords)
        if stored == password:
            return users[username]['role']
    return None

def login_page():
    st.title("🎓 BloomSetu Login")
    st.markdown("### AI-Powered Assessment Platform")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🔐 Login", type="primary", use_container_width=True):
                if username and password:
                    role = verify_login(username, password)
                    if role:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = role
                        st.success(f"Welcome {role.title()}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.warning("Please enter username and password")
        
        with col_b:
            if st.button("📝 Register", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()
        
        st.markdown("---")
        st.info("""
        **Demo Credentials:**
        
        👨‍🏫 Teacher: `teacher` / `teacher123`
        
        👨‍🎓 Student: `student` / `student123`
        """)

def register_page():
    st.title("📝 Register New Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        username = st.text_input("Username", placeholder="Choose a username")
        password = st.text_input("Password", type="password", placeholder="Choose a password")
        password_confirm = st.text_input("Confirm Password", type="password")
        role = st.selectbox("I am a:", ["student", "teacher"])
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("✅ Register", type="primary", use_container_width=True):
                if not username or not password:
                    st.error("All fields required")
                elif password != password_confirm:
                    st.error("Passwords don't match")
                else:
                    users = load_users()
                    if username in users:
                        st.error("Username already exists")
                    else:
                        users[username] = {"password": password, "role": role}
                        save_users(users)
                        st.success("Registration successful! Please login.")
                        st.session_state.show_register = False
                        time.sleep(1)
                        st.rerun()
        
        with col_b:
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.show_register = False
                st.rerun()

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

def check_auth():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'show_register' not in st.session_state:
        st.session_state.show_register = False
    
    return st.session_state.logged_in