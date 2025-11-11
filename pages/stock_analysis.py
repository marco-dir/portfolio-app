import streamlit as st
# Importa TUTTE le funzioni dal tuo codice esistente
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# COPIA TUTTE LE TUE FUNZIONI dal file allegato
# (fetch_data, fetch_company_profile, format_currency, ecc.)

import os

# ============================================
# CONFIGURAZIONE API KEY
FMP_API_KEY = os.getenv("MY_DATASET_API_KEY") # Inserisci la tua API key tra le virgolette

# Configurazione pagina
st.set_page_config(
    page_title="Analisi Finanziaria Titoli",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS per rimuovere TUTTI i link anchor da tutti i titoli
hide_all_anchor_links = """
    <style>
    /* Nasconde tutti i link anchor su tutti i livelli di titolo */
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Nasconde gli elementi anchor di Streamlit */
    .css-10trblm, .css-16idsys, .css-1dp5vir {
        display: none !important;
    }
    
    /* Metodo universale per tutte le versioni di Streamlit */
    [data-testid="stMarkdownContainer"] a[href^="#"] {
        display: none !important;
    }
    
    /* Nasconde specificamente i viewer badge */
    .viewerBadge_container__1QSob,
    .viewerBadge_link__1S137,
    .styles_viewerBadge__1yB5_,
    [class*="viewerBadge"] {
        display: none !important;
    }
    </style>
"""

st.markdown(hide_all_anchor_links, unsafe_allow_html=True)

# ============================================
# INIZIALIZZAZIONE SESSION STATE
# ============================================
if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False
if 'current_ticker' not in st.session_state:
    st.session_state.current_ticker = ""
if 'current_period' not in st.session_state:
    st.session_state.current_period = "annual"
if 'current_limit' not in st.session_state:
    st.session_state.current_limit = 10

# CSS personalizzato
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        font-size: 16px;
        font-weight: 500;
    }
    h1 {
        color: #1f77b4;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Titolo applicazione
st.title("Analisi Finanziaria Titoli Azionari")
st.markdown("---")

# Input controls sotto il titolo
col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

with col1:
    ticker = st.text_input(
        "Ticker",
        value="AAPL",
        help="Inserisci il ticker del titolo (es. AAPL, MSFT, ISP.MI, MC.PA, SAP.DE)"
    ).upper()

with col2:
    period = st.selectbox(
        "Periodo",
        ["annuale", "quarter"],
        help="Dati annuali o trimestrali"
    )

with col3:
    limit = st.slider(
        "Numero di periodi",
        min_value=5,
        max_value=20,
        value=10,
        help="Quanti periodi visualizzare"
    )

with col4:
    st.write("")  # Spacer
    st.write("")  # Spacer
    if st.button("🔍 Analizza", type="primary", use_container_width=True):
        st.session_state.analyzed = True
        st.session_state.current_ticker = ticker
        st.session_state.current_period = period
        st.session_state.current_limit = limit

st.markdown("---")

# Funzioni per recuperare i dati
@st.cache_data(ttl=3600)
def fetch_data(ticker, api_key, endpoint, period="annual", limit=10):
    """Recupera dati dall'API FMP"""
    base_url = "https://financialmodelingprep.com/api/v3"
    
    if endpoint == "insider":
        url = f"https://financialmodelingprep.com/api/v4/insider-trading?symbol={ticker}&limit={limit}&apikey={api_key}"
    else:
        url = f"{base_url}/{endpoint}/{ticker}?period={period}&limit={limit}&apikey={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Errore nel recupero dati {endpoint}: {str(e)}")
        return []

@st.cache_data(ttl=600)
def fetch_company_profile(ticker, api_key):
    """Recupera il profilo dell'azienda"""
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data[0] if isinstance(data, list) and len(data) > 0 else None
    except Exception as e:
        st.error(f"Errore nel recupero profilo: {str(e)}")
        return None

@st.cache_data(ttl=60)
def fetch_quote(ticker, api_key):
    """Recupera la quotazione in tempo reale"""
    url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data[0] if isinstance(data, list) and len(data) > 0 else None
    except Exception as e:
        st.error(f"Errore nel recupero quotazione: {str(e)}")
        return None

@st.cache_data(ttl=3600)
def fetch_historical_prices(ticker, api_key):
    """Recupera i prezzi storici dell'ultimo anno"""
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'historical' in data:
            return data['historical'][:365]
        return []
    except Exception as e:
        st.error(f"Errore nel recupero prezzi storici: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def fetch_company_news(ticker, api_key, limit=20):
    """Recupera le news della società"""
    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={ticker}&limit={limit}&apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Errore nel recupero news: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def fetch_earnings_calendar(ticker, api_key):
    """Recupera il calendario degli earnings"""
    url = f"https://financialmodelingprep.com/api/v3/historical/earning_calendar/{ticker}?apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Errore nel recupero calendario earnings: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def fetch_dividends_calendar(ticker, api_key):
    """Recupera lo storico dividendi"""
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/{ticker}?apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'historical' in data:
            return data['historical'][:20]  # Ultimi 20 dividendi
        return []
    except Exception as e:
        st.error(f"Errore nel recupero dividendi: {str(e)}")
        return []

def format_currency(value, currency="USD"):
    """Formatta valori monetari in base alla valuta"""
    if pd.isna(value) or value == 0:
        return f"{get_currency_symbol(currency)}0"
    
    abs_value = abs(value)
    symbol = get_currency_symbol(currency)
    sign = "-" if value < 0 else ""
    
    if abs_value >= 1e12:
        return f"{sign}{symbol}{abs_value/1e12:.2f}T"
    elif abs_value >= 1e9:
        return f"{sign}{symbol}{abs_value/1e9:.2f}B"
    elif abs_value >= 1e6:
        return f"{sign}{symbol}{abs_value/1e6:.2f}M"
    elif abs_value >= 1e3:
        return f"{sign}{symbol}{abs_value/1e3:.2f}K"
    else:
        return f"{sign}{symbol}{abs_value:.2f}"

def get_currency_symbol(currency):
    """Restituisce il simbolo della valuta"""
    currency_symbols = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'CHF': 'CHF ',
        'CAD': 'C$', 'AUD': 'A$', 'CNY': '¥', 'INR': '₹', 'BRL': 'R$',
        'KRW': '₩', 'MXN': 'Mex$', 'SEK': 'kr', 'NOK': 'kr', 'DKK': 'kr',
        'HKD': 'HK$', 'SGD': 'S$', 'NZD': 'NZ$', 'ZAR': 'R', 'TRY': '₺', 'RUB': '₽'
    }
    return currency_symbols.get(currency, currency + ' ')

def get_currency_from_exchange(exchange):
    """Determina la valuta in base all'exchange"""
    exchange_currency_map = {
        'NASDAQ': 'USD', 'NYSE': 'USD', 'NYSEARCA': 'USD', 'AMEX': 'USD', 'OTC': 'USD',
        'LSE': 'GBP', 'LON': 'GBP', 'XLON': 'GBP',
        'EURONEXT': 'EUR', 'EPA': 'EUR', 'PAR': 'EUR', 'FRA': 'EUR', 'XETRA': 'EUR',
        'BIT': 'EUR', 'MIL': 'EUR', 'BME': 'EUR', 'AMS': 'EUR', 'BRU': 'EUR', 'LIS': 'EUR',
        'SWX': 'CHF', 'TSX': 'CAD', 'TSXV': 'CAD',
        'ASX': 'AUD', 'NZX': 'NZD', 'JPX': 'JPY', 'TSE': 'JPY',
        'HKEX': 'HKD', 'SGX': 'SGD', 'SSE': 'CNY', 'SZSE': 'CNY',
        'BSE': 'INR', 'NSE': 'INR', 'BOVESPA': 'BRL', 'KRX': 'KRW',
        'BMV': 'MXN', 'OMX': 'SEK', 'OSE': 'NOK', 'CSE': 'DKK',
        'JSE': 'ZAR', 'BIST': 'TRY', 'MOEX': 'RUB'
    }
    
    exchange_upper = exchange.upper()
    for key, currency in exchange_currency_map.items():
        if key in exchange_upper:
            return currency
    
    return 'USD'

def safe_get(data, key, default=0):
    """Recupera in modo sicuro un valore dal dizionario"""
    value = data.get(key, default)
    return value if value is not None else default

def get_shares_outstanding(balance_data, income_data):
    """Recupera il numero di azioni outstanding dai dati disponibili"""
    if not balance_data:
        return 0
    
    latest_balance = balance_data[0]
    
    # Prova diversi campi possibili per le azioni
    shares = safe_get(latest_balance, 'commonStock', 0)
    
    # Se non disponibile nel balance sheet, prova dal conto economico
    if shares == 0 and income_data:
        latest_income = income_data[0]
        shares = safe_get(latest_income, 'weightedAverageShsOut', 0)
        if shares == 0:
            shares = safe_get(latest_income, 'weightedAverageShsOutDil', 0)
    
    return shares

def create_bar_chart(df, x_col, y_cols, title, yaxis_title="Valore", currency="USD"):
    """Crea grafico a barre interattivo"""
    fig = go.Figure()
    
    for col in y_cols:
        fig.add_trace(go.Bar(
            x=df[x_col],
            y=df[col],
            name=col
        ))
    
    currency_symbol = get_currency_symbol(currency)
    yaxis_title_with_currency = f"{yaxis_title} ({currency_symbol})"
    
    fig.update_layout(
        title=title,
        xaxis_title="Anno",
        yaxis_title=yaxis_title_with_currency,
        barmode='group',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_line_chart(df, x_col, y_cols, title, yaxis_title="Valore", currency=None):
    """Crea grafico a linee interattivo"""
    fig = go.Figure()
    
    for col in y_cols:
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[col],
            mode='lines+markers',
            name=col,
            line=dict(width=3),
            marker=dict(size=8)
        ))
    
    if currency and yaxis_title != "Percentuale (%)":
        currency_symbol = get_currency_symbol(currency)
        yaxis_title = f"{yaxis_title} ({currency_symbol})"
    
    fig.update_layout(
        title=title,
        xaxis_title="Anno",
        yaxis_title=yaxis_title,
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_mini_price_chart(historical_data, currency="USD"):
    """Crea un mini grafico dei prezzi dell'ultimo anno"""
    if not historical_data:
        return None
    
    df = pd.DataFrame(historical_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    first_price = df['close'].iloc[0]
    last_price = df['close'].iloc[-1]
    change_pct = ((last_price - first_price) / first_price) * 100
    
    # Colori in formato RGB
    if change_pct >= 0:
        line_color = 'rgb(0, 200, 83)'  # Verde
        fill_color = 'rgba(0, 200, 83, 0.1)'  # Verde con trasparenza
    else:
        line_color = 'rgb(255, 59, 48)'  # Rosso
        fill_color = 'rgba(255, 59, 48, 0.1)'  # Rosso con trasparenza
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['close'],
        mode='lines',
        line=dict(color=line_color, width=2),
        fill='tozeroy',
        fillcolor=fill_color,
        hovertemplate='<b>%{x|%d %b %Y}</b><br>Prezzo: ' + get_currency_symbol(currency) + '%{y:.2f}<extra></extra>',
        showlegend=False
    ))
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=120,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified'
    )
    
    return fig, change_pct

def show(user_id):
    """
    Mostra pagina analisi titoli.
    Integra con bottone "Aggiungi al Portafoglio".
    """

# Main logic
if st.session_state.analyzed:
    # Usa i valori salvati nel session state
    ticker = st.session_state.current_ticker
    period = st.session_state.current_period
    limit = st.session_state.current_limit
    api_key = FMP_API_KEY
    
    if not api_key:
        st.error("⚠️ Inserisci la tua API Key FMP o configurala nel codice")
    elif not ticker:
        st.error("⚠️ Inserisci un ticker valido")
    else:
        with st.spinner(f"Recupero dati per {ticker}..."):
            company_profile = fetch_company_profile(ticker, api_key)
            quote = fetch_quote(ticker, api_key)
            historical_prices = fetch_historical_prices(ticker, api_key)
            
            income_data = fetch_data(ticker, api_key, "income-statement", period, limit)
            balance_data = fetch_data(ticker, api_key, "balance-sheet-statement", period, limit)
            cashflow_data = fetch_data(ticker, api_key, "cash-flow-statement", period, limit)
            ratios_data = fetch_data(ticker, api_key, "ratios", period, limit)
            estimates_data = fetch_data(ticker, api_key, "analyst-estimates", period, min(5, limit))
            insider_data = fetch_data(ticker, api_key, "insider", limit=50)
            
            # Nuove funzioni per le tab aggiuntive
            news_data = fetch_company_news(ticker, api_key, limit=20)
            earnings_calendar = fetch_earnings_calendar(ticker, api_key)
            dividends_data = fetch_dividends_calendar(ticker, api_key)
            
            if not income_data:
                st.error("❌ Nessun dato trovato. Verifica il ticker e la tua API key.")
            else:
                currency = 'USD'
                if company_profile:
                    exchange = company_profile.get('exchangeShortName', 'NASDAQ')
                    currency = get_currency_from_exchange(exchange)
                
                if company_profile and quote:
                    st.markdown("---")
                    
                    col_name, col_chart, col_price, col_change, col_cap, col_sector = st.columns([1.5, 2, 1, 1, 1, 1])
                    
                    with col_name:
                        company_name = company_profile.get('companyName', ticker)
                        st.markdown(f"### {company_name}")
                        st.markdown(f"**{ticker}** • {company_profile.get('exchangeShortName', 'N/A')}")
                    
                    with col_chart:
                        if historical_prices:
                            chart_result = create_mini_price_chart(historical_prices, currency)
                            if chart_result:
                                mini_chart, change_1y = chart_result
                                st.markdown(f"<div style='text-align: center; font-size: 0.9em; color: {'#00C853' if change_1y >= 0 else '#FF3B30'}; font-weight: bold; margin-bottom: 5px;'>1 Anno: {'+' if change_1y >= 0 else ''}{change_1y:.2f}%</div>", unsafe_allow_html=True)
                                st.plotly_chart(mini_chart, use_container_width=True, config={'displayModeBar': False})
                    
                    with col_price:
                        price = quote.get('price', 0)
                        currency_symbol = get_currency_symbol(currency)
                        st.metric("Prezzo", f"{currency_symbol}{price:.2f}", delta=None)
                    
                    with col_change:
                        change = quote.get('change', 0)
                        change_percent = quote.get('changesPercentage', 0)
                        st.metric("Variazione", f"{currency_symbol}{change:.2f}", delta=f"{change_percent:.2f}%")
                    
                    with col_cap:
                        market_cap = company_profile.get('mktCap', 0)
                        st.metric("Capitalizzazione", format_currency(market_cap, currency))
                    
                    with col_sector:
                        sector = company_profile.get('sector', 'N/A')
                        industry = company_profile.get('industry', '')
                        st.markdown("**Settore**")
                        st.markdown(f"{sector}")
                        if industry:
                            st.caption(industry)
                
                st.markdown("---")
                st.success(f"✅ Dati caricati con successo per {ticker}")
                
                tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
                    "**Conto Economico**",
                    "**Stato Patrimoniale**", 
                    "**Cash Flow**",
                    "**Key Ratios**",
                    "**Valutazione**",
                    "**Stime Analisti**",
                    "**Insider Trading**",
                    "**Info Società**",
                    "**News**",
                    "**Calendario**"
                ])
                
                # TAB 1: Conto Economico
                with tab1:
                    st.header("Conto Economico")
                    
                    if income_data:
                        df_income = pd.DataFrame(income_data).sort_values('date')
                        df_income['year'] = pd.to_datetime(df_income['date']).dt.year.astype(str)
                        
                        col1, col2, col3, col4, col5 = st.columns(5)
                        latest = income_data[0]
                        
                        with col1:
                            st.metric("Ricavi", format_currency(safe_get(latest, 'revenue'), currency))
                        with col2:
                            st.metric("Utile Lordo", format_currency(safe_get(latest, 'grossProfit'), currency))
                        with col3:
                            st.metric("EBITDA", format_currency(safe_get(latest, 'ebitda'), currency))
                        with col4:
                            st.metric("Utile Operativo", format_currency(safe_get(latest, 'operatingIncome'), currency))
                        with col5:
                            st.metric("Utile Netto", format_currency(safe_get(latest, 'netIncome'), currency))
                        
                        col1, col2, col3, col4, col5 = st.columns(5)
                        
                        with col1:
                            eps = safe_get(latest, 'eps')
                            st.metric("EPS", f"{get_currency_symbol(currency)}{eps:.2f}" if eps else "N/A")
                        with col2:
                            revenue = safe_get(latest, 'revenue', 1)
                            gross_margin = (safe_get(latest, 'grossProfit') / revenue) * 100 if revenue > 0 else 0
                            st.metric("Margine Lordo", f"{gross_margin:.1f}%")
                        with col3:
                            operating_margin = (safe_get(latest, 'operatingIncome') / revenue) * 100 if revenue > 0 else 0
                            st.metric("Margine Operativo", f"{operating_margin:.1f}%")
                        with col4:
                            net_margin = (safe_get(latest, 'netIncome') / revenue) * 100 if revenue > 0 else 0
                            st.metric("Margine Netto", f"{net_margin:.1f}%")
                        with col5:
                            shares_out = safe_get(latest, 'weightedAverageShsOutDil')
                            if shares_out == 0:
                                shares_out = safe_get(latest, 'weightedAverageShsOut')
                            
                            if shares_out >= 1e9:
                                st.metric("Azioni (Diluito)", f"{shares_out/1e9:.2f}B")
                            elif shares_out >= 1e6:
                                st.metric("Azioni (Diluito)", f"{shares_out/1e6:.2f}M")
                            else:
                                st.metric("Azioni (Diluito)", f"{shares_out:,.0f}" if shares_out > 0 else "N/A")
                        
                        st.markdown("---")
                        
                        st.subheader("Visualizza Grafico")
                        income_options = {
                            'Ricavi': 'revenue',
                            'Costo del Venduto': 'costOfRevenue',
                            'Utile Lordo': 'grossProfit',
                            'Spese R&D': 'researchAndDevelopmentExpenses',
                            'Spese Generali e Amministrative': 'generalAndAdministrativeExpenses',
                            'Spese di Vendita e Marketing': 'sellingAndMarketingExpenses',
                            'Spese Operative Totali': 'operatingExpenses',
                            'Costi e Spese': 'costAndExpenses',
                            'Interessi Passivi': 'interestExpense',
                            'Interessi Attivi': 'interestIncome',
                            'Ammortamenti': 'depreciationAndAmortization',
                            'EBITDA': 'ebitda',
                            'EBITDA Ratio': 'ebitdaratio',
                            'Utile Operativo': 'operatingIncome',
                            'Utile Operativo Ratio': 'operatingIncomeRatio',
                            'Altri Ricavi/Spese': 'totalOtherIncomeExpensesNet',
                            'Utile ante Imposte': 'incomeBeforeTax',
                            'Imposte sul Reddito': 'incomeTaxExpense',
                            'Utile Netto': 'netIncome',
                            'EPS': 'eps',
                            'EPS Diluito': 'epsdiluted',
                            'Azioni Outstanding': 'weightedAverageShsOut',
                            'Azioni Outstanding Diluito': 'weightedAverageShsOutDil'
                        }
                        
                        selected_income = st.multiselect(
                            "Seleziona i dati da visualizzare:",
                            options=list(income_options.keys()),
                            default=['Ricavi', 'Utile Lordo', 'EBITDA', 'Utile Netto'],
                            key='income_select'
                        )
                        
                        if selected_income:
                            df_chart = df_income[['year'] + [income_options[col] for col in selected_income]].copy()
                            df_chart = df_chart.rename(columns={income_options[col]: col for col in selected_income})
                            
                            fig = create_bar_chart(df_chart, 'year', selected_income, 'Andamento Ricavi e Profitti', 'Valore', currency)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Seleziona almeno un dato da visualizzare")
                        
                        st.subheader("Dati Dettagliati")
                        display_df = pd.DataFrame({
                            'Anno': df_income['year'],
                            'Ricavi': df_income['revenue'].apply(lambda x: format_currency(x, currency)),
                            'Costo Venduto': df_income['costOfRevenue'].apply(lambda x: format_currency(x, currency)),
                            'Utile Lordo': df_income['grossProfit'].apply(lambda x: format_currency(x, currency)),
                            'Utile Operativo': df_income['operatingIncome'].apply(lambda x: format_currency(x, currency)),
                            'Utile Netto': df_income['netIncome'].apply(lambda x: format_currency(x, currency)),
                            'EPS': df_income['eps'].apply(lambda x: f"{get_currency_symbol(currency)}{x:.2f}" if pd.notna(x) else "N/A")
                        }).sort_values('Anno', ascending=False)
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # TAB 2: Stato Patrimoniale
                with tab2:
                    st.header("Stato Patrimoniale")
                    
                    if balance_data:
                        df_balance = pd.DataFrame(balance_data).sort_values('date')
                        df_balance['year'] = pd.to_datetime(df_balance['date']).dt.year.astype(str)
                        
                        col1, col2, col3, col4, col5 = st.columns(5)
                        latest = balance_data[0]
                        
                        with col1:
                            st.metric("Attività Totali", format_currency(safe_get(latest, 'totalAssets'), currency))
                        with col2:
                            st.metric("Passività Totali", format_currency(safe_get(latest, 'totalLiabilities'), currency))
                        with col3:
                            equity = safe_get(latest, 'totalStockholdersEquity')
                            if equity == 0:
                                equity = safe_get(latest, 'totalEquity')
                            st.metric("Patrimonio Netto", format_currency(equity, currency))
                        with col4:
                            st.metric("Book Value", format_currency(equity, currency))
                        with col5:
                            shares = get_shares_outstanding(balance_data, income_data)
                            if shares >= 1e9:
                                st.metric("Azioni Outstanding", f"{shares/1e9:.2f}B")
                            elif shares >= 1e6:
                                st.metric("Azioni Outstanding", f"{shares/1e6:.2f}M")
                            else:
                                st.metric("Azioni Outstanding", f"{shares:,.0f}" if shares > 0 else "N/A")
                        
                        st.markdown("---")
                        
                        st.subheader("Visualizza Grafico")
                        balance_options = {
                            'Attività Totali': 'totalAssets',
                            'Attività Correnti': 'totalCurrentAssets',
                            'Attività Non Correnti': 'totalNonCurrentAssets',
                            'Cassa e Equivalenti': 'cashAndCashEquivalents',
                            'Cassa e Investimenti a Breve': 'cashAndShortTermInvestments',
                            'Crediti': 'netReceivables',
                            'Inventario': 'inventory',
                            'Altre Attività Correnti': 'otherCurrentAssets',
                            'Immobilizzazioni Materiali': 'propertyPlantEquipmentNet',
                            'Avviamento': 'goodwill',
                            'Attività Immateriali': 'intangibleAssets',
                            'Goodwill e Immateriali': 'goodwillAndIntangibleAssets',
                            'Investimenti a Lungo Termine': 'longTermInvestments',
                            'Crediti Fiscali': 'taxAssets',
                            'Altre Attività Non Correnti': 'otherNonCurrentAssets',
                            'Passività Totali': 'totalLiabilities',
                            'Passività Correnti': 'totalCurrentLiabilities',
                            'Passività Non Correnti': 'totalNonCurrentLiabilities',
                            'Debiti Fornitori': 'accountPayables',
                            'Debito a Breve Termine': 'shortTermDebt',
                            'Debito a Lungo Termine': 'longTermDebt',
                            'Debito Totale': 'totalDebt',
                            'Debito Netto': 'netDebt',
                            'Ratei e Risconti Passivi': 'deferredRevenue',
                            'Altri Debiti Correnti': 'otherCurrentLiabilities',
                            'Altri Debiti Non Correnti': 'otherNonCurrentLiabilities',
                            'Debiti Fiscali': 'taxPayables',
                            'Fondi TFR': 'deferredRevenueNonCurrent',
                            'Capitale Sociale': 'commonStock',
                            'Utili Portati a Nuovo': 'retainedEarnings',
                            'Altre Riserve': 'accumulatedOtherComprehensiveIncomeLoss',
                            'Patrimonio Netto': 'totalStockholdersEquity',
                            'Azioni Proprie': 'treasuryStock',
                            'Interessi Minority': 'minorityInterest',
                            'Totale Equity': 'totalEquity',
                            'Totale Passività e Equity': 'totalLiabilitiesAndStockholdersEquity',
                            'Investimenti Totali': 'totalInvestments',
                            'Capitale Investito Totale': 'totalLiabilitiesAndTotalEquity',
                            'Capitale Circolante': 'totalCurrentAssets'
                        }
                        
                        selected_balance = st.multiselect(
                            "Seleziona i dati da visualizzare:",
                            options=list(balance_options.keys()),
                            default=['Attività Totali', 'Passività Totali', 'Patrimonio Netto'],
                            key='balance_select'
                        )
                        
                        if selected_balance:
                            df_chart = df_balance[['year'] + [balance_options[col] for col in selected_balance]].copy()
                            df_chart = df_chart.rename(columns={balance_options[col]: col for col in selected_balance})
                            
                            fig = create_bar_chart(df_chart, 'year', selected_balance, 'Composizione Patrimoniale', 'Valore', currency)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Seleziona almeno un dato da visualizzare")
                        
                        st.subheader("Dati Dettagliati")
                        display_df = pd.DataFrame({
                            'Anno': df_balance['year'],
                            'Attività Correnti': df_balance['totalCurrentAssets'].apply(lambda x: format_currency(x, currency)),
                            'Attività Totali': df_balance['totalAssets'].apply(lambda x: format_currency(x, currency)),
                            'Passività Correnti': df_balance['totalCurrentLiabilities'].apply(lambda x: format_currency(x, currency)),
                            'Passività Totali': df_balance['totalLiabilities'].apply(lambda x: format_currency(x, currency)),
                            'Patrimonio Netto': df_balance['totalStockholdersEquity'].apply(lambda x: format_currency(x, currency)),
                            'Debito Totale': df_balance['totalDebt'].apply(lambda x: format_currency(x, currency)),
                            'Cassa': df_balance['cashAndCashEquivalents'].apply(lambda x: format_currency(x, currency))
                        }).sort_values('Anno', ascending=False)
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # TAB 3: Cash Flow
                with tab3:
                    st.header("Rendiconto Finanziario")
                    
                    if cashflow_data:
                        df_cashflow = pd.DataFrame(cashflow_data).sort_values('date')
                        df_cashflow['year'] = pd.to_datetime(df_cashflow['date']).dt.year.astype(str)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        latest = cashflow_data[0]
                        
                        with col1:
                            st.metric("CF Operativo", format_currency(safe_get(latest, 'operatingCashFlow'), currency))
                        with col2:
                            investing_cf = safe_get(latest, 'netCashUsedForInvestingActivites')
                            if investing_cf == 0:
                                investing_cf = safe_get(latest, 'cashFlowFromInvestment')
                            st.metric("CF Investimenti", format_currency(investing_cf, currency))
                        with col3:
                            financing_cf = safe_get(latest, 'netCashUsedProvidedByFinancingActivities')
                            if financing_cf == 0:
                                financing_cf = safe_get(latest, 'cashFlowFromFinancing')
                            st.metric("CF Finanziario", format_currency(financing_cf, currency))
                        with col4:
                            st.metric("Free Cash Flow", format_currency(safe_get(latest, 'freeCashFlow'), currency))
                        
                        st.markdown("---")
                        
                        st.subheader("Visualizza Grafico")
                        cashflow_options = {
                            'CF Operativo': 'operatingCashFlow',
                            'CF Investimenti': 'netCashUsedForInvestingActivites',
                            'CF Finanziario': 'netCashUsedProvidedByFinancingActivities',
                            'Utile Netto': 'netIncome',
                            'Ammortamenti': 'depreciationAndAmortization',
                            'Imposte Differite': 'deferredIncomeTax',
                            'Stock Based Compensation': 'stockBasedCompensation',
                            'Variazione Capitale Circolante': 'changeInWorkingCapital',
                            'Variazione Crediti': 'accountsReceivables',
                            'Variazione Inventario': 'inventory',
                            'Variazione Debiti Fornitori': 'accountsPayables',
                            'Altre Attività/Passività': 'otherWorkingCapital',
                            'Altri CF Non Cash': 'otherNonCashItems',
                            'CF da Investimenti': 'cashFlowFromInvestment',
                            'Investimenti in Immobilizzazioni': 'investmentsInPropertyPlantAndEquipment',
                            'Acquisizioni Nette': 'acquisitionsNet',
                            'Acquisto Investimenti': 'purchasesOfInvestments',
                            'Vendita Investimenti': 'salesMaturitiesOfInvestments',
                            'Altri CF da Investimenti': 'otherInvestingActivites',
                            'CF da Finanziamenti': 'cashFlowFromFinancing',
                            'Rimborso Debito': 'debtRepayment',
                            'Emissione Azioni Ordinarie': 'commonStockIssued',
                            'Riacquisto Azioni Proprie': 'commonStockRepurchased',
                            'Dividendi Pagati': 'dividendsPaid',
                            'Altri CF da Finanziamenti': 'otherFinancingActivites',
                            'Free Cash Flow': 'freeCashFlow',
                            'Capex': 'capitalExpenditure',
                            'Variazione Cassa Netta': 'netChangeInCash',
                            'Cassa Inizio Periodo': 'cashAtBeginningOfPeriod',
                            'Cassa Fine Periodo': 'cashAtEndOfPeriod',
                            'CF Operativo per Azione': 'operatingCashFlowPerShare',
                            'FCF per Azione': 'freeCashFlowPerShare'
                        }
                        
                        selected_cashflow = st.multiselect(
                            "Seleziona i dati da visualizzare:",
                            options=list(cashflow_options.keys()),
                            default=['CF Operativo', 'Free Cash Flow'],
                            key='cashflow_select'
                        )
                        
                        if selected_cashflow:
                            df_chart = df_cashflow[['year'] + [cashflow_options[col] for col in selected_cashflow]].copy()
                            df_chart = df_chart.rename(columns={cashflow_options[col]: col for col in selected_cashflow})
                            
                            fig = create_bar_chart(df_chart, 'year', selected_cashflow, 'Flussi di Cassa', 'Valore', currency)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Seleziona almeno un dato da visualizzare")
                        
                        st.subheader("Dati Dettagliati")
                        display_df = pd.DataFrame({
                            'Anno': df_cashflow['year'],
                            'CF Operativo': df_cashflow['operatingCashFlow'].apply(lambda x: format_currency(x, currency)),
                            'CF Investimenti': df_cashflow['netCashUsedForInvestingActivites'].apply(lambda x: format_currency(x, currency)),
                            'CF Finanziario': df_cashflow['netCashUsedProvidedByFinancingActivities'].apply(lambda x: format_currency(x, currency)),
                            'Free Cash Flow': df_cashflow['freeCashFlow'].apply(lambda x: format_currency(x, currency)),
                            'Dividendi': df_cashflow['dividendsPaid'].apply(lambda x: format_currency(x, currency))
                        }).sort_values('Anno', ascending=False)
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # TAB 4: Key Ratios
                with tab4:
                    st.header("Indicatori Chiave")
                    
                    if ratios_data:
                        df_ratios = pd.DataFrame(ratios_data).sort_values('date')
                        df_ratios['year'] = pd.to_datetime(df_ratios['date']).dt.year.astype(str)
                        
                        col1, col2, col3, col4, col5 = st.columns(5)
                        latest = ratios_data[0]
                        
                        with col1:
                            pe = safe_get(latest, 'priceEarningsRatio')
                            st.metric("P/E Ratio", f"{pe:.2f}" if pe else "N/A")
                        with col2:
                            roe = safe_get(latest, 'returnOnEquity') * 100
                            st.metric("ROE", f"{roe:.2f}%" if roe else "N/A")
                        with col3:
                            roa = safe_get(latest, 'returnOnAssets') * 100
                            st.metric("ROA", f"{roa:.2f}%" if roa else "N/A")
                        with col4:
                            debt_eq = safe_get(latest, 'debtEquityRatio')
                            st.metric("Debt/Equity", f"{debt_eq:.2f}" if debt_eq else "N/A")
                        with col5:
                            payout = safe_get(latest, 'payoutRatio')
                            st.metric("Payout Ratio", f"{payout*100:.1f}%" if payout else "N/A")
                        
                        st.markdown("---")
                        
                        st.subheader("Visualizza Grafico")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Redditività (%)**")
                            profitability_options = {
                                'ROE': 'returnOnEquity',
                                'ROA': 'returnOnAssets',
                                'ROIC': 'returnOnCapitalEmployed',
                                'ROCE': 'returnOnCapitalEmployed',
                                'ROI': 'returnOnCapitalEmployed',
                                'Gross Profit Margin': 'grossProfitMargin',
                                'Operating Profit Margin': 'operatingProfitMargin',
                                'Pretax Profit Margin': 'pretaxProfitMargin',
                                'Net Profit Margin': 'netProfitMargin',
                                'EBITDA Margin': 'ebitdaMargin',
                                'Operating Income Margin': 'operatingIncomeMargin',
                                'Return On Tangible Assets': 'returnOnTangibleAssets',
                                'Dividend Yield': 'dividendYield',
                                'Earnings Yield': 'earningsYield',
                                'Dividend Payout Ratio': 'payoutRatio',
                                'Effective Tax Rate': 'effectiveTaxRate',
                                'Free Cash Flow Yield': 'freeCashFlowYield',
                                'Income Quality': 'incomeQuality'
                            }
                            
                            selected_profitability = st.multiselect(
                                "Seleziona indicatori di redditività:",
                                options=list(profitability_options.keys()),
                                default=['ROE', 'ROA', 'Net Profit Margin'],
                                key='profitability_select'
                            )
                            
                            if selected_profitability:
                                df_chart1 = df_ratios[['year'] + [profitability_options[col] for col in selected_profitability]].copy()
                                for col in selected_profitability:
                                    df_chart1[col] = df_chart1[profitability_options[col]] * 100
                                    df_chart1.drop(profitability_options[col], axis=1, inplace=True)
                                
                                fig1 = create_line_chart(df_chart1, 'year', selected_profitability, 'Indicatori di Redditività', 'Percentuale (%)')
                                st.plotly_chart(fig1, use_container_width=True)
                        
                        with col2:
                            st.markdown("**Solidità Finanziaria**")
                            leverage_options = {
                                'Current Ratio': 'currentRatio',
                                'Quick Ratio': 'quickRatio',
                                'Cash Ratio': 'cashRatio',
                                'Debt/Equity': 'debtEquityRatio',
                                'Debt Ratio': 'debtRatio',
                                'Long Term Debt to Capitalization': 'longTermDebtToCapitalization',
                                'Total Debt to Capitalization': 'totalDebtToCapitalization',
                                'Interest Coverage': 'interestCoverage',
                                'Cash Flow to Debt Ratio': 'cashFlowToDebtRatio',
                                'Company Equity Multiplier': 'companyEquityMultiplier',
                                'Receivables Turnover': 'receivablesTurnover',
                                'Payables Turnover': 'payablesTurnover',
                                'Inventory Turnover': 'inventoryTurnover',
                                'Fixed Asset Turnover': 'fixedAssetTurnover',
                                'Asset Turnover': 'assetTurnover',
                                'Operating Cycle': 'operatingCycle',
                                'Cash Conversion Cycle': 'cashConversionCycle',
                                'Days Sales Outstanding': 'daysOfSalesOutstanding',
                                'Days Payables Outstanding': 'daysOfPayablesOutstanding',
                                'Days Inventory Outstanding': 'daysOfInventoryOnHand',
                                'Capex to Operating Cash Flow': 'capexToOperatingCashFlow',
                                'Capex to Revenue': 'capexToRevenue',
                                'Capex to Depreciation': 'capexToDepreciation',
                                'Cash Per Share': 'cashPerShare',
                                'Operating Cash Flow Per Share': 'operatingCashFlowPerShare',
                                'Free Cash Flow Per Share': 'freeCashFlowPerShare'
                            }
                            
                            selected_leverage = st.multiselect(
                                "Seleziona indicatori di solidità:",
                                options=list(leverage_options.keys()),
                                default=['Current Ratio', 'Debt/Equity', 'Interest Coverage'],
                                key='leverage_select'
                            )
                            
                            if selected_leverage:
                                df_chart2 = df_ratios[['year'] + [leverage_options[col] for col in selected_leverage]].copy()
                                df_chart2 = df_chart2.rename(columns={leverage_options[col]: col for col in selected_leverage})
                                
                                fig2 = create_line_chart(df_chart2, 'year', selected_leverage, 'Indicatori di Solidità Finanziaria', 'Ratio')
                                st.plotly_chart(fig2, use_container_width=True)
                        
                        st.subheader("Dati Dettagliati")
                        display_df = pd.DataFrame({
                            'Anno': df_ratios['year'],
                            'P/E': df_ratios['priceEarningsRatio'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"),
                            'P/B': df_ratios.get('priceToBookRatio', pd.Series([0]*len(df_ratios))).apply(lambda x: f"{x:.2f}" if pd.notna(x) and x != 0 else "N/A"),
                            'P/S': df_ratios.get('priceToSalesRatio', pd.Series([0]*len(df_ratios))).apply(lambda x: f"{x:.2f}" if pd.notna(x) and x != 0 else "N/A"),
                            'ROE (%)': (df_ratios['returnOnEquity']*100).apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"),
                            'ROA (%)': (df_ratios['returnOnAssets']*100).apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"),
                            'Current Ratio': df_ratios['currentRatio'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"),
                            'Quick Ratio': df_ratios.get('quickRatio', pd.Series([0]*len(df_ratios))).apply(lambda x: f"{x:.2f}" if pd.notna(x) and x != 0 else "N/A"),
                            'Debt/Equity': df_ratios['debtEquityRatio'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"),
                            'Interest Coverage': df_ratios.get('interestCoverage', pd.Series([0]*len(df_ratios))).apply(lambda x: f"{x:.2f}" if pd.notna(x) and x != 0 else "N/A"),
                            'Gross Margin (%)': (df_ratios.get('grossProfitMargin', pd.Series([0]*len(df_ratios)))*100).apply(lambda x: f"{x:.2f}%" if pd.notna(x) and x != 0 else "N/A"),
                            'Net Margin (%)': (df_ratios.get('netProfitMargin', pd.Series([0]*len(df_ratios)))*100).apply(lambda x: f"{x:.2f}%" if pd.notna(x) and x != 0 else "N/A"),
                            'Dividend Yield (%)': (df_ratios.get('dividendYield', pd.Series([0]*len(df_ratios)))*100).apply(lambda x: f"{x:.2f}%" if pd.notna(x) and x != 0 else "N/A"),
                            'Payout Ratio (%)': (df_ratios['payoutRatio']*100).apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
                        }).sort_values('Anno', ascending=False)
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # TAB 5: Valutazione
                with tab5:
                    st.header("Valutazione Intrinseca")
                    
                    if income_data and balance_data and cashflow_data and quote:
                        st.info("💡 Questa sezione calcola il valore intrinseco del titolo utilizzando diversi modelli di valutazione finanziaria.")
                        
                        # Dati necessari
                        current_price = quote.get('price', 0)
                        latest_income = income_data[0]
                        latest_balance = balance_data[0]
                        latest_cashflow = cashflow_data[0]
                        
                        # Recupera i dati storici per calcolare i tassi di crescita
                        df_income_hist = pd.DataFrame(income_data).sort_values('date', ascending=False)
                        df_cashflow_hist = pd.DataFrame(cashflow_data).sort_values('date', ascending=False)
                        
                        # === PARAMETRI DI INPUT ===
                        st.markdown("---")
                        st.subheader(" Parametri di Valutazione")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            discount_rate = st.number_input(
                                "Tasso di Sconto (WACC) %",
                                min_value=1.0,
                                max_value=20.0,
                                value=10.0,
                                step=0.5,
                                help="Weighted Average Cost of Capital - tipicamente 8-12%"
                            ) / 100
                        
                        with col2:
                            terminal_growth = st.number_input(
                                "Crescita Terminale %",
                                min_value=0.0,
                                max_value=5.0,
                                value=2.5,
                                step=0.5,
                                help="Tasso di crescita perpetua - tipicamente 2-3%"
                            ) / 100
                        
                        with col3:
                            projection_years = st.number_input(
                                "Anni di Proiezione",
                                min_value=3,
                                max_value=10,
                                value=5,
                                step=1,
                                help="Periodo di proiezione esplicita"
                            )
                        
                        with col4:
                            # Calcola crescita media storica FCF
                            if len(df_cashflow_hist) >= 3:
                                fcf_values = df_cashflow_hist['freeCashFlow'].head(5).values
                                fcf_growth_rates = []
                                for i in range(len(fcf_values)-1):
                                    if fcf_values[i+1] != 0 and fcf_values[i] != 0:
                                        growth = ((fcf_values[i] / fcf_values[i+1]) - 1) * 100
                                        if -50 < growth < 200:  # Filtro per valori outlier
                                            fcf_growth_rates.append(growth)
                                avg_fcf_growth = sum(fcf_growth_rates) / len(fcf_growth_rates) if fcf_growth_rates else 5.0
                                # Limita il valore suggerito tra -10 e 100 per evitare errori
                                avg_fcf_growth = max(-10.0, min(100.0, avg_fcf_growth))
                            else:
                                avg_fcf_growth = 5.0
                            
                            fcf_growth = st.number_input(
                                "Crescita FCF Prevista %",
                                min_value=-10.0,
                                max_value=100.0,
                                value=round(avg_fcf_growth, 1),
                                step=1.0,
                                help="Tasso di crescita atteso del Free Cash Flow"
                            ) / 100
                        
                        st.markdown("---")
                        
                        # === CALCOLI ===
                        
                        # 1. DCF Model (Discounted Cash Flow)
                        st.subheader("1. DCF - Discounted Cash Flow")
                        
                        fcf_current = safe_get(latest_cashflow, 'freeCashFlow', 0)
                        
                        if fcf_current > 0:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Proiezioni FCF
                                fcf_projections = []
                                for year in range(1, projection_years + 1):
                                    fcf_projected = fcf_current * ((1 + fcf_growth) ** year)
                                    pv = fcf_projected / ((1 + discount_rate) ** year)
                                    fcf_projections.append({
                                        'Anno': year,
                                        'FCF Proiettato': fcf_projected,
                                        'Valore Attuale': pv
                                    })
                                
                                df_fcf = pd.DataFrame(fcf_projections)
                                
                                # Terminal Value
                                fcf_terminal_year = fcf_current * ((1 + fcf_growth) ** projection_years)
                                terminal_value = (fcf_terminal_year * (1 + terminal_growth)) / (discount_rate - terminal_growth)
                                terminal_value_pv = terminal_value / ((1 + discount_rate) ** projection_years)
                                
                                # Enterprise Value
                                pv_fcf_sum = df_fcf['Valore Attuale'].sum()
                                enterprise_value = pv_fcf_sum + terminal_value_pv
                                
                                # Equity Value
                                cash = safe_get(latest_balance, 'cashAndCashEquivalents', 0)
                                total_debt = safe_get(latest_balance, 'totalDebt', 0)
                                equity_value = enterprise_value + cash - total_debt
                                
                                # Shares e Valore per Azione
                                shares = safe_get(latest_income, 'weightedAverageShsOutDil', 0)
                                if shares == 0:
                                    shares = safe_get(latest_income, 'weightedAverageShsOut', 0)
                                
                                intrinsic_value_dcf = equity_value / shares if shares > 0 else 0
                                
                                # Metriche
                                st.metric("FCF Corrente", format_currency(fcf_current, currency))
                                st.metric("Enterprise Value", format_currency(enterprise_value, currency))
                                st.metric("Equity Value", format_currency(equity_value, currency))
                                st.metric("Valore Intrinseco DCF", f"{get_currency_symbol(currency)}{intrinsic_value_dcf:.2f}")
                                
                                if intrinsic_value_dcf > 0:
                                    upside_dcf = ((intrinsic_value_dcf - current_price) / current_price) * 100
                                    st.metric("Upside/Downside", f"{upside_dcf:+.1f}%", 
                                             delta=f"{upside_dcf:+.1f}%",
                                             delta_color="normal")
                            
                            with col2:
                                st.markdown("**Proiezioni Free Cash Flow**")
                                
                                # Mostra tabella proiezioni
                                display_fcf = df_fcf.copy()
                                display_fcf['FCF Proiettato'] = display_fcf['FCF Proiettato'].apply(lambda x: format_currency(x, currency))
                                display_fcf['Valore Attuale'] = display_fcf['Valore Attuale'].apply(lambda x: format_currency(x, currency))
                                st.dataframe(display_fcf, use_container_width=True, hide_index=True)
                                
                                st.markdown(f"**Terminal Value:** {format_currency(terminal_value, currency)}")
                                st.markdown(f"**Terminal Value (PV):** {format_currency(terminal_value_pv, currency)}")
                                st.markdown(f"**Somma VP FCF:** {format_currency(pv_fcf_sum, currency)}")
                        else:
                            st.warning("⚠️ Free Cash Flow non disponibile o negativo per il DCF")
                        
                        st.markdown("---")
                        
                        # 2. DDM Model (Dividend Discount Model)
                        st.subheader("2. DDM - Dividend Discount Model (Gordon Growth)")
                        
                        # Recupera dividendi
                        dividend_per_share = safe_get(latest_income, 'eps', 0) * safe_get(ratios_data[0] if ratios_data else {}, 'payoutRatio', 0)
                        
                        if dividend_per_share > 0:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Calcola crescita dividendi storica
                                dividends_hist = fetch_dividends_calendar(ticker, api_key)
                                if dividends_hist and len(dividends_hist) >= 8:
                                    df_div = pd.DataFrame(dividends_hist)
                                    recent_divs = df_div.head(4)['dividend'].sum()
                                    old_divs = df_div.iloc[4:8]['dividend'].sum()
                                    
                                    if old_divs > 0:
                                        div_growth_hist = ((recent_divs / old_divs) ** 0.25 - 1)  # CAGR annualizzato
                                    else:
                                        div_growth_hist = terminal_growth
                                else:
                                    div_growth_hist = terminal_growth
                                
                                # Gordon Growth Model: P = D1 / (r - g)
                                next_dividend = dividend_per_share * (1 + div_growth_hist)
                                
                                if discount_rate > div_growth_hist:
                                    intrinsic_value_ddm = next_dividend / (discount_rate - div_growth_hist)
                                    
                                    st.metric("Dividendo per Azione", f"{get_currency_symbol(currency)}{dividend_per_share:.4f}")
                                    st.metric("Crescita Dividendi Storica", f"{div_growth_hist*100:.2f}%")
                                    st.metric("Dividendo Atteso (D1)", f"{get_currency_symbol(currency)}{next_dividend:.4f}")
                                    st.metric("Valore Intrinseco DDM", f"{get_currency_symbol(currency)}{intrinsic_value_ddm:.2f}")
                                    
                                    if intrinsic_value_ddm > 0:
                                        upside_ddm = ((intrinsic_value_ddm - current_price) / current_price) * 100
                                        st.metric("Upside/Downside", f"{upside_ddm:+.1f}%", 
                                                 delta=f"{upside_ddm:+.1f}%",
                                                 delta_color="normal")
                                else:
                                    st.warning("⚠️ Il tasso di sconto deve essere maggiore della crescita dei dividendi")
                            
                            with col2:
                                st.markdown("**📝 Formula Gordon Growth Model**")
                                st.latex(r"V_0 = \frac{D_1}{r - g}")
                                st.markdown("""
                                Dove:
                                - V₀ = Valore intrinseco
                                - D₁ = Dividendo atteso prossimo anno
                                - r = Tasso di sconto (richiesto)
                                - g = Tasso di crescita dividendi
                                """)
                                
                                if discount_rate > div_growth_hist:
                                    st.info(f"""
                                    **Calcolo:**
                                    - D₀ = {get_currency_symbol(currency)}{dividend_per_share:.4f}
                                    - g = {div_growth_hist*100:.2f}%
                                    - D₁ = {get_currency_symbol(currency)}{next_dividend:.4f}
                                    - r = {discount_rate*100:.1f}%
                                    - V₀ = {get_currency_symbol(currency)}{intrinsic_value_ddm:.2f}
                                    """)
                        else:
                            st.warning("⚠️ Azienda non paga dividendi - DDM non applicabile")
                        
                        st.markdown("---")
                        
                        # 3. P/E Multiple Analysis
                        st.subheader("3. Valutazione Multipli (P/E)")
                        
                        eps = safe_get(latest_income, 'eps', 0)
                        
                        if eps > 0 and ratios_data:
                            # Calcola P/E medio storico PRIMA di creare le colonne
                            df_ratios_hist = pd.DataFrame(ratios_data)
                            pe_values = df_ratios_hist['priceEarningsRatio'].dropna()
                            pe_values = pe_values[(pe_values > 0) & (pe_values < 100)]  # Filtro outlier
                            
                            if len(pe_values) > 0:
                                pe_avg = pe_values.mean()
                                pe_median = pe_values.median()
                                
                                # ORA crea le colonne, dopo aver calcolato pe_avg
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    intrinsic_value_pe_avg = eps * pe_avg
                                    intrinsic_value_pe_med = eps * pe_median
                                    
                                    st.metric("EPS Corrente", f"{get_currency_symbol(currency)}{eps:.2f}")
                                    st.metric("P/E Medio Storico", f"{pe_avg:.2f}x")
                                    st.metric("P/E Mediano Storico", f"{pe_median:.2f}x")
                                    st.metric("Valore con P/E Medio", f"{get_currency_symbol(currency)}{intrinsic_value_pe_avg:.2f}")
                                    st.metric("Valore con P/E Mediano", f"{get_currency_symbol(currency)}{intrinsic_value_pe_med:.2f}")
                                    
                                    upside_pe = ((intrinsic_value_pe_avg - current_price) / current_price) * 100
                                    st.metric("Upside/Downside (P/E Avg)", f"{upside_pe:+.1f}%", 
                                             delta=f"{upside_pe:+.1f}%",
                                             delta_color="normal")
                                
                                with col2:
                                    # Grafico P/E storico
                                    fig_pe = go.Figure()
                                    
                                    df_ratios_plot = df_ratios_hist.sort_values('date')
                                    df_ratios_plot['year'] = pd.to_datetime(df_ratios_plot['date']).dt.year
                                    
                                    fig_pe.add_trace(go.Scatter(
                                        x=df_ratios_plot['year'],
                                        y=df_ratios_plot['priceEarningsRatio'],
                                        mode='lines+markers',
                                        name='P/E Ratio',
                                        line=dict(color='#1f77b4', width=3)
                                    ))
                                    
                                    # Linea P/E medio (ora pe_avg è accessibile!)
                                    fig_pe.add_hline(y=pe_avg, line_dash="dash", line_color="green", 
                                                    annotation_text=f"Media: {pe_avg:.2f}x")
                                    
                                    fig_pe.update_layout(
                                        title="P/E Ratio Storico",
                                        xaxis_title="Anno",
                                        yaxis_title="P/E Ratio",
                                        template='plotly_white',
                                        height=350
                                    )
                                    
                                    st.plotly_chart(fig_pe, use_container_width=True)
                            else:
                                st.warning("⚠️ Dati P/E insufficienti per l'analisi dei multipli")
                        else:
                            st.warning("⚠️ EPS non disponibile o negativo")
                        
                        st.markdown("---")
                        
                        # 4. Book Value Analysis
                        st.subheader("4. Analisi Book Value (P/B)")
                        
                        equity = safe_get(latest_balance, 'totalStockholdersEquity', 0)
                        if equity == 0:
                            equity = safe_get(latest_balance, 'totalEquity', 0)
                        
                        shares = safe_get(latest_income, 'weightedAverageShsOutDil', 0)
                        if shares == 0:
                            shares = safe_get(latest_income, 'weightedAverageShsOut', 0)
                        
                        if equity > 0 and shares > 0:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                book_value_per_share = equity / shares
                                
                                # Calcola P/B medio storico
                                if ratios_data:
                                    df_ratios_hist = pd.DataFrame(ratios_data)
                                    pb_values = df_ratios_hist.get('priceToBookRatio', pd.Series([]))
                                    pb_values = pb_values.dropna()
                                    pb_values = pb_values[(pb_values > 0) & (pb_values < 20)]  # Filtro outlier
                                    
                                    if len(pb_values) > 0:
                                        pb_avg = pb_values.mean()
                                        intrinsic_value_pb = book_value_per_share * pb_avg
                                        
                                        current_pb = current_price / book_value_per_share if book_value_per_share > 0 else 0
                                        
                                        st.metric("Book Value per Azione", f"{get_currency_symbol(currency)}{book_value_per_share:.2f}")
                                        st.metric("P/B Corrente", f"{current_pb:.2f}x")
                                        st.metric("P/B Medio Storico", f"{pb_avg:.2f}x")
                                        st.metric("Valore con P/B Medio", f"{get_currency_symbol(currency)}{intrinsic_value_pb:.2f}")
                                        
                                        upside_pb = ((intrinsic_value_pb - current_price) / current_price) * 100
                                        st.metric("Upside/Downside", f"{upside_pb:+.1f}%", 
                                                 delta=f"{upside_pb:+.1f}%",
                                                 delta_color="normal")
                            
                            with col2:
                                if len(pb_values) > 0:
                                    # Grafico P/B storico
                                    fig_pb = go.Figure()
                                    
                                    df_ratios_plot = df_ratios_hist.sort_values('date')
                                    df_ratios_plot['year'] = pd.to_datetime(df_ratios_plot['date']).dt.year
                                    
                                    fig_pb.add_trace(go.Scatter(
                                        x=df_ratios_plot['year'],
                                        y=df_ratios_plot.get('priceToBookRatio', []),
                                        mode='lines+markers',
                                        name='P/B Ratio',
                                        line=dict(color='#ff7f0e', width=3)
                                    ))
                                    
                                    # Linea P/B medio
                                    fig_pb.add_hline(y=pb_avg, line_dash="dash", line_color="green", 
                                                    annotation_text=f"Media: {pb_avg:.2f}x")
                                    
                                    fig_pb.update_layout(
                                        title="P/B Ratio Storico",
                                        xaxis_title="Anno",
                                        yaxis_title="P/B Ratio",
                                        template='plotly_white',
                                        height=350
                                    )
                                    
                                    st.plotly_chart(fig_pb, use_container_width=True)
                        else:
                            st.warning("⚠️ Dati Patrimonio Netto o Azioni non disponibili")
                        
                        st.markdown("---")
                        
                        # 5. FCFE Model (Free Cash Flow to Equity)
                        st.subheader("5. FCFE - Free Cash Flow to Equity")
                        
                        # Calcolo FCFE = FCF + Net Borrowing - Debt Repayment
                        fcf = safe_get(latest_cashflow, 'freeCashFlow', 0)
                        debt_repayment = safe_get(latest_cashflow, 'debtRepayment', 0)
                        net_borrowings = safe_get(latest_cashflow, 'netBorrowings', 0)
                        
                        if fcf != 0:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # FCFE = FCF + Net Borrowings - Debt Repayment
                                fcfe_current = fcf + net_borrowings - abs(debt_repayment)
                                
                                # Calcola crescita storica FCFE
                                if len(df_cashflow_hist) >= 3:
                                    fcfe_values = []
                                    for _, row in df_cashflow_hist.head(5).iterrows():
                                        fcf_h = safe_get(row, 'freeCashFlow', 0)
                                        debt_rep_h = safe_get(row, 'debtRepayment', 0)
                                        net_bor_h = safe_get(row, 'netBorrowings', 0)
                                        fcfe_h = fcf_h + net_bor_h - abs(debt_rep_h)
                                        fcfe_values.append(fcfe_h)
                                    
                                    fcfe_growth_rates = []
                                    for i in range(len(fcfe_values)-1):
                                        if fcfe_values[i+1] != 0 and fcfe_values[i] != 0:
                                            growth = ((fcfe_values[i] / fcfe_values[i+1]) - 1) * 100
                                            if -50 < growth < 200:  # Filtro outlier
                                                fcfe_growth_rates.append(growth)
                                    
                                    avg_fcfe_growth = sum(fcfe_growth_rates) / len(fcfe_growth_rates) if fcfe_growth_rates else 5.0
                                    avg_fcfe_growth = max(-10.0, min(100.0, avg_fcfe_growth))
                                else:
                                    avg_fcfe_growth = 5.0
                                
                                fcfe_growth_rate = avg_fcfe_growth / 100
                                
                                # Proiezioni FCFE
                                fcfe_projections = []
                                for year in range(1, projection_years + 1):
                                    fcfe_projected = fcfe_current * ((1 + fcfe_growth_rate) ** year)
                                    pv = fcfe_projected / ((1 + discount_rate) ** year)
                                    fcfe_projections.append({
                                        'Anno': year,
                                        'FCFE Proiettato': fcfe_projected,
                                        'Valore Attuale': pv
                                    })
                                
                                df_fcfe = pd.DataFrame(fcfe_projections)
                                
                                # Terminal Value
                                fcfe_terminal_year = fcfe_current * ((1 + fcfe_growth_rate) ** projection_years)
                                terminal_value_fcfe = (fcfe_terminal_year * (1 + terminal_growth)) / (discount_rate - terminal_growth)
                                terminal_value_fcfe_pv = terminal_value_fcfe / ((1 + discount_rate) ** projection_years)
                                
                                # Equity Value (già diretto, non serve sottrarre debito)
                                pv_fcfe_sum = df_fcfe['Valore Attuale'].sum()
                                equity_value_fcfe = pv_fcfe_sum + terminal_value_fcfe_pv
                                
                                # Shares e Valore per Azione
                                shares = safe_get(latest_income, 'weightedAverageShsOutDil', 0)
                                if shares == 0:
                                    shares = safe_get(latest_income, 'weightedAverageShsOut', 0)
                                
                                intrinsic_value_fcfe = equity_value_fcfe / shares if shares > 0 else 0
                                
                                # Metriche
                                st.metric("FCFE Corrente", format_currency(fcfe_current, currency))
                                st.metric("Crescita FCFE Storica", f"{avg_fcfe_growth:.1f}%")
                                st.metric("Equity Value (FCFE)", format_currency(equity_value_fcfe, currency))
                                st.metric("Valore Intrinseco FCFE", f"{get_currency_symbol(currency)}{intrinsic_value_fcfe:.2f}")
                                
                                if intrinsic_value_fcfe > 0:
                                    upside_fcfe = ((intrinsic_value_fcfe - current_price) / current_price) * 100
                                    st.metric("Upside/Downside", f"{upside_fcfe:+.1f}%", 
                                             delta=f"{upside_fcfe:+.1f}%",
                                             delta_color="normal")
                            
                            with col2:
                                st.markdown("**Proiezioni FCFE**")
                                
                                # Mostra tabella proiezioni
                                display_fcfe = df_fcfe.copy()
                                display_fcfe['FCFE Proiettato'] = display_fcfe['FCFE Proiettato'].apply(lambda x: format_currency(x, currency))
                                display_fcfe['Valore Attuale'] = display_fcfe['Valore Attuale'].apply(lambda x: format_currency(x, currency))
                                st.dataframe(display_fcfe, use_container_width=True, hide_index=True)
                                
                                st.markdown(f"**Terminal Value:** {format_currency(terminal_value_fcfe, currency)}")
                                st.markdown(f"**Terminal Value (PV):** {format_currency(terminal_value_fcfe_pv, currency)}")
                                st.markdown(f"**Somma VP FCFE:** {format_currency(pv_fcfe_sum, currency)}")
                                
                                st.info("""
                                **FCFE vs DCF:**
                                - FCFE valuta direttamente l'equity (azionisti)
                                - DCF valuta l'impresa (enterprise value)
                                - FCFE incorpora i flussi di debito
                                """)
                        else:
                            st.warning("⚠️ Dati insufficienti per calcolare il FCFE")
                        
                        st.markdown("---")
                        
                        # 6. Graham Number (Value Investing)
                        st.subheader("6. Numero di Graham (Value Investing)")
                        
                        eps = safe_get(latest_income, 'eps', 0)
                        book_value_per_share_graham = equity / shares if (equity > 0 and shares > 0) else 0
                        
                        if eps > 0 and book_value_per_share_graham > 0:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Formula di Graham: V = √(22.5 × EPS × BVPS)
                                graham_number = (22.5 * eps * book_value_per_share_graham) ** 0.5
                                
                                # Formula alternativa di Graham con crescita
                                # V = EPS × (8.5 + 2g) × 4.4 / Y
                                # Stima crescita EPS
                                if len(df_income_hist) >= 3:
                                    eps_values = df_income_hist['eps'].head(5).values
                                    eps_growth_rates = []
                                    for i in range(len(eps_values)-1):
                                        if eps_values[i+1] != 0 and eps_values[i] != 0 and eps_values[i+1] > 0 and eps_values[i] > 0:
                                            growth = ((eps_values[i] / eps_values[i+1]) - 1) * 100
                                            if -50 < growth < 100:
                                                eps_growth_rates.append(growth)
                                    avg_eps_growth = sum(eps_growth_rates) / len(eps_growth_rates) if eps_growth_rates else 7.0
                                    avg_eps_growth = max(0.0, min(30.0, avg_eps_growth))
                                else:
                                    avg_eps_growth = 7.0
                                
                                # Yield obbligazionario AAA (default 4.4%)
                                bond_yield = 4.4
                                
                                graham_growth_number = eps * (8.5 + 2 * avg_eps_growth) * 4.4 / bond_yield
                                
                                # Media delle due formule
                                graham_value_avg = (graham_number + graham_growth_number) / 2
                                
                                # Margine di sicurezza di Graham (50%)
                                margin_of_safety_price = graham_value_avg * 0.5
                                
                                st.metric("EPS", f"{get_currency_symbol(currency)}{eps:.2f}")
                                st.metric("Book Value per Share", f"{get_currency_symbol(currency)}{book_value_per_share_graham:.2f}")
                                st.metric("Crescita EPS Storica", f"{avg_eps_growth:.1f}%")
                                st.metric("Graham Number (Base)", f"{get_currency_symbol(currency)}{graham_number:.2f}")
                                st.metric("Graham Number (con Crescita)", f"{get_currency_symbol(currency)}{graham_growth_number:.2f}")
                                st.metric("Valore Graham Medio", f"{get_currency_symbol(currency)}{graham_value_avg:.2f}")
                                
                                upside_graham = ((graham_value_avg - current_price) / current_price) * 100
                                st.metric("Upside/Downside", f"{upside_graham:+.1f}%", 
                                         delta=f"{upside_graham:+.1f}%",
                                         delta_color="normal")
                            
                            with col2:
                                st.markdown("**📝 Formule di Graham**")
                                
                                st.markdown("**Formula Base:**")
                                st.latex(r"V = \sqrt{22.5 \times EPS \times BVPS}")
                                
                                st.markdown("**Formula con Crescita:**")
                                st.latex(r"V = EPS \times (8.5 + 2g) \times \frac{4.4}{Y}")
                                
                                st.markdown("""
                                Dove:
                                - EPS = Earnings per Share
                                - BVPS = Book Value per Share  
                                - g = Tasso di crescita EPS (%)
                                - Y = Yield obbligazioni AAA (default 4.4%)
                                """)
                                
                                st.markdown("---")
                                
                                st.markdown("**💡 Margine di Sicurezza**")
                                st.metric("Prezzo Target (50% MoS)", f"{get_currency_symbol(currency)}{margin_of_safety_price:.2f}")
                                
                                if current_price <= margin_of_safety_price:
                                    st.success("✅ Il prezzo corrente rispetta il margine di sicurezza del 50%!")
                                else:
                                    diff = ((current_price - margin_of_safety_price) / margin_of_safety_price) * 100
                                    st.warning(f"⚠️ Il prezzo corrente è del {diff:.1f}% sopra il margine di sicurezza")
                                
                                st.info("""
                                **Filosofia Graham:**
                                - Investire solo con margine di sicurezza
                                - Focus su valore intrinseco solido
                                - Acquistare quando sottovalutato
                                """)
                        else:
                            st.warning("⚠️ Dati EPS o Book Value non disponibili per calcolare il Graham Number")
                        
                        st.markdown("---")
                        
                        # 7. Riepilogo Valutazioni
                        st.subheader("Riepilogo Completo Valutazioni")
                        
                        valuations = []
                        
                        if fcf_current > 0 and intrinsic_value_dcf > 0:
                            valuations.append({
                                'Modello': 'DCF (Discounted Cash Flow)',
                                'Valore Intrinseco': intrinsic_value_dcf,
                                'Upside/Downside': ((intrinsic_value_dcf - current_price) / current_price) * 100
                            })
                        
                        if dividend_per_share > 0 and 'intrinsic_value_ddm' in locals():
                            valuations.append({
                                'Modello': 'DDM (Gordon Growth)',
                                'Valore Intrinseco': intrinsic_value_ddm,
                                'Upside/Downside': ((intrinsic_value_ddm - current_price) / current_price) * 100
                            })
                        
                        if eps > 0 and 'intrinsic_value_pe_avg' in locals():
                            valuations.append({
                                'Modello': 'P/E Multipli (Media)',
                                'Valore Intrinseco': intrinsic_value_pe_avg,
                                'Upside/Downside': ((intrinsic_value_pe_avg - current_price) / current_price) * 100
                            })
                        
                        if 'intrinsic_value_pb' in locals():
                            valuations.append({
                                'Modello': 'P/B Multipli (Media)',
                                'Valore Intrinseco': intrinsic_value_pb,
                                'Upside/Downside': ((intrinsic_value_pb - current_price) / current_price) * 100
                            })
                        
                        if 'intrinsic_value_fcfe' in locals() and intrinsic_value_fcfe > 0:
                            valuations.append({
                                'Modello': 'FCFE (Free Cash Flow to Equity)',
                                'Valore Intrinseco': intrinsic_value_fcfe,
                                'Upside/Downside': ((intrinsic_value_fcfe - current_price) / current_price) * 100
                            })
                        
                        if 'graham_value_avg' in locals() and graham_value_avg > 0:
                            valuations.append({
                                'Modello': 'Graham Number (Value Investing)',
                                'Valore Intrinseco': graham_value_avg,
                                'Upside/Downside': ((graham_value_avg - current_price) / current_price) * 100
                            })
                        
                        if valuations:
                            df_valuations = pd.DataFrame(valuations)
                            
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                # Tabella riepilogo
                                display_val = df_valuations.copy()
                                display_val['Valore Intrinseco'] = display_val['Valore Intrinseco'].apply(
                                    lambda x: f"{get_currency_symbol(currency)}{x:.2f}"
                                )
                                display_val['Upside/Downside'] = display_val['Upside/Downside'].apply(
                                    lambda x: f"{x:+.1f}%"
                                )
                                display_val['Prezzo Corrente'] = f"{get_currency_symbol(currency)}{current_price:.2f}"
                                
                                st.dataframe(display_val, use_container_width=True, hide_index=True)
                            
                            with col2:
                                # Valutazione media e mediana
                                avg_intrinsic = df_valuations['Valore Intrinseco'].mean()
                                median_intrinsic = df_valuations['Valore Intrinseco'].median()
                                std_intrinsic = df_valuations['Valore Intrinseco'].std()
                                
                                avg_upside = ((avg_intrinsic - current_price) / current_price) * 100
                                median_upside = ((median_intrinsic - current_price) / current_price) * 100
                                
                                # Coefficiente di variazione (misura dispersione)
                                cv = (std_intrinsic / avg_intrinsic * 100) if avg_intrinsic > 0 else 0
                                
                                st.metric("Prezzo Corrente", f"{get_currency_symbol(currency)}{current_price:.2f}")
                                st.metric("Valore Medio", f"{get_currency_symbol(currency)}{avg_intrinsic:.2f}")
                                st.metric("Valore Mediano", f"{get_currency_symbol(currency)}{median_intrinsic:.2f}")
                                st.metric("Upside Medio", f"{avg_upside:+.1f}%",
                                         delta=f"{avg_upside:+.1f}%",
                                         delta_color="normal")
                                
                                # Affidabilità della valutazione
                                st.markdown("**Affidabilità Valutazione:**")
                                if cv < 15:
                                    st.success(f"🎯 Alta (CV: {cv:.1f}%)")
                                    st.caption("I modelli sono molto concordi")
                                elif cv < 30:
                                    st.info(f"⚖️ Media (CV: {cv:.1f}%)")
                                    st.caption("Discreta concordanza tra modelli")
                                else:
                                    st.warning(f"⚠️ Bassa (CV: {cv:.1f}%)")
                                    st.caption("Alta dispersione tra i modelli")
                                
                                st.markdown("---")
                                
                                # Giudizio finale
                                st.markdown("**🎯 Giudizio Finale:**")
                                if avg_upside > 30:
                                    st.success("### 🟢 FORTEMENTE SOTTOVALUTATO")
                                    st.caption(f"Basato su {len(valuations)} modelli")
                                elif avg_upside > 15:
                                    st.success("### 🟢 SOTTOVALUTATO")
                                    st.caption(f"Basato su {len(valuations)} modelli")
                                elif avg_upside > 0:
                                    st.info("### 🟡 LEGGERMENTE SOTTOVALUTATO")
                                    st.caption(f"Basato su {len(valuations)} modelli")
                                elif avg_upside > -15:
                                    st.warning("### 🟠 LEGGERMENTE SOPRAVVALUTATO")
                                    st.caption(f"Basato su {len(valuations)} modelli")
                                elif avg_upside > -30:
                                    st.error("### 🔴 SOPRAVVALUTATO")
                                    st.caption(f"Basato su {len(valuations)} modelli")
                                else:
                                    st.error("### 🔴 FORTEMENTE SOPRAVVALUTATO")
                                    st.caption(f"Basato su {len(valuations)} modelli")
                            
                            # Grafico comparativo
                            fig_comp = go.Figure()
                            
                            # Aggiungi barra prezzo corrente
                            fig_comp.add_trace(go.Bar(
                                name='Prezzo Corrente',
                                x=['Prezzo Corrente'],
                                y=[current_price],
                                marker_color='lightgray'
                            ))
                            
                            # Aggiungi barre valutazioni
                            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
                            for idx, row in df_valuations.iterrows():
                                fig_comp.add_trace(go.Bar(
                                    name=row['Modello'],
                                    x=[row['Modello']],
                                    y=[row['Valore Intrinseco']],
                                    marker_color=colors[idx % len(colors)]
                                ))
                            
                            # Linea prezzo corrente
                            fig_comp.add_hline(y=current_price, line_dash="dash", line_color="red",
                                              annotation_text=f"Prezzo: {get_currency_symbol(currency)}{current_price:.2f}")
                            
                            fig_comp.update_layout(
                                title="Confronto Valutazioni",
                                yaxis_title=f"Valore ({get_currency_symbol(currency)})",
                                template='plotly_white',
                                height=400,
                                showlegend=True,
                                barmode='group'
                            )
                            
                            st.plotly_chart(fig_comp, use_container_width=True)
                        else:
                            st.warning("⚠️ Nessun modello di valutazione disponibile con i dati attuali")
                        
                        # Disclaimer
                        st.markdown("---")
                        st.caption("""
                        ⚠️ **Disclaimer**: Le valutazioni sono basate su modelli finanziari teorici e dati storici. 
                        Non costituiscono consigli di investimento. I risultati dipendono fortemente dalle assunzioni 
                        utilizzate (tasso di sconto, crescita, ecc.). Consultare sempre un consulente finanziario 
                        qualificato prima di prendere decisioni di investimento.
                        """)
                    
                    else:
                        st.warning("⚠️ Dati insufficienti per la valutazione")
                
                # TAB 6: Stime Analisti
                with tab6:
                    st.header("Stime degli Analisti")
                    
                    if estimates_data:
                        df_estimates = pd.DataFrame(estimates_data)
                        df_estimates['year'] = pd.to_datetime(df_estimates['date']).dt.year.astype(str)
                        
                        st.subheader("Dati Dettagliati")
                        display_df = pd.DataFrame({
                            'Anno': df_estimates['year'],
                            'Stima Ricavi': df_estimates['estimatedRevenueAvg'].apply(lambda x: format_currency(x, currency)),
                            'Stima EPS': df_estimates['estimatedEpsAvg'].apply(lambda x: f"{get_currency_symbol(currency)}{x:.2f}" if pd.notna(x) else "N/A"),
                            'Stima EBITDA': df_estimates['estimatedEbitdaAvg'].apply(lambda x: format_currency(x, currency)),
                            'N. Analisti': df_estimates.get('numberAnalystEstimatedRevenue', pd.Series([0]*len(df_estimates)))
                        }).sort_values('Anno', ascending=False)
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nessuna stima disponibile per questo titolo")
                
                # TAB 7: Insider Trading
                with tab7:
                    st.header("Insider Trading")
                    
                    if insider_data:
                        df_insider = pd.DataFrame(insider_data)
                        
                        col1, col2, col3 = st.columns(3)
                        
                        total_transactions = len(df_insider)
                        purchases = len(df_insider[df_insider['transactionType'].str.contains('P-Purchase', na=False)])
                        sales = total_transactions - purchases
                        
                        with col1:
                            st.metric("Transazioni Totali", total_transactions)
                        with col2:
                            st.metric("Acquisti", purchases, delta=f"{purchases/total_transactions*100:.1f}%")
                        with col3:
                            st.metric("Vendite", sales, delta=f"{sales/total_transactions*100:.1f}%", delta_color="inverse")
                        
                        st.markdown("---")
                        
                        st.subheader("Dati Dettagliati")
                        display_df = pd.DataFrame({
                            'Data': pd.to_datetime(df_insider['transactionDate']).dt.strftime('%Y-%m-%d'),
                            'Nome': df_insider['reportingName'],
                            'Tipo': df_insider['transactionType'].apply(
                                lambda x: '🟢 Acquisto' if 'P-Purchase' in str(x) else '🔴 Vendita'
                            ),
                            'Azioni': df_insider['securitiesTransacted'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "0"),
                            'Prezzo': df_insider['price'].apply(lambda x: f"{get_currency_symbol(currency)}{x:.2f}" if pd.notna(x) else "N/A"),
                            'Valore': (df_insider['securitiesTransacted'] * df_insider['price']).apply(lambda x: format_currency(x, currency))
                        }).head(30)
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nessun dato insider trading disponibile per questo titolo")
                
                # TAB 8: Info Società
                with tab8:
                    st.header("Informazioni sulla Società")
                    
                    if company_profile:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Dati Generali")
                            
                            # Logo se disponibile
                            image_url = company_profile.get('image', '')
                            if image_url:
                                try:
                                    st.image(image_url, width=100)
                                except:
                                    pass
                            
                            st.markdown(f"**Nome:** {company_profile.get('companyName', 'N/A')}")
                            st.markdown(f"**Ticker:** {company_profile.get('symbol', 'N/A')}")
                            st.markdown(f"**Exchange:** {company_profile.get('exchangeShortName', 'N/A')}")
                            st.markdown(f"**Settore:** {company_profile.get('sector', 'N/A')}")
                            st.markdown(f"**Industria:** {company_profile.get('industry', 'N/A')}")
                            st.markdown(f"**Paese:** {company_profile.get('country', 'N/A')}")
                            
                            city = company_profile.get('city', '')
                            state = company_profile.get('state', '')
                            location = f"{city}, {state}" if city and state else (city or state or 'N/A')
                            st.markdown(f"**Località:** {location}")
                            
                            address = company_profile.get('address', '')
                            if address:
                                st.markdown(f"**Indirizzo:** {address}")
                            
                            zip_code = company_profile.get('zip', '')
                            if zip_code:
                                st.markdown(f"**ZIP:** {zip_code}")
                            
                            phone = company_profile.get('phone', '')
                            if phone:
                                st.markdown(f"**Telefono:** {phone}")
                            
                            website = company_profile.get('website', '')
                            if website:
                                st.markdown(f"**Website:** [{website}]({website})")
                            
                            ceo = company_profile.get('ceo', '')
                            if ceo:
                                st.markdown(f"**CEO:** {ceo}")
                            
                            employees = company_profile.get('fullTimeEmployees')
                            if employees:
                                try:
                                    employees_num = int(employees) if isinstance(employees, str) else employees
                                    if employees_num > 0:
                                        st.markdown(f"**Dipendenti:** {employees_num:,}")
                                except (ValueError, TypeError):
                                    pass
                            
                            ipo_date = company_profile.get('ipoDate', '')
                            if ipo_date:
                                st.markdown(f"**IPO Date:** {ipo_date}")
                        
                        with col2:
                            st.subheader("💹 Dati di Mercato")
                            
                            price = company_profile.get('price', 0)
                            if price:
                                st.markdown(f"**Prezzo Corrente:** {get_currency_symbol(currency)}{price:.2f}")
                            
                            mkt_cap = company_profile.get('mktCap', 0)
                            if mkt_cap:
                                st.markdown(f"**Market Cap:** {format_currency(mkt_cap, currency)}")
                            
                            beta = company_profile.get('beta', 0)
                            if beta:
                                st.markdown(f"**Beta:** {beta:.2f}")
                            
                            vol_avg = company_profile.get('volAvg', 0)
                            if vol_avg:
                                st.markdown(f"**Volume Medio:** {vol_avg:,}")
                            
                            range_52 = company_profile.get('range', '')
                            if range_52:
                                st.markdown(f"**Range (52 settimane):** {get_currency_symbol(currency)}{range_52}")
                            
                            changes = company_profile.get('changes', 0)
                            if changes:
                                st.markdown(f"**Variazione:** {changes:.2f}%")
                            
                            dcf = company_profile.get('dcf', 0)
                            if dcf:
                                st.markdown(f"**DCF:** {get_currency_symbol(currency)}{dcf:.2f}")
                            
                            last_div = company_profile.get('lastDiv', 0)
                            if last_div:
                                st.markdown(f"**Ultimo Dividendo:** {get_currency_symbol(currency)}{last_div:.4f}")
                            
                            isin = company_profile.get('isin', '')
                            if isin:
                                st.markdown(f"**ISIN:** {isin}")
                            
                            cusip = company_profile.get('cusip', '')
                            if cusip:
                                st.markdown(f"**CUSIP:** {cusip}")
                            
                            cik = company_profile.get('cik', '')
                            if cik:
                                st.markdown(f"**CIK:** {cik}")
                        
                        st.markdown("---")
                        st.subheader("📝 Descrizione")
                        description = company_profile.get('description', '')
                        if description:
                            st.write(description)
                        else:
                            st.info("Descrizione non disponibile")
                    else:
                        st.warning("⚠️ Informazioni sulla società non disponibili. Il profilo aziendale potrebbe non essere stato caricato correttamente.")
                        st.info("💡 Suggerimento: Verifica che il ticker sia corretto e riprova.")
                
                # TAB 9: News
                with tab9:
                    st.header("Ultime Notizie")
                    
                    if news_data and len(news_data) > 0:
                        st.success(f"✅ Trovate {len(news_data)} notizie recenti")
                        st.markdown("---")
                        
                        for idx, news in enumerate(news_data):
                            with st.container():
                                col_content, col_image = st.columns([3, 1])
                                
                                with col_content:
                                    title = news.get('title', 'Titolo non disponibile')
                                    url = news.get('url', '')
                                    
                                    if url:
                                        st.markdown(f"### [{title}]({url})")
                                    else:
                                        st.markdown(f"### {title}")
                                    
                                    text = news.get('text', '')
                                    if text:
                                        # Limita il testo a 300 caratteri
                                        if len(text) > 300:
                                            text = text[:297] + "..."
                                        st.write(text)
                                    
                                    # Informazioni sulla fonte
                                    site = news.get('site', '')
                                    symbol = news.get('symbol', ticker)
                                    published = news.get('publishedDate', '')
                                    
                                    caption_parts = []
                                    if published:
                                        try:
                                            published_dt = pd.to_datetime(published)
                                            published_str = published_dt.strftime('%d/%m/%Y %H:%M')
                                            caption_parts.append(f"📅 {published_str}")
                                        except:
                                            caption_parts.append(f"📅 {published}")
                                    
                                    if site:
                                        caption_parts.append(f"🌐 {site}")
                                    
                                    if symbol:
                                        caption_parts.append(f"📈 {symbol}")
                                    
                                    if caption_parts:
                                        st.caption(" | ".join(caption_parts))
                                
                                with col_image:
                                    image = news.get('image', '')
                                    if image:
                                        try:
                                            st.image(image, use_container_width=True)
                                        except:
                                            st.info("🖼️ Immagine non disponibile")
                                
                                if idx < len(news_data) - 1:
                                    st.markdown("---")
                    else:
                        st.warning("⚠️ Nessuna notizia disponibile per questo titolo")
                        st.info("💡 Possibili cause:\n- Il piano API gratuito potrebbe non includere le news\n- Non ci sono notizie recenti per questo ticker\n- Il ticker potrebbe non essere supportato per le news")
                
                # TAB 10: Calendario
                with tab10:
                    st.header("Calendario Eventi")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Earnings Calendar")
                        
                        if earnings_calendar and len(earnings_calendar) > 0:
                            st.success(f"✅ Trovati {len(earnings_calendar)} earnings storici")
                            
                            df_earnings = pd.DataFrame(earnings_calendar).head(10)
                            
                            # Costruisci il dataframe in modo sicuro
                            display_data = {
                                'Data': pd.to_datetime(df_earnings['date']).dt.strftime('%Y-%m-%d')
                            }
                            
                            if 'eps' in df_earnings.columns:
                                display_data['EPS'] = df_earnings['eps'].apply(lambda x: f"{get_currency_symbol(currency)}{x:.2f}" if pd.notna(x) and x != 0 else "N/A")
                            
                            if 'epsEstimated' in df_earnings.columns:
                                display_data['EPS Stimato'] = df_earnings['epsEstimated'].apply(lambda x: f"{get_currency_symbol(currency)}{x:.2f}" if pd.notna(x) and x != 0 else "N/A")
                            
                            if 'revenue' in df_earnings.columns:
                                display_data['Ricavi'] = df_earnings['revenue'].apply(lambda x: format_currency(x, currency) if pd.notna(x) and x != 0 else "N/A")
                            
                            if 'revenueEstimated' in df_earnings.columns:
                                display_data['Ricavi Stimati'] = df_earnings['revenueEstimated'].apply(lambda x: format_currency(x, currency) if pd.notna(x) and x != 0 else "N/A")
                            
                            display_df = pd.DataFrame(display_data)
                            st.dataframe(display_df, use_container_width=True, hide_index=True)
                        else:
                            st.warning("⚠️ Nessun dato earnings disponibile")
                            st.info("💡 Possibili cause:\n- Il piano API gratuito potrebbe avere limitazioni\n- Il ticker potrebbe non avere storico earnings\n- Prova con un ticker più grande (es. AAPL, MSFT)")
                    
                    with col2:
                        st.subheader("Storico Dividendi")
                        
                        if dividends_data and len(dividends_data) > 0:
                            st.success(f"✅ Trovati {len(dividends_data)} dividendi storici")
                            
                            df_dividends = pd.DataFrame(dividends_data)
                            
                            # Calcola yield medio se disponibile il prezzo
                            if quote and quote.get('price'):
                                current_price = quote.get('price')
                                # Prendi i primi 4 dividendi (ultimo anno se trimestrali)
                                recent_divs = df_dividends.head(4)
                                annual_dividend = recent_divs['dividend'].sum() if 'dividend' in recent_divs.columns else 0
                                
                                if annual_dividend > 0 and current_price > 0:
                                    div_yield = (annual_dividend / current_price) * 100
                                    st.metric("Dividend Yield Annuale", f"{div_yield:.2f}%")
                                    st.metric("Dividendo Annuale", format_currency(annual_dividend, currency))
                            
                            st.markdown("---")
                            
                            # Costruisci il dataframe in modo sicuro
                            display_data = {
                                'Data': pd.to_datetime(df_dividends['date']).dt.strftime('%Y-%m-%d'),
                                'Dividendo': df_dividends['dividend'].apply(lambda x: f"{get_currency_symbol(currency)}{x:.4f}" if pd.notna(x) else "N/A")
                            }
                            
                            if 'recordDate' in df_dividends.columns:
                                display_data['Record Date'] = pd.to_datetime(df_dividends['recordDate']).dt.strftime('%Y-%m-%d')
                            
                            if 'paymentDate' in df_dividends.columns:
                                display_data['Payment Date'] = pd.to_datetime(df_dividends['paymentDate']).dt.strftime('%Y-%m-%d')
                            elif 'paymentDate' not in df_dividends.columns and 'declarationDate' in df_dividends.columns:
                                display_data['Declaration Date'] = pd.to_datetime(df_dividends['declarationDate']).dt.strftime('%Y-%m-%d')
                            
                            display_df = pd.DataFrame(display_data).head(15)
                            st.dataframe(display_df, use_container_width=True, hide_index=True)
                        else:
                            st.warning("⚠️ Nessuno storico dividendi disponibile")
                            st.info("💡 Possibili cause:\n- L'azienda non paga dividendi\n- Il piano API gratuito potrebbe avere limitazioni\n- Prova con un ticker che paga dividendi (es. KO, JNJ, PG)")

else:
    # Schermata iniziale
    st.info("👆 Inserisci i parametri sopra e clicca su 'Analizza' per visualizzare i dati finanziari")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### Conto Economico
        - Ricavi e profitti
        - Margini operativi
        - Utile per azione (EPS)
        - Trend storici
        """)
    
    with col2:
        st.markdown("""
        ### Stato Patrimoniale
        - Attività e passività
        - Patrimonio netto
        - Liquidità e indebitamento
        - Book Value e Azioni Outstanding
        """)
    
    with col3:
        st.markdown("""
        ### Cash Flow
        - Flussi operativi
        - Flussi di investimento
        - Free cash flow
        - Dividendi pagati
        """)
    
    st.markdown("---")
    
    st.markdown("""
    ### Come iniziare
    
    1. **Seleziona un ticker** (es: AAPL, MSFT, ISP.MI, MC.PA, SAP.DE)
    2. **Scegli periodo e numero di periodi** da analizzare
    3. **Clicca su Analizza** per visualizzare tutti i dati finanziari
    
    ### Funzionalità Principali
    - ✅ Valutazione Azione intelligente tramite DCF, DDM ecc.
    - ✅ Grafici interattivi personalizzabili
    - ✅ Analisi storica fino a 20 periodi
    - ✅ Dati trimestrali e annuali
    - ✅ Key Ratios (P/E, ROE, ROA, Payout Ratio, ecc.)
    - ✅ Book Value e Azioni Outstanding
    - ✅ Dividendi e Free Cash Flow
    - ✅ Stime degli analisti
    - ✅ Insider trading
    - ✅ Informazioni complete sulla società
    - ✅ News in tempo reale
    - ✅ Calendario earnings e dividendi
    
    ### Suggerimenti
    
    **Titoli popolari da provare:**
    - 🇺🇸 USA: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA
    - 🇪🇺 Europa: SAP.DE, ASML.AS, MC.PA, OR.PA
    - 🇮🇹 Italia: ENI.MI, ISP.MI, UCG.MI, RACE.MI
    
    ### Note Importanti
    
    - I grafici sono completamente interattivi e personalizzabili
    """)


# ... TUTTO IL TUO CODICE ...

    
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
# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Sviluppato da DIRAMCO</p>
</div>
""", unsafe_allow_html=True)
