import streamlit as st
from database.portfolios import (
    create_portfolio, get_user_portfolios, get_portfolio_positions,
    add_position, delete_position, delete_portfolio
)
from database.analytics import calculate_portfolio_performance
import pandas as pd
import plotly.express as px


def show(user_id):
    """Pagina gestione portafogli."""
    
    st.title("📊 I Miei Portafogli")
    
    # Tabs
    tab1, tab2 = st.tabs(["📋 I Miei Portafogli", "➕ Nuovo Portafoglio"])
    
    with tab1:
        portfolios = get_user_portfolios(user_id)
        
        if not portfolios:
            st.info("👋 Non hai ancora portafogli. Creane uno nel tab 'Nuovo Portafoglio'!")
            return
        
        for portfolio in portfolios:
            with st.expander(f"📁 {portfolio['portfolio_name']}", expanded=True):
                # Header con metriche
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.metric("Titoli", portfolio['num_positions'])
                    
                    # Performance real-time
                    perf = calculate_portfolio_performance(portfolio['id'])
                    if perf:
                        st.metric("Valore Corrente", f"${perf['current_value']:,.2f}")
                        st.metric("P/L", f"${perf['gain_loss']:,.2f}", 
                                 delta=f"{perf['gain_loss_pct']:+.2f}%")
                
                with col2:
                    if st.button("🔄 Aggiorna", key=f"refresh_{portfolio['id']}"):
                        from database.analytics import save_portfolio_snapshot
                        save_portfolio_snapshot(portfolio['id'])
                        st.success("Snapshot salvato!")
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Elimina", key=f"del_{portfolio['id']}"):
                        delete_portfolio(portfolio['id'])
                        st.success("Portafoglio eliminato!")
                        st.rerun()
                
                st.markdown("---")
                
                # Posizioni
                df = get_portfolio_positions(portfolio['id'])
                
                if not df.empty:
                    # Aggiungi prezzi correnti e P/L
                    if perf:
                        current_prices = perf['current_prices']
                        df['current_price'] = df['ticker'].map(current_prices)
                        df['current_value'] = df['shares'] * df['current_price']
                        df['gain_loss'] = df['current_value'] - df['total_cost']
                        df['gain_loss_pct'] = ((df['current_price'] - df['avg_price']) / df['avg_price'] * 100)
                    
                    # Tabella
                    display_df = df[[
                        'ticker', 'company_name', 'shares', 'avg_price', 
                        'current_price', 'total_cost', 'current_value', 
                        'gain_loss', 'gain_loss_pct', 'weight_%'
                    ]].copy()
                    
                    # Formattazione
                    display_df['avg_price'] = display_df['avg_price'].apply(lambda x: f"${x:.2f}")
                    display_df['current_price'] = display_df['current_price'].apply(lambda x: f"${x:.2f}")
                    display_df['total_cost'] = display_df['total_cost'].apply(lambda x: f"${x:,.2f}")
                    display_df['current_value'] = display_df['current_value'].apply(lambda x: f"${x:,.2f}")
                    display_df['gain_loss'] = display_df['gain_loss'].apply(lambda x: f"${x:+,.2f}")
                    display_df['gain_loss_pct'] = display_df['gain_loss_pct'].apply(lambda x: f"{x:+.2f}%")
                    display_df['weight_%'] = display_df['weight_%'].apply(lambda x: f"{x:.1f}%")
                    
                    # Rinomina colonne
                    display_df.columns = [
                        'Ticker', 'Azienda', 'Azioni', 'Prezzo Medio', 
                        'Prezzo Attuale', 'Costo Totale', 'Valore Attuale',
                        'Gain/Loss', 'Gain/Loss %', 'Peso'
                    ]
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    # Grafico distribuzione
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig = px.pie(
                            df, 
                            values='current_value', 
                            names='ticker',
                            title='Distribuzione per Titolo',
                            hole=0.4
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        if 'sector' in df.columns:
                            sector_df = df.groupby('sector')['current_value'].sum().reset_index()
                            fig2 = px.pie(
                                sector_df,
                                values='current_value',
                                names='sector',
                                title='Distribuzione per Settore',
                                hole=0.4
                            )
                            st.plotly_chart(fig2, use_container_width=True)
                    
                    # Gestione posizioni
                    st.markdown("#### ⚙️ Gestisci Posizioni")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        ticker_to_delete = st.selectbox(
                            "Elimina Posizione",
                            df['ticker'].tolist(),
                            key=f"del_pos_{portfolio['id']}"
                        )
                        
                        if st.button("Elimina", key=f"del_btn_{portfolio['id']}"):
                            delete_position(portfolio['id'], ticker_to_delete)
                            st.success(f"{ticker_to_delete} eliminato!")
                            st.rerun()
                    
                    with col2:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "📥 Esporta CSV",
                            csv,
                            file_name=f"{portfolio['portfolio_name']}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            key=f"export_{portfolio['id']}"
                        )
                else:
                    st.info("Portafoglio vuoto. Aggiungi titoli dalla sezione 'Analisi Titoli'")
    
    with tab2:
        st.subheader("Crea Nuovo Portafoglio")
        
        with st.form("new_portfolio"):
            name = st.text_input("Nome Portafoglio", placeholder="es. Portafoglio Pensione")
            description = st.text_area("Descrizione (opzionale)")
            
            submit = st.form_submit_button("Crea", use_container_width=True)
            
            if submit:
                if name:
                    create_portfolio(user_id, name, description)
                    st.success(f"✅ Portafoglio '{name}' creato!")
                    st.rerun()
                else:
                    st.error("Inserisci un nome")
