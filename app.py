import streamlit as st
import pandas as pd
import googlemaps
from datetime import datetime
import numpy as np

# --- CONFIGURAZIONE INIZIALE ---
st.set_page_config(page_title="Cieb - Analisi Consegne Vettori", layout="wide")

# --- DATI FISSI ---
PUNTI_PARTENZA_VETTORI = {
    "LINE": "BRESCIA", "DAM1": "BRESCIA", "NEX4": "BRESCIA", "NEX8": "BRESCIA",
    "MBE": "BRESCIA", "NEX3": "BRESCIA", "NEX6": "BRESCIA", "PAP2": "BRESCIA",
    "PEZZ": "BRESCIA", "NEX2": "BRESCIA", "DAM2": "BRESCIA", "NEX9": "BRESCIA",
    "PEZZ2": "ARTOGNE",  # MODIFICATO: Nuovo punto di partenza per PEZ2
    "NEX5": "BRESCIA", "PAPA": "BRESCIA", "LIN2": "BRESCIA",
    "NEX1": "BRESCIA", "PAP3": "BRESCIA", "NEX7": "BRESCIA",
    "CTM1": "CALDERARA DI RENO", "CTM2": "CALDERARA DI RENO", "CTM3": "CALDERARA DI RENO",
    "CTM4": "CALDERARA DI RENO", "CTM5": "CALDERARA DI RENO", "CTM6": "CALDERARA DI RENO",
    "TNT": "TRENTO"
}
INDIRIZZO_PARTENZA_CIEB = "Cieb S.p.A., Via Giovanni Battista Cacciamali, 62, 25125 Brescia BS, Italia"

# --- LOGICA DI AUTENTICAZIONE ---
def check_password():
    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except: return True
    if st.session_state.get("password_correct", False): return True
    password = st.text_input("Inserisci la password per accedere", type="password")
    if password == correct_password:
        st.session_state["password_correct"] = True
        st.rerun()
        return True
    elif password: st.error("Password errata.")
    return False

# --- UI DELLA SIDEBAR ---
st.sidebar.image("logo_cieb.png", use_container_width=True)
st.sidebar.markdown("---")

# --- APPLICAZIONE PRINCIPALE ---
if check_password():
    try:
        gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
    except Exception as e:
        st.error(f"Errore nella configurazione della chiave API: {e}")
        st.stop()

    # --- FUNZIONI CORE ---
    @st.cache_data
    def carica_dati(file_caricato):
        try: return pd.read_excel(file_caricato)
        except Exception as e: st.error(f"Errore lettura Excel: {e}"); return None

    def calcola_percorso_ottimizzato(_gmaps_client, indirizzi, origine, destinazione):
        if not indirizzi: return 0, 0, [], None
        try:
            res = _gmaps_client.directions(origin=origine, destination=destinazione, waypoints=indirizzi, optimize_waypoints=True, mode="driving", departure_time=datetime.now())
            if not res: st.warning("Google Maps non ha restituito un risultato."); return 0, 0, [], None
            dist_km = sum(leg['distance']['value'] for leg in res[0]['legs']) / 1000
            tempo_min = sum(leg['duration']['value'] for leg in res[0]['legs']) / 60
            ordine = [indirizzi[i] for i in res[0]['waypoint_order']]
            return round(dist_km, 2), round(tempo_min), ordine, res
        except Exception as e: st.error(f"Errore API Google Maps: {e}"); return 0, 0, [], None

    def estrai_coordinate_per_mappa(res):
        punti = []
        if not res: return pd.DataFrame()
        partenza = res[0]['legs'][0]['start_location']
        punti.append({'lat': partenza['lat'], 'lon': partenza['lng']})
        for leg in res[0]['legs']: punti.append({'lat': leg['end_location']['lat'], 'lon': leg['end_location']['lng']})
        return pd.DataFrame(punti)

    # --- UI PRINCIPALE ---
    st.title("🚚 Dashboard Analisi Conseg