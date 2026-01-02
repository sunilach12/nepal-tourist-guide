import streamlit as st
import json
from pathlib import Path
import folium
from streamlit_folium import st_folium
from authlib.integrations.requests_client import OAuth2Session

# ------------------ 1. PAGE CONFIG ------------------
st.set_page_config(page_title="Nepal Tourist Guide", layout="wide")

# ------------------ GOOGLE OAUTH CONFIG ------------------
CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = "https://nepal-tourist-guide.streamlit.app"  # replace with your deployed URL

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

# ------------------ LOGIN FLOW ------------------
if "user_info" not in st.session_state:
    st.session_state.user_info = None

code = st.query_params.get("code")

# --- Decide login state ---
if st.session_state.user_info:
    user_info = st.session_state.user_info

elif code:
    try:
        token = fetch_token(code)
        user_info = get_userinfo(token)
        st.session_state.user_info = user_info
        st.query_params.clear()
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Login error: {e}")
        st.query_params.clear()

else:
    # ------------------ LOGIN PAGE ------------------
    st.title("Nepal Tourist Guide")
    st.write("Please log in to continue.")

    # --- Username/Password Login ---
    st.subheader("Login with Username/Password")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        # Example credentials
        valid_users = {"admin": "1234", "guest": "guest"}  # replace with your users
        if username in valid_users and valid_users[username] == password:
            st.session_state.user_info = {"name": username}
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

    st.markdown("---")

    # --- Google Login ---
    st.subheader("Or login with Google")
    login_url = get_authorization_url()
    st.markdown(
        f'<a href="{login_url}" style="display: inline-flex; align-items: center; text-decoration: none; background-color: #4285F4; color: white; padding: 8px 12px; border-radius: 4px;">'
        f'<img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" width="20" style="margin-right:8px;"> Login with Google</a>',
        unsafe_allow_html=True
    )
    st.stop()

# ------------------ LOGOUT BUTTON ------------------
st.sidebar.markdown(f"👤 **{user_info['name']}**")
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state.user_info = None
    st.experimental_rerun()

# ------------------ APP CONTENT ------------------
st.success(f"Welcome, {user_info['name']}!")

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

# ------------------ FILTERS ------------------
col1, col2, col3 = st.columns(3)

with col1:
    district = st.selectbox(
        t("District"),
        ["All"] + sorted({p["district"] for p in DATA["places"]})
    )

with col2:
    category = st.selectbox(
        t("Category"),
        ["All"] + sorted({p["category"] for p in DATA["places"]})
    )

with col3:
    search = st.text_input(t("Search"))

def matches(p):
    if district != "All" and p["district"] != district:
        return False
    if category != "All" and p["category"] != category:
        return False
    if search and search.lower() not in (p["name"] + " " + p.get("tips", "")).lower():
        return False
    return True

filtered_places = [p for p in DATA["places"] if matches(p)]

# ------------------ MAP ------------------
st.subheader(t("Map View"))
m = folium.Map(location=[27.7, 85.3], zoom_start=7)

for p in filtered_places:
    folium.Marker([p["lat"], p["lng"]], popup=p["name"]).add_to(m)

st_folium(m, width=800, height=450)

# ------------------ PLACES ------------------
st.subheader(t("Places"))

for p in filtered_places:
    with st.expander(f'{p["name"]} — {p["district"]} ({p["category"]})'):
        st.write(p["description"])
        st.write(f'🕒 {t("Hours")}: {p["hours"]}')
        st.write(f'💰 {t("Fees")}: {p["fees"]}')
        st.write(f'💡 {t("Tips")}: {p.get("tips", "—")}')
        if p.get("images"):
            st.image(p["images"], width=300)
        maps_url = f'https://www.google.com/maps?q={p["lat"]},{p["lng"]}'
        st.markdown(f"[{t('Open in Google Maps')}]({maps_url})")

# ------------------ ITINERARIES ------------------
st.subheader(t("Itineraries"))

for it in DATA["itineraries"]:
    with st.expander(f'{it["name"]} — {it["days"]} {t("days")}'):
        for pid in it["stops"]:
            place = next((x for x in DATA["places"] if x["id"] == pid), None)
            if place:
                st.markdown(f"- {place['name']} ({place['district']})")

st.divider()
st.caption(t("Edit places.json to add more data."))
