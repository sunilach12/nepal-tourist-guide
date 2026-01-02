import streamlit as st
import json
from pathlib import Path
import folium
from streamlit_folium import st_folium
import os
from streamlit_authenticator import Authenticate

# ------------------ GOOGLE OAUTH LOGIN ------------------
GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]

config = {
    "client_id": GOOGLE_CLIENT_ID,
    "client_secret": GOOGLE_CLIENT_SECRET,
    "redirect_uri": "https://YOUR-APP-NAME.streamlit.app",  # replace with your deployed app URL
    "scope": ["openid", "email", "profile"]
}

authenticator = Authenticate(
    config=config,
    cookie_name="nepal_tourist_guide_auth",
    cookie_expiry_days=1
)

name, auth_status, user = authenticator.login("Login with Google", "main", oauth2=True)

if auth_status:
    st.success(f"Welcome, {name}!")

elif auth_status is False:
    st.error("Login failed. Try again.")
    st.stop()
else:
    st.info("Please login to continue.")
    st.stop()

# ------------------ LOAD DATA ------------------
DATA_FILE = Path("places.json")
TRANSLATION_FILE = Path("translations.json")
USERS_FILE = Path("users.json")  # optional backup login

def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default

DATA = load_json(DATA_FILE, {"places": [], "itineraries": []})
TRANSLATIONS = load_json(TRANSLATION_FILE, {"English": {}, "Nepali": {}})
USERS = load_json(USERS_FILE, {})

# ------------------ LANGUAGE ------------------
lang = st.sidebar.selectbox("🌐 Language", ["English", "Nepali"])
def t(key):
    return TRANSLATIONS.get(lang, {}).get(key, key)

st.set_page_config(page_title=t("Nepal Tourist Guide"), layout="wide")
st.title(t("Nepal Tourist Guide"))
st.caption(t("Discover places across districts, plan itineraries, and view maps."))
st.sidebar.markdown(f"👤 **{name}**")

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
        st.link_button(t("Open in Google Maps"), maps_url)

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
