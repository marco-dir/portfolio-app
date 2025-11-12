import streamlit as st
from database.db_connection import init_connection_pool
from auth.wordpress_auth import require_auth, get_current_user, logout
from database.users import get_user_stats
from database.analytics import check_alerts

# Configurazione pagina
st.set_page_config(
    page_title="DIRAMCO Financial Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializza database
init_connection_pool()

# CSS personalizzato
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stSidebar {
        background-color: #f8f9fa;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)


def main():
    """Router principale dell'applicazione."""
    
    # PROTEGGI APP - Richiedi autenticazione
    if not require_auth():
        return
    
    # Utente autenticato
    user = get_current_user()
    
    # SIDEBAR
    with st.sidebar:
        st.title("📊 DIRAMCO")
        st.markdown(f"**{user['display_name']}**")
        st.caption(f"📧 {user['email']}")
        st.caption(f"🎫 {user['membership_level']}")
        
        st.markdown("---")
        
        # Statistiche rapide
        stats = get_user_stats(user['id'])
        if stats:
            col1, col2 = st.columns(2)
            col1.metric("Portafogli", stats['num_portfolios'])
            col2.metric("Titoli", stats['num_positions'])
            
            if stats['total_invested'] > 0:
                st.metric("Investito", f"${stats['total_invested']:,.2f}")
        
        st.markdown("---")
        
        # Check alerts
        alerts = check_alerts(user['id'])
        if alerts:
            st.warning(f"🔔 {len(alerts)} Alert attivi!")
            for alert in alerts:
                st.caption(f"• {alert['ticker']}: ${alert['current_price']:.2f}")
        
        st.markdown("---")
        
        # MENU NAVIGAZIONE
        page = st.radio(
            "Menu",
            [
                "🔍 Analisi Titoli",
                "📊 I Miei Portafogli",
                "📈 Performance & P/L",
                "🤖 Analisi AI",
                "⭐ Watchlist",
                "🔔 Alert"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        
        st.markdown("---")
        st.caption("Made with ❤️ by DIRAMCO")
    
    # ROUTING PAGINE
    if page == "🔍 Analisi Titoli":
        from modules import stock_analysis
        stock_analysis.show(user['id'])
        
    elif page == "📊 I Miei Portafogli":
        from modules import portfolio
        portfolio.show(user['id'])
        
    elif page == "📈 Performance & P/L":
        from modules import performance
        performance.show(user['id'])
        
    elif page == "🤖 Analisi AI":
        from modules import portfolio_analysis
        portfolio_analysis.show(user['id'])
        
    elif page == "⭐ Watchlist":
        from modules import watchlist
        watchlist.show(user['id'])
        
    elif page == "🔔 Alert":
        from modules import alerts_page
        alerts_page.show(user['id'])


if __name__ == "__main__":
    main()
