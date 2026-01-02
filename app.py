import streamlit as st
import json
from pathlib import Path
import folium
from streamlit_folium import st_folium
from authlib.integrations.requests_client import OAuth2Session

# ------------------ 1. PAGE CONFIG MUST BE FIRST ------------------
st.set_page_config(page_title="Nepal Tourist Guide", layout="wide")

# ------------------ GOOGLE OAUTH CONFIG ------------------
CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
# Ensure this matches exactly what is in Google Cloud Console
REDIRECT_URI = "https://nepal-tourist-guide-xyz123.streamlit.app" 

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

# ------------------ LOGIN FLOW (CORRECTED) ------------------

# 1. Initialize session state for user info
if "user_info" not in st.session_state:
    st.session_state.user_info = None

# 2. Check for auth code in URL (works with newer Streamlit versions)
code = st.query_params.get("code")

# 3. Decision Logic
if st.session_state.user_info:
    # Case A: Already logged in
    user_info = st.session_state.user_info

elif code:
    # Case B: Returning from Google with a code
    try:
        token = fetch_token(code)
        user_info = get_userinfo(token)
        
        # Save to session state so we stay logged in
        st.session_state.user_info = user_info
        
        # CRITICAL: Clear the code from URL and rerun to prevent the error
        st.query_params.clear()
        st.rerun()
        
    except Exception as e:
        # If the code was invalid (e.g. refresh), clear it and show login again
        st.error(f"Login error: {e}")
        st.query_params.clear()
        # Optional: st.stop() or let it fall through to login button

else:
    # Case C: Not logged in, no code -> Show Login Button
    # Stop execution here so the rest of the app doesn't load
    login_url = get_authorization_url()
    st.title("Nepal Tourist Guide")
    st.write("Please log in to continue.")
    st.link_button("Login with Google", login_url)
    st.stop()

# ------------------ APP CONTENT (Only runs if logged in) ------------------

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
st.sidebar.markdown(f"👤 **{user_info['name']}**")

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
