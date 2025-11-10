import streamlit as st
from database.portfolios import get_user_portfolios, get_portfolio_positions
from database.analytics import calculate_portfolio_performance, save_analysis, get_portfolio_analyses
import anthropic


def show(user_id):
    """Pagina analisi AI del portafoglio."""
    
    st.title("🤖 Analisi AI del Portafoglio")
    
    portfolios = get_user_portfolios(user_id)
    
    if not portfolios:
        st.info("Crea un portafoglio per analizzarlo!")
        return
    
    # Seleziona portafoglio
    portfolio_names = {p['portfolio_name']: p['id'] for p in portfolios}
    selected_name = st.selectbox("Seleziona Portafoglio", list(portfolio_names.keys()))
    portfolio_id = portfolio_names[selected_name]
    
    # Ottieni posizioni e performance
    df = get_portfolio_positions(portfolio_id)
    
    if df.empty:
        st.warning("Portafoglio vuoto!")
        return
    
    perf = calculate_portfolio_performance(portfolio_id)
    
    # === PREVIEW PORTAFOGLIO ===
    st.markdown("### 📊 Il Tuo Portafoglio")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Titoli", len(df))
    with col2:
        st.metric("Valore", f"${perf['current_value']:,.2f}")
    with col3:
        st.metric("P/L", f"${perf['gain_loss']:,.2f}")
    with col4:
        st.metric("P/L %", f"{perf['gain_loss_pct']:+.2f}%")
    
    with st.expander("📋 Vedi Dettagli Portafoglio"):
        display_df = df[['ticker', 'company_name', 'shares', 'avg_price', 'total_cost', 'weight_%']].copy()
        display_df['avg_price'] = display_df['avg_price'].apply(lambda x: f"${x:.2f}")
        display_df['total_cost'] = display_df['total_cost'].apply(lambda x: f"${x:,.2f}")
        display_df['weight_%'] = display_df['weight_%'].apply(lambda x: f"{x:.1f}%")
        display_df.columns = ['Ticker', 'Azienda', 'Azioni', 'Prezzo', 'Valore', 'Peso']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # === OPZIONI ANALISI ===
    st.markdown("### ⚙️ Opzioni Analisi")
    
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_type = st.selectbox(
            "Tipo Analisi",
            [
                "Completa (Diversificazione + Rischi + Suggerimenti)",
                "Focus Diversificazione",
                "Focus Rischi",
                "Focus Value Investing",
                "Confronto con Benchmark"
            ]
        )
    
    with col2:
        include_news = st.checkbox("Includi Analisi News Recenti", value=False)
        include_macro = st.checkbox("Includi Contesto Macro", value=True)
    
    # === BOTTONE ANALISI ===
    if st.button("🚀 Analizza con Claude", type="primary", use_container_width=True):
        
        with st.spinner("🤖 Claude sta analizzando il tuo portafoglio..."):
            
            # Prepara dati per Claude
            portfolio_text = prepare_portfolio_for_ai(df, perf, analysis_type, include_macro)
            
            # Chiama Claude
            analysis = call_claude_api(portfolio_text, analysis_type)
            
            if analysis:
                st.markdown("---")
                st.markdown("### 📋 Risultato Analisi")
                
                st.markdown(analysis)
                
                # Salva nel database
                save_analysis(
                    portfolio_id=portfolio_id,
                    analysis_text=analysis,
                    analysis_type=analysis_type,
                    model_used="claude-sonnet-4-20250514"
                )
                
                # Download
                st.download_button(
                    "📥 Scarica Report Completo",
                    analysis,
                    file_name=f"analisi_{selected_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
    
    st.markdown("---")
    
    # === STORICO ANALISI ===
    st.markdown("### 📚 Storico Analisi")
    
    past_analyses = get_portfolio_analyses(portfolio_id, limit=10)
    
    if past_analyses:
        for i, analysis in enumerate(past_analyses):
            with st.expander(
                f"📄 Analisi del {analysis['created_at'][:16]} - {analysis['analysis_type'] or 'Generale'}"
            ):
                st.markdown(analysis['analysis_text'])
                
                st.download_button(
                    "📥 Scarica",
                    analysis['analysis_text'],
                    file_name=f"analisi_{i+1}.txt",
                    key=f"download_analysis_{i}"
                )
    else:
        st.info("Nessuna analisi passata. Crea la tua prima analisi!")


def prepare_portfolio_for_ai(df, perf, analysis_type, include_macro):
    """Prepara dati portafoglio per Claude."""
    
    output = f"""# PORTAFOGLIO DA ANALIZZARE

## Metriche Generali
- **Numero Posizioni**: {len(df)}
- **Valore Totale**: ${perf['current_value']:,.2f}
- **Costo Totale**: ${perf['total_cost']:,.2f}
- **Gain/Loss**: ${perf['gain_loss']:,.2f} ({perf['gain_loss_pct']:+.2f}%)

## Composizione Dettagliata

"""
    
    for _, row in df.iterrows():
        current_price = perf['current_prices'].get(row['ticker'], 0)
        current_value = row['shares'] * current_price
        gain_loss = current_value - row['total_cost']
        gain_loss_pct = (gain_loss / row['total_cost'] * 100) if row['total_cost'] > 0 else 0
        
        output += f"""### {row['ticker']} - {row.get('company_name', 'N/A')}
- **Azioni**: {row['shares']:.2f}
- **Prezzo Medio Acquisto**: ${row['avg_price']:.2f}
- **Prezzo Corrente**: ${current_price:.2f}
- **Valore Posizione**: ${current_value:,.2f}
- **Peso Portafoglio**: {row['weight_%']:.1f}%
- **P/L Posizione**: ${gain_loss:,.2f} ({gain_loss_pct:+.2f}%)
"""
        
        if pd.notna(row.get('sector')):
            output += f"- **Settore**: {row['sector']}\n"
        if pd.notna(row.get('industry')):
            output += f"- **Industria**: {row['industry']}\n"
        if pd.notna(row.get('notes')):
            output += f"- **Note**: {row['notes']}\n"
        
        output += "\n"
    
    # Distribuzione settoriale
    if 'sector' in df.columns and df['sector'].notna().any():
        output += "\n## Distribuzione Settoriale\n\n"
        sector_weights = df.groupby('sector')['weight_%'].sum().sort_values(ascending=False)
        for sector, weight in sector_weights.items():
            if pd.notna(sector):
                output += f"- **{sector}**: {weight:.1f}%\n"
    
    # Contesto macro (opzionale)
    if include_macro:
        from datetime import datetime
        output += f"\n## Contesto Temporale\n\n"
        output += f"- **Data Analisi**: {datetime.now().strftime('%d/%m/%Y')}\n"
        output += "- **Contesto**: Considera il contesto economico attuale (tassi, inflazione, mercati)\n"
    
    return output


def call_claude_api(portfolio_text, analysis_type):
    """Chiama Claude API per analisi."""
    
    # Verifica API key
    if "ANTHROPIC_API_KEY" not in st.secrets:
        st.error("❌ API Key Anthropic non configurata!")
        return None
    
    try:
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        
        # Crea prompt personalizzato in base al tipo di analisi
        prompts = {
            "Completa (Diversificazione + Rischi + Suggerimenti)": """Sei un analista finanziario esperto in value investing e gestione di portafoglio.

Analizza questo portafoglio in modo completo e dettagliato:

{portfolio_text}

Fornisci un'analisi strutturata che includa:

1. **📊 Diversificazione** (30% dell'analisi)
   - Distribuzione settoriale (è adeguata?)
   - Concentrazione geografica (se rilevante)
   - Rischio concentrazione su singoli titoli
   - Correlazioni tra asset

2. **⚠️ Analisi Rischi** (25% dell'analisi)
   - Esposizione a rischi specifici (settoriali, geografici, valutari)
   - Volatilità attesa del portafoglio
   - Rischi macro (tassi, inflazione, recessione)
   - Eventi specifici che potrebbero impattare

3. **🏆 Qualità Titoli** (25% dell'analisi)
   - Valutazione qualitativa delle aziende
   - Presenza di moat economici
   - Solidità bilanci e cash flow
   - Management quality (se rilevante)

4. **💡 Suggerimenti Operativi** (20% dell'analisi)
   - Titoli da ridurre o aumentare
   - Nuovi settori da considerare
   - Strategie di ribilanciamento
   - Timing suggerito

5. **🎯 Voto Complessivo** (1-10/10)
   - Voto numerico con spiegazione dettagliata
   - Profilo rischio/rendimento
   - Adeguatezza per investitore medio

Sii specifico, actionable e usa un tono professionale ma accessibile.""",
            
            "Focus Diversificazione": """Analizza la DIVERSIFICAZIONE di questo portafoglio:

{portfolio_text}

Focus su:
- Distribuzione settoriale ottimale
- Correlazioni tra asset
- Concentrazione geografica
- Suggerimenti per migliorare diversificazione
- Voto diversificazione (1-10)""",
            
            "Focus Rischi": """Analizza i RISCHI di questo portafoglio:

{portfolio_text}

Focus su:
- Rischi settoriali specifici
- Esposizione a rischi macro
- Volatilità attesa
- Scenari negativi possibili
- Strategie di mitigazione""",
            
            "Focus Value Investing": """Analizza questo portafoglio dal punto di vista VALUE INVESTING (Benjamin Graham, Warren Buffett):

{portfolio_text}

Focus su:
- Margini di sicurezza
- Qualità delle aziende (moat)
- Valutazioni attuali
- Opportunità di valore
- Titoli sopravvalutati da ridurre""",
            
            "Confronto con Benchmark": """Confronta questo portafoglio con benchmark standard (S&P 500, indici settoriali):

{portfolio_text}

Focus su:
- Performance vs benchmark
- Beta e volatilità
- Esposizione settoriale vs indici
- Alpha generation
- Suggerimenti per battere il mercato"""
        }
        
        prompt_template = prompts.get(analysis_type, prompts["Completa (Diversificazione + Rischi + Suggerimenti)"])
        prompt = prompt_template.format(portfolio_text=portfolio_text)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
        
    except Exception as e:
        st.error(f"❌ Errore chiamata Claude: {str(e)}")
        return None
