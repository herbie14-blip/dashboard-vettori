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
    "PEZZ2": "BRESCIA", "NEX5": "BRESCIA", "PAPA": "BRESCIA", "LIN2": "BRESCIA",
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
    st.title("🚚 Dashboard Analisi Consegne Vettori")
    st.markdown("Carica il file Excel per ottimizzare i percorsi.")
    st.sidebar.subheader("Controlli Dashboard")
    file_excel = st.sidebar.file_uploader("Carica foglio Excel", type=['xlsx', 'xls'])

    if file_excel is not None:
        df = carica_dati(file_excel)
        if df is not None:
            st.sidebar.success("File caricato!")
            
            # MODIFICATO: Aggiunte le colonne CAP alle colonne richieste
            colonne = ['COD-VETTORE', 'INDIRIZZO', 'LOCALITA', 'CAP', 'MS-LOCALIT', 'MS-CAP']
            if not all(col in df.columns for col in colonne):
                st.sidebar.error(f"Mancano colonne: assicurati che ci siano {', '.join(colonne)}.")
            else:
                vettori = sorted(df['COD-VETTORE'].dropna().unique().tolist())
                vettore_sel = st.sidebar.selectbox("Seleziona un vettore:", options=vettori)
                if vettore_sel:
                    st.markdown("---")
                    st.header(f"Analisi per il vettore: **{vettore_sel}**")
                    citta_partenza = PUNTI_PARTENZA_VETTORI.get(vettore_sel, "BRESCIA")
                    indirizzo_partenza = INDIRIZZO_PARTENZA_CIEB if citta_partenza == "BRESCIA" else citta_partenza
                    st.info(f"📍 Punto di partenza/arrivo: **{indirizzo_partenza}**")

                    df_vettore = df[df['COD-VETTORE'] == vettore_sel].copy()
                    
                    # === BLOCCO DI LOGICA DEFINITIVO CON GESTIONE CAP ===
                    # 1. Pulisci tutte le colonne necessarie
                    for col in ['INDIRIZZO', 'LOCALITA', 'MS-LOCALIT', 'CAP', 'MS-CAP']:
                        df_vettore[col] = df_vettore[col].fillna('').astype(str)
                        if 'CAP' in col:
                            # Rimuove ".0" dai CAP letti come numeri da Excel
                            df_vettore[col] = df_vettore[col].str.replace(r'\.0$', '', regex=True)

                    # 2. Definisci la condizione: MS-LOCALIT è compilata?
                    condition = df_vettore['MS-LOCALIT'].str.strip() != ''

                    # 3. Scegli la località e il CAP in base alla condizione
                    localita_scelta = np.where(condition, df_vettore['MS-LOCALIT'], df_vettore['LOCALITA'])
                    cap_scelto = np.where(condition, df_vettore['MS-CAP'], df_vettore['CAP'])

                    # 4. Crea l'indirizzo completo ultra-preciso
                    df_vettore['IndirizzoCompleto'] = df_vettore['INDIRIZZO'] + ", " + cap_scelto + " " + localita_scelta
                    # =======================================================
                    
                    indirizzi_da_visitare = df_vettore['IndirizzoCompleto'].unique().tolist()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"📍 {len(indirizzi_da_visitare)} Destinazioni uniche")
                        st.dataframe(pd.DataFrame({'Indirizzi da visitare': indirizzi_da_visitare}))
                    
                    if st.button("🚀 Calcola Percorso Ottimizzato"):
                        with st.spinner("Calcolo il percorso migliore..."):
                            distanza, tempo, tappe, result = calcola_percorso_ottimizzato(gmaps, indirizzi_da_visitare, indirizzo_partenza, indirizzo_partenza)
                        with col2:
                            st.subheader("✅ Risultato Ottimizzazione")
                            if distanza > 0:
                                m1, m2 = st.columns(2)
                                m1.metric("Distanza Totale", f"{distanza} km")
                                m2.metric("Tempo Stimato", f"~ {tempo} min")
                                st.write("**Ordine di consegna consigliato:**")
                                tappe_df = pd.DataFrame({'Tappe Ottimizzate': [f"{i+1}. {tappa}" for i, tappa in enumerate(tappe)]})
                                st.dataframe(tappe_df)
                                df_mappa = estrai_coordinate_per_mappa(result)
                                if not df_mappa.empty:
                                    st.subheader("Mappa delle Tappe")
                                    st.map(df_mappa)
                            else:
                                st.error("Impossibile calcolare il percorso.")