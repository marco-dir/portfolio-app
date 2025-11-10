import streamlit as st
from database.db_connection import execute_query
from database.analytics import get_current_prices


def show(user_id):
    """Pagina gestione alert."""
    
    st.title("🔔 Alert Prezzi")
    
    st.info("""
    💡 **Come funzionano gli alert:**
    
    Imposta un prezzo target per un titolo. Quando il prezzo raggiunge il target, 
    l'alert viene triggerato e disattivato automaticamente.
    
    **Nota**: Gli alert vengono controllati ad ogni accesso all'app.
    """)
    
    # === CREA ALERT ===
    st.markdown("### ➕ Crea Nuovo Alert")
    
    with st.form("create_alert"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            ticker = st.text_input("Ticker", placeholder="AAPL").upper()
        
        with col2:
            alert_type = st.selectbox(
                "Tipo Alert",
                ["PRICE_ABOVE", "PRICE_BELOW"]
            )
        
        with col3:
            target_value = st.number_input("Prezzo Target", min_value=0.0, step=0.01)
        
        notes = st.text_area("Note (opzionale)", placeholder="Motivo dell'alert...")
        
        submit = st.form_submit_button("Crea Alert")
        
        if submit:
            if not ticker or target_value <= 0:
                st.error("⚠️ Inserisci ticker e prezzo validi")
            else:
                query = """
                    INSERT INTO alerts (user_id, ticker, alert_type, target_value, notes)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                execute_query(query, (user_id, ticker, alert_type, target_value, notes), fetch=False)
                st.success(f"✅ Alert creato per {ticker}!")
                st.rerun()
    
    st.markdown("---")
    
    # === ALERT ATTIVI ===
    st.markdown("### 🟢 Alert Attivi")
    
    query_active = """
        SELECT id, ticker, alert_type, target_value, notes, created_at
        FROM alerts
        WHERE user_id = %s AND is_active = TRUE
        ORDER BY created_at DESC
    """
    
    active_alerts = execute_query(query_active, (user_id,))
    
    if active_alerts:
        # Ottieni prezzi correnti
        tickers = list(set([a['ticker'] for a in active_alerts]))
        current_prices = get_current_prices(tickers)
        
        for alert in active_alerts:
            ticker = alert['ticker']
            current_price = current_prices.get(ticker, 0)
            target = alert['target_value']
            alert_type = alert['alert_type']
            
            # Calcola distanza dal target
            if current_price > 0:
                distance = ((target - current_price) / current_price * 100)
            else:
                distance = 0
            
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**{ticker}**")
                    st.caption(f"Creato: {alert['created_at'][:10]}")
                
                with col2:
                    type_emoji = "📈" if alert_type == "PRICE_ABOVE" else "📉"
                    type_text = "sopra" if alert_type == "PRICE_ABOVE" else "sotto"
                    st.markdown(f"{type_emoji} **{type_text}** ${target:.2f}")
                    st.caption(f"Attuale: ${current_price:.2f}")
                
                with col3:
                    color = "🟢" if abs(distance) < 5 else "🟡" if abs(distance) < 10 else "🔴"
                    st.markdown(f"{color} Distanza: **{distance:+.1f}%**")
                    
                    if alert['notes']:
                        st.caption(alert['notes'])
                
                with col4:
                    if st.button("🗑️", key=f"del_alert_{alert['id']}"):
                        query_delete = "DELETE FROM alerts WHERE id = %s"
                        execute_query(query_delete, (alert['id'],), fetch=False)
                        st.success("Alert eliminato!")
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info("Nessun alert attivo")
    
    # === ALERT TRIGGERATI ===
    st.markdown("### ✅ Alert Triggerati (Ultimi 10)")
    
    query_triggered = """
        SELECT ticker, alert_type, target_value, current_value, triggered_at, notes
        FROM alerts
        WHERE user_id = %s AND is_active = FALSE
        ORDER BY triggered_at DESC
        LIMIT 10
    """
    
    triggered_alerts = execute_query(query_triggered, (user_id,))
    
    if triggered_alerts:
        for alert in triggered_alerts:
            with st.expander(f"✅ {alert['ticker']} - {alert['triggered_at'][:16]}"):
                type_text = "sopra" if alert['alert_type'] == "PRICE_ABOVE" else "sotto"
                st.markdown(f"**Tipo**: Prezzo {type_text} ${alert['target_value']:.2f}")
                st.markdown(f"**Prezzo al Trigger**: ${alert['current_value']:.2f}")
                
                if alert['notes']:
                    st.markdown(f"**Note**: {alert['notes']}")
    else:
        st.info("Nessun alert triggerato recentemente")
