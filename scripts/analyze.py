"""
Runs a set of organizing / analysis queries against ecommerce.db
and prints the results. This is the "make sense of the data" layer
of the project.
"""
import subprocess
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DB = ROOT / "data" / "store.db"
# SQLite needs real local disk locking; copy to a temp path before opening
# (works around network/mounted filesystems that don't support it).
DB_PATH = Path(tempfile.gettempdir()) / "ecommerce_readonly.db"
subprocess.run(["cp", str(SOURCE_DB), str(DB_PATH)], check=True)

QUERIES = {
    "Top 10 customers by total spend": """
        SELECT c.first_name || ' ' || c.last_name AS customer,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_spent
        FROM customers c
        JOIN orders o ON o.customer_id = c.customer_id
        JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.status != 'cancelled'
        GROUP BY c.customer_id
        ORDER BY total_spent DESC
        LIMIT 10;
    """,
    "Revenue by category": """
        SELECT cat.category_name,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM order_items oi
        JOIN products p ON p.product_id = oi.product_id
        JOIN categories cat ON cat.category_id = p.category_id
        JOIN orders o ON o.order_id = oi.order_id
        WHERE o.status != 'cancelled'
        GROUP BY cat.category_id
        ORDER BY revenue DESC;
    """,
    "Monthly revenue trend": """
        SELECT strftime('%Y-%m', o.order_date) AS month,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.status != 'cancelled'
        GROUP BY month
        ORDER BY month;
    """,
    "Order status breakdown": """
        SELECT status, COUNT(*) AS num_orders
        FROM orders
        GROUP BY status
        ORDER BY num_orders DESC;
    """,
    "Low stock products (under 20 units)": """
        SELECT product_name, stock_quantity
        FROM products
        WHERE stock_quantity < 20
        ORDER BY stock_quantity ASC;
    """,
    "Average order value": """
        SELECT ROUND(AVG(order_total), 2) AS avg_order_value FROM (
            SELECT o.order_id, SUM(oi.quantity * oi.unit_price) AS order_total
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.order_id
            WHERE o.status != 'cancelled'
            GROUP BY o.order_id
        );
    """,
}


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    for title, sql in QUERIES.items():
        print(f"\n=== {title} ===")
        rows = conn.execute(sql).fetchall()
        if not rows:
            print("(no rows)")
            continue
        headers = rows[0].keys()
        print(" | ".join(headers))
        for row in rows:
            print(" | ".join(str(row[h]) for h in headers))
    conn.close()


if __name__ == "__main__":
    run()
