from flask import render_template, request, redirect, url_for, current_app
from . import staff

@staff.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    return render_template("staff_login.html")


@staff.route("/staff/register", methods=["GET", "POST"])
def staff_register():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        designation = request.form.get("designation", "")

        # Access mysql safely
        mysql = current_app.extensions['mysql']

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO staff 
            (staff_name, email, phone, password, designation) 
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, phone, password, designation))

        mysql.connection.commit()
        cur.close()

        return redirect(url_for("staff.staff_login"))

    return render_template("staff_register.html")