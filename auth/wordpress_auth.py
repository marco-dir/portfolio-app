import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from database.users import sync_user_from_wordpress, get_user_by_id
import os

# Config
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "https://tuosito.com")
MP_CONSUMER_KEY = os.getenv("MP_CONSUMER_KEY", "")
MP_CONSUMER_SECRET = os.getenv("MP_CONSUMER_SECRET", "")


def authenticate_wordpress(username, password):
    """Autentica contro WordPress."""
    try:
        url = f"{WORDPRESS_URL}/wp-json/wp/v2/users/me"
        response = requests.get(url, auth=HTTPBasicAuth(username, password), timeout=15)
        
        if response.status_code == 200:
            user_data = response.json()
            return {
                'id': user_data['id'],
                'username': user_data['slug'],
                'email': user_data.get('email', ''),
                'name': user_data['name']
            }
        elif response.status_code == 403:
            st.error("❌ Usa una Application Password. Vai su WordPress → Profilo → Application Passwords")
        else:
            st.error("❌ Credenziali errate")
        
        return None
    except Exception as e:
        st.error(f"❌ Errore: {e}")
        return None


def check_memberpress_membership(email):
    """Verifica membership MemberPress."""
    try:
        url = f"{WORDPRESS_URL}/wp-json/mp/v1/members"
        response = requests.get(
            url,
            auth=HTTPBasicAuth(MP_CONSUMER_KEY, MP_CONSUMER_SECRET),
            params={'search': email},
            timeout=15
        )
        
        if response.status_code != 200:
            return None
        
        members = response.json()
        if not members:
            return {'has_active': False}
        
        member_id = members[0].get('id')
        subs_url = f"{WORDPRESS_URL}/wp-json/mp/v1/members/{member_id}/subscriptions"
        
        subs_response = requests.get(
            subs_url,
            auth=HTTPBasicAuth(MP_CONSUMER_KEY, MP_CONSUMER_SECRET),
            timeout=15
        )
        
        if subs_response.status_code != 200:
            return {'has_active': False}
        
        subscriptions = subs_response.json()
        
        for sub in subscriptions:
            if sub.get('status') == 'active':
                membership = sub.get('membership', {})
                return {
                    'has_active': True,
                    'membership_name': membership.get('title', 'Unknown'),
                    'status': 'active',
                    'created_at': sub.get('created_at'),
                    'expires_at': sub.get('expires_at', 'Never')
                }
        
        return {'has_active': False}
    except Exception as e:
        st.error(f"❌ Errore verifica membership: {e}")
        return None


def show_login_page():
    """Mostra form di login."""
    st.title("🔐 DIRAMCO Financial Platform")
    
    st.markdown("""
    ### Benvenuto!
    
    Accedi con le tue credenziali WordPress.
    """)
    
    st.info("""
    💡 **Nota**: WordPress richiede Application Password per sicurezza.
    
    **Come crearla:**
    1. Accedi a WordPress
    2. Vai su **Profilo → Application Passwords**
    3. Crea password "DIRAMCO App"
    4. Usa username + quella password qui
    """)
    
    with st.form("login_form"):
        username = st.text_input("Username WordPress")
        password = st.text_input("Application Password", type="password")
        submit = st.form_submit_button("🚀 Accedi", use_container_width=True)
        
        if submit:
            if not username or not password:
                st.error("⚠️ Compila tutti i campi")
            else:
                with st.spinner("🔐 Autenticazione..."):
                    wp_user = authenticate_wordpress(username, password)
                    
                    if not wp_user:
                        return
                    
                    st.success(f"✅ Autenticato: {wp_user['name']}")
                    
                    membership = check_memberpress_membership(wp_user['email'])
                    
                    if not membership or not membership.get('has_active', False):
                        st.error("❌ Nessuna membership attiva")
                        st.info("👉 [Attiva membership](https://tuosito.com/membership)")
                        return
                    
                    st.success(f"🎫 Membership: {membership['membership_name']}")
                    
                    # Sincronizza database
                    local_user_id = sync_user_from_wordpress(wp_user, membership)
                    
                    # Salva sessione
                    st.session_state.authenticated = True
                    st.session_state.user_id = local_user_id
                    st.session_state.user_data = wp_user
                    st.session_state.membership = membership
                    
                    st.balloons()
                    st.rerun()


def require_auth():
    """Proteggi app."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        # Re-verifica membership ogni 30 min
        if 'last_check' not in st.session_state:
            st.session_state.last_check = 0
        
        import time
        if time.time() - st.session_state.last_check > 1800:
            user_data = st.session_state.user_data
            membership = check_memberpress_membership(user_data['email'])
            
            if membership and membership.get('has_active', False):
                st.session_state.membership = membership
                st.session_state.last_check = time.time()
                sync_user_from_wordpress(user_data, membership)
            else:
                st.error("❌ Membership non più attiva")
                logout()
                return False
        
        return True
    
    show_login_page()
    return False


def get_current_user():
    """Ottieni utente corrente."""
    if st.session_state.get('authenticated', False):
        user_id = st.session_state.get('user_id')
        return get_user_by_id(user_id)
    return None


def logout():
    """Logout."""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_data = None
    st.session_state.membership = None
    st.rerun()
