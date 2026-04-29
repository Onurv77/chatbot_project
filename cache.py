import hashlib
from datetime import datetime, timedelta
import re
import streamlit as st

defaults = {    
    "response_cache": {},  
}


CACHE_EXPIRY_HOURS = 24  

def get_cache_key(text: str) -> str:  
    cleaned = re.sub(r'[^\w\s]', '', text.lower().strip())
    return hashlib.md5(cleaned.encode()).hexdigest()

def check_cache(user_message: str) -> dict | None:    
    cache_key = get_cache_key(user_message)
    
    if cache_key in st.session_state.response_cache:
        cached = st.session_state.response_cache[cache_key]
        
        
        if CACHE_EXPIRY_HOURS > 0:
            age = datetime.now() - cached["timestamp"]
            if age > timedelta(hours=CACHE_EXPIRY_HOURS):                
                del st.session_state.response_cache[cache_key]
                return None
        
        return cached
    
    return None

def save_to_cache(user_message: str, context: str, sources: list, answer: str):    
    cache_key = get_cache_key(user_message)
    st.session_state.response_cache[cache_key] = {
        "context": context,
        "sources": sources,
        "answer": answer,
        "timestamp": datetime.now()
    }