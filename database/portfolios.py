from database.db_connection import execute_query, execute_many
import pandas as pd


def create_portfolio(user_id, name, description=None):
    """Crea nuovo portafoglio."""
    query = """
        INSERT INTO portfolios (user_id, portfolio_name, description)
        VALUES (%s, %s, %s)
        RETURNING id
    """
    result = execute_query(query, (user_id, name, description))
    return result[0]['id']


def get_user_portfolios(user_id):
    """Ottieni tutti i portafogli dell'utente."""
    query = """
        SELECT 
            p.id,
            p.portfolio_name,
            p.description,
            p.created_at,
            p.updated_at,
            COUNT(pos.id) as num_positions,
            COALESCE(SUM(pos.shares * pos.avg_price), 0) as total_cost
        FROM portfolios p
        LEFT JOIN positions pos ON p.id = pos.portfolio_id
        WHERE p.user_id = %s AND p.is_active = TRUE
        GROUP BY p.id
        ORDER BY p.updated_at DESC
    """
    return execute_query(query, (user_id,))


def add_position(portfolio_id, ticker, shares, avg_price, currency='USD', 
                 company_name=None, sector=None, industry=None, 
                 purchase_date=None, notes=None):
    """Aggiungi o aggiorna posizione."""
    # Check esistente
    query_check = """
        SELECT id, shares, avg_price FROM positions
        WHERE portfolio_id = %s AND ticker = %s
    """
    existing = execute_query(query_check, (portfolio_id, ticker.upper()))
    
    if existing:
        # Update (media ponderata)
        old_shares = float(existing[0]['shares'])
        old_price = float(existing[0]['avg_price'])
        
        new_total_shares = old_shares + shares
        new_avg_price = ((old_shares * old_price) + (shares * avg_price)) / new_total_shares
        
        query_update = """
            UPDATE positions SET
                shares = %s,
                avg_price = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        execute_query(query_update, (new_total_shares, new_avg_price, existing[0]['id']), fetch=False)
        
        # Registra transazione
        add_transaction(portfolio_id, ticker, 'BUY', shares, avg_price, currency, purchase_date)
    else:
        # Insert
        query_insert = """
            INSERT INTO positions (
                portfolio_id, ticker, shares, avg_price, currency,
                company_name, sector, industry, purchase_date, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(query_insert, (
            portfolio_id, ticker.upper(), shares, avg_price, currency,
            company_name, sector, industry, purchase_date, notes
        ), fetch=False)
        
        # Registra transazione
        add_transaction(portfolio_id, ticker, 'BUY', shares, avg_price, currency, purchase_date)
    
    # Update portfolio timestamp
    execute_query("UPDATE portfolios SET updated_at = CURRENT_TIMESTAMP WHERE id = %s", 
                  (portfolio_id,), fetch=False)


def get_portfolio_positions(portfolio_id):
    """Ottieni posizioni come DataFrame."""
    query = """
        SELECT 
            ticker, company_name, shares, avg_price, currency,
            sector, industry, purchase_date, notes, added_at,
            (shares * avg_price) as total_cost
        FROM positions
        WHERE portfolio_id = %s
        ORDER BY ticker
    """
    data = execute_query(query, (portfolio_id,))
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # Calcola peso percentuale
    if not df.empty:
        df['weight_%'] = (df['total_cost'] / df['total_cost'].sum() * 100).round(2)
    
    return df


def delete_position(portfolio_id, ticker):
    """Elimina posizione."""
    query = "DELETE FROM positions WHERE portfolio_id = %s AND ticker = %s"
    execute_query(query, (portfolio_id, ticker.upper()), fetch=False)
    
    execute_query("UPDATE portfolios SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                  (portfolio_id,), fetch=False)


def add_transaction(portfolio_id, ticker, tx_type, shares, price, currency, tx_date=None, fees=0, notes=None):
    """Registra transazione per tracking P&L."""
    from datetime import date
    
    query = """
        INSERT INTO transactions (
            portfolio_id, ticker, transaction_type, shares, price,
            currency, transaction_date, fees, notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute_query(query, (
        portfolio_id, ticker.upper(), tx_type, shares, price,
        currency, tx_date or date.today(), fees, notes
    ), fetch=False)
