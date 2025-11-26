"""pages.profile

Streamlit page for viewing and editing the current user's profile.
Provides sections for user information, preferences (favorites and UI
settings), and profile visibility controls. This module communicates with
``data.user_management`` and ``data.supabase_client`` to persist changes.
"""

import streamlit as st
import json
from datetime import datetime
from data.user_management import (
    get_user_profile, 
    get_user_favorites, 
    update_user_favorites,
    update_user_preferences
)
from data.supabase_client import (
    get_offers_with_stats,
    update_user_bio,
    update_user_visibility,
    get_user_id_by_sub,
    get_user_registered_events,
    get_friend_count
)
from data.state_manager import get_user_activities
from data.auth import is_logged_in, get_user_sub, handle_logout

# Check authentication: bail out early for unauthenticated users
if not is_logged_in():
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()

# Render user info in sidebar (always visible on all pages)
from data.shared_sidebar import render_sidebar_user_info
render_sidebar_user_info()

# Page header
st.title("👤 My Profile")
st.caption("Manage your profile, preferences and settings")

st.divider()

# Load user profile
profile = get_user_profile()
if not profile:
    st.error("❌ Profile not found.")
    st.stop()

# Tabs for different sections
tab1, tab2, tab3 = st.tabs([
    "📋 Information", 
    "⚙️ Preferences", 
    "🌐 Visibility"
])

# === TAB 1: INFORMATION ===
with tab1:
    st.subheader("User Information")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Profile card with clean layout
        with st.container():
            st.markdown(f"### {profile.get('name', 'N/A')}")
            
            metadata = []
            if profile.get('email'):
                metadata.append(f"📧 {profile['email']}")
            if profile.get('created_at'):
                metadata.append(f"📅 Member since {profile['created_at'][:10]}")
            if profile.get('last_login'):
                metadata.append(f"🕐 Last login {profile['last_login'][:10]}")
            
            if metadata:
                st.caption(' • '.join(metadata))
    
    with col2:
        # Profile picture with fallback
        if profile.get('picture'):
            st.image(profile['picture'], width=120)
        else:
            name = profile.get('name', 'U')
            initials = ''.join([word[0].upper() for word in name.split()[:2]])
            st.markdown(f"""
            <div style="width: 120px; height: 120px; border-radius: 50%; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        display: flex; align-items: center; justify-content: center;
                        color: white; font-size: 40px; font-weight: bold;">
                {initials}
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Legal compliance status
    st.subheader("📋 Legal & Compliance")
    
    col1, col2 = st.columns(2)
    
    tos_accepted = profile.get('tos_accepted', False)
    privacy_accepted = profile.get('privacy_policy_accepted', False)
    tos_accepted_at = profile.get('tos_accepted_at')
    privacy_accepted_at = profile.get('privacy_policy_accepted_at')
    
    with col1:
        if tos_accepted:
            st.success("✅ Terms of Service")
            if tos_accepted_at:
                st.caption(f"Accepted: {tos_accepted_at[:10]}")
        else:
            st.warning("⚠️ Terms not accepted")
    
    with col2:
        if privacy_accepted:
            st.success("✅ Privacy Policy")
            if privacy_accepted_at:
                st.caption(f"Accepted: {privacy_accepted_at[:10]}")
        else:
            st.warning("⚠️ Privacy not accepted")
    
    st.caption("💡 These agreements are required to use the application")
    
    st.divider()
    
    # Bio editing
    st.subheader("📝 About Me")
    
    current_bio = profile.get('bio', '') or ''
    new_bio = st.text_area(
        "Biography",
        value=current_bio,
        help="Tell others about yourself",
        placeholder="Share your sports interests, goals, or anything you'd like others to know...",
        label_visibility="collapsed"
    )
    
    if st.button("💾 Save Bio", type="primary"):
        user_sub = get_user_sub()
        if update_user_bio(user_sub, new_bio):
            st.success("✅ Bio updated successfully!")
            st.rerun()
        else:
            st.error("❌ Error saving bio")

# === TAB 2: PREFERENCES ===
with tab2:
    st.subheader("🏃 Favorite Sports")
    
    try:
        sportangebote = get_offers_with_stats()
        sportarten_dict = {sport['name']: sport['href'] for sport in sportangebote}
        sportarten_options = sorted(list(sportarten_dict.keys()))
        
        # Load current favorites
        current_favorite_hrefs = get_user_favorites()
        current_favorite_names = [
            sport['name'] for sport in sportangebote 
            if sport['href'] in current_favorite_hrefs
        ]
        
        favorite_sports = st.multiselect(
            "Select your favorite activities",
            options=sportarten_options,
            default=current_favorite_names,
            help="These activities will be highlighted in your overview"
        )
        
        if current_favorite_names:
            st.caption(f"Currently {len(current_favorite_names)} favorite{'s' if len(current_favorite_names) != 1 else ''} selected")
    except Exception as e:
        st.error(f"Error loading sports: {e}")
        sportarten_dict = {}
        favorite_sports = []
    
    st.divider()
    
    # Other preferences
    st.subheader("🔔 Notifications & Appearance")
    
    # Load current preferences
    preferences_raw = profile.get('preferences', {}) or {}
    
    # Preferences may be stored as JSON string or as dict/object. Normalize
    # to a Python dictionary. If parsing fails we fall back to an empty
    # dict to avoid crashing the settings UI.
    if isinstance(preferences_raw, str):
        try:
            preferences = json.loads(preferences_raw)
        except json.JSONDecodeError:
            preferences = {}
    else:
        preferences = preferences_raw or {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        notifications = st.checkbox(
            "📧 Email notifications",
            value=preferences.get('notifications', True),
            help="Receive email notifications about your activities"
        )
    
    with col2:
        theme = st.selectbox(
            "🎨 Theme",
            options=["light", "dark", "auto"],
            index=["light", "dark", "auto"].index(preferences.get('theme', 'auto')),
            help="Choose your preferred color theme"
        )
    
    st.divider()
    
    # Save button
    if st.button("💾 Save Preferences", type="primary", use_container_width=True):
        try:
            # Map selected names back to hrefs (DB identifiers) before
            # persisting favorites.
            favorite_hrefs = [
                sportarten_dict[sport] 
                for sport in favorite_sports 
                if sport in sportarten_dict
            ]
            
            if update_user_favorites(favorite_hrefs):
                # Persist other preferences as a simple dict
                new_preferences = {
                    'notifications': notifications,
                    'theme': theme
                }
                update_user_preferences(new_preferences)
                st.success("✅ Preferences saved successfully!")
                st.rerun()
            else:
                st.error("❌ Error saving favorites")
        except Exception as e:
            # Surface a readable error to the user but avoid crashing.
            st.error(f"❌ Error: {e}")

# === TAB 3: VISIBILITY ===
with tab3:
    st.subheader("🌐 Profile Visibility")
    
    st.info("🔍 Control who can see your profile and connect with you")
    
    current_is_public = profile.get('is_public', False)
    
    is_public = st.toggle(
        "Make profile public",
        value=current_is_public,
        help="Allow other users to see your profile on the Athletes page"
    )
    
    if is_public:
        st.success("✅ Your profile is **public**")
        st.caption("Other users can find you, send friend requests, and see when you attend courses")
    else:
        st.warning("🔒 Your profile is **private**")
        st.caption("Only you can see your profile and activity")
    
    if st.button("💾 Save Visibility", type="primary"):
        user_sub = get_user_sub()
        if update_user_visibility(user_sub, is_public):
            st.success("✅ Visibility settings updated!")
            st.rerun()
        else:
            st.error("❌ Error updating visibility")
    
    st.divider()
    
    # Social statistics
    st.subheader("👥 Social Statistics")
    
    try:
        user_sub = get_user_sub()
        user_id = get_user_id_by_sub(user_sub)
        
        if user_id:
            friend_count = get_friend_count(user_id)
            event_count = len(get_user_registered_events(user_id))
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Friends", friend_count)
            
            with col2:
                st.metric("Registered", event_count)
            
            with col3:
                st.metric("Visibility", "Public" if current_is_public else "Private")
            
            if friend_count > 0 or event_count > 0:
                st.caption(f"💡 You're connected with {friend_count} athlete{'s' if friend_count != 1 else ''} and registered for {event_count} course{'s' if event_count != 1 else ''}")
    except Exception:
        pass
    
    st.divider()
    
    # Logout section
    st.subheader("🚪 Logout")
    st.caption("Sign out of your account")
    
    if st.button("🚪 Logout", type="primary", use_container_width=True):
        handle_logout()

