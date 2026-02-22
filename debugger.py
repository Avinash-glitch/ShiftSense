import streamlit as st
from datetime import datetime

def get_debug_logs():
    """Get or initialize debug logs in session state"""
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    return st.session_state.debug_logs

def log_debug(message, level="INFO"):
    """
    Log a message to the debug console
    
    Args:
        message (str): The message to log
        level (str): Log level - "INFO", "ERROR", "WARNING", "SUCCESS"
    
    Usage:
        from debug_logger import log_debug
        log_debug("Something happened!", level="SUCCESS")
    """
    logs = get_debug_logs()
    
    prefix = {
        "INFO": "ℹ️",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "SUCCESS": "✅",
        "DEBUG": "🔍"
    }.get(level, "📝")
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {prefix} {message}"
    
    logs.append(log_msg)
    print(log_msg)  # Also print to console

def clear_logs():
    """Clear all debug logs"""
    if 'debug_logs' in st.session_state:
        st.session_state.debug_logs = []

def get_all_logs():
    """Get all logs as a single string"""
    logs = get_debug_logs()
    return "\n".join(logs[-100:])  # Last 100 logs

# Aliases for common operations
def log_error(message):
    """Log an error message"""
    log_debug(message, level="ERROR")

def log_success(message):
    """Log a success message"""
    log_debug(message, level="SUCCESS")

def log_warning(message):
    """Log a warning message"""
    log_debug(message, level="WARNING")

def log_info(message):
    """Log an info message"""
    log_debug(message, level="INFO")