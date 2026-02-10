import streamlit as st

from ui.components import (
    init_session_state , 
    add_message , 
    clear_chat_history , 
    thread_id_generater ,
    add_thread,
    reset_chat)


init_session_state()


# Initialize thread_id first
if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = thread_id_generater()

# Add current thread to history
add_thread(st.session_state['thread_id'])
