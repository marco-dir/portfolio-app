from database.db_connection import execute_query
from datetime import datetime


def sync_user_from_wordpress(wp_user, membership):
    """
    Crea o aggiorna utente da dati WordPress.
    
    Returns:
        user_id locale
    """
    query_check = "SELECT id FROM users WHERE wordpress_id = %s"
    existing = execute_query(query_check, (wp_user['id'],))
    
    if existing:
        # Update
        query_update = """
            UPDATE users SET
                username = %s,
                email = %s,
                display_name = %s,
                membership_level = %s,
                membership_status = %s,
                membership_expires_at = %s,
                last_login = CURRENT_TIMESTAMP,
                last_sync = CURRENT_TIMESTAMP
            WHERE wordpress_id = %s
            RETURNING id
        """
        result = execute_query(query_update, (
            wp_user['username'],
            wp_user['email'],
            wp_user.get('name', ''),
            membership.get('membership_name'),
            membership.get('status'),
            membership.get('expires_at'),
            wp_user['id']
        ))
        return result[0]['id']
    else:
        # Insert
        query_insert = """
            INSERT INTO users (
                wordpress_id, username, email, display_name,
                membership_level, membership_status, membership_expires_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = execute_query(query_insert, (
            wp_user['id'],
            wp_user['username'],
            wp_user['email'],
            wp_user.get('name', ''),
            membership.get('membership_name'),
            membership.get('status'),
            membership.get('expires_at')
        ))
        return result[0]['id']


def get_user_by_id(user_id):
    """Ottieni dati utente per ID."""
    query = "SELECT * FROM users WHERE id = %s"
    result = execute_query(query, (user_id,))
    return result[0] if result else None


def get_user_stats(user_id):
    """Ottieni statistiche utente."""
    query = """
        SELECT 
            COUNT(DISTINCT p.id) as num_portfolios,
            COUNT(DISTINCT pos.id) as num_positions,
            COALESCE(SUM(pos.shares * pos.avg_price), 0) as total_invested
        FROM users u
        LEFT JOIN portfolios p ON u.id = p.user_id AND p.is_active = TRUE
        LEFT JOIN positions pos ON p.id = pos.portfolio_id
        WHERE u.id = %s
    """
    result = execute_query(query, (user_id,))
    return result[0] if result else None
