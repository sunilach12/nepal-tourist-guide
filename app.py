import streamlit as st
import json
from pathlib import Path
import folium
from streamlit_folium import st_folium
from authlib.integrations.requests_client import OAuth2Session

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Nepal Tourist Guide", layout="wide")

# ------------------ GOOGLE OAUTH CONFIG ------------------
CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = "https://YOUR-APP-NAME.streamlit.app"  # Replace with your app URL

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

def get_authorization_url():
    client = OAuth2Session(CLIENT_ID, CLIENT_SECRET, scope="openid email profile", redirect_uri=REDIRECT_URI)
    uri, state = client.create_authorization_url(AUTHORIZATION_ENDPOINT)
    st.session_state['oauth_state'] = state
    return uri

def fetch_token(code):
    client = OAuth2Session(CLIENT_ID, CLIENT_SECRET, redirect_uri=REDIRECT_URI, state=st.session_state.get('oauth_state'))
    token = client.fetch_token(TOKEN_ENDPOINT, code=code)
    return token

def get_userinfo(token):
    client = OAuth2Session(CLIENT_ID, CLIENT_SECRET, token=token)
    resp = client.get(USERINFO_ENDPOINT)
    return resp.json()

# ------------------ SESSION STATE ------------------
if "users_db" not in st.session_state:
    st.session_state.users_db = {"admin": "Admin1234"}  # default user
if "user_info" not in st.session_state:
    st.session_state.user_info = None

# ------------------ CHECK GOOGLE CODE ------------------
code = st.experimental_get_query_params().get("code")
if code:
    try:
        token = fetch_token(code[0])
        user_info = get_userinfo(token)
        st.session_state.user_info = user_info  # save to session
        st.experimental_set_query_params()  # clear code from URL
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Google login failed: {e}")

# ------------------ SHOW LOGIN / SIGNUP IF NOT LOGGED IN ------------------
if not st.session_state.user_info:
    st.title("Nepal Tourist Guide")
    st.write("Please log in to continue.")

    # Tabs for Login / Signup
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    # -------- LOGIN TAB --------
    with login_tab:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if username in st.session_state.users_db and st.session_state.users_db[username] == password:
                st.session_state.user_info = {"name": username}
                st.success(f"Welcome, {username}!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

        st.markdown("---")
        # -------- GOOGLE LOGIN BUTTON --------
        login_url = get_authorization_url()
        st.markdown(f"[Login with Google]( {login_url} )")

    # -------- SIGNUP TAB --------
    with signup_tab:
        st.markdown("""
**Signup Rules:**  
- Username must be lowercase letters only  
- Maximum 15 characters  
- Password must include at least one number  
- Confirm password must match
""")
        new_user = st.text_input("Choose Username", key="signup_user")
        new_pass = st.text_input("Choose Password", type="password", key="signup_pass")
        confirm_pass = st.text_input("Confirm Password", type="password", key="signup_confirm")

        if st.button("Sign Up"):
            if not new_user.islower():
                st.error("Username must be lowercase letters only")
            elif len(new_user) > 15:
                st.error("Username cannot exceed 15 characters")
            elif any(char.isdigit() for char in new_user):
                st.error("Username cannot contain numbers")
            elif len(new_pass) < 6:
                st.error("Password must be at least 6 characters")
            elif not any(char.isdigit() for char in new_pass):
                st.error("Password must contain at least one number")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match")
            elif new_user in st.session_state.users_db:
                st.error("Username already exists")
            else:
                st.session_state.users_db[new_user] = new_pass
                st.success("Account created! Switch to Login to continue.")
                # Clear signup fields
                st.session_state.signup_user = ""
                st.session_state.signup_pass = ""
                st.session_state.signup_confirm = ""

    st.stop()  # Stop app execution until user logs in

# ------------------ MAIN APP ------------------
user_info = st.session_state.user_info
st.sidebar.markdown(f"👤 **{user_info['name']}**")
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state.user_info = None
    st.experimental_rerun()

st.title(f"Welcome, {user_info['name']}!")
st.caption("Discover places across districts, plan itineraries, and view maps.")

# ------------------ LOAD DATA ------------------
DATA_FILE = Path("places.json")
TRANSLATION_FILE = Path("translations.json")

def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default

DATA = load_json(DATA_FILE, {"places": [], "itineraries": []})
TRANSLATIONS = load_json(TRANSLATION_FILE, {"English": {}, "Nepali": {}})

# ------------------ LANGUAGE ------------------
lang = st.sidebar.selectbox("🌐 Language", ["English", "Nepali"])
def t(key):
    return TRANSLATIONS.get(lang, {}).get(key, key)

st.title(t("Nepal Tourist Guide"))
st.caption(t("Discover places across districts, plan itineraries, and view maps."))
