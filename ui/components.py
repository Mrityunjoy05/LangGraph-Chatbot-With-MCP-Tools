import os 
import streamlit as st
from typing import List
import secrets

def init_session_state():

    if 'messages' not in st.session_state :
        st.session_state.messages = []

    if 'thread_id_history' not in st.session_state :
        st.session_state.thread_id_history = []
        
    if 'thread_titles' not in st.session_state :
        st.session_state.thread_titles = {}


def add_message(role: str, content: str, sources: List[str] = None):
    """
    Add a message to chat history.
    
    Args:
        role: 'user' or 'assistant'
        content: Message content
        sources: Optional list of source documents
    """

    message = {'role' :role ,"content" : content }

    if sources :
        message['sources'] = sources

    st.session_state.messages.append(message)

def clear_chat_history():

    st.session_state.messages = []

def display_chat_history():

    for message in st.session_state.messages :
        with st.chat_message(message['role']):
            st.markdown(message['content'])


def thread_id_generater():
    thread_id = secrets.token_hex(16)
    return str(thread_id)

def add_thread(thread_id):
    if thread_id not in st.session_state['thread_id_history']:
        st.session_state['thread_id_history'].append(thread_id)

def reset_chat():
    thread_id = thread_id_generater()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['session_history'] = []
    # Initialize with default title for new chat
    st.session_state['thread_titles'][thread_id] = "New Chat"

# def load_thread_history(thread_id):
#     try:
#         state = chatbot.get_state({'configurable': {'thread_id': thread_id}})
#         result = state.values.get('messages', [])
#         return result
#     except Exception as e:
#         st.error(f"Error loading thread: {e}")
#         return []

# def get_chat_title(thread_id):
#     """Get title for a thread with caching"""
#     # Check if already cached
#     if thread_id in st.session_state['thread_titles']:
#         return st.session_state['thread_titles'][thread_id]
    