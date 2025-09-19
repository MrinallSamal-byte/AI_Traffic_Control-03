import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.db_type = None
        
    def connect(self):
        """Connect to database (Postgres preferred, SQLite fallback)"""
        # Try Postgres first
        try:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 5432)),
                'database': os.getenv('DB_NAME', 'transport_system'),
                'user': os.getenv('DB_USER', 'admin'),
                'password': os.getenv('DB_PASSWORD', 'password')
            }
            self.conn = psycopg2.connect(**db_config)
            self.db_type = 'postgres'
            logger.info("Connected to PostgreSQL database")
            self._init_postgres_tables()
            return self.conn
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed: {e}")
            
        # Fallback to SQLite
        try:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'prototype.db')
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.db_type = 'sqlite'
            logger.info("Connected to SQLite database")
            self._init_sqlite_tables()
            return self.conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def _init_postgres_tables(self):
        """Initialize PostgreSQL tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Telemetry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id SERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                ts TIMESTAMPTZ NOT NULL,
                speed REAL,
                accel_x REAL,
                accel_y REAL,
                accel_z REAL,
                jerk REAL,
                yaw REAL
            )
        """)
        
        # Driver scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS driver_scores (
                id SERIAL PRIMARY KEY,
                telemetry_id INTEGER REFERENCES telemetry(id),
                score REAL NOT NULL,
                model TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        self.conn.commit()
        
    def _init_sqlite_tables(self):
        """Initialize SQLite tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Telemetry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                ts TIMESTAMP NOT NULL,
                speed REAL,
                accel_x REAL,
                accel_y REAL,
                accel_z REAL,
                jerk REAL,
                yaw REAL
            )
        """)
        
        # Driver scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS driver_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telemetry_id INTEGER REFERENCES telemetry(id),
                score REAL NOT NULL,
                model TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def insert_telemetry_and_score(self, telemetry_data, score_data):
        """Insert telemetry and score data"""
        cursor = self.conn.cursor()
        
        # Insert telemetry
        if self.db_type == 'postgres':
            cursor.execute("""
                INSERT INTO telemetry (device_id, ts, speed, accel_x, accel_y, accel_z, jerk, yaw)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                telemetry_data['device_id'],
                telemetry_data['timestamp'],
                telemetry_data.get('speed', 0),
                telemetry_data.get('accel_x', 0),
                telemetry_data.get('accel_y', 0),
                telemetry_data.get('accel_z', 9.8),
                telemetry_data.get('jerk', 0),
                telemetry_data.get('yaw', 0)
            ))
            telemetry_id = cursor.fetchone()[0]
        else:  # SQLite
            cursor.execute("""
                INSERT INTO telemetry (device_id, ts, speed, accel_x, accel_y, accel_z, jerk, yaw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                telemetry_data['device_id'],
                telemetry_data['timestamp'],
                telemetry_data.get('speed', 0),
                telemetry_data.get('accel_x', 0),
                telemetry_data.get('accel_y', 0),
                telemetry_data.get('accel_z', 9.8),
                telemetry_data.get('jerk', 0),
                telemetry_data.get('yaw', 0)
            ))
            telemetry_id = cursor.lastrowid
        
        # Insert score
        if self.db_type == 'postgres':
            cursor.execute("""
                INSERT INTO driver_scores (telemetry_id, score, model)
                VALUES (%s, %s, %s)
            """, (telemetry_id, score_data['score'], score_data['model']))
        else:  # SQLite
            cursor.execute("""
                INSERT INTO driver_scores (telemetry_id, score, model)
                VALUES (?, ?, ?)
            """, (telemetry_id, score_data['score'], score_data['model']))
        
        self.conn.commit()
        return telemetry_id
    
    def get_recent_scores(self, limit=50):
        """Get recent driver scores"""
        cursor = self.conn.cursor()
        
        if self.db_type == 'postgres':
            cursor.execute("""
                SELECT t.device_id, t.ts, ds.score, ds.model, ds.created_at
                FROM driver_scores ds
                JOIN telemetry t ON ds.telemetry_id = t.id
                ORDER BY ds.created_at DESC
                LIMIT %s
            """, (limit,))
        else:  # SQLite
            cursor.execute("""
                SELECT t.device_id, t.ts, ds.score, ds.model, ds.created_at
                FROM driver_scores ds
                JOIN telemetry t ON ds.telemetry_id = t.id
                ORDER BY ds.created_at DESC
                LIMIT ?
            """, (limit,))
        
        if self.db_type == 'postgres':
            return [dict(row) for row in cursor.fetchall()]
        else:  # SQLite
            return [dict(row) for row in cursor.fetchall()]

# Global database manager instance
db_manager = DatabaseManager()