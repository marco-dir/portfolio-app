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

# ========================================
# CONFIGURAZIONE MEMBERSHIP PREMIUM
# ========================================

# ID delle membership Premium autorizzate
PREMIUM_MEMBERSHIP_IDS = [2508, 2500]

# Nome visualizzato (opzionale, per i log)
PREMIUM_NAME = "Premium"


# ========================================
# FUNZIONI MEMBERPRESS API
# ========================================

def check_membership_by_email(email):
    """
    Verifica se l'email ha una membership PREMIUM attiva (ID: 2508 o 2500).
    Blocca accesso per membership Basic o altre.
    
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
        
        # ========================================
        # STEP 4: VERIFICA MEMBERSHIP PREMIUM
        # ========================================
        
        premium_found = False
        other_membership_found = False
        other_membership_name = None
        active_membership_data = None
        
        for sub in subscriptions:
            status = sub.get('status', '').lower()
            
            if status == 'active':
                membership = sub.get('membership', {})
                membership_title = membership.get('title', 'Unknown')
                membership_id = membership.get('id')
                expires_at = sub.get('expires_at', 'Mai')
                
                # Verifica se la subscription è effettivamente attiva (non scaduta)
                is_valid = True
                
                if expires_at and expires_at != 'Mai' and expires_at != '0000-00-00 00:00:00':
                    try:
                        exp_date = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                        
                        # Se scaduta, salta questa subscription
                        if exp_date < datetime.now():
                            is_valid = False
                    except:
                        pass
                
                if is_valid:
                    # ✅ Verifica se è una delle membership Premium autorizzate
                    if membership_id in PREMIUM_MEMBERSHIP_IDS:
                        premium_found = True
                        active_membership_data = {
                            'user': {
                                'id': user_id,
                                'username': user_slug,
                                'email': email,
                                'name': user_name
                            },
                            'membership': {
                                'membership_name': membership_title,
                                'membership_id': membership_id,
                                'status': 'active',
                                'created_at': sub.get('created_at'),
                                'expires_at': expires_at if expires_at != '0000-00-00 00:00:00' else 'Mai',
                                'subscription_id': sub.get('id'),
                                'member_id': member_id
                            }
                        }
                        break  # Trovata Premium, esci dal loop
                    else:
                        # Ha una membership attiva ma NON è Premium
                        other_membership_found = True
                        other_membership_name = membership_title
        
        # Risultati
        if premium_found:
            # ✅ Ha membership Premium attiva (ID: 2508 o 2500)
            return {
                'found': True,
                'has_active': True,
                **active_membership_data
            }
        
        elif other_membership_found:
            # ❌ Ha membership attiva ma non Premium (es. Basic)
            return {
                'found': True,
                'has_active': False,
                'is_other': True,
                'other_membership_name': other_membership_name,
                'message': f'Membership "{other_membership_name}" rilevata - serve Premium per accedere'
            }
        
        else:
            # ❌ Nessuna membership attiva
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

def show_login_page():
    """Mostra la pagina di login con verifica Premium (ID: 2508 o 2500)."""
    
    # Header
    st.title("🔐 DIRAMCO Financial Platform")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Accesso Riservato ai Membri Premium
        
        Questa piattaforma di analisi avanzata è riservata esclusivamente 
        ai membri con membership **Premium**.
        """)
    
    with col2:
        st.info("""
        **Serve aiuto?**
        
        📧 support@tuosito.com
        📚 [Guida](https://tuosito.com/guida)
        """)
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2 = st.tabs(["🔑 Accedi", "ℹ️ Informazioni"])
    
    with tab1:
        # Form centrato
        col_left, col_center, col_right = st.columns([1, 2, 1])
        
        with col_center:
            # Form di login
            with st.form("email_login_form", clear_on_submit=False):
                st.markdown("#### Inserisci la tua email")
                
                email = st.text_input(
                    "Email",
                    placeholder="tuaemail@esempio.com",
                    help="L'email usata per attivare la membership Premium",
                    key="login_email_input",
                    label_visibility="collapsed"
                )
                
                st.markdown("")  # Spazio
                
                submit = st.form_submit_button(
                    "🚀 Accedi",
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
                    with st.spinner("🔍 Verifica membership Premium..."):
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
                            
                            Per accedere alla piattaforma devi:
                            1. Registrarti su WordPress
                            2. Attivare la membership **Premium**
                            """)
                            st.markdown("""
                            <a href="https://tuosito.com/membership" target="_blank">
                                <button style="background-color: #0066cc; color: white; 
                                padding: 12px 24px; border: none; border-radius: 5px; 
                                cursor: pointer; width: 100%; margin-top: 10px; font-size: 16px;">
                                    ⭐ Attiva Membership Premium
                                </button>
                            </a>
                            """, unsafe_allow_html=True)
                            st.stop()
                        
                        # Ha membership diversa da Premium
                        if result.get('is_other'):
                            other_name = result.get('other_membership_name', 'Basic')
                            
                            st.warning(f"⚠️ Membership \"{other_name}\" rilevata")
                            st.error("""
                            **Questa piattaforma è riservata ai membri Premium**
                            
                            La tua membership attuale non include l'accesso 
                            a questa piattaforma di analisi avanzata.
                            
                            Per accedere serve la membership **Premium**.
                            """)
                            
                            st.info("""
                            **Vantaggi Membership Premium:**
                            
                            ✅ **Accesso completo alla piattaforma di analisi**
                            - Analisi fondamentale avanzata
                            - Modelli di valutazione DCF
                            - Portfolio management
                            - AI-powered insights
                            
                            ✅ **Strumenti esclusivi**
                            - Reports personalizzati
                            - Alerts automatici
                            - Dati storici completi
                            
                            ✅ **Supporto prioritario**
                            - Assistenza dedicata
                            - Webinar esclusivi
                            - Community Premium
                            """)
                            
                            st.markdown("""
                            <a href="https://tuosito.com/upgrade-premium" target="_blank">
                                <button style="background-color: #FFD700; color: black; 
                                padding: 14px 28px; border: none; border-radius: 5px; 
                                cursor: pointer; width: 100%; margin-top: 15px; font-size: 18px;
                                font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                    ⭐ Upgrade a Premium Ora
                                </button>
                            </a>
                            """, unsafe_allow_html=True)
                            st.stop()
                        
                        # Membership non attiva (né Premium né altre)
                        if not result.get('has_active'):
                            msg = result.get('message', 'Nessuna membership attiva')
                            st.error(f"❌ {msg}")
                            
                            st.warning("""
                            **Nessuna membership attiva**
                            
                            Per accedere alla piattaforma serve una membership **Premium** attiva.
                            
                            **Possibili motivi:**
                            - Membership scaduta
                            - Pagamento non completato
                            - Subscription cancellata
                            - Account in fase di attivazione
                            """)
                            
                            st.markdown("""
                            <a href="https://tuosito.com/membership" target="_blank">
                                <button style="background-color: #FF4B4B; color: white; 
                                padding: 12px 24px; border: none; border-radius: 5px; 
                                cursor: pointer; width: 100%; margin-top: 10px; font-size: 16px;">
                                    ⭐ Attiva Membership Premium
                                </button>
                            </a>
                            """, unsafe_allow_html=True)
                            st.stop()
                        
                        # ✅ ACCESSO CONSENTITO - Ha Premium!
                        user_data = result['user']
                        membership = result['membership']
                        
                        st.success(f"✅ Benvenuto **{user_data['name']}**!")
                        st.success(f"⭐ Membership Premium attiva: **{membership['membership_name']}**")
                        
                        # Mostra info scadenza
                        expires = membership.get('expires_at', 'Mai')
                        if expires != 'Mai':
                            st.info(f"📅 La tua membership scade il: {expires}")
                        else:
                            st.info("📅 Hai una membership Premium a vita!")
                    
                    # Sincronizza database locale
                    with st.spinner("💾 Caricamento piattaforma Premium..."):
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
        ### 📖 Informazioni Accesso Premium
        
        #### 🔐 Come Funziona
        
        Questa piattaforma è **riservata esclusivamente ai membri Premium**.
        
        **Processo di accesso:**
        
        1. **Inserisci la tua email**  
           L'email associata alla tua membership Premium
        
        2. **Verifica automatica**  
           Il sistema controlla che tu abbia una membership Premium attiva (ID: 2508 o 2500)
        
        3. **Accesso immediato**  
           Se hai Premium attivo, entri subito nella piattaforma!
        
        ---
        
        ### ⭐ Perché Solo Premium?
        
        Questa piattaforma offre strumenti di analisi avanzata e richiede 
        risorse computazionali significative. La membership Premium ci 
        permette di mantenere il servizio di alta qualità per tutti.
        
        **Cosa include Premium:**
        
        📊 **Analisi Avanzata**
        - Modelli DCF completi
        - Valutazioni Graham
        - Analisi comparativa
        - Metriche personalizzate
        
        🤖 **AI-Powered Insights**
        - Analisi con Claude AI
        - Raccomandazioni personalizzate
        - Pattern recognition
        
        💼 **Portfolio Management**
        - Tracking completo
        - Performance analytics
        - Risk assessment
        - Diversification analysis
        
        📈 **Dati in Tempo Reale**
        - Prezzi aggiornati
        - News finanziarie
        - Earnings calls
        - SEC filings
        
        📄 **Reports & Export**
        - PDF professionali
        - Excel dettagliati
        - Dati storici completi
        
        ---
        
        ### 🔒 Sicurezza e Privacy
        
        **Come proteggiamo il tuo accesso:**
        
        - ✅ Verifica membership in tempo reale ogni 30 minuti
        - ✅ Revoca automatica se membership scade
        - ✅ Connessione sicura HTTPS
        - ✅ API protette con autenticazione
        - ✅ Nessuna password salvata localmente
        - ✅ Conformità GDPR
        
        **Privacy:**
        - Usiamo solo dati necessari (nome, email, stato membership)
        - Non condividiamo mai i tuoi dati con terze parti
        - Puoi richiedere cancellazione dati in qualsiasi momento
        - I tuoi investimenti e portfolio sono privati
        
        ---
        
        ### ✅ Requisiti Tecnici
        
        **Per accedere alla piattaforma:**
        
        - ✅ Account WordPress registrato su tuosito.com
        - ✅ Membership Premium attiva (ID: 2508 o 2500)
        - ✅ Email verificata
        - ✅ Browser moderno (Chrome, Firefox, Safari, Edge)
        - ✅ Connessione internet stabile
        
        ---
        
        ### ❓ Domande Frequenti
        
        **"Ho pagato ma non riesco ad accedere"**  
        → Attendi qualche minuto per l'attivazione della membership  
        → Verifica l'email di conferma da WordPress  
        → Controlla che il pagamento sia andato a buon fine  
        → Contatta il supporto se persiste dopo 10 minuti
        
        **"Ho membership Basic, posso fare upgrade?"**  
        → Sì! Vai su tuosito.com/upgrade-premium  
        → Il costo sarà proporzionale al periodo rimanente  
        → L'accesso sarà immediato dopo l'upgrade
        
        **"Quanto costa la membership Premium?"**  
        → Visita tuosito.com/membership per i prezzi aggiornati  
        → Abbiamo piani mensili e annuali  
        → Offerte speciali per abbonamenti lunghi
        
        **"Posso provare prima di acquistare?"**  
        → Contatta support@tuosito.com per demo gratuita  
        → Offriamo garanzia soddisfatti o rimborsati 30 giorni  
        → Puoi cancellare in qualsiasi momento
        
        **"La membership si rinnova automaticamente?"**  
        → Sì, per garantire accesso continuo  
        → Puoi disattivare il rinnovo automatico quando vuoi  
        → Ricevi reminder 7 giorni prima della scadenza
        
        **"Posso condividere l'account?"**  
        → No, l'account è personale e non trasferibile  
        → Ogni utente deve avere la propria membership  
        → Offriamo sconti per team/aziende
        
        ---
        
        ### 💳 Gestione Membership
        
        **Gestisci la tua membership Premium:**
        
        🌐 [Account WordPress](https://tuosito.com/account)
        
        Da qui puoi:
        - Vedere stato e scadenza
        - Aggiornare metodi di pagamento
        - Fare upgrade o downgrade
        - Cancellare subscription
        - Scaricare fatture
        
        ---
        
        ### 📞 Supporto Premium
        
        Come membro Premium hai accesso al supporto prioritario:
        
        📧 **Email:** premium@tuosito.com  
        💬 **Chat:** Disponibile in piattaforma  
        📱 **Telefono:** +39 XXX XXXXXXX (Lun-Ven 9-18)  
        🌐 **Portal:** [support.tuosito.com](https://support.tuosito.com)
        
        **Tempo di risposta garantito:**
        - Email: < 4 ore (giorni lavorativi)
        - Chat: < 30 minuti
        - Telefono: Immediato
        
        ---
        
        ### 🎓 Risorse per Membri Premium
        
        Accedi a contenuti esclusivi:
        
        - 📚 Video tutorial avanzati
        - 📊 Template di analisi
        - 🎥 Webinar mensili dal vivo
        - 💬 Community privata Premium
        - 📖 Ebook e guide complete
        - 🎯 Sessioni di coaching 1-on-1
        
        ---
        
        **Pronto a iniziare con Premium?**
        
        [⭐ Attiva Premium Ora](https://tuosito.com/membership)
        """)


# ========================================
# PROTEZIONE APP
# ========================================

def require_auth():
    """
    Richiedi autenticazione Premium per accedere all'app.
    Verifica periodicamente che la membership Premium sia ancora attiva.
    
    Returns:
        bool: True se autenticato con Premium, False altrimenti
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
            
            with st.spinner("🔄 Verifica stato membership Premium..."):
                result = check_membership_by_email(email)
                
                if result and result.get('has_active'):
                    # Membership Premium ancora attiva - aggiorna dati
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
                        
                elif result and result.get('is_other'):
                    # Downgrade a membership non-Premium
                    other_name = result.get('other_membership_name', 'Basic')
                    
                    st.error(f"❌ Downgrade rilevato a membership \"{other_name}\"")
                    st.warning("""
                    **Accesso alla piattaforma revocato**
                    
                    La tua membership è stata modificata e non include più 
                    l'accesso a questa piattaforma.
                    
                    Per continuare ad usarla, riattiva la membership Premium.
                    """)
                    st.markdown("""
                    <a href="https://tuosito.com/upgrade-premium" target="_blank">
                        <button style="background-color: #FFD700; color: black; 
                        padding: 12px 24px; border: none; border-radius: 5px; 
                        cursor: pointer; margin-top: 10px; font-size: 16px;
                        font-weight: bold;">
                            ⭐ Riattiva Premium
                        </button>
                    </a>
                    """, unsafe_allow_html=True)
                    
                    # Attendi 3 secondi e poi logout
                    import time
                    time.sleep(3)
                    logout()
                    return False
                    
                else:
                    # Membership Premium non più attiva - forza logout
                    st.error("❌ La tua membership Premium non è più attiva")
                    st.warning("""
                    **Accesso revocato**
                    
                    Per continuare ad usare la piattaforma, rinnova la tua membership Premium.
                    """)
                    st.markdown("""
                    <a href="https://tuosito.com/membership" target="_blank">
                        <button style="background-color: #FF4B4B; color: white; 
                        padding: 12px 24px; border: none; border-radius: 5px; 
                        cursor: pointer; margin-top: 10px; font-size: 16px;">
                            ⭐ Rinnova Premium
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
    Ottieni i dati dell'utente Premium corrente.
    
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
    """Mostra informazioni utente Premium nella sidebar."""
    user = get_current_user()
    
    if user:
        with st.sidebar:
            st.markdown("---")
            
            # Nome utente
            st.markdown(f"### 👤 {user['wordpress_data']['name']}")
            st.caption(f"📧 {user['wordpress_data']['email']}")
            
            # Badge Premium
            st.markdown("⭐ **MEMBRO PREMIUM**")
            
            # Info membership
            membership = user.get('membership', {})
            if membership:
                st.success(f"🎫 {membership['membership_name']}")
                
                # Data scadenza
                expires = membership.get('expires_at', 'Mai')
                if expires != 'Mai':
                    st.caption(f"📅 Scade: {expires}")
                else:
                    st.caption("📅 Premium a vita ✨")
            
            st.markdown("---")
            
            # Link gestione account
            st.markdown("""
            <a href="https://tuosito.com/account" target="_blank">
                <button style="background-color: #555; color: white; 
                padding: 8px 16px; border: none; border-radius: 3px; 
                cursor: pointer; width: 100%; font-size: 14px;">
                    ⚙️ Gestisci Account
                </button>
            </a>
            """, unsafe_allow_html=True)
            
            st.markdown("")
            
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
    st.info("Grazie per aver usato DIRAMCO Platform! 👋")
    
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
    Mostra anche le membership Premium configurate.
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
            
            # Mostra membership Premium
            st.write("**Membership Premium autorizzate (ID: 2508, 2500):**")
            
            premium_found = []
            other_found = []
            
            for m in memberships:
                m_id = m.get('id')
                m_title = m.get('title', 'Unknown')
                
                if m_id in PREMIUM_MEMBERSHIP_IDS:
                    premium_found.append(f"⭐ **{m_title}** (ID: {m_id}) - PREMIUM")
                else:
                    other_found.append(f"- {m_title} (ID: {m_id})")
            
            if premium_found:
                st.success("**Membership Premium trovate:**")
                for p in premium_found:
                    st.write(p)
            else:
                st.warning("⚠️ Nessuna membership Premium trovata!")
                st.info(f"Cercando ID: {PREMIUM_MEMBERSHIP_IDS}")
            
            if other_found:
                st.write("**Altre membership:**")
                for o in other_found:
                    st.write(o)
            
            return True
            
        elif response.status_code == 401:
            st.error("❌ API Keys non valide!")
            st.warning("Verifica Consumer Key e Secret in MemberPress → Settings → Developer Tools")
            return False
            
        else:
            st.warning(f"⚠️ Risposta API inattesa: {response.status_code}")
            return False
            
    except Exception as e:
        st.error(f"❌ Errore: {e}")
        return False


def test_membership_check():
    """Test per verificare il controllo membership Premium."""
    st.subheader("🧪 Test Verifica Membership Premium")
    
    st.info(f"**ID Premium autorizzati:** {PREMIUM_MEMBERSHIP_IDS}")
    
    test_email = st.text_input("Email di test", placeholder="test@esempio.com")
    
    if st.button("🔍 Verifica"):
        if test_email:
            with st.spinner("Verifica in corso..."):
                result = check_membership_by_email(test_email)
                
                st.write("**Risultato verifica:**")
                
                if result:
                    if result.get('has_active'):
                        st.success("✅ ACCESSO CONSENTITO - Membership Premium attiva!")
                        st.json(result)
                    elif result.get('is_other'):
                        st.warning(f"⚠️ ACCESSO NEGATO - Membership \"{result.get('other_membership_name')}\" trovata (non Premium)")
                    elif not result.get('found'):
                        st.error("❌ Email non trovata")
                    else:
                        st.error("❌ Nessuna membership attiva")
                    
                    st.write("**Dettagli completi:**")
                    st.json(result)
                else:
                    st.error("❌ Errore durante la verifica")
