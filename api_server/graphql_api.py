#!/usr/bin/env python3
"""
GraphQL API - Flexible query interface for transportation data
"""

import graphene
from graphene import ObjectType, String, Float, Int, List, Field, Schema
from flask import Flask
from flask_graphql import GraphQLView
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# GraphQL Types
class Location(ObjectType):
    lat = Float()
    lon = Float()

class Telemetry(ObjectType):
    device_id = String()
    timestamp = String()
    location = Field(Location)
    speed_kmph = Float()
    heading = Float()
    acceleration_x = Float()
    acceleration_y = Float()
    acceleration_z = Float()

class Vehicle(ObjectType):
    vehicle_id = String()
    registration_no = String()
    obu_device_id = String()
    user_id = String()
    wallet_address = String()
    balance = Float()

class TollTransaction(ObjectType):
    tx_id = String()
    vehicle_id = String()
    gantry_id = String()
    price = Float()
    timestamp = String()
    status = String()

class DriverScore(ObjectType):
    vehicle_id = String()
    score = Float()
    confidence = Float()
    timestamp = String()
    factors = String()

class Query(ObjectType):
    # Vehicle queries
    vehicle = Field(Vehicle, vehicle_id=String(required=True))
    vehicles = List(Vehicle, user_id=String())
    
    # Telemetry queries
    telemetry = List(
        Telemetry,
        device_id=String(required=True),
        limit=Int(default_value=100),
        hours=Int(default_value=1)
    )
    
    # Transaction queries
    transactions = List(
        TollTransaction,
        vehicle_id=String(),
        limit=Int(default_value=50)
    )
    
    # Driver score queries
    driver_score = Field(DriverScore, vehicle_id=String(required=True))
    
    def resolve_vehicle(self, info, vehicle_id):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT v.*, w.balance 
            FROM vehicles v
            LEFT JOIN wallets w ON v.vehicle_id = w.vehicle_id
            WHERE v.vehicle_id = %s
        """, (vehicle_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return Vehicle(**dict(result))
        return None
    
    def resolve_vehicles(self, info, user_id=None):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if user_id:
            cursor.execute("""
                SELECT v.*, w.balance 
                FROM vehicles v
                LEFT JOIN wallets w ON v.vehicle_id = w.vehicle_id
                WHERE v.user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT v.*, w.balance 
                FROM vehicles v
                LEFT JOIN wallets w ON v.vehicle_id = w.vehicle_id
                LIMIT 100
            """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [Vehicle(**dict(row)) for row in results]
    
    def resolve_telemetry(self, info, device_id, limit, hours):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM telemetry 
            WHERE device_id = %s 
            AND time >= NOW() - INTERVAL '%s hours'
            ORDER BY time DESC 
            LIMIT %s
        """, (device_id, hours, limit))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        telemetry_list = []
        for row in results:
            location = Location(lat=row['latitude'], lon=row['longitude'])
            telemetry_list.append(Telemetry(
                device_id=row['device_id'],
                timestamp=row['time'].isoformat(),
                location=location,
                speed_kmph=row['speed_kmph'],
                heading=row['heading'],
                acceleration_x=row['acceleration_x'],
                acceleration_y=row['acceleration_y'],
                acceleration_z=row['acceleration_z']
            ))
        
        return telemetry_list
    
    def resolve_transactions(self, info, vehicle_id=None, limit=50):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if vehicle_id:
            cursor.execute("""
                SELECT * FROM toll_transactions 
                WHERE vehicle_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (vehicle_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM toll_transactions 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [TollTransaction(
            tx_id=row['tx_id'],
            vehicle_id=row['vehicle_id'],
            gantry_id=row['gantry_id'],
            price=row['price'],
            timestamp=row['created_at'].isoformat(),
            status=row['status']
        ) for row in results]
    
    def resolve_driver_score(self, info, vehicle_id):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM driver_scores 
            WHERE vehicle_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (vehicle_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return DriverScore(
                vehicle_id=result['vehicle_id'],
                score=result['score'],
                confidence=result.get('confidence', 0.8),
                timestamp=result['timestamp'].isoformat(),
                factors=result.get('factors', '{}')
            )
        return None

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='transport_system',
        user='admin',
        password='password'
    )

# Create GraphQL schema
schema = Schema(query=Query)

def create_graphql_app():
    """Create Flask app with GraphQL endpoint"""
    app = Flask(__name__)
    
    app.add_url_rule(
        '/graphql',
        view_func=GraphQLView.as_view(
            'graphql',
            schema=schema,
            graphiql=True  # Enable GraphiQL interface
        )
    )
    
    return app

if __name__ == "__main__":
    app = create_graphql_app()
    app.run(host='0.0.0.0', port=5002, debug=True)