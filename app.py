import streamlit as st
import sqlite3
import pandas as pd
import time
from geopy.distance import geodesic

# --- 1. CONFIGURATION ASKUP ---
st.set_page_config(
    page_title="AskUp - Le Match du Savoir",
    page_icon="🚀",
    layout="centered"
)

# --- 2. FONCTIONS (BACKEND) ---
def init_db():
    conn = sqlite3.connect('savoir.db')
    c = conn.cursor()
    # Création table si n'existe pas
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, nom TEXT, lat REAL, lon REAL, 
                  offres TEXT, recherches TEXT, bio TEXT, job TEXT)''')
    
    # Remplissage démo (si vide)
    c.execute('SELECT count(*) FROM users')
    if c.fetchone()[0] == 0:
        users_data = [
            ("Alice", 48.8566, 2.3522, "Maths, Excel", "Piano", "J'adore les chiffres.", "Comptable"),
            ("Karim", 48.8600, 2.3500, "Piano, Guitare", "Maths", "Musicien pro.", "Musicien"),
            ("Sophie", 48.8584, 2.3600, "Anglais, Espagnol", "Code", "Teacher by day.", "Professeur"),
            ("Marc", 48.8550, 2.3400, "Python, Web", "Anglais", "Dev Fullstack.", "Développeur"),
            ("Lucie", 43.6045, 1.4442, "Cuisine", "Web", "Chef étoilée (Toulouse).", "Chef")
        ]
        c.executemany('INSERT INTO users (nom, lat, lon, offres, recherches, bio, job) VALUES (?,?,?,?,?,?,?)', users_data)
        conn.commit()
    return conn

def get_all_users_for_map(conn):
    # Récupère tout le monde pour la carte
    df = pd.read_sql_query("SELECT nom, lat, lon, offres, job FROM users", conn)
    return df

def get_matches(user_wants, user_lat, user_lon, conn):
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    potential = []
    wants_list = [x.strip().lower() for x in user_wants.split(',')]
    
    for u in c.fetchall():
        u_offres = [x.strip().lower() for x in u[4].split(',')]
        common = set(wants_list).intersection(u_offres)
        if common:
            dist = geodesic((user_lat, user_lon), (u[2], u[3])).km
            if dist < 15: 
                potential.append({
                    "id": u[0], "nom": u[1], "lat": u[2], "lon": u[3],
                    "dist": round(dist, 1), "skill": list(common)[0].upper(), 
                    "bio": u[6], "job": u[7] if len(u) > 7 else "Membre"
                })
    return potential

# --- 3. INTERFACE (FRONTEND) ---

st.markdown("""
    <style>
    .stAppHeader {display: none;}
    h1 {color: #FF4B4B; font-weight: 800;}
    .stButton>button {border-radius: 20px;}
    </style>
    """, unsafe_allow_html=True)

conn = init_db()
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'my_matches' not in st.session_state: st.session_state.my_matches = []
if 'current_index' not in st.session_state: st.session_state.current_index = 0

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.title("🚀 AskUp")
    st.image("https://api.dicebear.com/7.x/avataaars/svg?seed=Moi&backgroundColor=FF4B4B", width=80)
    st.write("**Mon Profil**")
    my_wants = st.text_input("Je veux apprendre :", "Piano")
    
    st.divider()
    if st.button("🔍 Trouver des Matchs", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
    if st.button("🗺️ Carte des Mentors", use_container_width=True):
        st.session_state.page = 'map'
        st.rerun()
    if st.button(f"💬 Messages ({len(st.session_state.my_matches)})", use_container_width=True):
        st.session_state.page = 'chat'
        st.rerun()

# --- PAGE 1: SWIPE ---
if st.session_state.page == 'home':
    st.markdown("# Découvrez vos Mentors")
    matches = get_matches(my_wants, 48.8566, 2.3522, conn)
    
    if matches and st.session_state.current_index < len(matches):
        profile = matches[st.session_state.current_index]
        
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(f"https://api.dicebear.com/7.x/avataaars/svg?seed={profile['nom']}", use_container_width=True)
            with col2:
                st.subheader(f"{profile['nom']}, {profile['job']}")
                st.caption(f"📍 À {profile['dist']} km de vous")
                st.markdown(f"**Expert en :** :red[{profile['skill']}]")
                st.info(f"{profile['bio']}")
            
            st.divider()
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("❌ Passer", use_container_width=True):
                    st.session_state.current_index += 1
                    st.rerun()
            with c2:
                if st.button("🔥 CONNECTER", type="primary", use_container_width=True):
                    st.toast(f"Match avec {profile['nom']} !", icon="🎉")
                    st.session_state.my_matches.append(profile)
                    st.session_state.current_index += 1
                    time.sleep(1)
                    st.rerun()
    elif not matches:
        st.warning("Personne ne correspond à votre recherche pour l'instant.")
    else:
        st.success("Plus de profils pour aujourd'hui !")
        if st.button("Recommencer"):
            st.session_state.current_index = 0
            st.rerun()

# --- PAGE 2: CARTE ---
elif st.session_state.page == 'map':
    st.markdown("# 🗺️ Autour de vous")
    st.markdown("Visualisez où se trouvent les compétences.")
    
    # On récupère les données et on affiche la carte
    df_users = get_all_users_for_map(conn)
    # Streamlit a besoin des colonnes 'lat' et 'lon' ou 'latitude' et 'longitude'
    st.map(df_users, zoom=12, color='#FF4B4B')
    
    st.caption("Les points rouges représentent les utilisateurs AskUp.")

# --- PAGE 3: CHAT & RENCONTRE ---
elif st.session_state.page == 'chat':
    st.markdown("# 💬 Vos Discussions")
    
    if not st.session_state.my_matches:
        st.info("Aucun match. Allez swiper !")
    
    for m in st.session_state.my_matches:
        with st.expander(f"👤 {m['nom']} ({m['skill']})", expanded=True):
            st.markdown(f"**Sujet :** Apprendre le {m['skill']}")
            
            # Simulation chat
            st.markdown(f"""
            <div style="background-color:#F0F2F6; padding:10px; border-radius:10px; margin-bottom:5px; width: fit-content;">
            👋 Salut ! Dispo pour m'apprendre le {m['skill']} ?
            </div>""", unsafe_allow_html=True)
            
            # --- FEATURE LIEU DE RENCONTRE ---
            st.markdown("---")
            st.markdown("**📍 Se rencontrer en vrai ?**")
            col_meet, col_link = st.columns([2, 1])
            with col_meet:
                st.write("Trouver un endroit sympa à mi-chemin :")
            with col_link:
                # Lien intelligent Google Maps : Cherche 'Café' autour de la position du match
                maps_url = f"https://www.google.com/maps/search/café+sympa+coworking/@{m['lat']},{m['lon']},15z"
                st.link_button("☕ Trouver un Café", maps_url)
                
