import streamlit as st
import json
from pathlib import Path
import folium
from streamlit_folium import st_folium

# Load data
DATA_FILE = Path("places.json")
TRANSLATION_FILE = Path("translations.json")
USERS_FILE = Path("users.json")

DATA = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {"places": [], "itineraries": []}
TRANSLATIONS = json.loads(TRANSLATION_FILE.read_text(encoding="utf-8")) if TRANSLATION_FILE.exists() else {}
USERS = json.loads(USERS_FILE.read_text(encoding="utf-8")) if USERS_FILE.exists() else {}

# Login
if "user" not in st.session_state:
    st.title("🔐 Nepal Tourist Guide Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.user = username
            st.success("Login successful!")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

# Language toggle
lang = st.sidebar.selectbox("🌐 Language", ["English", "Nepali"])
def t(key): return TRANSLATIONS.get(lang, {}).get(key, key)

st.set_page_config(page_title=t("Nepal Tourist Guide"), layout="wide")
st.title(t("Nepal Tourist Guide"))
st.caption(t("Discover places across districts, plan itineraries, and view maps."))

# Filters
cols = st.columns(4)
with cols[0]:
    district = st.selectbox(t("District"), ["All"] + sorted({p["district"] for p in DATA["places"]}))
with cols[1]:
    category = st.selectbox(t("Category"), ["All"] + sorted({p["category"] for p in DATA["places"]}))
with cols[2]:
    q = st.text_input(t("Search (name/tips)"))
with cols[3]:
    st.markdown(f"👤 {st.session_state.user}")

def matches(p):
    if district != "All" and p["district"] != district: return False
    if category != "All" and p["category"] != category: return False
    if q and q.lower() not in (p["name"] + " " + p.get("tips","")).lower(): return False
    return True

filtered = [p for p in DATA["places"] if matches(p)]

# Map
st.subheader(t("Map View"))
m = folium.Map(location=[27.7, 85.3], zoom_start=8)
for p in filtered:
    folium.Marker([p["lat"], p["lng"]], popup=p["name"]).add_to(m)
st_folium(m, width=700, height=400)

# Places
st.subheader(t("Places"))
for p in filtered:
    with st.expander(f'{p["name"]} — {p["district"]} ({p["category"]})'):
        st.write(p["description"])
        st.write(f'{t("Hours")}: {p["hours"]} | {t("Fees")}: {p["fees"]}')
        st.write(f'{t("Tips")}: {p.get("tips", "—")}')
        if p.get("images"):
            st.image(p["images"], width=240)
        maps_url = f'https://www.google.com/maps?q={p["lat"]},{p["lng"]}'
        st.link_button(t("Open in Google Maps"), maps_url)

# Itineraries
st.subheader(t("Itineraries"))
for it in DATA["itineraries"]:
    with st.expander(f'{it["name"]} — {it["days"]} {t("days")}'):
        for pid in it["stops"]:
            place = next((x for x in DATA["places"] if x["id"] == pid), None)
            if place:
                st.markdown(f'- {place["name"]} ({place["district"]})')

st.divider()
st.caption(t("Add data by editing places.json. You can later connect an admin UI."))