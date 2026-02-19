import streamlit as st
import cv2
import face_recognition
import os
import sqlite3
import pandas as pd
from datetime import datetime
import warnings
from streamlit_option_menu import option_menu

# --- 0. CONFIGURATIONS ---
warnings.filterwarnings("ignore")
st.set_page_config(
    page_title="SecuriFace Pro",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GESTION DE L'ÉTAT (SESSION STATE) ---
if 'run' not in st.session_state:
    st.session_state.run = False
if 'last_log_update' not in st.session_state:
    st.session_state.last_log_update = datetime.now()

# --- 1. FONCTIONS BACKEND ---
Dossier_img = "images_"
if not os.path.exists(Dossier_img):
    os.makedirs(Dossier_img)

def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (nom TEXT, date TEXT, heure TEXT)''')
    conn.commit()
    conn.close()

def log_presence(name):
    """Retourne True si c'est une NOUVELLE entrée aujourd'hui"""
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    c.execute("SELECT * FROM logs WHERE nom=? AND date=?", (name, date_str))
    if c.fetchone() is None:
        c.execute("INSERT INTO logs VALUES (?, ?, ?)", (name, date_str, time_str))
        conn.commit()
        conn.close()
        return True 
    conn.close()
    return False 

def get_logs():
    conn = sqlite3.connect('attendance.db')
    try:
        df = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC, heure DESC", conn)
    except:
        df = pd.DataFrame(columns=['nom', 'date', 'heure'])
    conn.close()
    return df

@st.cache_resource
def load_known_faces(Dossier_img):
    known_encodings = []
    known_names = []
    if not os.path.exists(Dossier_img): return [], []
    for filename in os.listdir(Dossier_img):
        if filename.lower().endswith((".jpg", ".png", ".jpeg")):
            path = os.path.join(Dossier_img, filename)
            try:
                img = face_recognition.load_image_file(path)
                encs = face_recognition.face_encodings(img)
                if encs:
                    known_encodings.append(encs[0])
                    known_names.append(os.path.splitext(filename)[0])
            except Exception as e: pass
    return known_encodings, known_names

init_db()

# --- 2. CSS OPTIMISÉ ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #131525; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1D2038; border-right: 1px solid #2F334D; }
    .header-banner {
        background: linear-gradient(90deg, #5D5FEF 0%, #8D5FFF 100%);
        padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(93, 95, 239, 0.3); display: flex; justify-content: space-between; align-items: center;
    }
    .metric-card {
        background-color: #262B46; padding: 15px; border-radius: 12px;
        border: 1px solid #373D5C; box-shadow: 0 4px 6px rgba(0,0,0,0.2); margin-bottom: 10px;
    }
    .metric-title { color: #A0A3BD; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; margin-top: 5px; }
    .metric-icon { float: right; font-size: 1.5rem; color: #5D5FEF; background: rgba(93, 95, 239, 0.1); padding: 8px; border-radius: 8px; }
    .custom-container { background-color: #262B46; padding: 20px; border-radius: 16px; border: 1px solid #373D5C; height: 100%; }
    
    /* Bouton Stop Rouge quand actif */
    .stop-btn > button {
        background-color: #FF4B4B !important; color: white !important; border: 1px solid #FF4B4B !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. UI HELPERS ---
def card_html(title, value, icon):
    return f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """

def render_recent_table(df):
    if df.empty: return "<div style='color:#A0A3BD; text-align:center; padding:20px;'>En attente...</div>"
    table_html = "<table style='width:100%; border-collapse: collapse;'>"
    table_html += "<tr style='border-bottom: 1px solid #373D5C; color: #A0A3BD;'><th style='text-align:left; padding:10px;'>Nom</th><th style='text-align:right;'>Heure</th></tr>"
    for index, row in df.head(5).iterrows():
        table_html += f"""
        <tr style='border-bottom: 1px solid #2F334D;'>
            <td style='padding: 10px 0; font-weight: bold;'>
                <span style='background:#5D5FEF; padding:4px 8px; border-radius:50%; margin-right:8px; font-size:0.8rem'>👤</span>{row['nom']}
            </td>
            <td style='text-align:right; color:#A0A3BD;'>{row['heure']}</td>
        </tr>"""
    table_html += "</table>"
    return table_html

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("## 🛡️ SecuriFace")
    selected = option_menu(
        menu_title=None,
        options=["Tableau de Bord", "Logs & Données", "Configuration"],
        icons=["grid-1x2", "database", "sliders"],
        default_index=0,
        styles={"nav-link": {"background-color": "transparent", "color": "white"}, "nav-link-selected": {"background-color": "#5D5FEF"}}
    )
    st.markdown("---")
    known_encodings, known_names = load_known_faces(Dossier_img)
    st.success(f"🟢 {len(known_encodings)} Visages chargés")

# --- 5. LOGIQUE PRINCIPALE ---

# HEADER GLOBAL
st.markdown(f"""
<div class="header-banner">
    <div>
        <h1 style="margin:0; font-size: 1.8rem;">Tableau de Bord</h1>
    </div>
    <div style="background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; font-size: 0.9rem;">
        📅 {datetime.now().strftime('%d/%m/%Y')}
    </div>
</div>
""", unsafe_allow_html=True)

if selected == "Tableau de Bord":
    # --- ZONE DES KPI (PLACEHOLDERS) ---
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    ph_kpi1, ph_kpi2, ph_kpi3, ph_kpi4 = kpi_col1.empty(), kpi_col2.empty(), kpi_col3.empty(), kpi_col4.empty()

    def update_kpis():
        df = get_logs()
        today_str = datetime.now().strftime("%Y-%m-%d")
        total_today = len(df[df['date'] == today_str]) if not df.empty else 0
        last_person = df.iloc[0]['nom'] if (not df.empty and total_today > 0) else "---"
        
        ph_kpi1.markdown(card_html("PASSAGES AUJOURD'HUI", total_today, "👣"), unsafe_allow_html=True)
        ph_kpi2.markdown(card_html("DERNIÈRE ENTRÉE", last_person, "🕒"), unsafe_allow_html=True)
        ph_kpi3.markdown(card_html("TOTAL LOGS", len(df), "📚"), unsafe_allow_html=True)
        ph_kpi4.markdown(card_html("VISAGES ACTIFS", len(known_encodings), "👥"), unsafe_allow_html=True)
        return df

    df_current = update_kpis()
    st.write("") 

    # --- ZONE PRINCIPALE ---
    c_cam, c_data = st.columns([2, 1.2])

    with c_data:
        st.markdown('<div class="custom-container">', unsafe_allow_html=True)
        st.subheader("📋 Activité en temps réel")
        ph_table = st.empty()
        ph_table.markdown(render_recent_table(df_current), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_cam:
        st.markdown('<div class="custom-container">', unsafe_allow_html=True)
        st.subheader("📹 Surveillance Live")
        
        # --- NOUVEAU : SÉLECTEUR DE CAMÉRA ---
        # On désactive le choix si le système tourne déjà pour éviter les conflits
        disable_select = st.session_state.run
        
        col_source, col_btn = st.columns([2, 1])
        
        with col_source:
            cam_choice = st.selectbox(
                "Source Vidéo", 
                ["Webcam Intégrée (Index 0)", "Caméra Externe (Index 1)", "Caméra Externe (Index 2)", "URL RTSP / IP"],
                disabled=disable_select
            )
            
            source_index = 0
            if "Index 1" in cam_choice: source_index = 1
            elif "Index 2" in cam_choice: source_index = 2
            elif "RTSP" in cam_choice:
                rtsp_url = st.text_input("Entrez l'URL du flux (ex: rtsp://192.168.1.10...)", disabled=disable_select)
                source_index = rtsp_url if rtsp_url else 0

        with col_btn:
            st.write("") # Spacer pour aligner le bouton avec le selectbox
            st.write("") 
            if not st.session_state.run:
                if st.button("🟢 Démarrer", key="start", use_container_width=True):
                    st.session_state.run = True
                    st.session_state.source = source_index # On stocke la source choisie
                    st.rerun()
            else:
                if st.button("🔴 Arrêter", key="stop", use_container_width=True):
                    st.session_state.run = False
                    st.rerun()

        frame_placeholder = st.empty()
        st.markdown('</div>', unsafe_allow_html=True)

        # --- BOUCLE DE DÉTECTION ---
        if st.session_state.run:
            # On récupère la source stockée (soit un int 0/1, soit une string URL)
            src = st.session_state.get('source', 0)
            video_capture = cv2.VideoCapture(src)
            
            if not video_capture.isOpened():
                st.error(f"❌ Impossible d'ouvrir la caméra : {src}")
                st.session_state.run = False
            else:
                frame_count = 0
                process_every_n_frames = 4 
                face_locations = []
                face_names = []
                
                while st.session_state.run:
                    ret, frame = video_capture.read()
                    if not ret:
                        st.warning("Signal vidéo perdu ou caméra déconnectée.")
                        break

                    frame_count += 1
                    
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                    if frame_count % process_every_n_frames == 0:
                        face_locations = face_recognition.face_locations(rgb_small_frame)
                        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                        face_names = []
                        new_detection = False 

                        for face_encoding in face_encodings:
                            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
                            name = "Inconnu"
                            dists = face_recognition.face_distance(known_encodings, face_encoding)
                            if len(dists) > 0:
                                best_idx = dists.argmin()
                                if matches[best_idx]:
                                    name = known_names[best_idx]
                                    if log_presence(name):
                                        new_detection = True
                                        cv2.putText(frame, "ACCES VALIDE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                            face_names.append(name)
                        
                        if new_detection:
                            df_updated = update_kpis()
                            ph_table.markdown(render_recent_table(df_updated), unsafe_allow_html=True)

                    for (top, right, bottom, left), name in zip(face_locations, face_names):
                        top *= 4; right *= 4; bottom *= 4; left *= 4
                        color = (0, 255, 0) if name != "Inconnu" else (0, 0, 255)
                        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                        cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

                    frame_placeholder.image(frame, channels="BGR", use_container_width=True)

                video_capture.release()

elif selected == "Logs & Données":
    st.markdown('<div class="custom-container">', unsafe_allow_html=True)
    st.subheader("Historique Complet")
    df_all = get_logs()
    st.dataframe(df_all, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif selected == "Configuration":
    st.markdown('<div class="custom-container">', unsafe_allow_html=True)
    st.header("⚙️ Configuration")
    if st.button("🗑️ Reset Database"):
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()
        c.execute("DELETE FROM logs")
        conn.commit()
        conn.close()
        st.success("Reset effectué")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)