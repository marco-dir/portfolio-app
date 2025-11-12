import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from database.users import sync_user_from_wordpress, get_user_by_id
import os
from datetime import datetime

# Config
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "https://tuosito.com")
MP_CONSUMER_KEY = os.getenv("MP_CONSUMER_KEY", "")
MP_CONSUMER_SECRET = os.getenv("MP_CONSUMER_SECRET", "")

# FUNZIONI MEMBERPRESS API
# ========================================

def check_membership_by_email(email):
    """
    Verifica se l'email ha una membership attiva.
    
    Args:
        email (str): Email dell'utente
        
    Returns:
        dict: Risultato della verifica con dati utente e membership
    """
    try:
        # STEP 1: Cerca membro per email
        url = f"{WORDPRESS_URL}/wp-json/mp/v1/members"
        response = requests.get(
            url,
            auth=HTTPBasicAuth(MP_CONSUMER_KEY, MP_CONSUMER_SECRET),
            params={'search': email},
            timeout=15
        )
        
        # Gestione errori API
        if response.status_code == 401:
            st.error("❌ API Keys MemberPress non valide!")
            st.info("Verifica Consumer Key e Secret in MemberPress → Settings → Developer Tools")
            return None
        
        if response.status_code != 200:
            st.warning(f"⚠️ Errore API MemberPress: {response.status_code}")
            return None
        
        members = response.json()
        
        # Email non trovata
        if not members:
            return {
                'found': False,
                'message': 'Email non trovata nel sistema'
            }
        
        member = members[0]
        member_id = member.get('id')
        user_id = member.get('user_id')
        
        # STEP 2: Ottieni info utente WordPress
        user_url = f"{WORDPRESS_URL}/wp-json/wp/v2/users/{user_id}"
        
        user_response = requests.get(
            user_url,
            auth=HTTPBasicAuth(MP_CONSUMER_KEY, MP_CONSUMER_SECRET),
            timeout=15
        )
        
        # Dati utente
        if user_response.status_code == 200:
            user_data = user_response.json()
            user_name = user_data.get('name', email.split('@')[0].title())
            user_slug = user_data.get('slug', email.split('@')[0])
        else:
            # Fallback se non riesce a ottenere dati WP
            user_name = email.split('@')[0].title()
            user_slug = email.split('@')[0]
        
        # STEP 3: Verifica subscriptions attive
        subs_url = f"{WORDPRESS_URL}/wp-json/mp/v1/members/{member_id}/subscriptions"
        
        subs_response = requests.get(
            subs_url,
            auth=HTTPBasicAuth(MP_CONSUMER_KEY, MP_CONSUMER_SECRET),
            timeout=15
        )
        
        if subs_response.status_code != 200:
            return {
                'found': True,
                'has_active': False,
                'message': 'Impossibile verificare subscriptions'
            }
        
        subscriptions = subs_response.json()
        
        # STEP 4: Cerca subscription attiva e non scaduta
        for sub in subscriptions:
            status = sub.get('status', '').lower()
            
            if status == 'active':
                membership = sub.get('membership', {})
                expires_at = sub.get('expires_at', 'Mai')
                
                # Verifica se la subscription è effettivamente attiva
                is_valid = True
                
                if expires_at and expires_at != 'Mai' and expires_at != '0000-00-00 00:00:00':
                    try:
                        from datetime import datetime
                        exp_date = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                        
                        # Se scaduta, salta questa subscription
                        if exp_date < datetime.now():
                            is_valid = False
                    except:
                        pass
                
                if is_valid:
                    # Subscription valida trovata!
                    return {
                        'found': True,
                        'has_active': True,
                        'user': {
                            'id': user_id,
                            'username': user_slug,
                            'email': email,
                            'name': user_name
                        },
                        'membership': {
                            'membership_name': membership.get('title', 'Premium'),
                            'membership_id': membership.get('id'),
                            'status': 'active',
                            'created_at': sub.get('created_at'),
                            'expires_at': expires_at if expires_at != '0000-00-00 00:00:00' else 'Mai',
                            'subscription_id': sub.get('id'),
                            'member_id': member_id
                        }
                    }
        
        # Nessuna subscription attiva trovata
        return {
            'found': True,
            'has_active': False,
            'message': 'Nessuna membership attiva o tutte scadute'
        }
        
    except requests.exceptions.Timeout:
        st.error("⏱️ Timeout connessione - Riprova tra poco")
        return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 Impossibile connettersi al server WordPress")
        return None
    except Exception as e:
        st.error(f"❌ Errore imprevisto: {e}")
        return None


# ========================================
# UI - PAGINA LOGIN
# ========================================

✅ Ecco il codice con il form più stretto e centrato
Modifico solo la sezione del form di login in auth.py:
pythondef show_login_page():
    """Mostra la pagina di login con form email centrato e stretto."""
    
    # Header
    st.title("Analisi Finanziaria Avanzata e Portafoglio IA")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Accesso Riservato ai Membri
        
        Inserisci l'email associata alla tua membership per accedere immediatamente alla piattaforma.
        """)
    
    with col2:
        st.info("""
        **Serve aiuto?**
        
        info@diramco.com
        [Guida](https://diramco.com/guida)
        """)
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2 = st.tabs([" Accedi", " Informazioni"])
    
    with tab1:
        # ========================================
        # FORM CENTRATO E STRETTO
        # ========================================
        
        # Crea colonne per centrare il form
        # [spazio vuoto] [form] [spazio vuoto]
        col_left, col_center, col_right = st.columns([1, 2, 1])
        
        with col_center:
            # Form di login
            with st.form("email_login_form", clear_on_submit=False):
                st.markdown("#### Inserisci la tua email")
                
                email = st.text_input(
                    "Email",
                    placeholder="tuaemail@esempio.com",
                    help="L'email usata per registrarti e attivare la membership",
                    key="login_email_input",
                    label_visibility="collapsed"  # Nasconde label ripetuta
                )
                
                st.markdown("")  # Spazio
                
                submit = st.form_submit_button(
                    "Accedi",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit:
                    # Validazione email
                    if not email:
                        st.error("⚠️ Inserisci la tua email")
                        st.stop()
                    
                    if '@' not in email or '.' not in email.split('@')[1]:
                        st.error("⚠️ Inserisci un'email valida (es. nome@dominio.com)")
                        st.stop()
                    
                    # Normalizza email (lowercase e trim)
                    email = email.strip().lower()
                    
                    # Verifica membership
                    with st.spinner("🔍 Verifica membership in corso..."):
                        result = check_membership_by_email(email)
                        
                        # Errore durante la verifica
                        if result is None:
                            st.error("❌ Errore durante la verifica. Riprova tra poco.")
                            st.stop()
                        
                        # Email non trovata
                        if not result.get('found'):
                            st.error("❌ Email non trovata nel sistema")
                            st.warning("""
                            **Non hai ancora un account?**
                            
                            Per accedere alla piattaforma devi prima:
                            1. Registrarti su WordPress
                            2. Attivare una membership
                            """)
                            st.markdown("""
                            <a href="https://tuosito.com/membership" target="_blank">
                                <button style="background-color: #0066cc; color: white; 
                                padding: 12px 24px; border: none; border-radius: 5px; 
                                cursor: pointer; width: 100%; margin-top: 10px; font-size: 16px;">
                                     Registrati e Attiva Membership
                                </button>
                            </a>
                            """, unsafe_allow_html=True)
                            st.stop()
                        
                        # Membership non attiva
                        if not result.get('has_active'):
                            msg = result.get('message', 'Membership non attiva')
                            st.error(f"❌ {msg}")
                            
                            st.warning("""
                            **La tua membership non è attiva**
                            
                            Per accedere alla piattaforma devi avere una membership attiva.
                            
                            Possibili motivi:
                            - Membership scaduta
                            - Pagamento non completato
                            - Subscription cancellata
                            
                            Verifica lo stato della tua membership su WordPress o rinnovala.
                            """)
                            
                            st.markdown("""
                            <a href="https://tuosito.com/membership" target="_blank">
                                <button style="background-color: #FF4B4B; color: white; 
                                padding: 12px 24px; border: none; border-radius: 5px; 
                                cursor: pointer; width: 100%; margin-top: 10px; font-size: 16px;">
                                    🎯 Verifica o Rinnova Membership
                                </button>
                            </a>
                            """, unsafe_allow_html=True)
                            st.stop()
                        
                        # ✅ ACCESSO CONSENTITO!
                        user_data = result['user']
                        membership = result['membership']
                        
                        st.success(f"✅ Benvenuto **{user_data['name']}**!")
                        st.success(f"🎫 Membership attiva: **{membership['membership_name']}**")
                        
                        # Mostra info scadenza
                        expires = membership.get('expires_at', 'Mai')
                        if expires != 'Mai':
                            st.info(f"📅 La tua membership scade il: {expires}")
                        else:
                            st.info("📅 Hai una membership a vita - Nessuna scadenza!")
                    
                    # Sincronizza database locale
                    with st.spinner(" Caricamento dati utente..."):
                        try:
                            # Salva/aggiorna utente nel database locale
                            local_user_id = sync_user_from_wordpress(user_data, membership)
                            
                            # Salva nella sessione
                            st.session_state.authenticated = True
                            st.session_state.user_id = local_user_id
                            st.session_state.user_data = user_data
                            st.session_state.membership = membership
                            st.session_state.last_check = datetime.now().timestamp()
                            st.session_state.login_email = email
                            
                            st.success("✅ Accesso completato con successo!")
                            st.balloons()
                            
                            # Attendi 1 secondo prima di ricaricare
                            import time
                            time.sleep(1)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Errore durante il salvataggio dati: {e}")
                            st.warning("Contatta il supporto se il problema persiste.")
                            st.stop()
    
    with tab2:
        st.markdown("""
        ### Come Funziona l'Accesso
        
        Il nostro sistema di accesso è **semplice e sicuro**:
        
        #### Processo di Login
        
        1. **Inserisci la tua email**  
           L'email che hai usato per registrarti su WordPress
        
        2. **Verifica automatica**  
           Il sistema controlla se hai una membership MemberPress attiva
        
        3. **Accesso immediato**  
           Se tutto è OK, entri subito nella piattaforma!
        
        ---
        
        ### 🔒 Sicurezza e Privacy
        
        **Come proteggiamo il tuo account:**
        
        - ✅ Ogni accesso viene verificato in tempo reale con WordPress
        - ✅ La sessione viene ricontrollata automaticamente ogni 30 minuti
        - ✅ Se la membership scade, l'accesso viene revocato immediatamente
        - ✅ Non salviamo password - solo email e dati pubblici del profilo
        - ✅ Connessione sicura HTTPS
        - ✅ API protette con chiavi criptate
        
        **Privacy:**
        - Usiamo solo i dati necessari (nome, email, stato membership)
        - Non condividiamo i tuoi dati con terze parti
        - Puoi richiedere la cancellazione dei dati in qualsiasi momento
        
        ---
        
        ### ✅ Requisiti per Accedere
        
        Per accedere alla piattaforma devi avere:
        
        - ✅ Account WordPress registrato su tuosito.com
        - ✅ Membership MemberPress attiva e valida
        - ✅ Email verificata e confermata
        
        ---
        
        ### ❓ Domande Frequenti
        
        **"Non riesco ad accedere - cosa faccio?"**  
        → Verifica che l'email sia scritta correttamente  
        → Assicurati che la membership sia attiva su WordPress  
        → Prova a svuotare la cache del browser  
        → Contatta il supporto se il problema persiste
        
        **"Email non trovata nel sistema"**  
        → Assicurati di aver completato la registrazione su WordPress  
        → Verifica di usare la stessa email del tuo account WordPress  
        → Se sei sicuro che l'email sia corretta, contatta il supporto
        
        **"Membership non attiva"**  
        → Verifica lo stato della tua membership su WordPress  
        → Controlla la data di scadenza  
        → Se hai pagato recentemente, attendi qualche minuto e riprova  
        → Attiva o rinnova la membership se necessario
        
        **"L'accesso funziona ma poi mi disconnette"**  
        → Probabilmente la membership è scaduta durante la sessione  
        → Il sistema ricontrolla lo stato ogni 30 minuti per sicurezza  
        → Rinnova la membership per continuare ad usare la piattaforma
        
        **"Posso usare la stessa membership su più dispositivi?"**  
        → Sì, puoi accedere da qualsiasi dispositivo  
        → La sessione è indipendente per ogni dispositivo  
        → Assicurati solo di fare logout sui dispositivi pubblici
        
        ---
        
        ### Gestione Membership
        
        **Dove gestisco la mia membership?**  
        Accedi al tuo account WordPress:  
        🌐 [tuosito.com/account](https://tuosito.com/account)
        
        Qui puoi:
        - Vedere lo stato della membership
        - Aggiornare i metodi di pagamento
        - Rinnovare o cancellare la subscription
        - Modificare i dati del profilo
        
        ---
        
        ### 📞 Supporto Tecnico
        
        Hai ancora problemi o domande?
        
         **Email:** support@tuosito.com  
         **Web:** [tuosito.com/supporto](https://tuosito.com/supporto)  
         **Orari:** Lun-Ven 9:00-18:00
        
        Il nostro team è sempre pronto ad aiutarti! 💪
        """)


# ========================================
# PROTEZIONE APP
# ========================================

def require_auth():
    """
    Richiedi autenticazione per accedere all'app.
    Verifica periodicamente che la membership sia ancora attiva.
    
    Returns:
        bool: True se autenticato, False altrimenti
    """
    # Inizializza stato autenticazione
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Se autenticato, verifica periodicamente
    if st.session_state.authenticated:
        last_check = st.session_state.get('last_check', 0)
        current_time = datetime.now().timestamp()
        
        # Re-verifica ogni 30 minuti (1800 secondi)
        if current_time - last_check > 1800:
            email = st.session_state.user_data.get('email')
            
            with st.spinner("🔄 Verifica stato membership..."):
                result = check_membership_by_email(email)
                
                if result and result.get('has_active'):
                    # Membership ancora attiva - aggiorna dati
                    st.session_state.membership = result['membership']
                    st.session_state.last_check = current_time
                    
                    # Aggiorna anche il database locale
                    try:
                        sync_user_from_wordpress(
                            st.session_state.user_data,
                            result['membership']
                        )
                    except:
                        pass  # Non bloccare se sync fallisce
                else:
                    # Membership non più attiva - forza logout
                    st.error("❌ La tua membership non è più attiva")
                    st.warning("""
                    **Accesso revocato**
                    
                    Per continuare ad usare la piattaforma, rinnova la tua membership.
                    """)
                    st.markdown("""
                    <a href="https://tuosito.com/membership" target="_blank">
                        <button style="background-color: #FF4B4B; color: white; 
                        padding: 12px 24px; border: none; border-radius: 5px; 
                        cursor: pointer; margin-top: 10px; font-size: 16px;">
                            🎯 Rinnova Membership
                        </button>
                    </a>
                    """, unsafe_allow_html=True)
                    
                    # Attendi 3 secondi e poi logout
                    import time
                    time.sleep(3)
                    logout()
                    return False
        
        return True
    
    # Non autenticato - mostra pagina login
    show_login_page()
    return False


def get_current_user():
    """
    Ottieni i dati dell'utente corrente.
    
    Returns:
        dict: Dati utente completi o None se non autenticato
    """
    if st.session_state.get('authenticated', False):
        user_id = st.session_state.get('user_id')
        user = get_user_by_id(user_id)
        
        if user:
            # Aggiungi info membership e WordPress alla risposta
            user['membership'] = st.session_state.get('membership', {})
            user['wordpress_data'] = st.session_state.get('user_data', {})
        
        return user
    
    return None


def show_user_info_sidebar():
    """Mostra informazioni utente nella sidebar."""
    user = get_current_user()
    
    if user:
        with st.sidebar:
            st.markdown("---")
            
            # Nome utente
            st.markdown(f"### 👤 {user['wordpress_data']['name']}")
            st.caption(f"📧 {user['wordpress_data']['email']}")
            
            # Info membership
            membership = user.get('membership', {})
            if membership:
                st.success(f"🎫 {membership['membership_name']}")
                
                # Data scadenza
                expires = membership.get('expires_at', 'Mai')
                if expires != 'Mai':
                    st.caption(f"📅 Scade: {expires}")
                else:
                    st.caption("📅 Membership a vita")
            
            st.markdown("---")
            
            # Pulsante logout
            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                logout()


def logout():
    """
    Esegui logout completo.
    Pulisce tutta la sessione e ricarica la pagina.
    """
    # Pulisci tutti i dati della sessione
    keys_to_delete = list(st.session_state.keys())
    for key in keys_to_delete:
        del st.session_state[key]
    
    st.success("✅ Logout effettuato con successo")
    st.info("Torna presto! 👋")
    
    # Attendi 1 secondo e ricarica
    import time
    time.sleep(1)
    st.rerun()


# ========================================
# FUNZIONE UTILITY - TEST API
# ========================================

def test_memberpress_api():
    """
    Testa la connessione alle API MemberPress.
    Utile per debug e verifica configurazione.
    
    Returns:
        bool: True se le API funzionano, False altrimenti
    """
    try:
        url = f"{WORDPRESS_URL}/wp-json/mp/v1/memberships"
        response = requests.get(
            url,
            auth=HTTPBasicAuth(MP_CONSUMER_KEY, MP_CONSUMER_SECRET),
            timeout=10
        )
        
        if response.status_code == 200:
            memberships = response.json()
            st.success("✅ Connessione API MemberPress OK!")
            st.info(f"Trovate {len(memberships)} membership configurate sul sito")
            
            # Mostra elenco membership
            if memberships:
                st.write("**Membership disponibili:**")
                for m in memberships:
                    st.write(f"- {m.get('title', 'Unknown')} (ID: {m.get('id')})")
            
            return True
            
        elif response.status_code == 401:
            st.error("❌ API Keys non valide!")
            st.warning("Verifica Consumer Key e Secret in MemberPress → Settings → Developer Tools")
            return False
            
        else:
            st.warning(f"⚠️ Risposta API inattesa: {response.status_code}")
            st.write(response.text)
            return False
            
    except requests.exceptions.Timeout:
        st.error("⏱️ Timeout connessione")
        return False
    except requests.exceptions.ConnectionError:
        st.error("🔌 Impossibile connettersi a WordPress")
        st.info("Verifica che l'URL sia corretto e il sito sia raggiungibile")
        return False
    except Exception as e:
        st.error(f"❌ Errore: {e}")
        return False
