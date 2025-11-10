import os
import sys
from datetime import datetime

# Aggiungi path al modulo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_connection import execute_query
from database.analytics import save_portfolio_snapshot

def run_daily_snapshots():
    """Salva snapshot di tutti i portafogli attivi."""
    
    print(f"[{datetime.now()}] Inizio snapshot giornalieri...")
    
    # Ottieni tutti i portafogli attivi
    query = "SELECT id FROM portfolios WHERE is_active = TRUE"
    portfolios = execute_query(query)
    
    if not portfolios:
        print("Nessun portafoglio attivo")
        return
    
    success_count = 0
    
    for portfolio in portfolios:
        try:
            save_portfolio_snapshot(portfolio['id'])
            success_count += 1
        except Exception as e:
            print(f"Errore portfolio {portfolio['id']}: {e}")
    
    print(f"Snapshot completati: {success_count}/{len(portfolios)}")

if __name__ == "__main__":
    run_daily_snapshots()
```

Per eseguirlo automaticamente su Render, aggiungi un **Cron Job** nel dashboard.

---

## **RIEPILOGO COMPLETO**

### **Cosa Abbiamo Creato:**

✅ **Autenticazione WordPress/MemberPress** - Zero modifiche a WordPress
✅ **Database PostgreSQL** - Completo con relazioni e indici
✅ **Analisi Titoli** - Il tuo codice integrato con bottone "Aggiungi"
✅ **Gestione Portafogli** - CRUD completo, import CSV
✅ **Performance & P/L Tracking** - Grafici real-time, storico
✅ **Analisi AI** - Claude analizza portafogli con vari focus
✅ **Watchlist** - Monitora titoli di interesse
✅ **Sistema Alert** - Notifiche prezzi target
✅ **Deployment Render** - Pronto per produzione

### **Struttura Finale:**
```
diramco-app/
├── app.py                          # Router principale
├── pages/
│   ├── stock_analysis.py          # Tuo codice + integrazione
│   ├── portfolio.py                # Gestione portafogli
│   ├── performance.py              # P/L tracking
│   ├── portfolio_analysis.py      # Analisi AI
│   ├── watchlist.py                # Watchlist
│   └── alerts_page.py              # Alert
├── auth/
│   └── wordpress_auth.py           # Autenticazione
├── database/
│   ├── db_connection.py            # Connection pool
│   ├── users.py                    # CRUD utenti
│   ├── portfolios.py               # CRUD portafogli
│   └── analytics.py                # Performance, P/L
├── scripts/
│   └── daily_snapshot.py           # Manutenzione
├── requirements.txt
├── render.yaml
└── .gitignore
