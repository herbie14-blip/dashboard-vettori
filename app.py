import streamlit as st
import pandas as pd
import googlemaps
from datetime import datetime
import numpy as np

# --- CONFIGURAZIONE INIZIALE ---
st.set_page_config(page_title="Cieb - Analisi Consegne Vettori", layout="wide")

# --- DATI FISSI ---
# Rubrica interna per i punti di partenza e arrivo dei vettori
PUNTI_PARTENZA_VETTORI = {
    "LINE": "BRESCIA", "DAM1": "BRESCIA", "NEX4": "BRESCIA", "NEX8": "BRESCIA",
    "MBE": "BRESCIA", "NEX3": "BRESCIA", "NEX6": "BRESCIA", "PAP2": "BRESCIA",
    "PEZZ": "BRESCIA", "NEX2": "BRESCIA", "DAM2": "BRESCIA", "NEX9": "BRESCIA",
    "PEZZ2": "BRESCIA", "NEX5": "BRESCIA", "PAPA": "BRESCIA", "LIN2": "BRESCIA",
    "NEX1": "BRESCIA", "PAP3": "BRESCIA", "NEX7": "BRESCIA",
    "CTM1": "CALDERARA DI RENO", "CTM2": "CALDERARA DI RENO", "CTM3": "CALDERARA DI RENO",
    "CTM4": "CALDERARA DI RENO", "CTM5": "CALDERARA DI RENO", "CTM6": "CALDERARA DI RENO",
    "TNT": "TRENTO"
}
# Indirizzo specifico per Cieb a Brescia
INDIRIZZO_PARTENZA_CIEB = "Cieb S.p.A., Via Giovanni Battista Cacciamali, 62, 25125 Brescia BS, Italia"


# --- LOGICA DI AUTENTICAZIONE ---
def check_password():
    """Restituisce True se l'utente ha inserito la password corretta."""
    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except:
        # Se la password non è impostata nei segreti, permette l'accesso per test locali
        return True

    if st.session_state.get("password_correct", False):
        return True

    password = st.text_input("Inserisci la password per accedere", type="password")
    if password == correct_password:
        st.session_state["password_correct"] = True
        st.rerun()
        return True
    elif password:
        st.error("Password errata.")
    return False

# --- UI DELLA SIDEBAR (VISIBILE A TUTTI) ---
st.sidebar.image("logo_cieb.png", use_container_width=True)
st.sidebar.markdown("---")


# --- APPLICAZIONE PRINCIPALE (VISIBILE DOPO LOGIN) ---
if check_password():
    # Inizializza il client di Google Maps solo dopo che la password è corretta
    try:
        gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
    except Exception as e:
        st.error(f"Errore nella configurazione della chiave API. Controlla i tuoi Secrets: {e}")
        st.stop()

    # --- FUNZIONI CORE ---
    @st.cache_data
    def carica_dati(file_caricato):
        try:
            return pd.read_excel(file_caricato)
        except Exception as e:
            st.error(f"Errore durante la lettura del file Excel: {e}")
            return None

    def calcola_percorso_ottimizzato(_gmaps_client, indirizzi_waypoint, origine, destinazione):
        if not indirizzi_waypoint:
            return 0, 0, [], None
        try:
            directions_result = _gmaps_client.directions(
                origin=origine, destination=destinazione,
                waypoints=indirizzi_waypoint, optimize_waypoints=True,
                mode="driving", departure_time=datetime.now()
            )
            if not directions_result:
                st.warning("Google Maps non ha restituito un risultato per questo percorso.")
                return 0, 0, [], None
            distanza_totale_km = sum(leg['distance']['value'] for leg in directions_result[0]['legs']) / 1000
            tempo_totale_secondi = sum(leg['duration']['value'] for leg in directions_result[0]['legs'])
            tempo_totale_minuti = tempo_totale_secondi / 60
            ordine_ottimizzato_idx = directions_result[0]['waypoint_order']
            indirizzi_ordinati = [indirizzi_waypoint[i] for i in ordine_ottimizzato_idx]
            return round(distanza_totale_km, 2), round(tempo_totale_minuti), indirizzi_ordinati, directions_result
        except Exception as e:
            st.error(f"Errore durante la chiamata a Google Maps API: {e}")
            return 0, 0, [], None

    def estrai_coordinate_per_mappa(directions_result):
        punti_mappa = []
        if not directions_result:
            return pd.DataFrame()
        partenza = directions_result[0]['legs'][0]['start_location']
        punti_mappa.append({'lat': partenza['lat'], 'lon': partenza['lng']})
        for leg in directions_result[0]['legs']:
            tappa = leg['end_location']
            punti_mappa.append({'lat': tappa['lat'], 'lon': tappa['lng']})
        return pd.DataFrame(punti_mappa)

    # --- UI PRINCIPALE ---
    st.title("🚚 Dashboard Analisi Consegne Vettori")
    st.markdown("Carica il tuo file Excel per analizzare le consegne e calcolare i percorsi ottimizzati.")

    st.sidebar.subheader("Controlli Dashboard")
    file_excel = st.sidebar.file_uploader("Carica il tuo foglio Excel", type=['xlsx', 'xls'])

    if file_excel is not None:
        df = carica_dati(file_excel)
        if df is not None:
            st.sidebar.success("File Excel caricato con successo!")
            
            colonne_richieste = ['COD-VETTORE', 'INDIRIZZO', 'LOCALITA', 'MS-LOCALIT']
            if not all(col in df.columns for col in colonne_richieste):
                st.sidebar.error(f"Il file Excel deve contenere le colonne: {', '.join(colonne_richieste)}.")
            else:
                vettori_disponibili = sorted(df['COD-VETTORE'].dropna().unique().tolist())
                vettore_selezionato = st.sidebar.selectbox("Seleziona un vettore da analizzare:", options=vettori_disponibili)

                if vettore_selezionato:
                    st.markdown("---")
                    st.header(f"Analisi per il vettore: **{vettore_selezionato}**")

                    citta_partenza = PUNTI_PARTENZA_VETTORI.get(vettore_selezionato, "BRESCIA")
                    if citta_partenza == "BRESCIA":
                        indirizzo_partenza_attuale = INDIRIZZO_PARTENZA_CIEB
                    else:
                        indirizzo_partenza_attuale = citta_partenza
                    st.info(f"📍 Punto di partenza/arrivo calcolato per questo giro: **{indirizzo_partenza_attuale}**")

                    df_vettore = df[df['COD-VETTORE'] == vettore_selezionato].copy()

                    # --- BLOCCO DI LOGICA PER LA DESTINAZIONE ---
                    df_vettore['MS-LOCALIT'] = df_vettore['MS-LOCALIT'].fillna('')
                    df_vettore['LOCALITA'] = df_vettore['LOCALITA'].fillna('')
                    df_vettore['MS-LOCALIT'] = df_vettore['MS-LOCALIT'].astype(str)
                    df_vettore['LOCALITA'] = df_vettore['LOCALITA'].astype(str)
                    df_vettore['INDIRIZZO'] = df_vettore['INDIRIZZO'].astype(str)
                    localita_scelta = np.where(df_vettore['MS-LOCALIT'].str.strip() != '', df_vettore['MS-LOCALIT'], df_vettore['LOCALITA'])
                    df_vettore['IndirizzoCompleto'] = df_vettore['INDIRIZZO'] + ", " + localita_scelta
                    
                    indirizzi_da_visitare = df_vettore['IndirizzoCompleto'].unique().tolist()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"