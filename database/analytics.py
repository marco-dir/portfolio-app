from database.db_connection import execute_query
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf


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
        SELECT ticker, shares, avg_price, currency
        FROM positions
        WHERE portfolio_id = %s
    """
    positions = execute_query(query, (portfolio_id,))
    
    if not positions:
        return None
    
    # Ottieni prezzi correnti
    tickers = [p['ticker'] for p in positions]
    current_prices = get_current_prices(tickers)
    
    # Calcola metriche
    total_cost = 0
    current_value = 0
    
    for pos in positions:
        ticker = pos['ticker']
        shares = float(pos['shares'])
        avg_price = float(pos['avg_price'])
        current_price = current_prices.get(ticker, 0)
        
        total_cost += shares * avg_price
        current_value += shares * current_price
    
    gain_loss = current_value - total_cost
    gain_loss_pct = (gain_loss / total_cost * 100) if total_cost > 0 else 0
    
    return {
        'total_cost': total_cost,
        'current_value': current_value,
        'gain_loss': gain_loss,
        'gain_loss_pct': gain_loss_pct,
        'positions': positions,
        'current_prices': current_prices
    }


def save_portfolio_snapshot(portfolio_id):
    """Salva snapshot giornaliero del portafoglio."""
    from datetime import date
    
    perf = calculate_portfolio_performance(portfolio_id)
    
    if not perf:
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
