import os
import uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import math
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# In-memory task store
tasks_store: list = []

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        # Guard against None values in category field (e.g. restocking orders)
        filtered = [item for item in filtered if (item.get('category') or '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if (item.get('status') or '').lower() == status.lower()]

    return filtered

# CORS middleware - restrict origins to known frontends
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str
    unit_cost: float

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class RestockingRecommendationItem(BaseModel):
    item_sku: str
    item_name: str
    demand_gap: int
    unit_cost: float
    quantity: int
    line_cost: float

class RestockingRecommendationResponse(BaseModel):
    budget: float
    total_cost: float
    remaining_budget: float
    items: List[RestockingRecommendationItem]

class RestockingOrderItem(BaseModel):
    item_sku: str = Field(min_length=1, max_length=50)
    item_name: str = Field(min_length=1, max_length=255)
    quantity: int = Field(gt=0, le=100000)
    unit_cost: float = Field(gt=0, le=999999.99)

class RestockingOrderRequest(BaseModel):
    items: List[RestockingOrderItem] = Field(min_length=1)
    total_value: float = Field(gt=0, le=10000000)

# Task models
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    priority: str = Field(default="medium")
    dueDate: Optional[str] = None
    status: str = Field(default="pending")

class Task(BaseModel):
    id: str
    title: str
    priority: str
    dueDate: Optional[str] = None
    status: str

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

# Pre-built lookup set for O(1) purchase order checks instead of O(n) per backlog item
_po_backlog_ids = {po["backlog_item_id"] for po in purchase_orders}

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        item_dict["has_purchase_order"] = item["id"] in _po_backlog_ids
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports():
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in orders:
        order_date = order.get('order_date', '')
        # Determine quarter using QUARTER_MAP to avoid duplicating month logic
        quarter = None
        for q, months in QUARTER_MAP.items():
            if any(m in order_date for m in months):
                quarter = q
                break
        if not quarter:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends():
    """Get month-over-month trends"""
    months = {}

    for order in orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

@app.get("/api/restocking/recommend", response_model=RestockingRecommendationResponse)
def get_restocking_recommendations(budget: float = Query(gt=0, le=1000000, description="Budget must be positive, max $1M")):
    """Recommend items to restock based on demand gap, constrained by budget."""
    # Build candidates: only items where forecasted > current demand
    candidates = []
    for f in demand_forecasts:
        gap = f["forecasted_demand"] - f["current_demand"]
        if gap > 0:
            candidates.append({
                "item_sku": f["item_sku"],
                "item_name": f["item_name"],
                "demand_gap": gap,
                "unit_cost": f["unit_cost"],
            })

    # Sort by demand gap descending (highest unmet demand first)
    candidates.sort(key=lambda x: x["demand_gap"], reverse=True)

    # Greedy fill within budget
    selected = []
    remaining = budget
    for c in candidates:
        full_cost = c["demand_gap"] * c["unit_cost"]
        if full_cost <= remaining:
            selected.append({
                **c,
                "quantity": c["demand_gap"],
                "line_cost": round(full_cost, 2),
            })
            remaining -= full_cost
        elif remaining >= c["unit_cost"]:
            # Partial fill: as many units as the remaining budget allows
            qty = math.floor(remaining / c["unit_cost"])
            line_cost = round(qty * c["unit_cost"], 2)
            selected.append({
                **c,
                "quantity": qty,
                "line_cost": line_cost,
            })
            remaining -= line_cost

    total_cost = round(budget - remaining, 2)
    return {
        "budget": budget,
        "total_cost": total_cost,
        "remaining_budget": round(remaining, 2),
        "items": selected,
    }


@app.post("/api/restocking/order", response_model=Order, status_code=201)
def submit_restocking_order(request: RestockingOrderRequest):
    """Submit a restocking order. Creates a new order with status 'Restocking'."""
    # Generate IDs based on current orders count
    new_id = str(len(orders) + 1)
    order_number = f"ORD-2025-{len(orders) + 1:04d}"

    # Compute lead time based on total quantity
    total_quantity = sum(item.quantity for item in request.items)
    if total_quantity < 100:
        lead_days = 7
    elif total_quantity <= 500:
        lead_days = 14
    else:
        lead_days = 21

    now = datetime.now()
    order_date = now.strftime("%Y-%m-%dT%H:%M:%S")
    expected_delivery = (now + timedelta(days=lead_days)).strftime("%Y-%m-%dT%H:%M:%S")

    new_order = {
        "id": new_id,
        "order_number": order_number,
        "customer": "Internal Restocking",
        "items": [
            {
                "sku": item.item_sku,
                "name": item.item_name,
                "quantity": item.quantity,
                "unit_price": item.unit_cost,
            }
            for item in request.items
        ],
        "status": "Restocking",
        "order_date": order_date,
        "expected_delivery": expected_delivery,
        "total_value": request.total_value,
        "actual_delivery": None,
        "warehouse": None,
        "category": None,
    }

    orders.append(new_order)
    return new_order


# --- Task endpoints ---

@app.get("/api/tasks", response_model=List[Task])
def get_tasks():
    """Get all tasks"""
    return tasks_store

@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(task: TaskCreate):
    """Create a new task"""
    new_task = {
        "id": str(uuid.uuid4()),
        "title": task.title,
        "priority": task.priority,
        "dueDate": task.dueDate,
        "status": task.status,
    }
    tasks_store.append(new_task)
    return new_task

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    """Delete a task"""
    for i, task in enumerate(tasks_store):
        if task["id"] == task_id:
            tasks_store.pop(i)
            return {"message": "Task deleted"}
    raise HTTPException(status_code=404, detail="Task not found")

@app.patch("/api/tasks/{task_id}", response_model=Task)
def toggle_task(task_id: str):
    """Toggle a task's status between pending and completed"""
    for task in tasks_store:
        if task["id"] == task_id:
            task["status"] = "completed" if task["status"] == "pending" else "pending"
            return task
    raise HTTPException(status_code=404, detail="Task not found")

# --- Purchase Order endpoints ---

@app.post("/api/purchase-orders", response_model=PurchaseOrder, status_code=201)
def create_purchase_order(request: CreatePurchaseOrderRequest):
    """Create a purchase order for a backlog item"""
    # Verify backlog item exists
    backlog_item = next((item for item in backlog_items if item["id"] == request.backlog_item_id), None)
    if not backlog_item:
        raise HTTPException(status_code=404, detail="Backlog item not found")

    new_po = {
        "id": str(uuid.uuid4()),
        "backlog_item_id": request.backlog_item_id,
        "supplier_name": request.supplier_name,
        "quantity": request.quantity,
        "unit_cost": request.unit_cost,
        "expected_delivery_date": request.expected_delivery_date,
        "status": "Pending",
        "created_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "notes": request.notes,
    }
    purchase_orders.append(new_po)
    # Update lookup set so backlog endpoint reflects the new PO
    _po_backlog_ids.add(request.backlog_item_id)
    return new_po

@app.get("/api/purchase-orders/{backlog_item_id}", response_model=PurchaseOrder)
def get_purchase_order_by_backlog_item(backlog_item_id: str):
    """Get purchase order for a specific backlog item"""
    po = next((po for po in purchase_orders if po["backlog_item_id"] == backlog_item_id), None)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
