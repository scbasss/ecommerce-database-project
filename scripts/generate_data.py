"""
Generates realistic sample data for the e-commerce database
and loads it into ecommerce.db using the schema in schema.sql.
"""
import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path("/tmp/ecommerce.db")  # build on local disk (mounted dirs can't handle sqlite locking)
FINAL_DB_PATH = ROOT / "data" / "store.db"
SCHEMA_PATH = ROOT / "schema.sql"

NUM_CUSTOMERS = 200
NUM_PRODUCTS_PER_CATEGORY = 15
NUM_ORDERS = 800
MAX_ITEMS_PER_ORDER = 5

CATEGORIES = [
    "Electronics", "Home & Kitchen", "Clothing", "Books",
    "Sports & Outdoors", "Beauty & Personal Care", "Toys & Games"
]

PRODUCT_WORDS = {
    "Electronics": ["Headphones", "Bluetooth Speaker", "Webcam", "Smartwatch", "Charger", "Monitor", "Keyboard", "Mouse", "Tablet", "Router"],
    "Home & Kitchen": ["Blender", "Air Fryer", "Cookware Set", "Vacuum", "Toaster", "Coffee Maker", "Bedding Set", "Lamp", "Storage Bin", "Knife Set"],
    "Clothing": ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Hoodie", "Dress", "Socks", "Hat", "Scarf", "Belt"],
    "Books": ["Novel", "Cookbook", "Biography", "Self-Help Guide", "Textbook", "Comic", "Journal", "Poetry Collection", "History Book", "Guidebook"],
    "Sports & Outdoors": ["Yoga Mat", "Dumbbell Set", "Tent", "Water Bottle", "Bike Helmet", "Running Shoes", "Backpack", "Camping Chair", "Fishing Rod", "Resistance Bands"],
    "Beauty & Personal Care": ["Shampoo", "Face Cream", "Perfume", "Electric Razor", "Hair Dryer", "Lipstick", "Sunscreen", "Toothbrush", "Body Lotion", "Nail Kit"],
    "Toys & Games": ["Board Game", "Puzzle", "Action Figure", "Building Blocks", "RC Car", "Doll", "Card Game", "Plush Toy", "Drone", "Art Set"],
}

ORDER_STATUSES = ["pending", "shipped", "delivered", "cancelled"]
STATUS_WEIGHTS = [0.10, 0.20, 0.65, 0.05]


def build_schema(conn):
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())


def seed_categories(conn):
    conn.executemany(
        "INSERT INTO categories (category_name) VALUES (?)",
        [(c,) for c in CATEGORIES],
    )
    conn.commit()
    return {name: cid for cid, name in conn.execute("SELECT category_id, category_name FROM categories")}


def seed_customers(conn):
    rows = []
    for _ in range(NUM_CUSTOMERS):
        first = fake.first_name()
        last = fake.last_name()
        email = f"{first.lower()}.{last.lower()}{random.randint(1,999)}@{fake.free_email_domain()}"
        rows.append((
            first, last, email,
            fake.city(), fake.state_abbr(), "USA",
            fake.date_between(start_date="-3y", end_date="-1d").isoformat(),
        ))
    conn.executemany(
        """INSERT INTO customers (first_name, last_name, email, city, state, country, signup_date)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()


def seed_products(conn, category_ids):
    rows = []
    for cat_name, cat_id in category_ids.items():
        words = PRODUCT_WORDS[cat_name]
        for w in words[:NUM_PRODUCTS_PER_CATEGORY]:
            price = round(random.uniform(5, 300), 2)
            stock = random.randint(0, 500)
            rows.append((f"{w}", cat_id, price, stock))
    conn.executemany(
        "INSERT INTO products (product_name, category_id, unit_price, stock_quantity) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def seed_orders_and_items(conn):
    customer_ids = [row[0] for row in conn.execute("SELECT customer_id FROM customers")]
    products = conn.execute("SELECT product_id, unit_price FROM products").fetchall()

    order_rows = []
    for _ in range(NUM_ORDERS):
        cust = random.choice(customer_ids)
        order_date = fake.date_between(start_date="-2y", end_date="today").isoformat()
        status = random.choices(ORDER_STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
        order_rows.append((cust, order_date, status))

    cur = conn.cursor()
    cur.executemany("INSERT INTO orders (customer_id, order_date, status) VALUES (?, ?, ?)", order_rows)
    conn.commit()

    order_ids = [row[0] for row in conn.execute("SELECT order_id FROM orders")]

    item_rows = []
    for order_id in order_ids:
        n_items = random.randint(1, MAX_ITEMS_PER_ORDER)
        chosen = random.sample(products, k=min(n_items, len(products)))
        for product_id, unit_price in chosen:
            qty = random.randint(1, 4)
            item_rows.append((order_id, product_id, qty, unit_price))

    conn.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
        item_rows,
    )
    conn.commit()


def main():
    import subprocess

    FINAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    build_schema(conn)
    category_ids = seed_categories(conn)
    seed_customers(conn)
    seed_products(conn, category_ids)
    seed_orders_and_items(conn)

    counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ["categories", "customers", "products", "orders", "order_items"]
    }
    conn.close()

    subprocess.run(["cp", str(DB_PATH), str(FINAL_DB_PATH)], check=True)

    print(f"Database built at: {FINAL_DB_PATH}")
    for table, count in counts.items():
        print(f"  {table}: {count} rows")


if __name__ == "__main__":
    main()
