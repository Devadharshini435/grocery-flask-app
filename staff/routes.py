import MySQLdb
from flask import render_template, request, redirect, url_for,session
from . import staff
from extensions import mysql
from email.message import EmailMessage
import smtplib

EMAIL_ADDRESS = "devadharshiniramachandran435@gmail.com"
EMAIL_PASSWORD = "vadk tqhr arsr ltfi"



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




@staff.route("/staff/login", methods=["GET", "POST"])
def staff_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()

        cur.execute("""
        SELECT * FROM staff
        WHERE email = %s
        """, (email,))

        staff_user = cur.fetchone()
        cur.close()

        # check login
        if staff_user and staff_user["password"] == password:

            session["staff_id"] = staff_user["staff_id"]
            session["staff_name"] = staff_user["staff_name"]

            return redirect(url_for("staff.dashboard"))

        else:
            return "Invalid email or password"

    return render_template("staff_login.html")


@staff.route("/staff/register", methods=["GET","POST"])
def staff_register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        designation = request.form.get("designation","")

        cur = mysql.connection.cursor()

        cur.execute("""
        INSERT INTO staff (staff_name,email,phone,password,designation)
        VALUES (%s,%s,%s,%s,%s)
        """,(name,email,phone,password,designation))

        mysql.connection.commit()
        cur.close()

        return redirect(url_for("staff.staff_login"))

    return render_template("staff_register.html")

@staff.route("/staff/dashboard")
def dashboard():

    cur = mysql.connection.cursor()

    # total orders
    cur.execute("SELECT COUNT(*) AS total FROM orders")
    total_orders = cur.fetchone()["total"]

    # placed orders
    cur.execute("SELECT COUNT(*) AS placed FROM orders WHERE status='Placed'")
    placed_orders = cur.fetchone()["placed"]

    # packed orders
    cur.execute("SELECT COUNT(*) AS packed FROM orders WHERE status='Packed'")
    packed_orders = cur.fetchone()["packed"]

    # total products
    cur.execute("SELECT COUNT(*) AS total FROM products")
    total_products = cur.fetchone()["total"]

    cur.execute("""
    SELECT 
        o.id,
        o.customer_id,
        o.total_amount,
        o.status,
        o.order_date,
        c.customer_name
    FROM orders o
    JOIN customer c
    ON o.customer_id = c.customer_id
    ORDER BY o.order_date DESC
    LIMIT 5
""")
    recent_orders = cur.fetchall()

    cur.close()

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        placed_orders=placed_orders,
        packed_orders=packed_orders,
        total_products=total_products,
        recent_orders=recent_orders
    )

@staff.route("/staff/products")
def products():

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")

    products = cur.fetchall()

    return render_template("staff_products.html", products=products)

@staff.route("/staff/orders")
def orders():

    cur = mysql.connection.cursor()

    # ✅ Customer Wise Orders
    cur.execute("""
        SELECT 
            o.id,
            o.customer_id,
            c.customer_name,
            c.address,
            o.total_amount,
            o.status,
            o.order_date
        FROM orders o
        JOIN customer c
        ON o.customer_id = c.customer_id
        ORDER BY o.order_date DESC
    """)

    orders = cur.fetchall()


    # ✅ Product Wise Orders (merged table)
    cur.execute("""
        SELECT 
            o.id,
            o.customer_id,
            p.product_name,
            o.quantity,
            o.price,
            o.status
        FROM orders o
        JOIN products p
        ON o.product_id = p.product_id
    """)

    product_orders = cur.fetchall()

    cur.close()

    return render_template(
        "staff/orders.html",
        orders=orders,
        product_orders=product_orders
    )

@staff.route("/staff/edit_product/<int:id>", methods=["GET","POST"])
def edit_product(id):

    cur = mysql.connection.cursor()

    if request.method == "POST":

        category = request.form["category"]
        product_name = request.form["product_name"]
        dish_name = request.form["dish_name"]
        description = request.form["description"]
        price = request.form["price"]
        stock = request.form["stock"]

        image = request.files["image"]

        if image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join("static/uploads", filename))

            cur.execute("""
            UPDATE products
            SET category=%s, product_name=%s, dish_name=%s,
            description=%s, price=%s, stock=%s, image=%s
            WHERE product_id=%s
            """,(category,product_name,dish_name,description,price,stock,filename,id))

        else:

            cur.execute("""
            UPDATE products
            SET category=%s, product_name=%s, dish_name=%s,
            description=%s, price=%s, stock=%s
            WHERE product_id=%s
            """,(category,product_name,dish_name,description,price,stock,id))

        mysql.connection.commit()

        return redirect(url_for("staff.products"))

    cur.execute("SELECT * FROM products WHERE product_id=%s",(id,))
    product = cur.fetchone()

    return render_template("staff/staff_edit_product.html",product=product)
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "static/uploads"

@staff.route("/staff/add_product", methods=["GET","POST"])
def add_product():

    if request.method == "POST":

        category = request.form["category"]
        product_name = request.form["product_name"]
        dish_name = request.form["dish_name"]
        description = request.form["description"]
        price = request.form["price"]
        stock = request.form["stock"]

        image = request.files["image"]

        filename = secure_filename(image.filename)
        image.save(os.path.join(UPLOAD_FOLDER, filename))

        cur = mysql.connection.cursor()

        cur.execute("""
        INSERT INTO products
        (category, product_name, dish_name, description, price, stock, image)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,(category, product_name, dish_name, description, price, stock, filename))

        mysql.connection.commit()
        cur.close()

        return redirect(url_for("staff.products"))

    return render_template("staff/add_product.html")

import MySQLdb.cursors

@staff.route("/staff/update_order_status", methods=["POST"])
def update_order_status():

    order_id = request.form["order_id"]
    new_status = request.form["status"]

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ✅ get order + email + date
    cur.execute("""
    SELECT 
        o.id,
        o.status,
        o.customer_id,
        o.total_amount,
        o.order_date,
        c.customer_email
    FROM orders o
    JOIN customer c
        ON o.customer_id = c.customer_id
    WHERE o.id = %s
    """, (order_id,))

    order = cur.fetchone()

    if not order:
        cur.close()
        return redirect(url_for("staff.orders"))

    old_status = order["status"]
    customer_id = order["customer_id"]
    total = float(order["total_amount"] or 0)

    # ✅ update status
    cur.execute("""
        UPDATE orders
        SET status = %s
        WHERE id = %s
    """, (new_status, order_id))


    # ✅ SEND EMAIL FOR EVERY STATUS
    send_status_email(
        order["customer_email"],
        order_id,
        order["order_date"],
        new_status
    )


    # ✅ ADD REWARD ONLY WHEN DELIVERED
    if (
        new_status.strip().lower() == "delivered"
        and old_status.strip().lower() != "delivered"
    ):

        coins = int(total // 100)

        # check already rewarded
        cur.execute("""
            SELECT id
            FROM customer_rewards
            WHERE order_id = %s
        """, (order_id,))

        exists = cur.fetchone()
    if not exists and coins > 0:

    # get last balance
        cur.execute("""
        SELECT balance
        FROM customer_rewards
        WHERE customer_id = %s
        ORDER BY id DESC
        LIMIT 1
    """, (customer_id,))

        row = cur.fetchone()

        current_balance = row["balance"] if row else 0

        new_balance = current_balance + coins

        cur.execute("""
        INSERT INTO customer_rewards
        (customer_id, points_added, balance, order_id)
        VALUES (%s,%s,%s,%s)
    """, (
        customer_id,
        coins,
        new_balance,
        order_id
    ))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for("staff.orders"))

@staff.route("/staff/delete_product/<int:id>")
def delete_product(id):

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM products WHERE product_id=%s",(id,))

    mysql.connection.commit()

    return redirect(url_for("staff.products"))

@staff.route("/suppliers")
def suppliers():

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT suppliers.supplier_id, suppliers.supplier_name,
               products.product_name, suppliers.phone,
               suppliers.email, suppliers.address
        FROM suppliers
        LEFT JOIN products ON suppliers.product_id = products.product_id
    """)

    suppliers = cursor.fetchall()

    return render_template("staff/suppliers.html", suppliers=suppliers)

@staff.route("/add_supplier", methods=["GET","POST"])
def add_supplier():

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT product_id, product_name FROM products")
    products = cursor.fetchall()

    if request.method == "POST":

        name = request.form["supplier_name"]
        product_id = request.form["product_id"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        cursor.execute("""
            INSERT INTO suppliers
            (supplier_name, product_id, phone, email, address)
            VALUES (%s,%s,%s,%s,%s)
        """,(name, product_id, phone, email, address))

        mysql.connection.commit()

        return redirect(url_for("staff.suppliers"))

    return render_template("add_supplier.html", products=products)

@staff.route("/customers")
def customers():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT 
            c.customer_id,
            c.customer_name,
            c.customer_email,

            COALESCE(SUM(r.balance),0) AS reward_points,

            COUNT(o.id) AS total_orders

        FROM customer c

        LEFT JOIN orders o
            ON c.customer_id = o.customer_id

        LEFT JOIN customer_rewards r
            ON c.customer_id = r.customer_id

        GROUP BY c.customer_id
    """)

    customer = cursor.fetchall()

    cursor.close()

    return render_template(
        "staff_customers.html",
        customer=customer
    )
@staff.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("staff.staff_login"))