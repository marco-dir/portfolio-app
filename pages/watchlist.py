import streamlit as st
from database.db_connection import execute_query
from database.analytics import get_current_prices
import pandas as pd


def show(user_id):
    """Pagina watchlist."""
    
    st.title("⭐ Watchlist")
    
    # === AGGIUNGI A WATCHLIST ===
    st.markdown("### ➕ Aggiungi Titolo")
    
    with st.form("add_watchlist"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            ticker = st.text_input("Ticker", placeholder="AAPL").upper()
        
        with col2:
            company_name = st.text_input("Nome Azienda (opzionale)", placeholder="Apple Inc.")
        
        with col3:
            target_price = st.number_input("Prezzo Target (opzionale)", min_value=0.0, step=0.01)
        
        notes = st.text_area("Note", placeholder="Perché ti interessa questo titolo?")
        
        submit = st.form_submit_button("➕ Aggiungi a Watchlist")
        
        if submit:
            if not ticker:
                st.error("Inserisci un ticker")
            else:
                # Aggiungi a database
                query = """
                    INSERT INTO watchlist (user_id, ticker, company_name, target_price, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, ticker) DO UPDATE
                    SET company_name = EXCLUDED.company_name,
                        target_price = EXCLUDED.target_price,
                        notes = EXCLUDED.notes
                """
                
                execute_query(query, (user_id, ticker, company_name, target_price, notes), fetch=False)
                st.success(f"✅ {ticker} aggiunto alla watchlist!")
                st.rerun()
    
    st.markdown("---")
    
    # === VISUALIZZA WATCHLIST ===
    st.markdown("### 📋 I Tuoi Titoli")
    
    query = """
        SELECT id, ticker, company_name, target_price, notes, added_at
        FROM watchlist
        WHERE user_id = %s
        ORDER BY added_at DESC
    """
    
    watchlist = execute_query(query, (user_id,))
    
    if not watchlist:
        st.info("👋 Watchlist vuota. Aggiungi titoli che vuoi monitorare!")
        return
    
    # Ottieni prezzi correnti
    tickers = [w['ticker'] for w in watchlist]
    current_prices = get_current_prices(tickers)
    
    # Crea DataFrame
    data = []
    for item in watchlist:
        ticker = item['ticker']
        current_price = current_prices.get(ticker, 0)
        target = item['target_price'] or 0
        
        upside = ((target - current_price) / current_price * 100) if target > 0 and current_price > 0 else 0
        
        data.append({
            'id': item['id'],
            'Ticker': ticker,
            'Azienda': item['company_name'] or 'N/A',
            'Prezzo Attuale': f"${current_price:.2f}",
            'Target': f"${target:.2f}" if target > 0 else 'N/A',
            'Upside': f"{upside:+.1f}%" if upside != 0 else 'N/A',
            'Note': item['notes'] or '',
            'Aggiunto': item['added_at'][:10]
        })
    
    df = pd.DataFrame(data)
    
    # Mostra tabella
    st.dataframe(
        df[['Ticker', 'Azienda', 'Prezzo Attuale', 'Target', 'Upside', 'Note', 'Aggiunto']],
        use_container_width=True,
        hide_index=True
    )
    
    # === GESTIONE WATCHLIST ===
    st.markdown("### ⚙️ Gestisci")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ticker_to_remove = st.selectbox("Rimuovi dalla Watchlist", tickers)
        
        if st.button("🗑️ Rimuovi"):
            query_delete = "DELETE FROM watchlist WHERE user_id = %s AND ticker = %s"
            execute_query(query_delete, (user_id, ticker_to_remove), fetch=False)
            st.success(f"{ticker_to_remove} rimosso!")
            st.rerun()
    
    with col2:
        # Analizza titolo dalla watchlist
        ticker_to_analyze = st.selectbox("Vai ad Analisi Titolo", tickers, key="analyze_select")
        
        if st.button("🔍 Analizza"):
            st.session_state.analyzed = True
            st.session_state.current_ticker = ticker_to_analyze
            st.session_state.current_period = "annual"
            st.session_state.current_limit = 10
            st.switch_page("pages/stock_analysis.py")
