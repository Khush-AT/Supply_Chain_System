import sqlite3
import os

DB_DIR = "databases"

# Ensure the directory exists
os.makedirs(DB_DIR, exist_ok=True)

def setup_inventory_db():
    conn = sqlite3.connect(os.path.join(DB_DIR, "inventory.db"))
    cursor = conn.cursor()
    
    # 1. Reset the schemas so we don't get column errors
    cursor.execute('DROP TABLE IF EXISTS inventory')
    cursor.execute('DROP TABLE IF EXISTS suppliers')
    cursor.execute('DROP TABLE IF EXISTS purchase_orders')
    
    # 2. Create Inventory Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            product_id TEXT PRIMARY KEY,
            product_name TEXT,
            current_stock INTEGER,
            daily_burn_rate INTEGER,
            supplier_id TEXT
        )
    ''')
    
    # 3. Create Suppliers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id TEXT PRIMARY KEY,
            name TEXT,
            contact_email TEXT,
            lead_time_days INTEGER
        )
    ''')

    # 4. Create Purchase Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_number TEXT PRIMARY KEY,
            product_id TEXT,
            supplier_id TEXT,
            quantity INTEGER,
            status TEXT,
            order_date TEXT
        )
    ''')
    
    # 5. Insert Mock Data
    suppliers_data = [
        ('SUP-01', 'Global Tech Components', 'orders@globaltech.com', 5),
        ('SUP-02', 'Alloy Dynamics', 'sales@alloydynamics.com', 12)
    ]
    
    inventory_data = [
        ('SKU-101', 'Microcontrollers', 150, 50, 'SUP-01'),
        ('SKU-102', 'Lithium Batteries', 5000, 200, 'SUP-01'),
        ('SKU-103', 'Aluminum Casing', 800, 10, 'SUP-02')
    ]
    
    cursor.executemany('INSERT INTO suppliers VALUES (?, ?, ?, ?)', suppliers_data)
    cursor.executemany('INSERT INTO inventory VALUES (?, ?, ?, ?, ?)', inventory_data)
    
    conn.commit()
    conn.close()
    print("Inventory and Procurement databases set up successfully.")

def setup_logistics_db():
    conn = sqlite3.connect(os.path.join(DB_DIR, "logistics.db"))
    cursor = conn.cursor()
    
    # Reset schema
    cursor.execute('DROP TABLE IF EXISTS shipments')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id TEXT PRIMARY KEY,
            status TEXT,
            current_latitude REAL,
            current_longitude REAL
        )
    ''')
    
    shipments_data = [
        ('SHP-999', 'Delayed - Severe Weather', 35.0, -170.0),
        ('SHP-123', 'In Transit', 40.7128, -74.0060)
    ]
    
    cursor.executemany('INSERT INTO shipments VALUES (?, ?, ?, ?)', shipments_data)
    
    conn.commit()
    conn.close()
    print("Logistics database set up successfully.")

if __name__ == "__main__":
    setup_inventory_db()
    setup_logistics_db()