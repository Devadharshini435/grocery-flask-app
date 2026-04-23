import MySQLdb
from flask import render_template, request, redirect, url_for,session
from . import staff
from extensions import mysql
from email.message import EmailMessage
import smtplib
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

EMAIL_ADDRESS = "dish2cart.grocery@gmail.com"
EMAIL_PASSWORD = "qsjd wjsn klgz qois"



def send_status_email(to_email, order_id, order_date, status):

    status_lower = status.lower().strip()

    # ✅ dynamic subject + color + message
    if status_lower == "pending":
        subject = "🕒 Order Pending"
        title = "Order Pending"
        color = "#ffc107"
        message = "Your order is pending."

    elif status_lower == "packed":
        subject = "📦 Order Packed"
        title = "Order Packed"
        color = "#17a2b8"
        message = "Your order has been packed."

    elif status_lower == "shipped":
        subject = "🚚 Order Shipped"
        title = "Order Shipped"
        color = "#007bff"
        message = "Your order has been shipped."

    elif status_lower == "delivered":
        subject = "🎉 Order Delivered"
        title = "Order Delivered Successfully"
        color = "#28a745"
        message = "Your order has been delivered 🎉"

    elif status_lower == "cancelled":
        subject = "❌ Order Cancelled"
        title = "Order Cancelled"
        color = "#dc3545"
        message = "Your order has been cancelled."

    else:
        subject = "Order Update"
        title = "Order Status Updated"
        color = "#6c757d"
        message = f"Order status changed to {status}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    msg.set_content(message)

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

            <div style="background:{color};color:white;padding:20px;text-align:center;">
                <h2>Dish2Cart</h2>
                <h3>{title}</h3>
            </div>

            <div style="padding:25px;color:#333;">

                <p>Hello Customer,</p>

                <p>{message}</p>

                <table style="width:100%;margin-top:15px;border-collapse:collapse;">
                    <tr>
                        <td><b>Order ID</b></td>
                        <td>#{order_id}</td>
                    </tr>
                    <tr style="background:#f2f2f2;">
                        <td><b>Order Date</b></td>
                        <td>{order_date}</td>
                    </tr>
                    <tr>
                        <td><b>Status</b></td>
                        <td style="color:{color};"><b>{status}</b></td>
                    </tr>
                </table>

                <div style="text-align:center;margin-top:25px;">
                    <a href="http://127.0.0.1:5000"
                       style="
                       background:{color};
                       color:white;
                       padding:12px 20px;
                       text-decoration:none;
                       border-radius:5px;
                       font-weight:bold;">
                       View Website
                    </a>
                </div>

            </div>

            <div style="background:#f1f1f1;padding:15px;text-align:center;font-size:12px;">
                © 2026 Dish2Cart
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

    # pending orders
    cur.execute("SELECT COUNT(*) AS pending FROM orders WHERE status='Pending'")
    pending_orders = cur.fetchone()["pending"]

    # packed orders
    cur.execute("SELECT COUNT(*) AS packed FROM orders WHERE status='Packed'")
    packed_orders = cur.fetchone()["packed"]

    # total products
    cur.execute("SELECT COUNT(*) AS total FROM products")
    total_products = cur.fetchone()["total"]

    # recent orders
    cur.execute("""
    SELECT 
        o.id,
        o.customer_id,
        o.total_amount,
        o.status,
        o.order_date,
        c.customer_name
    FROM orders o
    JOIN customer c ON o.customer_id = c.customer_id
    ORDER BY o.order_date DESC
    LIMIT 5
    """)

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

@staff.route("/staff/products")
def products():

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")

    products = cur.fetchall()

    return render_template("staff_products.html", products=products)

from flask import request, render_template, redirect, url_for, send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io

# =========================
# ORDERS PAGE
# =========================
@staff.route('/staff/orders')
def orders():

    status_filter = request.args.get('status')

    cur = mysql.connection.cursor()

    query = """
    SELECT 
        o.id,
        o.total_amount,
        o.status,
        o.order_date,
        c.customer_name,
        c.address,
        p.product_name,
        oi.quantity,
        oi.price
    FROM orders o
    JOIN customer c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    """

    if status_filter and status_filter != "All":
        query += " WHERE o.status = %s"
        cur.execute(query + " ORDER BY o.id DESC", (status_filter,))
    else:
        cur.execute(query + " ORDER BY o.id DESC")

    data = cur.fetchall()

    # ✅ Group orders
    orders_dict = {}

    for row in data:
        order_id = row['id']

        if order_id not in orders_dict:
            orders_dict[order_id] = {
                "id": row['id'],
                "customer_name": row['customer_name'],
                "address": row['address'],
                "total_amount": row['total_amount'],
                "status": row['status'],
                "order_items": []
            }

        orders_dict[order_id]["order_items"].append({
            "name": row['product_name'],
            "qty": row['quantity'],
            "price": row['price']
        })

    orders = list(orders_dict.values())

    return render_template(
        'staff/orders.html',
        orders=orders,
        selected_status=status_filter
    )


# =========================
# UPDATE STATUS
# =========================
@staff.route('/staff/update_order_status', methods=['POST'])
def update_order_status():
    order_id = request.form['order_id']
    new_status = request.form['status']

    cur = mysql.connection.cursor()

    cur.execute("SELECT status FROM orders WHERE id=%s", (order_id,))
    current_status = cur.fetchone()['status']

    # ❌ prevent editing completed
    if current_status in ['Delivered', 'Cancelled']:
        return redirect(url_for('staff.orders'))

    cur.execute("UPDATE orders SET status=%s WHERE id=%s", (new_status, order_id))
    mysql.connection.commit()

    return redirect(url_for('staff.orders'))


# =========================
# PDF REPORT
# =========================
@staff.route('/staff/orders/report')
def orders_report():

    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    import io

    # ✅ Register Unicode font (fix ₹)
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

    status_filter = request.args.get('status')

    cur = mysql.connection.cursor()

    query = """
    SELECT 
        o.id,
        o.total_amount,
        o.status,
        o.order_date,
        c.customer_name,
        c.address,
        p.product_name,
        oi.quantity,
        oi.price
    FROM orders o
    JOIN customer c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    """

    if status_filter and status_filter != "All":
        query += " WHERE o.status = %s"
        cur.execute(query, (status_filter,))
    else:
        cur.execute(query)

    data = cur.fetchall()

    # ✅ Group orders (same logic)
    orders_dict = {}

    for row in data:
        order_id = row['id']

        if order_id not in orders_dict:
            orders_dict[order_id] = {
                "customer": row['customer_name'],
                "address": row['address'],
                "total": row['total_amount'],
                "status": row['status'],
                "date": row['order_date'],
                "items": []
            }

        orders_dict[order_id]["items"].append(
            f"{row['product_name']} (x{row['quantity']})"
        )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(Paragraph("Orders Report", styles['Title']))
    elements.append(Spacer(1, 10))

    if status_filter:
        elements.append(Paragraph(f"Filter: {status_filter}", styles['Normal']))
        elements.append(Spacer(1, 10))

    # Table
    table_data = [["ID", "Customer", "Address", "Items", "Total", "Status", "Date"]]

    for order_id, order in orders_dict.items():
        items_text = ", ".join(order["items"])

        table_data.append([
            str(order_id),
            order["customer"],
            order["address"],
            items_text,
            f"₹{order['total']}",   # ✅ rupee fixed
            order["status"],
            str(order["date"])
        ])

    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'STSong-Light'),  # ✅ apply font
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))

    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name="orders_report.pdf",
                     mimetype='application/pdf')

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
@staff.route("/staff/logout")
def staff_logout():
    session.pop("staff_id", None)
    session.pop("staff_name", None)

    return redirect(url_for("staff.staff_login"))