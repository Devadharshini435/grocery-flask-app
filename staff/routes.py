import MySQLdb
from flask import render_template, request, redirect, url_for,session
from . import staff
from extensions import mysql


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

    cur.execute("SELECT COUNT(*) AS total FROM orders")
    total_orders = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS pending FROM orders WHERE status='Pending'")
    pending_orders = cur.fetchone()["pending"]

    cur.execute("SELECT COUNT(*) AS packed FROM orders WHERE status='Packed'")
    packed_orders = cur.fetchone()["packed"]

    cur.execute("SELECT COUNT(*) AS total FROM products")
    total_products = cur.fetchone()["total"]

    cur.execute("SELECT * FROM orders ORDER BY order_date DESC LIMIT 5")
    recent_orders = cur.fetchall()

    cur.close()

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        pending_orders=pending_orders,
        packed_orders=packed_orders,
        total_products=total_products,
        recent_orders=recent_orders
    )

@staff.route("/staff/orders")
def orders():

    cur = mysql.connection.cursor()

    # Customer Wise Orders (with address)
    cur.execute("""
        SELECT 
            o.order_id,
            u.customer_id,
            u.customer_name,
            u.address,
            o.total_amount,
            o.status
        FROM orders o
        JOIN customer u ON o.customer_id = u.customer_id
        ORDER BY o.order_date DESC
    """)

    orders = cur.fetchall()

    # Product Wise Orders
    cur.execute("""
        SELECT 
            o.customer_id,
            p.product_name,
            oi.quantity,
            oi.price,
            o.status
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
    """)

    product_orders = cur.fetchall()

    cur.close()

    return render_template(
        "staff/orders.html",
        orders=orders,
        product_orders=product_orders
    )

@staff.route("/staff/update_order_status", methods=["POST"])
def update_order_status():

    order_id = request.form["order_id"]
    new_status = request.form["status"]

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE orders
        SET status = %s
        WHERE order_id = %s
    """, (new_status, order_id))

    mysql.connection.commit()
    cur.close()

    return redirect(url_for("staff.orders"))

@staff.route("/staff/products")
def products():

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM products")

    products = cur.fetchall()

    cur.close()

    return render_template("staff/products.html", products=products)

@staff.route("/staff/add_product", methods=["GET","POST"])
def add_product():

    if request.method == "POST":

        name = request.form["product_name"]
        price = request.form["price"]
        stock = request.form["stock"]

        image = request.files["image"]
        filename = secure_filename(image.filename)

        image.save("static/uploads/" + filename)

        cur = mysql.connection.cursor()

        cur.execute("""
        INSERT INTO products (product_name, price, stock, image)
        VALUES (%s,%s,%s,%s)
        """,(name,price,stock,filename))

        mysql.connection.commit()
        cur.close()

        return redirect(url_for("staff.products"))

    return render_template("staff/add_product.html")