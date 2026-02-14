from flask import Flask, render_template, request, redirect, url_for, session,flash, sessions
import sqlite3
from werkzeug.utils import secure_filename
from functools import wraps
import json
import os
from datetime import datetime, timedelta
import random,time
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.message import EmailMessage
app = Flask(__name__)
EMAIL_ADDRESS = "devadharshiniramachandran435@gmail.com"
EMAIL_PASSWORD = "vadk tqhr arsr ltfi"
app.secret_key = "12345"  # Session secret key
OTP_EXPIRY = 300 
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

# 1️⃣ Define the function once

def send_status_email(to_email, order_id, order_date, status): 
    msg = EmailMessage()
    msg['Subject'] = 'Order Status Updated'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email

    msg.set_content(f"""
Hello,

Your order has been updated successfully.

Order ID: {order_id}
Order Date: {order_date}
Current Status: {status}

Thank you for shopping with us.
""")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg) 


def send_new_product_email(description):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT email FROM users")
        users = cur.fetchall()
        conn.close()

        for user in users:
            receiver = user["email"]

            msg = EmailMessage()
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = receiver
            msg["Subject"] = "New Product Added"

            msg.set_content(
                f"Hello,\n\n"
                f"A new product has been added to our store.\n\n"
                f"Product Description:\n{description}\n\n"
                f"Visit the app to know more.\n\n"
                f"Thank you."
            )

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

        print("Emails sent successfully")

    except Exception as e:
        print("EMAIL ERROR:", e)


def send_otp_email(to_email, otp):
    msg = EmailMessage()
    msg['Subject'] = "Your OTP Verification Code"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg.set_content(
        f"Your OTP is {otp}. It is valid for 5 minutes."
    )

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
def send_account_created_email(to_email, name):
    msg = EmailMessage()
    msg['Subject'] = "Welcome! Your Account is Ready 🎉"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email

    msg.set_content(f"""
Hi {name},

Your account has been created successfully.

You can now log in using your email and password.

Thanks,
Dish2Cart Team
""")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
def generate_otp():
    return str(random.randint(100000, 999999))
# Absolute database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")
# ---------- DB Connection ----------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Home Page ----------
@app.route("/")
def home():
    return render_template("home.html")

# ---------- Register ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        # Check if email already exists
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        existing = cur.fetchone()
        if existing:
            conn.close()
            return render_template("register.html", error="Email already exists")

        # Insert new user into database
        cur.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )
        conn.commit()
        conn.close()

        # Redirect to login page (manual login)
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------- Login ----------


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        # Fetch user by email only
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()

        # Verify password hash
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            session["profile_img"] = url_for('static', filename='images/male.png')

            return redirect(url_for("home"))
        else:
            # Show error message in login page
            return render_template("login.html", error="Invalid login details")

    return render_template("login.html")



@app.context_processor
def cart_count_processor():
    user_id = session.get('user_id')
    if not user_id:
        return dict(cart_count=0)

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT SUM(quantity) FROM cart WHERE user_id=?", (user_id,))
    count = cur.fetchone()[0] or 0
    conn.close()
    return dict(cart_count=count)

# ---------- Profile ----------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT name, email, reward_points
        FROM users
        WHERE id=?
    """, (user_id,))

    user = cur.fetchone()
    conn.close()

    return render_template("profile.html", user=user)


# ---------- Logout ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------- Products Page (optional) ----------


@app.route('/products')
def products():
    # Step 1: Check if user is logged in
    if 'user_id' not in session:
        flash("Please login to see products")
        return redirect(url_for('login'))

    # Step 2: Check if Show More was clicked
    show_all_category = request.args.get('category')
    show_all_flag = request.args.get('show_all')

    # Step 3: Connect to database
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY category")
    rows = cur.fetchall()
    conn.close()

    # Step 4: Group products by category
    from collections import defaultdict
    all_categories = defaultdict(list)
    for row in rows:
        all_categories[row['category']].append(row)

    # Step 5: Limit products to 5 per category, unless Show More clicked
    categories = {}
    for cat, items in all_categories.items():
        if show_all_flag and show_all_category == cat:
            categories[cat] = items
        else:
            categories[cat] = items[:5]
    # Step 6: Render template
    return render_template('products.html', categories=categories, all_categories=all_categories)

@app.route('/orders')
def orders():
    return render_template('orders.html')

@app.route('/search')
def search():
    query = request.args.get('query', '').strip().lower()
    search_by = request.args.get('search_by', 'item').strip()

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = []

    if search_by == 'dish':
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()

        for row in rows:
            if row['dish_name']:  # skip empty
                # split multiple dishes
                dishes = [d.strip().lower() for d in row['dish_name'].split(',')]
                # check if query matches any dish partially
                if any(query in dish for dish in dishes):
                    results.append(row)
    else:  # search by item
        cursor.execute("""
            SELECT * FROM products
            WHERE LOWER(product_name) LIKE ?
        """, ('%' + query + '%',))
        results = cursor.fetchall()

    conn.close()

    return render_template(
        'products.html',
        results=results,
        query=query
    )

@app.route('/product/<int:pid>', methods=['GET', 'POST'])
def product_detail(pid):
    # ✅ STEP 0: Get logged-in user
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # ✅ STEP 1: Get product details
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id = ?", (pid,))
    product = cur.fetchone()
    conn.close()

    if not product:
        return "Product not found"

    quantity = 1  # default quantity
    total_price = product['price'] * quantity

    # ✅ STEP 2: Handle form submission
    if request.method == 'POST':
        quantity = int(request.form['quantity'])
        action = request.form.get('action')

        # -------- STOCK CHECK --------
        if product['stock'] == 0:
            return redirect(url_for('product_detail', pid=pid))

        # -------- BUY NOW --------
        if action == 'buy':
           session['buy_now'] = {
             'product_id': pid,
             'quantity': quantity
              }
           return redirect(url_for('checkout'))

        # -------- ADD TO CART --------
        elif action == 'add_to_cart':
            conn = sqlite3.connect('database.db')
            cur = conn.cursor()

            # Check if item already in cart
            cur.execute(
                "SELECT id, quantity FROM cart WHERE user_id=? AND product_id=?",
                (user_id, pid)
            )
            existing = cur.fetchone()

            if existing:
                # Update quantity
                new_qty = existing[1] + quantity
                cur.execute(
                    "UPDATE cart SET quantity=? WHERE id=?",
                    (new_qty, existing[0])
                )
            else:
                # Insert new
                cur.execute(
                    "INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
                    (user_id, pid, quantity)
                )

            conn.commit()
            conn.close()

            # Stay on product page after adding to cart
            return redirect(url_for('product_detail', pid=pid))

    # ✅ STEP 3: Calculate total price for display
    total_price = product['price'] * quantity

    # ✅ STEP 4: Render template
    return render_template(
        'product_detail.html',
        product=product,
        quantity=quantity,
        total_price=total_price
    )

@app.route('/checkout')
def checkout():
    buy_now = session.get('buy_now')

    if not buy_now:
        return "No product selected for Buy Now"

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id=?", (buy_now['product_id'],))
    product = cur.fetchone()
    conn.close()

    if not product:
        return "Product not found"

    total = product['price'] * buy_now['quantity']

    return render_template(
        'checkout.html',
        mode='buy_now',          # ✅ THIS WAS MISSING
        product=product,
        quantity=buy_now['quantity'],
        total=total
    )

@app.route('/cart_checkout')
def cart_checkout():
    cart_items = session.get('cart', [])

    if not cart_items:
        return "Your cart is empty"

    total_price = sum(item['price'] * item['quantity'] for item in cart_items)

    return render_template(
        'cart_checkout.html',
        cart_items=cart_items,
        total_price=total_price
    )

@app.route('/set-password', methods=['POST', 'GET'])
def set_password():
    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            return "Passwords do not match"

        hashed_password = generate_password_hash(password)
        name = session.get('name')   # ✅ Get name from session
        email = session.get('email')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                       (name, email, hashed_password))
        conn.commit()
        conn.close()
        send_account_created_email(email, name)
        session.clear()
        return render_template("account_created.html")


    return render_template('set_password.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.form.get('email') or request.args.get('email')


    if request.method == 'POST':
        user_otp = request.form['otp']

        cursor = get_db().cursor()
        cursor.execute(
            "SELECT otp, created_at FROM email_otp WHERE email=?",
            (email,)
        )
        record = cursor.fetchone()

        if not record:
            return "OTP not found. Please resend."

        stored_otp, stored_time = record
        current_time = int(time.time())

        if current_time - stored_time > OTP_EXPIRY:
            return "OTP expired. Please resend."

        if user_otp != stored_otp:
            return "Invalid OTP"

        return redirect(url_for('set_password', email=email))

    return render_template('verify_otp.html', email=email)

@app.route('/send-otp', methods=['POST'])
def send_otp():
    # 1️⃣ Get data from form
    name = request.form['name'].strip()
    email = request.form['email'].strip().lower()

    # 2️⃣ Open database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # 3️⃣ Check if email already exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return redirect(url_for('register', error="Email already registered"))

    # 4️⃣ Generate OTP
    otp = generate_otp()
    current_time = int(time.time())

    # 5️⃣ Store required data in session (NOT OTP)
    session['name'] = name
    session['email'] = email

    # 6️⃣ Remove old OTP and insert new one
    cursor.execute("DELETE FROM email_otp WHERE email = ?", (email,))
    cursor.execute(
        "INSERT INTO email_otp (email, otp, created_at) VALUES (?, ?, ?)",
        (email, otp, current_time)
    )

    # 7️⃣ Save and close DB
    conn.commit()
    conn.close()

    # 8️⃣ TEMP debug (remove later)
    print("OTP for", email, "is", otp)
    send_otp_email(email, otp)


    # 9️⃣ Go to verify page
    return redirect(url_for('verify_otp', email=email))



@app.route('/address', methods=['GET', 'POST'])
def address():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Pre-fill address if exists
    cur.execute("SELECT * FROM user_addresses WHERE user_id=?", (user_id,))
    existing_address = cur.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address_text = request.form['address']
        city = request.form['city']
        pincode = request.form['pincode']

        if existing_address:
            cur.execute("""
                UPDATE user_addresses
                SET name=?, phone=?, address=?, city=?, pincode=?
                WHERE user_id=?
            """, (name, phone, address_text, city, pincode, user_id))
        else:
            cur.execute("""
                INSERT INTO user_addresses (user_id, name, phone, address, city, pincode)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, name, phone, address_text, city, pincode))

        conn.commit()
        conn.close()

        # Save in session for current checkout
        session['address'] = {
            'name': name,
            'phone': phone,
            'address': address_text,
            'city': city,
            'pincode': pincode
        }

        return redirect(url_for('payment'))

    conn.close()
    return render_template('address.html', address=existing_address)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    address = session.get('address')
    if not address:
        return redirect(url_for('address'))

    buy_now = session.get('buy_now')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == 'POST':
        session['payment_method'] = request.form['payment_method']
        return redirect(url_for('place_order'))

    if buy_now:
        cur.execute("SELECT * FROM products WHERE id=?", (buy_now['product_id'],))
        product = cur.fetchone()
        conn.close()
        return render_template('payment.html', mode='buy_now', product=product, quantity=buy_now['quantity'], address=address)
    else:
        cur.execute("""
            SELECT products.product_name, products.price, cart.quantity
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = ?
        """, (user_id,))
        cart_items = cur.fetchall()
        total_price = sum(item['price'] * item['quantity'] for item in cart_items)
        conn.close()
        return render_template('payment.html', mode='cart', cart_items=cart_items, total_price=total_price, address=address)


@app.route('/cart')
def cart():
    user_id = session.get('user_id')
    if not user_id:
         return redirect(url_for('login'))


    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT cart.id AS cart_id,
               products.product_name,
                products.image,
               products.price,
               cart.quantity,
               (products.price * cart.quantity) AS total
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
    """, (user_id,))
    cart_items = cur.fetchall()

    # 🔢 Cart count
    cur.execute(
        "SELECT SUM(quantity) FROM cart WHERE user_id=?",
        (user_id,)
    )
    cart_count = cur.fetchone()[0] or 0

    grand_total = sum(item['total'] for item in cart_items)

    conn.close()

    return render_template(
        'cart.html',
        cart_items=cart_items,
        grand_total=grand_total,
        cart_count=cart_count
    )

@app.route('/cart/increase/<int:cart_id>')
def increase_quantity(cart_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        "UPDATE cart SET quantity = quantity + 1 WHERE id = ?",
        (cart_id,)
    )

    conn.commit()
    conn.close()
    return redirect(url_for('cart'))


@app.route('/cart/decrease/<int:cart_id>')
def decrease_quantity(cart_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # Prevent quantity going below 1
    cur.execute(
        "UPDATE cart SET quantity = CASE WHEN quantity > 1 THEN quantity - 1 ELSE 1 END WHERE id = ?",
        (cart_id,)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))
@app.route('/remove_cart/<int:cart_id>', methods=['POST'])
def remove_cart(cart_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM cart WHERE id=?", (cart_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

@app.route('/place_order')
def place_order():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    address_dict = session.get('address')
    payment_method = session.get('payment_method', 'COD')
    if not address_dict:
        return redirect(url_for('address'))

    # Convert address dict → JSON string
    address = json.dumps(address_dict)

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    products_list = []  # 🔥 This will store products for orders.products

    # ================= BUY NOW =================
    buy_now = session.get('buy_now')
    if buy_now:
        product_id = buy_now['product_id']
        quantity = buy_now['quantity']

        cur.execute("SELECT id, product_name, price, stock FROM products WHERE id = ?", (product_id,))
        product = cur.fetchone()
        if not product:
            conn.close()
            return "Product not found"

        # Add to products_list
        products_list.append({
            "product_id": product['id'],
            "product_name": product['product_name'],
            "quantity": quantity,
            "price": product['price']
        })

        # Update stock
        new_stock = max(product['stock'] - quantity, 0)
        cur.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, product_id))

        session.pop('buy_now', None)

    # ================= CART =================
    else:
        cur.execute("""
            SELECT cart.product_id, cart.quantity, products.product_name, products.price, products.stock
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = ?
        """, (user_id,))
        cart_items = cur.fetchall()

        for item in cart_items:
            products_list.append({
                "product_id": item['product_id'],
                "product_name": item['product_name'],
                "quantity": item['quantity'],
                "price": item['price']
            })

            # Update stock
            new_stock = max(item['stock'] - item['quantity'], 0)
            cur.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, item['product_id']))

        # Clear cart
        cur.execute("DELETE FROM cart WHERE user_id=?", (user_id,))

    # 🔥 Convert products_list → JSON string
    products_json = json.dumps(products_list)

    # ================= CREATE ORDER =================
    cur.execute("""
        INSERT INTO orders (user_id, address, payment_method, status, products)
        VALUES (?, ?, ?, 'Placed', ?)
    """, (user_id, address, payment_method, products_json))
    order_id = cur.lastrowid

    # ================= INSERT INTO order_items =================
    for p in products_list:
        cur.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
        """, (order_id, p['product_id'], p['quantity'], p['price']))

    conn.commit()
    conn.close()

    # Clear session
    session.pop('address', None)
    session.pop('payment_method', None)

    return redirect(url_for('order_success'))


@app.route('/order/<int:order_id>')
def order_details(order_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM orders
        WHERE id = ? AND user_id = ?
    """, (order_id, user_id))
    order = cur.fetchone()

    if not order:
        conn.close()
        return "Order not found"

    address = json.loads(order['address'])

    cur.execute("""
        SELECT products.product_name,
               order_items.quantity,
               order_items.price
        FROM order_items
        JOIN products ON order_items.product_id = products.id
        WHERE order_items.order_id = ?
    """, (order_id,))
    items = cur.fetchall()

    # ✅ CALCULATE TOTAL HERE
    total = sum(item['price'] * item['quantity'] for item in items)
    conn.close()
    return render_template(
        'order_details.html',
        order=order,
        items=items,
        address=address,
        total=total   # 🔥 PASS TOTAL
    )

@app.route('/cancel_order/<int:order_id>')
def cancel_order(order_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Get order (security + status check)
    cur.execute("""
        SELECT * FROM orders
        WHERE id = ? AND user_id = ?
    """, (order_id, user_id))
    order = cur.fetchone()
    if not order:
        conn.close()
        return "Order not found"
    # ❌ Only Placed orders can be cancelled
    if order['status'] != 'Placed':
        conn.close()
        return "Order cannot be cancelled"
    # Get ordered items
    cur.execute("""
        SELECT product_id, quantity
        FROM order_items
        WHERE order_id = ?
    """, (order_id,))
    items = cur.fetchall()
    # Restore stock
    for item in items:
        cur.execute("""
            UPDATE products
            SET stock = stock + ?
            WHERE id = ?
        """, (item['quantity'], item['product_id']))
    # Update order status
    cur.execute("""
        UPDATE orders
        SET status = 'Cancelled'
        WHERE id = ?
    """, (order_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('my_orders'))

@app.route('/update_order_status/<int:order_id>/<status>')
def update_order_status(order_id, status):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (status, order_id))

    conn.commit()
    conn.close()

    return redirect(url_for('my_orders'))


@app.route('/my_orders')
def my_orders():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))
    orders = cur.fetchall()

    orders_with_items = []

    for order in orders:
        cur.execute("""
            SELECT order_items.quantity,
                   order_items.price,
                   products.product_name
            FROM order_items
            JOIN products ON order_items.product_id = products.id
            WHERE order_items.order_id = ?
        """, (order['id'],))

        order_items = cur.fetchall()  # 🔥 RENAMED

        orders_with_items.append({
            'order': order,
            'order_items': order_items   # 🔥 RENAMED
        })

    conn.close()

    return render_template('my_orders.html', orders=orders_with_items)

@app.route("/invoice/<int:order_id>")
def download_invoice(order_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ---------- Fetch order ----------
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cur.fetchone()

    if not order:
        conn.close()
        return "Order not found"

    # ---------- Load address JSON safely ----------
    try:
        address = json.loads(order['address']) if order['address'] else {}
    except json.JSONDecodeError:
        address = {}

    # ---------- Fetch order items with product name ----------
    cur.execute("""
        SELECT 
            products.product_name AS product_name,
            order_items.quantity,
            order_items.price
        FROM order_items
        JOIN products ON order_items.product_id = products.id
        WHERE order_items.order_id = ?
    """, (order_id,))
    items = cur.fetchall()

    conn.close()

    # ---------- PDF Setup ----------
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    # ---------- Title ----------
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, y, "INVOICE")
    y -= 40

    # ---------- Order Info ----------
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Order ID: {order['id']}")
    y -= 18
    pdf.drawString(50, y, f"Payment Method: {order['payment_method']}")
    y -= 18
    pdf.drawString(50, y, f"Order Status: {order['status']}")
    y -= 25
    # ---------- Delivery Address ----------
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "Delivery Address:")
    y -= 15
    pdf.setFont("Helvetica", 11)
    address_lines = [
        f"Name: {address.get('name', '')}",
        f"Phone: {address.get('phone', '')}",
        f"Address: {address.get('address', '')}",
        f"City: {address.get('city', '')}",
        f"Pincode: {address.get('pincode', '')}"
    ]

    for line in address_lines:
        if y < 80:   # page break safety
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 50
        pdf.drawString(50, y, line)
        y -= 15
    y -= 10
    # ---------- Table Header ----------
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "Product")
    pdf.drawString(300, y, "Qty")
    pdf.drawString(350, y, "Price")
    pdf.drawString(430, y, "Total")
    y -= 15
    pdf.setFont("Helvetica", 11)
    total_amount = 0    # ---------- Items ----------
    for item in items:
        item_total = item['price'] * item['quantity']
        total_amount += item_total

        if y < 80:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 50

        pdf.drawString(50, y, item['product_name'])
        pdf.drawString(300, y, str(item['quantity']))
        pdf.drawString(350, y, f"Rs. {item['price']}")
        pdf.drawString(430, y, f"Rs. {item_total}")
        y -= 18

    # ---------- Grand Total ----------
    y -= 15
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(350, y, "Grand Total:")
    pdf.drawString(430, y, f"Rs. {total_amount}")

    # ---------- Save PDF ----------
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Invoice_Order_{order_id}.pdf",
        mimetype="application/pdf"
    )

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, role FROM users WHERE email=? AND password=?",
            (email, password)
        )
        admin = cur.fetchone()
        conn.close()

        if admin and admin[1] == "admin":
            session["admin_id"] = admin[0]
            session["admin_logged_in"] = True   # ✅ ADD THIS LINE
            return redirect("/admin/dashboard")
        else:
            return "Invalid admin credentials"

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    if "admin_id" not in session:
        return redirect("/admin/login")

    conn = get_db()
    cur = conn.cursor()

    # Total products
    cur.execute("SELECT COUNT(*) FROM products")
    total_products = cur.fetchone()[0]

    # Total orders
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]

    # Orders by status
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='Placed'")
    placed = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE status='Packed'")
    packed = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE status='Shipped'")
    shipped = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE status='Delivered'")
    delivered = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
    total_users = cur.fetchone()[0]


    # 🔔 NEW: Fetch latest 5 new orders
    cur.execute("""
        SELECT id, user_id, order_date
        FROM orders
        WHERE status='Placed'
        ORDER BY order_date DESC
        LIMIT 5
    """)
    new_orders = cur.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        placed=placed,
        packed=packed,
        shipped=shipped,
        delivered=delivered,
        total_users=total_users,
        new_orders=new_orders   # 🔔 send to template
    )

@app.route("/admin/orders", methods=["GET", "POST"])
def admin_orders():
    if "admin_id" not in session:
        return redirect("/admin/login")

    conn = get_db()
    cur = conn.cursor()

    # ---------------- POST: update status + rewards ----------------
    if request.method == "POST":
        order_id = request.form["order_id"]
        new_status = request.form["status"]

        # Update order status
        cur.execute(
            "UPDATE orders SET status=? WHERE id=?",
            (new_status, order_id)
        )
        conn.commit()

        # Reward logic ONLY when Delivered
        if new_status == "Delivered":

            # Check reward flag
            cur.execute(
                "SELECT reward_given, user_id FROM orders WHERE id=?",
                (order_id,)
            )
            reward_given, user_id = cur.fetchone()

            if reward_given == 0:
                # Calculate total amount
                cur.execute("""
                    SELECT SUM(quantity * price)
                    FROM order_items
                    WHERE order_id=?
                """, (order_id,))
                total_amount = cur.fetchone()[0] or 0

                reward_points = int(total_amount // 100)

                # Add reward points to user
                cur.execute("""
                    UPDATE users
                    SET reward_points = reward_points + ?
                    WHERE id=?
                """, (reward_points, user_id))

                # Mark reward as given
                cur.execute("""
                    UPDATE orders
                    SET reward_given = 1
                    WHERE id=?
                """, (order_id,))

                conn.commit()

    # ---------------- GET: fetch orders ----------------
    cur.execute("""
        SELECT id, user_id, order_date, status
        FROM orders
        ORDER BY order_date DESC
    """)
    orders = cur.fetchall()

    # Fetch products for each order
    order_products = {}
    for order in orders:
        oid = order[0]
        cur.execute("""
            SELECT p.product_name, oi.quantity, oi.price
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id=?
        """, (oid,))
        order_products[oid] = cur.fetchall()

    conn.close()

    return render_template(
        "admin_orders.html",
        orders=orders,
        order_products=order_products
    )



@app.route('/order_success')
def order_success():
    return "Order placed successfully!"

@app.route("/admin/users")
def admin_users():
    if "admin_id" not in session:
        return redirect("/admin/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            u.id,
            u.name,
            u.email,
            u.reward_points,
            COUNT(o.id) as total_orders
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
                 WHERE u.role = 'user'
        GROUP BY u.id
        ORDER BY u.id DESC
    """)

    users = cur.fetchall()
    conn.close()

    return render_template("admin_users.html", users=users)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/admin/login")



@app.route("/admin/products")
@admin_required
def admin_products():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    conn.close()

    return render_template("admin_products.html", products=products)



@app.route("/admin/add-product", methods=["GET", "POST"])
def admin_add_product():

    # 🔐 Optional: protect admin page
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        product_name = request.form["product_name"]
        dish_name = request.form.get("dish_name")
        category = request.form["category"]
        description = request.form["description"]
        price = request.form["price"]
        stock = request.form["stock"]

        image_file = request.files["image"]

        # Save image
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image_file.save(image_path)

        # Store relative path in DB
        image_db_path = f"{filename}"

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO products 
            (product_name, dish_name, category, description, price, stock, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product_name,
            dish_name,
            category,
            description,
            price,
            stock,
            image_db_path
        ))

        conn.commit()

        send_new_product_email(description)
        conn.close()

        return redirect(url_for("admin_products"))

    return render_template("admin_add_product.html")

@app.route("/admin/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        product_name = request.form["product_name"]
        dish_name = request.form["dish_name"]
        category = request.form["category"]
        description = request.form["description"]
        price = request.form["price"]
        stock = request.form["stock"]

        cur.execute("""
            UPDATE products
            SET product_name=?, dish_name=?, category=?, description=?, price=?, stock=?
            WHERE id=?
        """, (product_name, dish_name, category, description, price, stock, product_id))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_products"))

    # GET request → fetch product
    cur.execute("SELECT * FROM products WHERE id=?", (product_id,))
    product = cur.fetchone()
    conn.close()

    return render_template("admin_edit_product.html", product=product)


@app.route("/admin/delete-product/<int:product_id>")
def delete_product(product_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()
    cur = conn.cursor()

    # Get image name before deleting product
    cur.execute("SELECT image FROM products WHERE id=?", (product_id,))
    product = cur.fetchone()

    if product:
        image_filename = product["image"]

        # Delete product from DB
        cur.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()

        # Delete image file
        image_path = os.path.join("static/uploads", image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

    conn.close()
    return redirect(url_for("admin_products"))


if __name__ == "__main__":
    app.run(debug=True)
