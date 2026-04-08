from database_manager import db
import time
from datetime import datetime, timedelta
import random

# Sample data with specific CITIES to trigger the map
dummy_risks = [
    {
        "source": "Simulation",
        "signal": "Heavy flooding reported in Colombo near the harbor area.",
        "risk_score": 8,
        "published": datetime.now().isoformat(),
        "link": "http://simulation.test"
    },
    {
        "source": "Simulation",
        "signal": "Protest gathering in Kandy city center causing traffic delays.",
        "risk_score": 6,
        "published": (datetime.now() - timedelta(hours=2)).isoformat(),
        "link": "http://simulation.test"
    },
    {
        "source": "Simulation",
        "signal": "Power outage affecting large areas of Jaffna peninsula.",
        "risk_score": 7,
        "published": (datetime.now() - timedelta(hours=5)).isoformat(),
        "link": "http://simulation.test"
    },
    {
        "source": "Simulation",
        "signal": "Tourist bus accident reported in Galle, minor injuries.",
        "risk_score": 4,
        "published": (datetime.now() - timedelta(days=1)).isoformat(),
        "link": "http://simulation.test"
    },
    {
        "source": "Simulation",
        "signal": "Agricultural warning issued for Anuradhapura due to drought.",
        "risk_score": 5,
        "published": (datetime.now() - timedelta(days=2)).isoformat(),
        "link": "http://simulation.test"
    }
]

print("💉 Injecting 5 test records into the database...")

for risk in dummy_risks:
    # unique ID generation to prevent errors
    risk_id = f"sim_{int(time.time())}_{random.randint(1000,9999)}"
    
    # We use the internal _get_connection for a quick raw insert
    # because we want to force this data in without the collector logic
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO risks (id, source, signal, risk_score, published, link, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            risk_id, 
            risk['source'], 
            risk['signal'], 
            risk['risk_score'], 
            risk['published'], 
            risk['link'],
            datetime.now().isoformat()
        ))
        conn.commit()

print("✅ Success! Data injected.")
print("🔄 Now refresh your Streamlit Dashboard (Press 'R' in the browser).")