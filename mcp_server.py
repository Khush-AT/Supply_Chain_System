from mcp.server.fastmcp import FastMCP
import sqlite3
import httpx
import os
import uuid
from datetime import datetime
from typing import Optional

# Initialize the official FastMCP Server
mcp = FastMCP("Supply Chain Environment")
DB_DIR = "databases"

@mcp.tool()
async def check_weather_disruptions(latitude: float, longitude: float) -> str:
    """Fetches current weather alerts and conditions for specific shipping coordinates."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            return str(response.json().get("current_weather"))
        return "Weather API request failed."

@mcp.tool()
def query_inventory_db(product_id: str) -> str:
    """Queries the internal ERP database to check current stock and daily burn rate."""
    conn = sqlite3.connect(os.path.join(DB_DIR, "inventory.db"))
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, current_stock, daily_burn_rate FROM inventory WHERE product_id=?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return f"Product: {row[0]}, Stock: {row[1]}, Burn Rate: {row[2]}"
    return f"Product {product_id} not found."

@mcp.tool()
def track_shipment_status(shipment_id: str) -> str:
    """Checks the logistics DB for the current status and GPS location of a shipment."""
    conn = sqlite3.connect(os.path.join(DB_DIR, "logistics.db"))
    cursor = conn.cursor()
    cursor.execute("SELECT status, current_latitude, current_longitude FROM shipments WHERE shipment_id=?", (shipment_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return f"Status: {row[0]}, Latitude: {row[1]}, Longitude: {row[2]}"
    return f"Shipment {shipment_id} not found."

@mcp.tool()
def update_shipment_status(shipment_id: str, new_status: str) -> str:
    """Updates the status of a shipment in the logistics database (e.g., to mark as 'Delayed' or 'Delivered')."""
    # Note: We connect to logistics.db here
    conn = sqlite3.connect(os.path.join(DB_DIR, "logistics.db"))
    cursor = conn.cursor()
    
    # Check if shipment exists
    cursor.execute("SELECT status FROM shipments WHERE shipment_id=?", (shipment_id,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("UPDATE shipments SET status=? WHERE shipment_id=?", (new_status, shipment_id))
        conn.commit()
        conn.close()
        return f"SUCCESS: Shipment {shipment_id} status updated to '{new_status}'."
    
    conn.close()
    return f"ERROR: Shipment {shipment_id} not found."

@mcp.tool()
def reorder_inventory(product_id: str, quantity: int) -> str:
    """Drafts a Purchase Order (PO) to the correct supplier for a low-stock product."""
    conn = sqlite3.connect(os.path.join(DB_DIR, "inventory.db"))
    cursor = conn.cursor()
    
    # 1. Find the product and its assigned supplier
    cursor.execute("SELECT product_name, supplier_id FROM inventory WHERE product_id=?", (product_id,))
    item = cursor.fetchone()
    
    if not item:
        conn.close()
        return f"ERROR: Product {product_id} not found."
        
    product_name, supplier_id = item
    
    # 2. Get supplier details
    cursor.execute("SELECT name, lead_time_days FROM suppliers WHERE supplier_id=?", (supplier_id,))
    supplier = cursor.fetchone()
    supplier_name, lead_time = supplier

    # 3. Generate a Purchase Order
    po_number = f"PO-{str(uuid.uuid4())[:8].upper()}"
    order_date = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute(
        "INSERT INTO purchase_orders (po_number, product_id, supplier_id, quantity, status, order_date) VALUES (?, ?, ?, ?, ?, ?)",
        (po_number, product_id, supplier_id, quantity, "Draft", order_date)
    )
    
    conn.commit()
    conn.close()
    
    return (f"SUCCESS: Drafted Purchase Order {po_number} for {quantity} units of {product_name}. "
            f"Supplier: {supplier_name}. Expected lead time: {lead_time} days.")

@mcp.tool()
def get_supplier_info(supplier_id: Optional[str] = None) -> str:
    """Retrieves lead times and contact details for suppliers from the procurement database."""
    conn = sqlite3.connect(os.path.join(DB_DIR, "inventory.db"))
    cursor = conn.cursor()
    
    if supplier_id:
        cursor.execute("SELECT name, contact_email, lead_time_days FROM suppliers WHERE supplier_id=?", (supplier_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return f"Supplier: {row[0]} | Email: {row[1]} | Avg Lead Time: {row[2]} days"
        return f"Error: Supplier ID {supplier_id} not found."
    else:
        # If no ID provided, list all suppliers
        cursor.execute("SELECT supplier_id, name FROM suppliers")
        rows = cursor.fetchall()
        conn.close()
        return "Available Suppliers: " + ", ".join([f"{r[1]} ({r[0]})" for r in rows])
if __name__ == "__main__":
    # LangChain connects to local tools best using standard I/O streams
    mcp.run(transport="stdio")