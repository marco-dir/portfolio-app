import streamlit as st
from database.portfolios import get_user_portfolios, get_portfolio_positions
from database.analytics import (
    calculate_portfolio_performance,
    get_portfolio_history,
    get_position_pl,
    save_portfolio_snapshot
)
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def show(user_id):
    """Pagina performance e P/L tracking."""
    
    st.title("📈 Performance & P/L Tracking")
    
    portfolios = get_user_portfolios(user_id)
    
    if not portfolios:
        st.info("Crea un portafoglio per vedere le performance!")
        return
    
    # Seleziona portafoglio
    portfolio_names = {p['portfolio_name']: p['id'] for p in portfolios}
    selected_name = st.selectbox("Seleziona Portafoglio", list(portfolio_names.keys()))
    portfolio_id = portfolio_names[selected_name]
    
    # Calcola performance corrente
    perf = calculate_portfolio_performance(portfolio_id)
    
    if not perf:
        st.warning("Nessuna posizione nel portafoglio")
        return
    
    # === METRICHE PRINCIPALI ===
    st.markdown("### 📊 Panoramica")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Investito", f"${perf['total_cost']:,.2f}")
    
    with col2:
        st.metric("Valore Corrente", f"${perf['current_value']:,.2f}")
    
    with col3:
        st.metric(
            "Gain/Loss", 
            f"${perf['gain_loss']:,.2f}",
            delta=f"{perf['gain_loss_pct']:+.2f}%"
        )
    
    with col4:
        # Salva snapshot
        if st.button("💾 Salva Snapshot"):
            save_portfolio_snapshot(portfolio_id)
            st.success("✅ Snapshot salvato!")
            st.rerun()
    
    st.markdown("---")
    
    # === GRAFICO ANDAMENTO STORICO ===
    st.markdown("### 📈 Andamento Storico")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        period = st.selectbox("Periodo", ["30 giorni", "90 giorni", "180 giorni", "1 anno"])
        days_map = {"30 giorni": 30, "90 giorni": 90, "180 giorni": 180, "1 anno": 365}
        days = days_map[period]
    
    df_history = get_portfolio_history(portfolio_id, days=days)
    
    if not df_history.empty:
        fig = go.Figure()
        
        # Linea valore portafoglio
        fig.add_trace(go.Scatter(
            x=df_history['snapshot_date'],
            y=df_history['total_value'],
            mode='lines',
            name='Valore Portafoglio',
            line=dict(color='#1f77b4', width=3),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))
        
        # Linea costo (investito)
        fig.add_trace(go.Scatter(
            x=df_history['snapshot_date'],
            y=df_history['total_cost'],
            mode='lines',
            name='Costo Totale',
            line=dict(color='gray', width=2, dash='dash')
        ))
        
        fig.update_layout(
            title=f"Performance {period}",
            xaxis_title="Data",
            yaxis_title="Valore ($)",
            hovermode='x unified',
            template='plotly_white',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Metriche periodo
        if len(df_history) >= 2:
            first_value = df_history.iloc[0]['total_value']
            last_value = df_history.iloc[-1]['total_value']
            period_return = ((last_value - first_value) / first_value * 100)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Valore Inizio Periodo", f"${first_value:,.2f}")
            with col2:
                st.metric("Valore Fine Periodo", f"${last_value:,.2f}")
            with col3:
                st.metric("Rendimento Periodo", f"{period_return:+.2f}%", 
                         delta=f"{period_return:+.2f}%")
    else:
        st.info("📊 Non ci sono dati storici ancora. Salva snapshot giornalmente per tracciare la performance.")
    
    st.markdown("---")
    
    # === P/L PER POSIZIONE ===
    st.markdown("### 💰 P/L per Posizione")
    
    df = get_portfolio_positions(portfolio_id)
    
    if not df.empty:
        pl_data = []
        
        for _, row in df.iterrows():
            ticker = row['ticker']
            pl = get_position_pl(portfolio_id, ticker)
            
            if pl:
                pl_data.append({
                    'Ticker': ticker,
                    'Azioni': pl['shares'],
                    'Prezzo Medio': f"${pl['avg_price']:.2f}",
                    'Prezzo Attuale': f"${pl['current_price']:.2f}",
                    'Costo': f"${pl['total_cost']:,.2f}",
                    'Valore': f"${pl['current_value']:,.2f}",
                    'Gain/Loss': f"${pl['gain_loss']:+,.2f}",
                    'Gain/Loss %': f"{pl['gain_loss_pct']:+.2f}%"
                })
        
        df_pl = pd.DataFrame(pl_data)
        st.dataframe(df_pl, use_container_width=True, hide_index=True)
        
        # Grafico P/L
        fig_pl = go.Figure()
        
        # Converti string a float per grafico
        df_pl['gain_loss_numeric'] = df_pl['Gain/Loss'].str.replace('$', '').str.replace(',', '').astype(float)
        
        colors = ['green' if x >= 0 else 'red' for x in df_pl['gain_loss_numeric']]
        
        fig_pl.add_trace(go.Bar(
            x=df_pl['Ticker'],
            y=df_pl['gain_loss_numeric'],
            marker_color=colors,
            text=df_pl['Gain/Loss %'],
            textposition='outside'
        ))
        
        fig_pl.update_layout(
            title="Gain/Loss per Titolo",
            xaxis_title="Ticker",
            yaxis_title="Gain/Loss ($)",
            template='plotly_white',
            height=400
        )
        
        st.plotly_chart(fig_pl, use_container_width=True)
        
        # Best & Worst performers
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏆 Top Performer")
            best_idx = df_pl['gain_loss_numeric'].idxmax()
            best = df_pl.iloc[best_idx]
            st.success(f"**{best['Ticker']}**: {best['Gain/Loss']} ({best['Gain/Loss %']})")
        
        with col2:
            st.markdown("#### 📉 Worst Performer")
            worst_idx = df_pl['gain_loss_numeric'].idxmin()
            worst = df_pl.iloc[worst_idx]
            st.error(f"**{worst['Ticker']}**: {worst['Gain/Loss']} ({worst['Gain/Loss %']})")
    
    st.markdown("---")
    
    # === ASSET ALLOCATION ===
    st.markdown("### 🎯 Asset Allocation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Per settore
        if 'sector' in df.columns:
            sector_df = df.groupby('sector').agg({
                'total_cost': 'sum'
            }).reset_index()
            
            fig_sector = px.pie(
                sector_df,
                values='total_cost',
                names='sector',
                title='Allocazione per Settore',
                hole=0.4
            )
            st.plotly_chart(fig_sector, use_container_width=True)
    
    with col2:
        # Per valuta
        if 'currency' in df.columns:
            currency_df = df.groupby('currency').agg({
                'total_cost': 'sum'
            }).reset_index()
            
            fig_currency = px.pie(
                currency_df,
                values='total_cost',
                names='currency',
                title='Allocazione per Valuta',
                hole=0.4
            )
            st.plotly_chart(fig_currency, use_container_width=True)
