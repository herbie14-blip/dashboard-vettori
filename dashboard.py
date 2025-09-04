# Importa le librerie
import streamlit as st
import pandas as pd
import googlemaps
from datetime import datetime

# --- FUNZIONE PER IL CONTROLLO PASSWORD ---
def check_password():
    """Restituisce True se l'utente ha inserito la password corretta."""
    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except:
        # Se la password non è impostata nei segreti, permette l'accesso
        return True

    if st.session_state.get("password_correct", False):
        return True

    # Chiede all'utente di inserire la password
    password = st.text_input("Inserisci la password per accedere", type="password")
    if password == correct_password:
        st.session_state["password_correct"] = True
        st.rerun()  # Ricarica l'app per mostrare il contenuto
        return True
    elif password:
        st.error("Password errata.")
    return False

# --- CODICE PRINCIPALE DELLA DASHBOARD ---
st.set_page_config(page_title="Cieb - Analisi Consegne Vettori", layout="wide") # Titolo della pagina nel browser

# --- Mostra il logo nella sidebar prima del controllo password ---
st.sidebar.image("logo_cieb.png", use_column_width=True) # NUOVO: Aggiunge il logo

# Controlla la password prima di mostrare qualsiasi altra cosa
if check_password():
    INDIRIZZO_PARTENZA = "Cieb S.p.A., Via Giovanni Battista Cacciamali, 62, 25125 Brescia BS, Italia"

    try:
        gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
    except Exception as e:
        st.error(f"Errore nella configurazione della chiave API. Controlla il tuo file secrets.toml: {e}")
        st.stop()

    # --- FUNZIONI CORE (rimangono invariate) ---
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

    # --- INTERFACCIA UTENTE (UI) ---
    st.title("🚚 Dashboard Analisi Consegne Vettori") # Questo rimane il titolo nella pagina principale
    st.markdown("Carica il tuo file Excel per analizzare le consegne e calcolare i percorsi ottimizzati.")

    # --- Spostiamo i controlli nella sidebar ---
    st.sidebar.markdown("---") # Linea separatrice
    st.sidebar.subheader("Controlli Dashboard") # Titolo per la sezione dei controlli

    file_excel = st.sidebar.file_uploader("Carica il tuo foglio Excel", type=['xlsx', 'xls']) # NUOVO: sposta il file_uploader nella sidebar

    if file_excel is not None:
        df = carica_dati(file_excel)
        if df is not None:
            st.sidebar.success("File Excel caricato con successo!") # NUOVO: il messaggio di successo va nella sidebar
            
            colonne_richieste = ['COD-VETTORE', 'INDIRIZZO', 'LOCALITA']
            if not all(col in df.columns for col in colonne_richieste):
                st.sidebar.error(f"Il file Excel deve contenere le colonne: {', '.join(colonne_richieste)}. Rinominale se necessario.") # NUOVO: errore nella sidebar
            else:
                vettori_disponibili = sorted(df['COD-VETTORE'].dropna().unique().tolist())
                vettore_selezionato = st.sidebar.selectbox("Seleziona un vettore da analizzare:", options=vettori_disponibili) # NUOVO: sposta il selectbox nella sidebar

                if vettore_selezionato:
                    st.markdown("---")
                    st.header(f"Analisi per il vettore: **{vettore_selezionato}**")

                    df_vettore = df[df['COD-VETTORE'] == vettore_selezionato].copy()
                    df_vettore['IndirizzoCompleto'] = df_vettore['INDIRIZZO'].astype(str) + ", " + df_vettore['LOCALITA'].astype(str)
                    indirizzi_da_visitare = df_vettore['IndirizzoCompleto'].unique().tolist()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"📍 {len(indirizzi_da_visitare)} Destinazioni uniche")
                        st.dataframe(pd.DataFrame({'Indirizzi da visitare': indirizzi_da_visitare}), use_container_width=True)

                    if st.button("🚀 Calcola Percorso Ottimizzato"):
                        with st.spinner("Calcolo il percorso migliore..."):
                            distanza_km, tempo_min, tappe_ordinate, result_completo = calcola_percorso_ottimizzato(
                                gmaps, indirizzi_da_visitare, INDIRIZZO_PARTENZA, INDIRIZZO_PARTENZA
                            )
                        with col2:
                            st.subheader("✅ Risultato Ottimizzazione")
                            if distanza_km > 0:
                                metrica1, metrica2 = st.columns(2)
                                metrica1.metric(label="Distanza Totale Stimata", value=f"{distanza_km} km")
                                metrica2.metric(label="Tempo di Percorrenza Stimato", value=f"~ {tempo_min} min")
                                
                                st.write("**Ordine di consegna consigliato:**")
                                tappe_visualizzazione = [f"{i+1}. {tappa}" for i, tappa in enumerate(tappe_ordinate)]
                                st.dataframe(pd.DataFrame({'Tappe Ottimizzate': tappe_visualizzazione}), use_container_width=True)

                                df_mappa = estrai_coordinate_per_mappa(result_completo)
                                if not df_mappa.empty:
                                    st.subheader("Mappa delle Tappe")
                                    st.map(df_mappa)
                            else:
                                st.error("Impossibile calcolare il percorso. Controlla la validità degli indirizzi.")