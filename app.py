import os
import json
import sqlite3
import time
from urllib.parse import quote

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    flash
)

from werkzeug.utils import secure_filename
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "glassylook-secret-key-2026"
)

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

DATABASE_PATH = os.path.join(
    DATABASE_DIR,
    "glassylook.db"
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(DATABASE_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================================================
# BUSINESS DETAILS
# =========================================================

OWNER_PHONE = "919915645918"
DISPLAY_PHONE = "99156 45918"

OWNER_EMAIL = "goutamaartti@gmail.com"

UPI_ID = "goutamaartti@okaxis"

BUSINESS_NAME = "GlassyLook"

ADDRESS = "Jassia Road, Haibowal, Ludhiana"

RETURN_POLICY = "7 Days Return"

PAYMENT_POLICY = "75% Before Order + 25% After Delivery"


# =========================================================
# ADMIN DEFAULT DETAILS
# =========================================================

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "glassy"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "aaarti"
)

SECURITY_PIN = os.environ.get(
    "SECURITY_PIN",
    "aaarti"
)

ADMIN_OWNER_PHONE = os.environ.get(
    "ADMIN_OWNER_PHONE",
    "9915645918"
)


# =========================================================
# ALLOWED IMAGE FILES
# =========================================================

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif"
}


def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


def get_db_connection():

    return get_db()


# =========================================================
# ENSURE DATABASE COLUMN
# =========================================================

def ensure_column(
    conn,
    table_name,
    column_name,
    column_definition
):

    columns = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing_columns = [
        row["name"]
        for row in columns
    ]

    if column_name not in existing_columns:

        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name}
            {column_definition}
            """
        )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_database():

    conn = get_db()

    # -----------------------------------------------------
    # PRODUCTS
    # -----------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            price REAL NOT NULL DEFAULT 0,

            image TEXT DEFAULT '',

            description TEXT DEFAULT '',

            category TEXT DEFAULT '',

            size TEXT DEFAULT '',

            shape TEXT DEFAULT '',

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    # -----------------------------------------------------
    # ORDERS
    # -----------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            customer_name TEXT NOT NULL,

            phone TEXT NOT NULL,

            address TEXT NOT NULL,

            city TEXT NOT NULL,

            pincode TEXT NOT NULL,

            items TEXT NOT NULL,

            total REAL NOT NULL DEFAULT 0,

            payment_method TEXT
            DEFAULT 'Cash on Delivery',

            status TEXT DEFAULT 'New',

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    # -----------------------------------------------------
    # ADMIN USERS
    # -----------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password_hash TEXT NOT NULL

        )
        """
    )

    # -----------------------------------------------------
    # SAFE MIGRATION - PRODUCTS
    # -----------------------------------------------------

    ensure_column(
        conn,
        "products",
        "description",
        "TEXT DEFAULT ''"
    )

    ensure_column(
        conn,
        "products",
        "category",
        "TEXT DEFAULT ''"
    )

    ensure_column(
        conn,
        "products",
        "size",
        "TEXT DEFAULT ''"
    )

    ensure_column(
        conn,
        "products",
        "shape",
        "TEXT DEFAULT ''"
    )

    ensure_column(
        conn,
        "products",
        "created_at",
        "TIMESTAMP"
    )

    # -----------------------------------------------------
    # SAFE MIGRATION - ORDERS
    # -----------------------------------------------------

    ensure_column(
        conn,
        "orders",
        "payment_method",
        "TEXT DEFAULT 'Cash on Delivery'"
    )

    ensure_column(
        conn,
        "orders",
        "status",
        "TEXT DEFAULT 'New'"
    )

    ensure_column(
        conn,
        "orders",
        "created_at",
        "TIMESTAMP"
    )

    # -----------------------------------------------------
    # DEFAULT ADMIN
    # -----------------------------------------------------

    admin = conn.execute(
        """
        SELECT *
        FROM admin_users
        WHERE username = ?
        """,
        (ADMIN_USERNAME,)
    ).fetchone()

    if not admin:

        conn.execute(
            """
            INSERT INTO admin_users
            (
                username,
                password_hash
            )
            VALUES (?, ?)
            """,
            (
                ADMIN_USERNAME,
                generate_password_hash(
                    ADMIN_PASSWORD
                )
            )
        )

    conn.commit()

    conn.close()


# =========================================================
# START DATABASE
# =========================================================

init_database()


# =========================================================
# ADMIN LOGIN CHECK
# =========================================================

def admin_logged_in():

    return session.get(
        "admin_logged_in",
        False
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if admin_logged_in():

        return redirect(
            url_for("admin")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        conn = get_db()

        admin_user = conn.execute(
            """
            SELECT *
            FROM admin_users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        conn.close()

        if (
            admin_user
            and check_password_hash(
                admin_user["password_hash"],
                password
            )
        ):

            session["admin_logged_in"] = True
            session["admin_username"] = username

            return redirect(
                url_for("admin")
            )

        flash(
            "Invalid username or password."
        )

    return render_template(
        "admin-login.html"
    )


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route(
    "/admin/forgot-password",
    methods=["GET", "POST"]
)
def admin_forgot_password():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        owner_phone = request.form.get(
            "owner_phone",
            ""
        ).strip()

        pin = request.form.get(
            "pin",
            ""
        ).strip()

        new_password = request.form.get(
            "new_password",
            ""
        ).strip()

        confirm_password = request.form.get(
            "confirm_password",
            ""
        ).strip()

        clean_phone = (
            owner_phone
            .replace(" ", "")
            .replace("-", "")
        )

        saved_phone = (
            ADMIN_OWNER_PHONE
            .replace(" ", "")
            .replace("-", "")
        )

        if not username:

            flash("Please enter username.")

            return redirect(
                url_for("admin_forgot_password")
            )

        if not clean_phone:

            flash("Please enter owner mobile number.")

            return redirect(
                url_for("admin_forgot_password")
            )

        if not pin:

            flash("Please enter security PIN.")

            return redirect(
                url_for("admin_forgot_password")
            )

        if not new_password:

            flash("Please enter new password.")

            return redirect(
                url_for("admin_forgot_password")
            )

        if new_password != confirm_password:

            flash("New passwords do not match.")

            return redirect(
                url_for("admin_forgot_password")
            )

        if len(new_password) < 4:

            flash(
                "Password must be at least 4 characters."
            )

            return redirect(
                url_for("admin_forgot_password")
            )

        if clean_phone != saved_phone:

            flash("Invalid owner mobile number.")

            return redirect(
                url_for("admin_forgot_password")
            )

        if pin != SECURITY_PIN:

            flash("Invalid security PIN.")

            return redirect(
                url_for("admin_forgot_password")
            )

        conn = get_db()

        admin_user = conn.execute(
            """
            SELECT *
            FROM admin_users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        if not admin_user:

            conn.close()

            flash("Admin username not found.")

            return redirect(
                url_for("admin_forgot_password")
            )

        conn.execute(
            """
            UPDATE admin_users
            SET password_hash = ?
            WHERE username = ?
            """,
            (
                generate_password_hash(
                    new_password
                ),
                username
            )
        )

        conn.commit()
        conn.close()

        flash(
            "Password updated successfully. Please login."
        )

        return redirect(
            url_for("admin_login")
        )

    return render_template(
        "admin-forgot-password.html"
    )


# =========================================================
# ADMIN PANEL
# =========================================================

@app.route("/admin")
def admin():

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    products = conn.execute(
        """
        SELECT *
        FROM products
        ORDER BY id DESC
        """
    ).fetchall()

    rows = conn.execute(
        """
        SELECT *
        FROM orders
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    orders = []

    for row in rows:

        order = dict(row)

        try:

            order["items"] = json.loads(
                order.get("items") or "[]"
            )

        except Exception:

            order["items"] = []

        orders.append(order)

    return render_template(
        "admin.html",
        products=products,
        orders=orders
    )


# =========================================================
# ADD PRODUCT
# =========================================================

@app.route(
    "/admin/add-product",
    methods=["POST"]
)
def admin_add_product():

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    price = request.form.get(
        "price",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    size = request.form.get(
        "size",
        ""
    ).strip()

    shape = request.form.get(
        "shape",
        ""
    ).strip()

    image = request.files.get("image")

    if not name or not price:

        flash(
            "Please enter product name and price."
        )

        return redirect(
            url_for("admin")
        )

    try:

        price_value = float(price)

    except ValueError:

        flash("Invalid price.")

        return redirect(
            url_for("admin")
        )

    filename = ""

    # -----------------------------------------------------
    # IMAGE UPLOAD
    # -----------------------------------------------------

    if image and image.filename:

        if allowed_file(image.filename):

            filename = secure_filename(
                image.filename
            )

            base, ext = os.path.splitext(
                filename
            )

            filename = (
                base
                + "_"
                + str(int(time.time()))
                + ext
            )

            image.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )
            )

        else:

            flash(
                "Only PNG, JPG, JPEG, WEBP and GIF files allowed."
            )

            return redirect(
                url_for("admin")
            )

    # -----------------------------------------------------
    # SAVE PRODUCT
    # -----------------------------------------------------

    conn = get_db()

    conn.execute(
        """
        INSERT INTO products
        (
            name,
            price,
            image,
            description,
            category,
            size,
            shape
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            price_value,
            filename,
            description,
            category,
            size,
            shape
        )
    )

    conn.commit()
    conn.close()

    flash("Product added successfully.")

    return redirect(
        url_for("admin")
    )


# =========================================================
# DELETE PRODUCT
# =========================================================

@app.route(
    "/admin/delete-product/<int:product_id>",
    methods=["POST"]
)
def admin_delete_product(product_id):

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    product = conn.execute(
        """
        SELECT image
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()

    conn.execute(
        """
        DELETE FROM products
        WHERE id = ?
        """,
        (product_id,)
    )

    conn.commit()
    conn.close()

    if product and product["image"]:

        image_path = os.path.join(
            UPLOAD_FOLDER,
            product["image"]
        )

        if os.path.exists(image_path):

            try:
                os.remove(image_path)
            except OSError:
                pass

    flash("Product deleted successfully.")

    return redirect(
        url_for("admin")
    )


# =========================================================
# UPDATE ORDER STATUS
# =========================================================

@app.route(
    "/admin/update-order-status/<int:order_id>",
    methods=["POST"]
)
def admin_update_order_status(order_id):

    if not admin_logged_in():

        return redirect(
            url_for("admin_login")
        )

    status = request.form.get(
        "status",
        "New"
    )

    allowed_statuses = [
        "New",
        "Confirmed",
        "Processing",
        "Shipped",
        "Out for Delivery",
        "Delivered",
        "Cancelled"
    ]

    if status not in allowed_statuses:

        status = "New"

    conn = get_db()

    conn.execute(
        """
        UPDATE orders
        SET status = ?
        WHERE id = ?
        """,
        (
            status,
            order_id
        )
    )

    conn.commit()
    conn.close()

    flash("Order status updated.")

    return redirect(
        url_for("admin")
    )


# =========================================================
# UPLOAD FILE
# =========================================================

@app.route(
    "/uploads/<path:filename>"
)
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    conn = get_db()

    products = conn.execute(
        """
        SELECT *
        FROM products
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        products=products
    )


# =========================================================
# PRODUCT PAGE
# =========================================================

@app.route(
    "/product/<int:product_id>"
)
def product(product_id):

    conn = get_db()

    product_data = conn.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()

    conn.close()

    if not product_data:

        return "Product not found", 404

    return render_template(
        "product.html",
        product=product_data
    )


# =========================================================
# CART
# =========================================================

@app.route("/cart")
def cart():

    return render_template(
        "cart.html"
    )


# =========================================================
# ADD TO CART SERVER
# =========================================================

@app.route(
    "/add-to-cart/<int:product_id>",
    methods=["POST"]
)
def add_to_cart(product_id):

    conn = get_db()

    product_data = conn.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()

    conn.close()

    if not product_data:

        return {
            "success": False,
            "message": "Product not found"
        }, 404

    return {
        "success": True,
        "product": {
            "id": product_data["id"],
            "name": product_data["name"],
            "price": product_data["price"],
            "image": product_data["image"] or "",
            "size": product_data["size"] or "",
            "shape": product_data["shape"] or ""
        }
    }


# =========================================================
# CHECKOUT
# =========================================================

@app.route(
    "/checkout",
    methods=["GET", "POST"]
)
def checkout():

    items = []

    if request.method == "POST":

        raw_items = request.form.get(
            "items",
            "[]"
        )

        try:

            items = json.loads(
                raw_items
            )

        except Exception:

            items = []

    return render_template(
        "checkout.html",
        items=items
    )


# =========================================================
# CALCULATE ORDER ITEMS
# =========================================================

def calculate_order_items(raw_items):

    if not isinstance(
        raw_items,
        list
    ):

        return [], 0

    clean_items = []

    total = 0

    conn = get_db()

    for item in raw_items:

        try:

            product_id = int(
                item.get("id")
            )

        except Exception:

            continue

        try:

            quantity = int(
                item.get(
                    "quantity",
                    1
                )
            )

        except Exception:

            quantity = 1

        if quantity < 1:

            quantity = 1

        product_data = conn.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if not product_data:

            continue

        price = float(
            product_data["price"] or 0
        )

        subtotal = (
            price * quantity
        )

        total += subtotal

        clean_items.append(
            {
                "id": product_data["id"],

                "name": product_data["name"],

                "price": price,

                "image":
                    product_data["image"] or "",

                "quantity": quantity,

                "size":
                    product_data["size"] or "",

                "shape":
                    product_data["shape"] or ""
            }
        )

    conn.close()

    return clean_items, total


# =========================================================
# PLACE ORDER
# =========================================================

@app.route(
    "/place-order",
    methods=["POST"]
)
def place_order():

    customer_name = request.form.get(
        "customer_name",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    address = request.form.get(
        "address",
        ""
    ).strip()

    city = request.form.get(
        "city",
        ""
    ).strip()

    pincode = request.form.get(
        "pincode",
        ""
    ).strip()

    payment_method = request.form.get(
        "payment_method",
        "Cash on Delivery"
    ).strip()

    raw_items = request.form.get(
        "items",
        "[]"
    )

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not customer_name:

        flash(
            "Please enter your name."
        )

        return redirect(
            url_for("checkout")
        )

    if not phone:

        flash(
            "Please enter your phone number."
        )

        return redirect(
            url_for("checkout")
        )

    if not address:

        flash(
            "Please enter your address."
        )

        return redirect(
            url_for("checkout")
        )

    if not city:

        flash(
            "Please enter your city."
        )

        return redirect(
            url_for("checkout")
        )

    if not pincode:

        flash(
            "Please enter your pincode."
        )

        return redirect(
            url_for("checkout")
        )

    # -----------------------------------------------------
    # ITEMS
    # -----------------------------------------------------

    try:

        raw_items_list = json.loads(
            raw_items
        )

    except Exception:

        raw_items_list = []

    items, total = calculate_order_items(
        raw_items_list
    )

    if not items:

        flash(
            "Your cart is empty."
        )

        return redirect(
            url_for("cart")
        )

    # -----------------------------------------------------
    # PAYMENT
    # -----------------------------------------------------

    allowed_payment_methods = [
        "Online Payment",
        "Cash on Delivery"
    ]

    if payment_method not in allowed_payment_methods:

        payment_method = (
            "Cash on Delivery"
        )

    # -----------------------------------------------------
    # SAVE ORDER
    # -----------------------------------------------------

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO orders
        (
            customer_name,
            phone,
            address,
            city,
            pincode,
            items,
            total,
            payment_method,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            customer_name,
            phone,
            address,
            city,
            pincode,
            json.dumps(
                items,
                ensure_ascii=False
            ),
            total,
            payment_method,
            "New"
        )
    )

    order_id = cursor.lastrowid

    conn.commit()

    conn.close()

    # -----------------------------------------------------
    # SAVE CUSTOMER PHONE
    # -----------------------------------------------------

    session[
        "customer_phone"
    ] = phone

    return redirect(
        url_for(
            "order_success",
            order_id=order_id
        )
    )


# =========================================================
# GET ORDER
# =========================================================

def get_order(order_id):

    conn = get_db()

    order = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE id = ?
        """,
        (order_id,)
    ).fetchone()

    conn.close()

    return order


# =========================================================
# PARSE ORDER ITEMS
# =========================================================

def parse_order_items(order):

    if not order:

        return []

    try:

        raw_items = order["items"]

        if isinstance(
            raw_items,
            str
        ):

            items = json.loads(
                raw_items
            )

        else:

            items = raw_items

        if isinstance(
            items,
            list
        ):

            return items

    except Exception:

        pass

    return []


# =========================================================
# WHATSAPP MESSAGE
# =========================================================

def build_whatsapp_message(order):

    items = parse_order_items(
        order
    )

    message_lines = []

    message_lines.append(
        "🪞 GLASSYLOOK - NEW ORDER"
    )

    message_lines.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    message_lines.append(
        f"📦 Order ID: #{order['id']}"
    )

    message_lines.append(
        f"📌 Status: {order['status'] or 'New'}"
    )

    message_lines.append("")

    message_lines.append(
        "👤 CUSTOMER DETAILS"
    )

    message_lines.append(
        f"Name: {order['customer_name']}"
    )

    message_lines.append(
        f"Phone: {order['phone']}"
    )

    message_lines.append("")

    message_lines.append(
        "📍 SHIPPING ADDRESS"
    )

    message_lines.append(
        order["address"]
    )

    message_lines.append(
        order["city"]
    )

    message_lines.append(
        f"Pincode: {order['pincode']}"
    )

    message_lines.append("")

    message_lines.append(
        "🪞 PRODUCT DETAILS"
    )

    for index, item in enumerate(
        items,
        start=1
    ):

        message_lines.append("")

        message_lines.append(
            f"{index}. "
            f"{item.get('name', 'Mirror')}"
        )

        message_lines.append(
            f"Price: ₹"
            f"{float(item.get('price', 0)):.2f}"
        )

        message_lines.append(
            f"Quantity: "
            f"{item.get('quantity', 1)}"
        )

        if item.get("size"):

            message_lines.append(
                f"Size: "
                f"{item.get('size')}"
            )

        if item.get("shape"):

            message_lines.append(
                f"Shape: "
                f"{item.get('shape')}"
            )

        if item.get("image"):

            image_url = url_for(
                "uploaded_file",
                filename=item["image"],
                _external=True
            )

            message_lines.append(
                f"Photo: {image_url}"
            )

    message_lines.append("")

    message_lines.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    total = float(
        order["total"] or 0
    )

    message_lines.append(
        f"💰 TOTAL: ₹{total:.2f}"
    )

    payment = (
        order["payment_method"]
        or "Cash on Delivery"
    )

    message_lines.append(
        f"💳 Payment: {payment}"
    )

    if payment == "Online Payment":

        before_amount = (
            total * 0.75
        )

        after_amount = (
            total * 0.25
        )

        message_lines.append(
            f"75% Before Order: "
            f"₹{before_amount:.2f}"
        )

        message_lines.append(
            f"25% After Delivery: "
            f"₹{after_amount:.2f}"
        )

        message_lines.append(
            f"UPI: {UPI_ID}"
        )

    message_lines.append("")

    message_lines.append(
        "📲 Please confirm this order."
    )

    message_lines.append(
        "Thank you - GlassyLook"
    )

    return "\n".join(
        message_lines
    )


# =========================================================
# WHATSAPP URL
# =========================================================

def get_whatsapp_url(order):

    message = build_whatsapp_message(
        order
    )

    return (
        "https://wa.me/"
        + OWNER_PHONE
        + "?text="
        + quote(
            message,
            safe=""
        )
    )


# =========================================================
# ORDER SUCCESS
# =========================================================

@app.route(
    "/order-success/<int:order_id>"
)
def order_success(order_id):

    order = get_order(order_id)

    if not order:

        return "Order not found", 404

    items = parse_order_items(order)

    whatsapp_url = get_whatsapp_url(order)

    return render_template(
        "order-details.html",
        order=order,
        items=items,
        whatsapp_url=whatsapp_url
    )


# =========================================================
# ORDER DETAILS
# =========================================================

@app.route(
    "/order/<int:order_id>"
)
def order_details(order_id):

    order = get_order(order_id)

    if not order:

        return "Order not found", 404

    items = parse_order_items(order)

    whatsapp_url = get_whatsapp_url(order)

    return render_template(
        "order-details.html",
        order=order,
        items=items,
        whatsapp_url=whatsapp_url
    )


# =========================================================
# SEND ORDER TO WHATSAPP
# =========================================================

@app.route(
    "/send-whatsapp/<int:order_id>"
)
def send_whatsapp(order_id):

    order = get_order(order_id)

    if not order:

        return "Order not found", 404

    whatsapp_url = get_whatsapp_url(order)

    return redirect(whatsapp_url)


# =========================================================
# MY ORDERS
# =========================================================

@app.route("/my-orders")
def my_orders():

    phone = session.get(
        "customer_phone"
    )

    orders = []

    if phone:

        conn = get_db()

        rows = conn.execute(
            """
            SELECT *
            FROM orders
            WHERE phone = ?
            ORDER BY id DESC
            """,
            (phone,)
        ).fetchall()

        conn.close()

        for row in rows:

            order = dict(row)

            try:

                order["items"] = json.loads(
                    order.get("items") or "[]"
                )

            except Exception:

                order["items"] = []

            orders.append(order)

    return render_template(
        "my-orders.html",
        orders=orders
    )


# =========================================================
# TRACK ORDER
# =========================================================

@app.route(
    "/track-order",
    methods=["GET", "POST"]
)
def track_order():

    order = None
    items = []

    if request.method == "POST":

        order_id = request.form.get(
            "order_id",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not order_id or not phone:

            return render_template(
                "tracking.html",
                order=None,
                items=[],
                error=(
                    "Please enter Order ID and Mobile Number."
                )
            )

        # -------------------------------------------------
        # ORDER ID
        # -------------------------------------------------

        try:

            order_id = int(order_id)

        except ValueError:

            return render_template(
                "tracking.html",
                order=None,
                items=[],
                error="Invalid Order ID."
            )

        # -------------------------------------------------
        # FIND ORDER
        # -------------------------------------------------

        conn = get_db()

        row = conn.execute(
            """
            SELECT *
            FROM orders
            WHERE id = ?
            AND phone = ?
            """,
            (
                order_id,
                phone
            )
        ).fetchone()

        conn.close()

        # -------------------------------------------------
        # ORDER FOUND
        # -------------------------------------------------

        if row:

            order = dict(row)

            items = parse_order_items(order)

        # -------------------------------------------------
        # ORDER NOT FOUND
        # -------------------------------------------------

        else:

            return render_template(
                "tracking.html",
                order=None,
                items=[],
                error=(
                    "Order not found. "
                    "Please check Order ID and Mobile Number."
                )
            )

    return render_template(
        "tracking.html",
        order=order,
        items=items
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin-logout")
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    session.pop(
        "admin_username",
        None
    )

    return redirect(
        url_for("admin_login")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )