import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import streamlit as st

# Database URL da secrets
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Connection pool globale
_connection_pool = None


def init_connection_pool():
    """Inizializza connection pool PostgreSQL."""
    global _connection_pool
    
    if _connection_pool is None:
        try:
            _connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL
            )
            print("✅ Connection pool PostgreSQL inizializzato")
        except Exception as e:
            print(f"❌ Errore inizializzazione pool: {e}")
            raise


def get_connection_pool():
    """Ottieni connection pool (crea se non esiste)."""
    if _connection_pool is None:
        init_connection_pool()
    return _connection_pool


@contextmanager
def get_db_connection():
    """Context manager per connessioni database."""
    pool = get_connection_pool()
    conn = pool.getconn()
    
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        pool.putconn(conn)


def execute_query(query, params=None, fetch=True):
    """
    Esegue query e ritorna risultati.
    
    Args:
        query: Query SQL
        params: Parametri query (tuple)
        fetch: Se True, ritorna risultati. Se False, solo esecuzione
        
    Returns:
        Lista di dizionari con risultati o None
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(query, params or ())
        
        if fetch and cursor.description:
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            return [dict(zip(columns, row)) for row in results]
        
        return None


def execute_many(query, params_list):
    """Esegue query multiple (batch insert/update)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
