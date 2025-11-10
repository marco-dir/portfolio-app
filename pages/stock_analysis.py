import streamlit as st
# Importa TUTTE le funzioni dal tuo codice esistente
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# COPIA TUTTE LE TUE FUNZIONI dal file allegato
# (fetch_data, fetch_company_profile, format_currency, ecc.)
# ... TUTTO IL TUO CODICE ...

def show(user_id):
    """
    Mostra pagina analisi titoli.
    Integra con bottone "Aggiungi al Portafoglio".
    """
    
    # IL TUO CODICE ESISTENTE COMPLETO
    # Ma alla fine, dopo l'analisi, aggiungi:
    
    # ... dopo aver mostrato tutti i tab ...
    
    # SEZIONE AGGIUNTA: Aggiungi al Portafoglio
    if st.session_state.get('analyzed', False):
        ticker = st.session_state.current_ticker
        
        st.markdown("---")
        st.markdown("### ➕ Aggiungi al Portafoglio")
        
        from database.portfolios import get_user_portfolios, add_position
        
        portfolios = get_user_portfolios(user_id)
        
        if not portfolios:
            st.info("Crea prima un portafoglio nella sezione '📊 I Miei Portafogli'")
        else:
            with st.form(f"add_to_portfolio_{ticker}"):
                portfolio_names = {p['portfolio_name']: p['id'] for p in portfolios}
                selected_portfolio = st.selectbox("Seleziona Portafoglio", list(portfolio_names.keys()))
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    shares = st.number_input("Azioni", min_value=0.0, step=1.0, value=10.0)
                
                with col2:
                    price = st.number_input("Prezzo", min_value=0.0, step=0.01, 
                                          value=float(quote.get('price', 0)) if quote else 0.0)
                
                with col3:
                    currency = st.selectbox("Valuta", ["USD", "EUR", "GBP"])
                
                purchase_date = st.date_input("Data Acquisto", value=datetime.today())
                notes = st.text_area("Note (opzionale)")
                
                submit = st.form_submit_button("➕ Aggiungi", use_container_width=True)
                
                if submit:
                    if shares > 0 and price > 0:
                        portfolio_id = portfolio_names[selected_portfolio]
                        
                        add_position(
                            portfolio_id=portfolio_id,
                            ticker=ticker,
                            shares=shares,
                            avg_price=price,
                            currency=currency,
                            company_name=company_profile.get('companyName') if company_profile else None,
                            sector=company_profile.get('sector') if company_profile else None,
                            industry=company_profile.get('industry') if company_profile else None,
                            purchase_date=purchase_date,
                            notes=notes
                        )
                        
                        st.success(f"✅ {ticker} aggiunto a {selected_portfolio}!")
                        st.balloons()
