"""
Security utilities for input validation and data protection
"""

import re
import html
from typing import Any, Optional
import streamlit as st


def sanitize_html(text: str) -> str:
    """Escape HTML to prevent XSS attacks"""
    if not text:
        return ""
    return html.escape(text)


def validate_rating(rating: Any) -> bool:
    """Validate rating is between 1 and 5"""
    try:
        rating_int = int(rating)
        return 1 <= rating_int <= 5
    except (ValueError, TypeError):
        return False


def validate_comment(text: str, max_length: int = 2000) -> tuple[bool, Optional[str]]:
    """
    Validate comment text
    Returns: (is_valid, error_message)
    """
    if not text:
        return True, None
    
    # Check length
    if len(text) > max_length:
        return False, f"Comment exceeds maximum length of {max_length} characters"
    
    # Check for potentially malicious content
    dangerous_patterns = [
        r'<script',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'onerror=',  # Event handlers
        r'onload=',  # Event handlers
        r'<iframe',  # Iframes
        r'eval\('  # Eval function
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Comment contains potentially dangerous content"
    
    return True, None


def secure_log(level: str, message: str, details: dict = None):
    """
    Securely log events without exposing sensitive data
    """
    # Don't log sensitive information
    sensitive_fields = ['password', 'token', 'secret', 'key', 'cookie']
    
    if details:
        safe_details = {}
        for key, value in details.items():
            key_lower = str(key).lower()
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                safe_details[key] = "[REDACTED]"
            else:
                safe_details[key] = value
    else:
        safe_details = {}
    
    # In production, this should go to a proper logging system
    # For now, just keep it simple
    if "security_log" not in st.session_state:
        st.session_state["security_log"] = []
    
    log_entry = {
        "level": level,
        "message": message,
        "details": safe_details,
        "timestamp": str(st.runtime.get_instance()._main_script_path)
    }
    
    st.session_state["security_log"].append(log_entry)
    
    # Keep only last 50 logs
    if len(st.session_state["security_log"]) > 50:
        st.session_state["security_log"] = st.session_state["security_log"][-50:]


def rate_limit_check(action: str, user_identifier: str, max_actions: int = 10, time_window: int = 60) -> bool:
    """
    Simple rate limiting
    Returns True if action is allowed, False if rate limit exceeded
    """
    import time
    
    rate_limit_key = f"rate_limit_{action}_{user_identifier}"
    current_time = time.time()
    
    if rate_limit_key not in st.session_state:
        st.session_state[rate_limit_key] = {
            "actions": [],
            "last_reset": current_time
        }
    
    rate_limit_data = st.session_state[rate_limit_key]
    
    # Reset if time window has passed
    if current_time - rate_limit_data["last_reset"] > time_window:
        rate_limit_data["actions"] = []
        rate_limit_data["last_reset"] = current_time
    
    # Check if limit exceeded
    if len(rate_limit_data["actions"]) >= max_actions:
        secure_log("WARNING", f"Rate limit exceeded for action: {action}", {"user": user_identifier})
        return False
    
    # Record action
    rate_limit_data["actions"].append(current_time)
    return True

