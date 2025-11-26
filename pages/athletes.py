"""pages.athletes

Streamlit page that displays public athlete profiles, friend requests,
and the current user's friends. This module renders a tabbed interface
with three main sections: discovery of public profiles, handling incoming
friend requests, and listing the user's friends.

Docstring style: Google-style for public functions in this module.
"""

import streamlit as st
from data.auth import is_logged_in
from data.supabase_client import (
    get_user_id_by_sub,
    get_public_users,
    get_friend_status,
    send_friend_request,
    accept_friend_request,
    reject_friend_request,
    unfollow_user,
    get_pending_friend_requests,
    get_user_friends,
    get_supabase_client,
    get_user_by_id
)

def get_user_id(user_sub=None):
    """Resolve the numeric user id for the currently authenticated user.

    If `user_sub` (the authentication subject) is not provided this helper
    will attempt to obtain it from the authentication layer. If the user
    record is missing in the Supabase database the function will try to
    synchronize the authenticated user into Supabase and retry once.

    Args:
        user_sub (str | None): Optional authentication subject (sub).

    Returns:
        int | None: The database `user.id` for the given subject or ``None``
            when no authenticated user could be resolved.

    Notes:
        - This helper intentionally swallows sync errors and returns ``None``
          on failure so callers can display a user-friendly message.
    """
    from data.auth import get_user_sub as auth_get_user_sub, sync_user_to_supabase

    if not user_sub:
        user_sub = auth_get_user_sub()
        if not user_sub:
            return None

    # Try to get existing user from DB
    user_id = get_user_id_by_sub(user_sub)

    # If user doesn't exist in the DB, attempt to sync the authenticated
    # identity into Supabase and re-read the id. Failures are non-fatal.
    if not user_id:
        try:
            sync_user_to_supabase()
            user_id = get_user_id_by_sub(user_sub)
        except:
            # TODO: Optionally log the exception to an application logger.
            pass

    return user_id

def render_athletes_page():
    """Render the Athletes Streamlit page.

    This function implements the full UI for the athletes page. It checks
    authentication, renders a sidebar with user info, and shows three tabs:
    - Discover Athletes: list public profiles and allow sending friend
      requests.
    - Friend Requests: accept or reject incoming requests.
    - My Friends: list current friends with an option to unfriend.

    The UI text is intentionally localized (German) to match the rest of the
    application.
    """

    # Check authentication and stop rendering if user is not logged in
    if not is_logged_in():
        st.error("❌ Bitte melden Sie sich an, um Athletes zu finden.")
        st.stop()

    # Render user info in sidebar (always visible on all pages)
    from data.shared_sidebar import render_sidebar_user_info
    render_sidebar_user_info()

    try:
        current_user_id = get_user_id()
        if not current_user_id:
            # Informational guidance for users when their auth identity is
            # not yet synchronized to Supabase.
            st.error("❌ Fehler beim Laden Ihres Profiles. Ihr Benutzer wurde nicht in der Datenbank gefunden.")
            st.info("💡 Versuchen Sie, sich abzumelden und erneut anzumelden.")
            st.stop()
    except Exception as e:
        # Present a user-friendly error message while avoiding raising
        # unexpected exceptions from the UI layer.
        st.error(f"❌ Fehler beim Laden Ihres Profiles: {str(e)}")
        st.stop()

    # Page header
    st.title("👥 Athletes & Friends")
    st.caption("Connect with other athletes and build your sports community")

    st.divider()

    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["🔍 Discover Athletes", "📩 Friend Requests", "👥 My Friends"])

    with tab1:
        st.subheader("Discover Public Profiles")

        with st.spinner('🔄 Loading athletes...'):
            public_users = get_public_users()

        if not public_users:
            st.info("📭 No public profiles available yet.")
            st.caption("Be the first to make your profile public in Settings!")
            return

        # Filter out own profile
        public_users = [u for u in public_users if u['id'] != current_user_id]

        if not public_users:
            st.info("📭 No other public profiles available yet.")
            st.caption("Check back later as more athletes join the community!")
            return

        # Display count
        st.caption(f"**{len(public_users)}** athlete{'s' if len(public_users) != 1 else ''} found")

        # Display users in modern card layout
        for user in public_users:
            with st.container():
                col_pic, col_info, col_action = st.columns([1, 4, 2])

                with col_pic:
                    if user.get('picture'):
                        st.image(user['picture'], width=100)
                    else:
                        # Placeholder with initials
                        name = user.get('name', 'U')
                        initials = ''.join([word[0].upper() for word in name.split()[:2]])
                        st.markdown(f"""
                        <div style="width: 100px; height: 100px; border-radius: 50%; 
                                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                    display: flex; align-items: center; justify-content: center;
                                    color: white; font-size: 32px; font-weight: bold;">
                            {initials}
                        </div>
                        """, unsafe_allow_html=True)

                with col_info:
                    st.markdown(f"### {user.get('name', 'Unknown')}")

                    # Bio preview
                    if user.get('bio'):
                        bio = user['bio']
                        preview = bio[:120] + "..." if len(bio) > 120 else bio
                        st.caption(preview)

                    # Metadata
                    metadata = []
                    if user.get('email'):
                        metadata.append(f"📧 {user['email']}")
                    if user.get('created_at'):
                        join_date = user['created_at'][:10]
                        metadata.append(f"📅 Joined {join_date}")

                    if metadata:
                        st.caption(' • '.join(metadata))

                with col_action:
                    st.write("")  # Spacing
                    status = get_friend_status(current_user_id, user['id'])

                    # Render actions depending on friendship status
                    if status == "friends":
                        st.success("✓ Friends")
                        if st.button("🗑️ Unfriend", key=f"unfollow_{user['id']}", use_container_width=True):
                            if unfollow_user(current_user_id, user['id']):
                                st.success("✅ Unfriended")
                                st.rerun()

                    elif status == "request_sent":
                        st.info("⏳ Pending")

                    elif status == "request_received":
                        # Request received means the current user can accept/reject
                        st.warning("📨 Respond")

                    else:
                        if st.button("➕ Add Friend", key=f"request_{user['id']}",
                                     use_container_width=True, type="primary"):
                            if send_friend_request(current_user_id, user['id']):
                                st.success("✅ Request sent!")
                                st.rerun()
                            else:
                                st.warning("Request already pending")

                st.divider()

    with tab2:
        st.subheader("Friend Requests")

        with st.spinner('🔄 Loading requests...'):
            requests = get_pending_friend_requests(current_user_id)

        if not requests:
            st.info("📭 No pending friend requests.")
            st.caption("You'll see requests here when other athletes want to connect with you.")
        else:
            st.caption(f"**{len(requests)}** pending request{'s' if len(requests) != 1 else ''}")

            for req in requests:
                with st.container():
                    # Extract requester info
                    requester = req.get('requester', {})
                    if isinstance(requester, dict) and len(requester) > 0:
                        requester_name = requester.get('name', 'Unknown')
                        requester_picture = requester.get('picture')
                        requester_email = requester.get('email', '')
                    else:
                        # Fallback: query user separately
                        try:
                            requester_data = get_user_by_id(req['requester_id'])
                            if requester_data:
                                requester_name = requester_data.get('name', 'Unknown')
                                requester_picture = requester_data.get('picture')
                                requester_email = requester_data.get('email', '')
                            else:
                                requester_name = "Unknown"
                                requester_picture = None
                                requester_email = ""
                        except:
                            requester_name = "Unknown"
                            requester_picture = None
                            requester_email = ""

                    col_pic, col_info, col_action = st.columns([1, 4, 2])

                    with col_pic:
                        if requester_picture:
                            st.image(requester_picture, width=80)
                        else:
                            initials = ''.join([word[0].upper() for word in requester_name.split()[:2]])
                            st.markdown(f"""
                            <div style="width: 80px; height: 80px; border-radius: 50%; 
                                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                        display: flex; align-items: center; justify-content: center;
                                        color: white; font-size: 28px; font-weight: bold;">
                                {initials}
                            </div>
                            """, unsafe_allow_html=True)

                    with col_info:
                        st.markdown(f"### {requester_name}")

                        metadata = []
                        if requester_email:
                            metadata.append(f"📧 {requester_email}")
                        if req.get('created_at'):
                            request_date = req['created_at'][:10]
                            metadata.append(f"📅 Requested {request_date}")

                        if metadata:
                            st.caption(' • '.join(metadata))

                    with col_action:
                        st.write("")  # Spacing

                        if st.button("✅ Accept", key=f"accept_{req['id']}",
                                     use_container_width=True, type="primary"):
                            if accept_friend_request(req['id'], req['requester_id'], req['addressee_id']):
                                st.success("✅ Friend request accepted!")
                                st.rerun()

                        if st.button("❌ Decline", key=f"reject_{req['id']}",
                                     use_container_width=True):
                            if reject_friend_request(req['id']):
                                st.success("Request declined")
                                st.rerun()

                    st.divider()

    with tab3:
        st.subheader("My Friends")

        with st.spinner('🔄 Loading friends...'):
            friends = get_user_friends(current_user_id)

        if not friends:
            st.info("👋 No friends yet - start connecting with other athletes!")
            st.caption("Browse the Discover Athletes tab to send friend requests.")
        else:
            # Remove duplicates by tracking unique IDs
            seen_ids = set()
            unique_friends = []
            for friend in friends:
                friend_id = friend.get('id')
                if friend_id and friend_id not in seen_ids:
                    seen_ids.add(friend_id)
                    unique_friends.append(friend)

            st.caption(f"**{len(unique_friends)}** friend{'s' if len(unique_friends) != 1 else ''}")

            for friend in unique_friends:
                with st.container():
                    col_pic, col_info = st.columns([1, 5])

                    with col_pic:
                        if friend.get('picture'):
                            st.image(friend['picture'], width=80)
                        else:
                            name = friend.get('name', 'U')
                            initials = ''.join([word[0].upper() for word in name.split()[:2]])
                            st.markdown(f"""
                            <div style="width: 80px; height: 80px; border-radius: 50%; 
                                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                        display: flex; align-items: center; justify-content: center;
                                        color: white; font-size: 28px; font-weight: bold;">
                                {initials}
                            </div>
                            """, unsafe_allow_html=True)

                    with col_info:
                        st.markdown(f"### {friend.get('name', 'Unknown')}")

                        metadata = []
                        if friend.get('email'):
                            metadata.append(f"📧 {friend['email']}")
                        if friend.get('bio'):
                            bio_preview = friend['bio'][:80] + "..." if len(friend['bio']) > 80 else friend['bio']
                            metadata.append(bio_preview)

                        if metadata:
                            st.caption(' • '.join(metadata))

                    st.divider()

# Main execution
if __name__ == "__main__" or not st.session_state.get('_is_main'):
    render_athletes_page()

