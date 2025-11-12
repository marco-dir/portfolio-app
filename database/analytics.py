from database.db_connection import execute_query
import pandas as pd
from datetime import datetime, timedelta, date
import yfinance as yf
import json


def get_current_prices(tickers):
    """Ottieni prezzi correnti per lista ticker."""
    prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            prices[ticker] = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        except:
            prices[ticker] = 0
    return prices


def calculate_portfolio_performance(portfolio_id):
    """
    Calcola performance completa del portafoglio.
    
    Returns:
        dict con metriche: total_cost, current_value, gain_loss, gain_loss_pct, etc.
    """
    # Ottieni posizioni
    query = """
        SELECT ticker, shares, avg_price, currency, company_name, sector
        FROM positions
        WHERE portfolio_id = %s
    """
    positions = execute_query(query, (portfolio_id,))
    
    if not positions:
        return {
            'total_cost': 0,
            'current_value': 0,
            'gain_loss': 0,
            'gain_loss_pct': 0,
            'positions': [],
            'current_prices': {},
            'positions_performance': []
        }
    
    # Ottieni prezzi correnti
    tickers = [p['ticker'] for p in positions]
    current_prices = get_current_prices(tickers)
    
    # Calcola metriche
    total_cost = 0
    current_value = 0
    positions_performance = []
    
    for pos in positions:
        ticker = pos['ticker']
        shares = float(pos['shares'])
        avg_price = float(pos['avg_price'])
        current_price = current_prices.get(ticker, 0)
        
        position_cost = shares * avg_price
        position_value = shares * current_price
        position_gain_loss = position_value - position_cost
        position_gain_loss_pct = (position_gain_loss / position_cost * 100) if position_cost > 0 else 0
        
        total_cost += position_cost
        current_value += position_value
        
        positions_performance.append({
            'ticker': ticker,
            'company_name': pos.get('company_name'),
            'sector': pos.get('sector'),
            'shares': shares,
            'avg_price': avg_price,
            'current_price': current_price,
            'invested': position_cost,
            'current_value': position_value,
            'gain_loss': position_gain_loss,
            'gain_loss_pct': position_gain_loss_pct,
            'weight': 0  # Calcolato dopo
        })
    
    # Calcola i pesi
    for perf in positions_performance:
        perf['weight'] = (perf['current_value'] / current_value * 100) if current_value > 0 else 0
    
    gain_loss = current_value - total_cost
    gain_loss_pct = (gain_loss / total_cost * 100) if total_cost > 0 else 0
    
    return {
        'total_cost': total_cost,
        'current_value': current_value,
        'gain_loss': gain_loss,
        'gain_loss_pct': gain_loss_pct,
        'positions': positions,
        'current_prices': current_prices,
        'positions_performance': positions_performance,
        'total_invested': total_cost,  # Alias per compatibilità
        'total_gain_loss': gain_loss,  # Alias per compatibilità
        'total_gain_loss_pct': gain_loss_pct  # Alias per compatibilità
    }


def save_analysis(portfolio_id, analysis_data, analysis_type='snapshot'):
    """
    Salva un'analisi del portafoglio nel database.
    
    Args:
        portfolio_id: ID del portafoglio
        analysis_data: Dizionario con i dati dell'analisi
        analysis_type: Tipo di analisi (default: 'snapshot')
        
    Returns:
        int: ID dell'analisi salvata o None se errore
    """
    try:
        # Converti analysis_data in JSON se non lo è già
        if isinstance(analysis_data, dict):
            analysis_json = json.dumps(analysis_data, default=str)
        else:
            analysis_json = analysis_data
        
        query = """
            INSERT INTO portfolio_analyses 
            (portfolio_id, analysis_type, analysis_data, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        
        result = execute_query(
            query, 
            (portfolio_id, analysis_type, analysis_json, datetime.now()),
            fetch=True
        )
        
        if result:
            return result[0]['id']
        return None
        
    except Exception as e:
        print(f"Errore salvataggio analisi: {e}")
        return None


def get_portfolio_analyses(portfolio_id, limit=10):
    """
    Recupera le analisi storiche di un portafoglio.
    
    Args:
        portfolio_id: ID del portafoglio
        limit: Numero massimo di analisi da recuperare
        
    Returns:
        list: Lista di dizionari con le analisi
    """
    try:
        query = """
            SELECT id, portfolio_id, analysis_type, analysis_data, created_at
            FROM portfolio_analyses
            WHERE portfolio_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        analyses = execute_query(query, (portfolio_id, limit))
        
        if not analyses:
            return []
        
        # Converti JSON string in dict
        result = []
        for analysis in analyses:
            analysis_dict = dict(analysis)
            if isinstance(analysis_dict['analysis_data'], str):
                try:
                    analysis_dict['analysis_data'] = json.loads(analysis_dict['analysis_data'])
                except:
                    pass
            result.append(analysis_dict)
        
        return result
        
    except Exception as e:
        print(f"Errore recupero analisi: {e}")
        return []


def save_portfolio_snapshot(portfolio_id):
    """Salva snapshot giornaliero del portafoglio."""
    perf = calculate_portfolio_performance(portfolio_id)
    
    if not perf or perf['total_cost'] == 0:
        return
    
    query = """
        INSERT INTO portfolio_snapshots (
            portfolio_id, snapshot_date, total_value, total_cost,
            gain_loss, gain_loss_pct, currency
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (portfolio_id, snapshot_date) 
        DO UPDATE SET
            total_value = EXCLUDED.total_value,
            total_cost = EXCLUDED.total_cost,
            gain_loss = EXCLUDED.gain_loss,
            gain_loss_pct = EXCLUDED.gain_loss_pct
    """
    
    execute_query(query, (
        portfolio_id,
        date.today(),
        perf['current_value'],
        perf['total_cost'],
        perf['gain_loss'],
        perf['gain_loss_pct'],
        'USD'  # TODO: gestire multi-currency
    ), fetch=False)


def get_portfolio_history(portfolio_id, days=90):
    """Ottieni storico performance portafoglio."""
    query = """
        SELECT 
            snapshot_date,
            total_value,
            total_cost,
            gain_loss,
            gain_loss_pct
        FROM portfolio_snapshots
        WHERE portfolio_id = %s
            AND snapshot_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY snapshot_date
    """
    data = execute_query(query, (portfolio_id, days))
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_position_pl(portfolio_id, ticker):
    """Calcola P&L di una singola posizione."""
    # Ottieni posizione corrente
    query = """
        SELECT shares, avg_price, currency
        FROM positions
        WHERE portfolio_id = %s AND ticker = %s
    """
    pos = execute_query(query, (portfolio_id, ticker.upper()))
    
    if not pos:
        return None
    
    shares = float(pos[0]['shares'])
    avg_price = float(pos[0]['avg_price'])
    
    # Prezzo corrente
    current_price = get_current_prices([ticker.upper()])[ticker.upper()]
    
    # Transazioni
    query_tx = """
        SELECT transaction_type, shares, price, transaction_date
        FROM transactions
        WHERE portfolio_id = %s AND ticker = %s
        ORDER BY transaction_date
    """
    transactions = execute_query(query_tx, (portfolio_id, ticker.upper()))
    
    return {
        'ticker': ticker.upper(),
        'shares': shares,
        'avg_price': avg_price,
        'current_price': current_price,
        'total_cost': shares * avg_price,
        'current_value': shares * current_price,
        'gain_loss': (current_price - avg_price) * shares,
        'gain_loss_pct': ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0,
        'transactions': transactions
    }


def delete_analysis(analysis_id):
    """
    Elimina un'analisi specifica.
    
    Args:
        analysis_id: ID dell'analisi da eliminare
        
    Returns:
        bool: True se eliminata con successo, False altrimenti
    """
    try:
        query = """
            DELETE FROM portfolio_analyses 
            WHERE id = %s
        """
        execute_query(query, (analysis_id,), fetch=False)
        return True
        
    except Exception as e:
        print(f"Errore eliminazione analisi: {e}")
        return False


def calculate_portfolio_metrics(positions_performance):
    """
    Calcola metriche aggiuntive del portafoglio.
    
    Args:
        positions_performance: Lista delle performance delle singole posizioni
        
    Returns:
        dict: Dizionario con metriche aggregate
    """
    if not positions_performance:
        return {
            'best_performer': None,
            'worst_performer': None,
            'avg_gain_loss_pct': 0,
            'positive_positions': 0,
            'negative_positions': 0,
            'sectors_allocation': {},
            'total_positions': 0
        }
    
    # Ordina per performance
    sorted_positions = sorted(positions_performance, 
                             key=lambda x: x['gain_loss_pct'], 
                             reverse=True)
    
    best_performer = sorted_positions[0] if sorted_positions else None
    worst_performer = sorted_positions[-1] if sorted_positions else None
    
    # Calcola media
    avg_gain_loss_pct = sum(p['gain_loss_pct'] for p in positions_performance) / len(positions_performance)
    
    # Conta posizioni positive/negative
    positive_positions = sum(1 for p in positions_performance if p['gain_loss'] > 0)
    negative_positions = sum(1 for p in positions_performance if p['gain_loss'] < 0)
    
    # Calcola allocazione per settore
    sectors_allocation = {}
    for pos in positions_performance:
        sector = pos.get('sector', 'Unknown')
        if sector not in sectors_allocation:
            sectors_allocation[sector] = {
                'value': 0,
                'weight': 0,
                'positions': 0
            }
        sectors_allocation[sector]['value'] += pos['current_value']
        sectors_allocation[sector]['positions'] += 1
    
    # Calcola pesi settoriali
    total_value = sum(p['current_value'] for p in positions_performance)
    for sector in sectors_allocation:
        sectors_allocation[sector]['weight'] = (
            sectors_allocation[sector]['value'] / total_value * 100
        ) if total_value > 0 else 0
    
    return {
        'best_performer': best_performer,
        'worst_performer': worst_performer,
        'avg_gain_loss_pct': avg_gain_loss_pct,
        'positive_positions': positive_positions,
        'negative_positions': negative_positions,
        'total_positions': len(positions_performance),
        'sectors_allocation': sectors_allocation
    }


def check_alerts(user_id):
    """Controlla alert attivi e triggera se necessario."""
    query = """
        SELECT id, ticker, alert_type, target_value
        FROM alerts
        WHERE user_id = %s AND is_active = TRUE
    """
    alerts = execute_query(query, (user_id,))
    
    if not alerts:
        return []
    
    triggered = []
    
    tickers = [a['ticker'] for a in alerts]
    current_prices = get_current_prices(tickers)
    
    for alert in alerts:
        ticker = alert['ticker']
        current_price = current_prices.get(ticker, 0)
        target = float(alert['target_value'])
        alert_type = alert['alert_type']
        
        should_trigger = False
        
        if alert_type == 'PRICE_ABOVE' and current_price >= target:
            should_trigger = True
        elif alert_type == 'PRICE_BELOW' and current_price <= target:
            should_trigger = True
        
        if should_trigger:
            # Update alert
            query_update = """
                UPDATE alerts SET
                    is_active = FALSE,
                    current_value = %s,
                    triggered_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            execute_query(query_update, (current_price, alert['id']), fetch=False)
            
            triggered.append({
                **alert,
                'current_price': current_price
            })
    
    return triggered
