import email
from flask import Flask, render_template, request, redirect, url_for, session,flash, sessions
import sqlite3
import pymysql
pymysql.install_as_MySQLdb()
from flask_mysqldb import MySQL
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
from staff import staff
app.register_blueprint(staff)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Avc@1234'
app.config['MYSQL_DB'] = 'grocery_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)
EMAIL_ADDRESS = "devadharshiniramachandran435@gmail.com"
EMAIL_PASSWORD = "vadk tqhr arsr ltfi"
app.secret_key = "12345"  # Session secret key
OTP_EXPIRY = 300 
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------- Register ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT customer_id FROM customer WHERE customer_email = %s",
            (email,)
        )
        if cur.fetchone():
            cur.close()
            return render_template("register.html", error="Email already exists")

        cur.execute(
            """
            INSERT INTO customer (customer_name, customer_email, customer_password)
            VALUES (%s, %s, %s)
            """,
            (name, email, password)
        )
        mysql.connection.commit()
        cur.close()

        return redirect(url_for("login"))

    return render_template("register.html")

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
    msg["Subject"] = "🎉 Your Order Has Been Delivered!"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    # Plain text fallback
    msg.set_content("Your order has been delivered successfully.")

    # HTML DESIGN EMAIL
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f6f8; padding:20px;">

        <div style="
            max-width:600px;
            margin:auto;
            background:white;
            border-radius:10px;
            overflow:hidden;
            box-shadow:0 0 10px rgba(0,0,0,0.1);
        ">

            <!-- Header -->
            <div style="background:#28a745;color:white;padding:20px;text-align:center;">
                <h2>Dish2Cart</h2>
                <h3>✅ Order Delivered Successfully</h3>
            </div>

            <!-- Body -->
            <div style="padding:25px;color:#333;">

                <p>Hello Customer,</p>

                <p>Your order has been <b style="color:green;">Delivered</b> 🎉</p>

                <table style="width:100%;margin-top:15px;border-collapse:collapse;">
                    <tr>
                        <td style="padding:8px;"><b>Order ID</b></td>
                        <td style="padding:8px;">#{order_id}</td>
                    </tr>
                    <tr style="background:#f2f2f2;">
                        <td style="padding:8px;"><b>Order Date</b></td>
                        <td style="padding:8px;">{order_date}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px;"><b>Status</b></td>
                        <td style="padding:8px;color:green;"><b>{status}</b></td>
                    </tr>
                </table>

                <p style="margin-top:20px;">
                    Thank you for shopping with us ❤️<br>
                    We hope to see you again!
                </p>

                <div style="text-align:center;margin-top:25px;">
                    <a href="http://127.0.0.1:5000"
                       style="
                       background:#28a745;
                       color:white;
                       padding:12px 20px;
                       text-decoration:none;
                       border-radius:5px;
                       font-weight:bold;">
                       Continue Shopping
                    </a>
                </div>

            </div>

            <!-- Footer -->
            <div style="background:#f1f1f1;padding:15px;text-align:center;font-size:12px;">
                © 2026 Dish2Cart • Grocery Management System
            </div>

        </div>

    </body>
    </html>
    """

    msg.add_alternative(html_content, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


@app.route('/set-password', methods=['POST', 'GET'])
def set_password():
    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            return "Passwords do not match"

        
        name = session.get('name')   # ✅ Get name from session
        email = session.get('email')
        

        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute("INSERT INTO customer (customer_name, customer_email, customer_password) VALUES (%s, %s, %s)",
                       (name, email, password))
        conn.commit()
        cursor.close()
        send_account_created_email(email, name)
        session.clear()
        return render_template("account_created.html")


    return render_template('set_password.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.form.get('email') or request.args.get('email')


    if request.method == 'POST':
        user_otp = request.form['otp']

        cursor = mysql.connection.cursor()
        cursor.execute(
    """
    SELECT otp 
    FROM email_otp 
    WHERE email = %s 
    AND created_at >= NOW() - INTERVAL 5 MINUTE
    """,
    (email,)
)
        record = cursor.fetchone()

        if not record:
            return "OTP expired or not found. Please resend."

        stored_otp = record['otp']

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
    conn = mysql.connection
    cursor = conn.cursor()

    # 3️⃣ Check if email already exists
    cursor.execute("SELECT customer_id FROM customer WHERE customer_email = %s", (email,))
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
    cursor.execute("DELETE FROM email_otp WHERE email = %s", (email,))
    cursor.execute(
        "INSERT INTO email_otp (email, otp) VALUES (%s, %s)",
        (email, otp)
    )

    # 7️⃣ Save and close DB
    conn.commit()
    cursor.close()

    # 8️⃣ TEMP debug (remove later)
    print("OTP for", email, "is", otp)
    send_otp_email(email, otp)


    # 9️⃣ Go to verify page
    return redirect(url_for('verify_otp', email=email))



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

# ---------- Login ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT customer_id, customer_name, customer_email, customer_password "
            "FROM customer WHERE customer_email = %s",
            (email,)
        )
        user = cursor.fetchone()
        cursor.close()

        if not user:
            print("NO USER FOUND")
            return render_template("login.html", error="Invalid login details")

        db_password = str(user["customer_password"]).strip()

        if password != db_password:
            print("PASSWORD MISMATCH")
            return render_template("login.html", error="Invalid login details")

        session["customer_id"] = user["customer_id"]
        session["customer_name"] = user["customer_name"]
        session["customer_email"] = user["customer_email"]

        print("LOGIN SUCCESS")
        return redirect(url_for("home"))

    return render_template("login.html")

@app.context_processor
def cart_count_processor():
    user_id = session.get("customer_id")  # FIXED KEY

    if not user_id:
        return dict(cart_count=0)

    cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)  # FIXED CURSOR
    cursor.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS total FROM cart WHERE customer_id = %s",
        (user_id,)
    )
    result = cursor.fetchone()
    cursor.close()

    return dict(cart_count=result["total"] if result else 0)
# ---------- Profile ----------

@app.route("/profile")
def profile():
    if "customer_id" not in session:
        return redirect(url_for("login"))

    customer_id = session["customer_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            customer_name,
            customer_email,
            reward_points
        FROM customer
        WHERE customer_id = %s
    """, (customer_id,))

    user = cur.fetchone()
    cur.close()

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
    if 'customer_id' not in session:
        flash("Please login to see products")
        return redirect(url_for('login'))

    # Step 2: Check if Show More was clicked
    show_all_category = request.args.get('category')
    show_all_flag = request.args.get('show_all')

    # Step 3: Connect to MySQL database
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products ORDER BY category")
    rows = cur.fetchall()
    cur.close()

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
    return render_template(
        'products.html',
        categories=categories,
        all_categories=all_categories
    )
@app.route('/orders')
def orders():
    return render_template('orders.html')

@app.route('/search')
def search():
    query = request.args.get('query', '').strip().lower()
    search_by = request.args.get('search_by', 'item').strip()

    cur = mysql.connection.cursor()
    results = []

    if search_by == 'dish':
        # Fetch all products (dish_name needs Python-side processing)
        cur.execute("SELECT * FROM products")
        rows = cur.fetchall()

        for row in rows:
            if row['dish_name']:  # skip empty / NULL
                dishes = [d.strip().lower() for d in row['dish_name'].split(',')]
                if any(query in dish for dish in dishes):
                    results.append(row)

    else:  # search by item (product_name)
        cur.execute("""
            SELECT * FROM products
            WHERE LOWER(product_name) LIKE %s
        """, ('%' + query + '%',))
        results = cur.fetchall()

    cur.close()

    return render_template(
        'products.html',
        results=results,
        query=query
    )
@app.route('/product/<int:pid>', methods=['GET', 'POST'])
def product_detail(pid):
    # ✅ STEP 0: Get logged-in user
    user_id = session.get('customer_id')
    if not user_id:
        return redirect(url_for('login'))

    # ✅ STEP 1: Get product details (MySQL)
    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM products WHERE product_id = %s",
        (pid,)
    )
    product = cur.fetchone()

    if not product:
        cur.close()
        return "Product not found"

    quantity = 1  # default quantity
    total_price = product['price'] * quantity

    # ✅ STEP 2: Handle form submission
    if request.method == 'POST':
        quantity = int(request.form['quantity'])
        action = request.form.get('action')

        # -------- STOCK CHECK --------
        if product['stock'] == 0:
            cur.close()
            return redirect(url_for('product_detail', pid=pid))

        # -------- BUY NOW --------
        if action == 'buy':
            session['buy_now'] = {
                'product_id': pid,
                'quantity': quantity
            }
            cur.close()
            return redirect(url_for('checkout'))

        # -------- ADD TO CART --------
        elif action == 'add_to_cart':

            # Check if item already in cart
            cur.execute(
                "SELECT cart_id, quantity FROM cart WHERE customer_id = %s AND product_id = %s",
                (user_id, pid)
            )
            existing = cur.fetchone()

            if existing:
                # Update quantity
                new_qty = existing['quantity'] + quantity
                cur.execute(
                    "UPDATE cart SET quantity = %s WHERE cart_id = %s",
                    (new_qty, existing['cart_id'])
                )
            else:
                # Insert new
                cur.execute(
                    "INSERT INTO cart (customer_id, product_id, quantity) VALUES (%s, %s, %s)",
                    (user_id, pid, quantity)
                )

            mysql.connection.commit()
            cur.close()

            # Stay on product page after adding to cart
            return redirect(url_for('product_detail', pid=pid))

    cur.close()

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

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM products WHERE product_id = %s",
        (buy_now['product_id'],)
    )
    product = cur.fetchone()
    cur.close()

    if not product:
        return "Product not found"

    total = product['price'] * buy_now['quantity']

    return render_template(
        'checkout.html',
        mode='buy_now',
        product=product,
        quantity=buy_now['quantity'],
        total=total
    )

@app.route('/cart_checkout')
def cart_checkout():
    user_id = session.get('customer_id')
    if not user_id:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            p.product_id,
            p.product_name,
            p.price,
            p.image,
            c.quantity
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    """, (user_id,))

    cart_items = cur.fetchall()
    cur.close()

    if not cart_items:
        return "Your cart is empty"

    total_price = sum(
        item['price'] * item['quantity']
        for item in cart_items
    )

    return render_template(
        'cart_checkout.html',
        cart_items=cart_items,
        total_price=total_price
    )

@app.route('/address', methods=['GET', 'POST'])
def address():
    customer_id = session.get('customer_id')   # user_id == customer_id
    if not customer_id:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # 🔹 Fetch existing customer address details
    cur.execute("""
        SELECT customer_name, phone, address, city, pincode
        FROM customer
        WHERE customer_id = %s
    """, (customer_id,))
    customer = cur.fetchone()

    if request.method == 'POST':
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        address_text = request.form['address'].strip()
        city = request.form['city'].strip()
        pincode = request.form['pincode'].strip()

        # 🔐 Basic validation
        if not phone.isdigit() or len(phone) != 10:
            cur.close()
            return "Invalid phone number"

        if not pincode.isdigit() or len(pincode) != 6:
            cur.close()
            return "Invalid pincode"

        # 🔹 Update customer address info
        cur.execute("""
            UPDATE customer
            SET customer_name = %s,
                phone = %s,
                address = %s,
                city = %s,
                pincode = %s
            WHERE customer_id = %s
        """, (name, phone, address_text, city, pincode, customer_id))

        mysql.connection.commit()
        cur.close()

        # 🔹 Store address in session for checkout flow
        session['address'] = {
            'name': name,
            'phone': phone,
            'address': address_text,
            'city': city,
            'pincode': pincode
        }

        return redirect(url_for('payment'))

    cur.close()
    return render_template('address.html', address=customer)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    customer_id = session.get('customer_id')
    if not customer_id:
        return redirect(url_for('login'))

    address = session.get('address')
    if not address:
        return redirect(url_for('address'))

    buy_now = session.get('buy_now')
    cur = mysql.connection.cursor()   # ✅ FIXED

    # 🔹 Handle payment submission
    if request.method == 'POST':
        session['payment_method'] = request.form['payment_method']
        cur.close()
        return redirect(url_for('place_order'))

    # ================= BUY NOW FLOW =================
    if buy_now:
        cur.execute(
            "SELECT * FROM products WHERE product_id = %s",
            (buy_now['product_id'],)
        )
        product = cur.fetchone()
        cur.close()

        if not product:
            return "Product not found"

        return render_template(
            'payment.html',
            mode='buy_now',
            product=product,
            quantity=buy_now['quantity'],
            address=address
        )

    # ================= CART FLOW =================
    cur.execute("""
        SELECT 
            p.product_name,
            p.price,
            c.quantity
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.customer_id = %s
    """, (customer_id,))

    cart_items = cur.fetchall()
    cur.close()

    if not cart_items:
        return "Your cart is empty"

    total_price = sum(item['price'] * item['quantity'] for item in cart_items)

    return render_template(
        'payment.html',
        mode='cart',
        cart_items=cart_items,
        total_price=total_price,
        address=address
    )

@app.route('/cart')
def cart():
    customer_id = session.get('customer_id')
    if not customer_id:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            c.cart_id,
            p.product_name,
            p.image,
            p.price,
            c.quantity,
            (p.price * c.quantity) AS total
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.customer_id = %s
    """, (customer_id,))

    cart_items = cur.fetchall()

    # 🔢 Cart count
    cur.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS cart_count FROM cart WHERE customer_id = %s",
        (customer_id,)
    )
    cart_count = cur.fetchone()['cart_count']

    grand_total = sum(item['total'] for item in cart_items)

    cur.close()

    return render_template(
        'cart.html',
        cart_items=cart_items,
        grand_total=grand_total,
        cart_count=cart_count
    )

@app.route('/cart/increase/<int:cart_id>')
def increase_quantity(cart_id):
    cur = mysql.connection.cursor()

    cur.execute(
        "UPDATE cart SET quantity = quantity + 1 WHERE cart_id = %s",
        (cart_id,)
    )

    mysql.connection.commit()
    cur.close()

    return redirect(url_for('cart'))

@app.route('/cart/decrease/<int:cart_id>')
def decrease_quantity(cart_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE cart
        SET quantity = CASE 
            WHEN quantity > 1 THEN quantity - 1 
            ELSE 1 
        END
        WHERE cart_id = %s
    """, (cart_id,))

    mysql.connection.commit()
    cur.close()

    return redirect(url_for('cart'))

@app.route('/remove_cart/<int:cart_id>', methods=['POST'])
def remove_cart(cart_id):
    cur = mysql.connection.cursor()

    cur.execute(
        "DELETE FROM cart WHERE cart_id = %s",
        (cart_id,)
    )

    mysql.connection.commit()
    cur.close()

    return redirect(url_for('cart'))

@app.route('/place_order')
def place_order():
    customer_id = session.get('customer_id')
    if not customer_id:
        return redirect(url_for('login'))

    address = session.get('address')
    payment_method = session.get('payment_method', 'COD')

    if not address:
        return redirect(url_for('address'))

    cur = mysql.connection.cursor()

    try:
        buy_now = session.get('buy_now')

        # ================= CREATE ORDER =================
        cur.execute("""
            INSERT INTO orders (customer_id, address, payment_method, status)
            VALUES (%s, %s, %s, 'Placed')
        """, (customer_id, json.dumps(address), payment_method))

        order_id = cur.lastrowid
        total_amount = 0

        # ================= BUY NOW =================
        if buy_now:
            cur.execute("""
                SELECT product_id, price, stock
                FROM products
                WHERE product_id = %s
            """, (buy_now['product_id'],))

            product = cur.fetchone()
            if not product:
                raise Exception("Product not found")

            if product['stock'] < buy_now['quantity']:
                raise Exception("Not enough stock")

            cur.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (
                order_id,
                buy_now['product_id'],
                buy_now['quantity'],
                product['price']
            ))

            cur.execute("""
                UPDATE products
                SET stock = stock - %s
                WHERE product_id = %s
            """, (buy_now['quantity'], buy_now['product_id']))

            total_amount += product['price'] * buy_now['quantity']
            session.pop('buy_now', None)

        # ================= CART =================
        else:
            cur.execute("""
                SELECT c.product_id, c.quantity, p.price, p.stock
                FROM cart c
                JOIN products p ON c.product_id = p.product_id
                WHERE c.customer_id = %s
            """, (customer_id,))

            cart_items = cur.fetchall()
            if not cart_items:
                raise Exception("Cart empty")

            for item in cart_items:
                if item['stock'] < item['quantity']:
                    raise Exception("Stock issue")

                cur.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, price)
                    VALUES (%s, %s, %s, %s)
                """, (
                    order_id,
                    item['product_id'],
                    item['quantity'],
                    item['price']
                ))

                cur.execute("""
                    UPDATE products
                    SET stock = stock - %s
                    WHERE product_id = %s
                """, (item['quantity'], item['product_id']))

                total_amount += item['price'] * item['quantity']

            cur.execute(
                "DELETE FROM cart WHERE customer_id = %s",
                (customer_id,)
            )

        # ================= UPDATE TOTAL =================
        cur.execute("""
            UPDATE orders
            SET total_amount = %s
            WHERE order_id = %s
        """, (total_amount, order_id))

        mysql.connection.commit()

        session.pop('address', None)
        session.pop('payment_method', None)

        return redirect(url_for('order_details', order_id=order_id))

    except Exception as e:
        mysql.connection.rollback()
        return str(e)

    finally:
        cur.close()

@app.route('/order/<int:order_id>')
def order_details(order_id):
    customer_id = session.get('customer_id')
    if not customer_id:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # 🔹 Fetch order (security: only owner can view)
    cur.execute("""
        SELECT *
        FROM orders
        WHERE order_id = %s AND customer_id = %s
    """, (order_id, customer_id))

    order = cur.fetchone()

    if not order:
        cur.close()
        return "Order not found"

    # 🔹 Decode address JSON
    address = json.loads(order['address'])

    # 🔹 Fetch ordered items
    cur.execute("""
        SELECT
            p.product_name,
            p.image,
            oi.quantity,
            oi.price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
    """, (order_id,))

    items = cur.fetchall()
    cur.close()

    # 🔹 Calculate total
    total = sum(item['price'] * item['quantity'] for item in items)

    return render_template(
        'order_details.html',
        order=order,
        items=items,
        address=address,
        total=total
    )

@app.route('/cancel_order/<int:order_id>')
def cancel_order(order_id):
    customer_id = session.get('customer_id')
    if not customer_id:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    try:
        # 🔹 Fetch order (security + status check)
        cur.execute("""
            SELECT status
            FROM orders
            WHERE order_id = %s AND customer_id = %s
        """, (order_id, customer_id))

        order = cur.fetchone()
        if not order:
            return "Order not found"

        # ❌ Only 'Placed' orders can be cancelled
        if order['status'] != 'Placed':
            return "Order cannot be cancelled"

        # 🔹 Fetch ordered items
        cur.execute("""
            SELECT product_id, quantity
            FROM order_items
            WHERE order_id = %s
        """, (order_id,))
        items = cur.fetchall()

        # 🔹 Restore stock
        for item in items:
            cur.execute("""
                UPDATE products
                SET stock = stock + %s
                WHERE product_id = %s
            """, (item['quantity'], item['product_id']))

        # 🔹 Update order status
        cur.execute("""
            UPDATE orders
            SET status = 'Cancelled'
            WHERE order_id = %s
        """, (order_id,))

        mysql.connection.commit()

        return redirect(url_for('my_orders'))

    except Exception as e:
        mysql.connection.rollback()
        return str(e)

    finally:
        cur.close()

@app.route('/my_orders')
def my_orders():
    customer_id = session.get('customer_id')
    if not customer_id:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # 🔹 Fetch all orders for the logged-in customer
    cur.execute("""
        SELECT *
        FROM orders
        WHERE customer_id = %s
        ORDER BY order_id DESC
    """, (customer_id,))
    orders = cur.fetchall()

    orders_with_items = []

    # 🔹 Fetch items for each order
    for order in orders:
        cur.execute("""
            SELECT
                oi.quantity,
                oi.price,
                p.product_name
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
        """, (order['order_id'],))

        items = cur.fetchall()

        orders_with_items.append({
            'order': order,
            'order_items': items
        })

    cur.close()

    return render_template(
        'my_orders.html',
        orders=orders_with_items
    )
@app.route("/invoice/<int:order_id>")
def download_invoice(order_id):

    cur = mysql.connection.cursor()

    # ---------- Fetch order ----------
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cur.fetchone()

    if not order:
        cur.close()
        return "Order not found"

    # If you're using DictCursor, order will be dictionary.
    # Otherwise it's tuple (tell me if you're unsure).

    # ---------- Load address JSON safely ----------
    try:
        address = json.loads(order['address']) if order['address'] else {}
    except (json.JSONDecodeError, TypeError, KeyError):
        address = {}

    # ---------- Fetch order items with product name ----------
    cur.execute("""
        SELECT 
            products.product_name AS product_name,
            order_items.quantity,
            order_items.price
        FROM order_items
        JOIN products ON order_items.product_id = products.product_id
        WHERE order_items.order_id = %s
    """, (order_id,))
    
    items = cur.fetchall()

    cur.close()

    # continue your PDF logic here...

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
    pdf.drawString(50, y, f"Order ID: {order['order_id']}")
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


@app.route('/update_order_status', methods=['POST'])
def update_order_status():

    order_id = request.form['order_id']
    status = request.form['status']

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Update order
    cur.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (status, order_id))

    conn.commit()

    # Get user email
    cur.execute("""
        SELECT users.email, orders.order_date
        FROM orders
        JOIN users ON orders.user_id = users.id
        WHERE orders.id = ?
    """, (order_id,))

    order = cur.fetchone()
    conn.close()

    print("STATUS:", status)

    # ✅ Send mail when delivered
    if order and status.lower() == "delivered":
        print("Sending email...")
        send_status_email(
            order["email"],
            order_id,
            order["order_date"],
            status
        )

    return redirect(url_for('admin_orders'))

@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM staff WHERE email = %s AND password = %s AND status='active'",
            (email, password)
        )
        staff = cur.fetchone()
        cur.close()

        if staff:
            session["staff_id"] = staff[0]      # id
            session["staff_logged_in"] = True
            return redirect("/staff/dashboard")
        else:
            return "Invalid staff credentials"

    return render_template("staff/login.html")

@app.route("/staff/register", methods=["GET", "POST"])
def staff_register():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]   # plain password

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO staff (name, email, phone, password)
            VALUES (%s, %s, %s, %s)
        """, (name, email, phone, password))

        mysql.connection.commit()
        cur.close()

        return redirect("/staff/login")

    return render_template("staff/register.html")


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
