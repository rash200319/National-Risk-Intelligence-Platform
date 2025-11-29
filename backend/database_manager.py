import sqlite3
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import hashlib

DB_NAME = "data/modelx.db"

class DatabaseManager:
    def __init__(self, db_path: str = DB_NAME):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self._init_tables()
    
    def _get_connection(self):
        """Create a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def _init_tables(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            c = conn.cursor()
            
            # Risks table with enhanced schema for historical data
            c.execute('''
                CREATE TABLE IF NOT EXISTS risks (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    link TEXT,
                    published TEXT,
                    risk_score INTEGER,
                    category TEXT,
                    location TEXT,
                    district TEXT,
                    province TEXT,
                    confidence FLOAT DEFAULT 1.0,
                    keywords TEXT,
                    sentiment_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_historical BOOLEAN DEFAULT 0,
                    data_source TEXT,
                    raw_data TEXT
                )
            ''')
            
            # Historical data collection status
            c.execute('''
                CREATE TABLE IF NOT EXISTS historical_collection (
                    source TEXT PRIMARY KEY,
                    last_collected_date TEXT,
                    status TEXT,
                    total_collected INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Location reference data for Sri Lanka
            c.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,  -- 'district', 'province', 'city'
                    parent_id INTEGER,
                    geo_json TEXT,
                    population INTEGER,
                    risk_profile TEXT,
                    FOREIGN KEY (parent_id) REFERENCES locations (id)
                )
            ''')
            
            # Time series data for trend analysis
            c.execute('''
                CREATE TABLE IF NOT EXISTS risk_trends (
                    date TEXT,
                    location_id INTEGER,
                    category TEXT,
                    avg_risk_score FLOAT,
                    event_count INTEGER,
                    PRIMARY KEY (date, location_id, category),
                    FOREIGN KEY (location_id) REFERENCES locations (id)
                )
            ''')
            
            # Add indexes for better query performance
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_source ON risks(source)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_risk_score ON risks(risk_score)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_created_at ON risks(created_at)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_location ON risks(district, province)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_category ON risks(category)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_historical ON risks(is_historical, published)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risk_trends_date ON risk_trends(date)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risk_trends_location ON risk_trends(location_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risk_trends_category ON risk_trends(category)')
            
            # Create a table for tracking data collection
            c.execute('''
                CREATE TABLE IF NOT EXISTS data_collection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    items_collected INTEGER DEFAULT 0,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()

    def _generate_id(self, source: str, signal: str) -> str:
        """Generate a unique ID for a record."""
        unique_str = f"{source}_{signal}"
        return hashlib.md5(unique_str.encode('utf-8')).hexdigest()
    
    def insert_risk(self, record: Dict[str, Any]) -> bool:
        """Insert or update a risk record."""
        if not all(k in record for k in ['source', 'signal']):
            raise ValueError("Record must contain 'source' and 'signal' fields")
            
        record_id = self._generate_id(record['source'], record['signal'])
        
        with self._get_connection() as conn:
            c = conn.cursor()
            
            # Check if record exists
            c.execute('SELECT id FROM risks WHERE id = ?', (record_id,))
            exists = c.fetchone() is not None
            
            if exists:
                # Update existing record
                query = """
                    UPDATE risks 
                    SET source = :source,
                        signal = :signal,
                        link = :link,
                        published = :published,
                        risk_score = :risk_score,
                        category = :category,
                        location = :location,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """
                record['id'] = record_id
                c.execute(query, record)
                return False
            else:
                # Insert new record
                query = """
                    INSERT INTO risks (
                        id, source, signal, link, published, 
                        risk_score, category, location
                    ) VALUES (
                        :id, :source, :signal, :link, :published, 
                        :risk_score, :category, :location
                    )
                """
                record['id'] = record_id
                c.execute(query, record)
                return True

    def batch_insert_risks(self, records: List[Dict[str, Any]]) -> tuple[int, int]:
        """Insert or update multiple risk records in a single transaction."""
        if not records:
            return 0, 0
            
        new_count = 0
        updated_count = 0
        
        with self._get_connection() as conn:
            c = conn.cursor()
            
            for record in records:
                if not all(k in record for k in ['source', 'signal']):
                    continue
                    
                record_id = self._generate_id(record['source'], record['signal'])
                record['id'] = record_id
                
                # Check if record exists
                c.execute('SELECT id FROM risks WHERE id = ?', (record_id,))
                exists = c.fetchone() is not None
                
                if exists:
                    # Update existing record
                    query = """
                        UPDATE risks 
                        SET source = :source,
                            signal = :signal,
                            link = :link,
                            published = :published,
                            risk_score = :risk_score,
                            category = :category,
                            location = :location,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """
                    c.execute(query, record)
                    updated_count += 1
                else:
                    # Insert new record
                    query = """
                        INSERT INTO risks (
                            id, source, signal, link, published, 
                            risk_score, category, location
                        ) VALUES (
                            :id, :source, :signal, :link, :published, 
                            :risk_score, :category, :location
                        )
                    """
                    c.execute(query, record)
                    new_count += 1
            
            conn.commit()
            
        return new_count, updated_count

    def get_risks(
        self,
        limit: int = 100,
        offset: int = 0,
        min_score: Optional[int] = None,
        sources: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Query risks with filtering options."""
        query = """
            SELECT 
                id, source, signal, link, published, 
                risk_score, category, location,
                datetime(created_at, 'localtime') as created_at,
                datetime(updated_at, 'localtime') as updated_at
            FROM risks
            WHERE 1=1
        """
        params = {}
        
        if min_score is not None:
            query += " AND risk_score >= :min_score"
            params['min_score'] = min_score
            
        if sources:
            placeholders = ", ".join([":source_" + str(i) for i in range(len(sources))])
            query += f" AND source IN ({placeholders})"
            for i, source in enumerate(sources):
                params[f"source_{i}"] = source
                
        if start_date:
            query += " AND datetime(created_at) >= datetime(:start_date)"
            params['start_date'] = start_date
            
        if end_date:
            query += " AND datetime(created_at) <= datetime(:end_date)"
            params['end_date'] = end_date
            
        query += " ORDER BY created_at DESC"
        query += " LIMIT :limit OFFSET :offset"
        params.update({'limit': limit, 'offset': offset})
        
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            
        return df
    
    def get_risk_stats(self) -> Dict[str, Any]:
        """Get statistics about risks in the database."""
        with self._get_connection() as conn:
            # Total count
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as total FROM risks")
            total = c.fetchone()['total']
            
            # Count by source
            c.execute("""
                SELECT source, COUNT(*) as count 
                FROM risks 
                GROUP BY source 
                ORDER BY count DESC
            """)
            sources = [dict(row) for row in c.fetchall()]
            
            # Count by risk level
            c.execute("""
                SELECT 
                    CASE 
                        WHEN risk_score >= 8 THEN 'High (8-10)'
                        WHEN risk_score >= 5 THEN 'Medium (5-7)'
                        ELSE 'Low (1-4)'
                    END as risk_level,
                    COUNT(*) as count
                FROM risks
                GROUP BY risk_level
                ORDER BY risk_level
            """)
            risk_levels = [dict(row) for row in c.fetchall()]
            
            # Recent activity
            c.execute("""
                SELECT 
                    strftime('%Y-%m-%d', created_at) as date,
                    COUNT(*) as count
                FROM risks
                WHERE created_at >= date('now', '-30 days')
                GROUP BY date
                ORDER BY date
            """)
            recent_activity = [dict(row) for row in c.fetchall()]
            
        return {
            'total_risks': total,
            'sources': sources,
            'risk_levels': risk_levels,
            'recent_activity': recent_activity
        }
    
    def log_data_collection(
        self, 
        source: str, 
        status: str, 
        items_collected: int = 0, 
        error_message: Optional[str] = None
    ) -> None:
        """Log a data collection event."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO data_collection_logs 
                (source, status, items_collected, error_message)
                VALUES (?, ?, ?, ?)
                """,
                (source, status, items_collected, error_message)
            )
            conn.commit()

# Create a singleton instance
db = DatabaseManager()

# Backward compatibility functions
def init_db():
    """Initialize the database (for backward compatibility)."""
    pass  # No need to do anything as the DatabaseManager handles initialization

def save_risks(df):
    """Save risks from a DataFrame (for backward compatibility)."""
    if df.empty:
        return 0, 0
    records = df.to_dict('records')
    return db.batch_insert_risks(records)

def load_risks():
    """Load all risks (for backward compatibility)."""
    return db.get_risks()