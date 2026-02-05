import os
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, redirect, url_for
from flask import session,flash
import json

from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime

import mysql.connector

app = Flask(__name__)
app.secret_key = "cartsecret"#secret_mandatory for work session

ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="product"
    )

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM p_details")
    products = cursor.fetchall()
    return render_template('user_products.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        f_name = request.form.get('f_name')
        l_name = request.form.get('l_name')
        email = request.form.get('email')
        phno = request.form.get('phno')
        password = request.form.get('password')
        c_password = request.form.get('c_password')

              # ✅ Password match check
        if password != c_password:
            flash("⚠ Password and Confirm Password do not match!")
            return redirect('/register')

        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (f_name,l_name, email, phno, password) VALUES (%s,%s,%s,%s,%s)",
                (f_name, l_name, email, phno, hashed_pw)
            )
            conn.commit()
            print("Inserted rows:", cursor.rowcount)
            flash("✅ Registration successful! Please login.")
        except mysql.connector.IntegrityError:
            flash("⚠ Email already registered!")
        conn.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # after successful login
        session['logged_in'] = True

        # 🔐 ADMIN LOGIN CHECK (FIRST)
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin'] = True
            session['user_name'] = "Admin"
            flash("✅ Admin login successful")
            return redirect(url_for('admin'))   # 👉 admin page

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            # login success
            session['user_id'] = user['user_id']
            session['user_name'] = user['f_name']
            flash("✅ Login successful!")
         

            return redirect('/products')   # after login page
        else:
            flash("❌ Invalid Email or Password")
            return redirect('/login')

    return render_template('login.html')

#for setting logout time
@app.route('/logout')
def logout():
    user_id = session.get('user_id')

    if user_id:
        user_id = session.get('user_id')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE login_logs 
            SET logout_time = NOW() 
            WHERE user_id=%s AND logout_time IS NULL
            """,
            (user_id,)
        )
        conn.commit()
        conn.close()

    session.clear()
    flash("Logged out successfully")
    session.pop('logged_in',None)
    return redirect('/products')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
        if not session.get('admin'):
            flash("⚠ Please login as admin")
            return redirect(url_for('login'))
       
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM p_details")
        products = cursor.fetchall()
        conn.close()
       
        return render_template("p_details.html", products=products)

@app.route('/add', methods=['POST'])
def add():
    if request.method == 'POST':
        p_id = request.form.get('p_id')
        p_name = request.form.get('p_name')
        p_rate = request.form.get('p_rate')
        p_quantity = request.form.get('p_quantity')

        file = request.files.get('p_image')

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join('static/uploads', filename))
        else:
            filename = "default.png"   # keep a default image

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO p_details (p_id, p_name, p_rate, p_quantity, p_image) VALUES (%s,%s,%s,%s,%s)",
            (p_id, p_name, p_rate, p_quantity, filename)
        )
        conn.commit()

        return redirect(url_for('admin'))

    return render_template('p_details.html', products=[])


@app.route('/update', methods=['POST'])
def update():
    conn = get_db_connection()
    p_id = request.form['p_id']
    p_name = request.form['p_name']
    p_rate = request.form['p_rate']
    p_quantity = request.form['p_quantity']
    file = request.files['p_image']

    if file and file.filename != "":
        filename = secure_filename(file.filename)
        file.save(os.path.join('static/uploads', filename))
        
        cursor = conn.cursor()
        cursor.execute(
        "UPDATE p_details SET p_name=%s, p_rate=%s, p_quantity=%s,p_image=%s WHERE p_id=%s",
        (p_name, p_rate, p_quantity, filename, p_id)
        )
    else:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE p_details SET p_name=%s,p_rate=%s,p_quantity=%s WHERE p_id=%s",
            (p_name,p_rate,p_quantity,p_id)
        )
    conn.commit()
    return redirect('/admin')

@app.route('/delete/<p_id>', methods=['POST'])
def delete(p_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM p_details WHERE p_id=%s", (p_id,))
    conn.commit()
    return redirect(url_for('admin'))

#user_product.html route 
@app.route('/products')
def user_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM p_details")
    products = cursor.fetchall()
    print(products)
    return render_template("user_products.html", products=products)

#for counting crat itme and showed on dashboard
@app.route('/add_to_cart/<p_id>')
def add_to_cart(p_id):
    
    p_id = str(p_id) 

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    if p_id in cart:
        cart[p_id] += 1
    else:
        cart[p_id] = 1

    session['cart'] = cart
    session.modified = True   # 🔥 VERY IMPORTANT

    return redirect(url_for('user_products'))


@app.context_processor
def inject_cart_count():
    count = 0
    if 'cart' in session:
        count = sum(session['cart'].values())
    return dict(cart_count=count)



#cart page retrieves product_id from session,
# fetches p_details from DB,
# cal order_quantity and total price 
@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})

    if not cart:
        return render_template("cart.html", products=[])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    product_ids = list(cart.keys())

    placeholders=','.join(['%s']*len(product_ids))
    query = f"SELECT * FROM p_details WHERE p_id IN ({placeholders})"

    cursor.execute(query, product_ids)
    products = cursor.fetchall()

    for p in products:
        pid=str(p['p_id'])
        p['order_qty'] = cart.get(pid,0)
        p['total_price'] = p['order_qty'] * p['p_rate']

    return render_template("cart.html", products=products)

#Remove Item from cart
@app.route('/remove/<p_id>',methods=['POST'])
def remove_from_cart(p_id):
    print("🔥 REMOVE ROUTE HIT 🔥", p_id)

    cart = session.get('cart', {})
    p_id = str(p_id) 

    if p_id in cart:
        cart.pop(p_id)

    if len(cart)==0:
        session.pop('cart', None) 
    else:     
        session['cart'] = cart
    
    session.modified = True
    return redirect(url_for('view_cart'))


#inc or dec
@app.route('/update_cart', methods=['POST'])
def update_cart():
    p_id = str(request.form['p_id'])
    action = request.form['action']

    cart = session.get('cart', {})

    if p_id in cart:
        if action == "increase":
            cart[p_id] += 1
        elif action == "decrease":
            cart[p_id] -= 1
            if cart[p_id] < 1:
                cart.pop(p_id)  # remove if quantity 0

    session['cart'] = cart
    return redirect('/cart')

@app.route('/checkout')
def checkout():
    cart = session.get('cart', {})

    if not cart:
        flash("Your cart is empty 😢")
        return redirect('/products')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    products = []
    subtotal = 0

    for p_id, qty in cart.items():
        qty = int(qty)

        cursor.execute(
            "SELECT p_name, p_rate FROM p_details WHERE p_id = %s",
            (p_id,)
        )
        product = cursor.fetchone()

        if not product:
            continue

        price = int(product['p_rate'])
        total_price = price * qty
        subtotal += total_price

        products.append({
            'p_id': p_id,
            'p_name': product['p_name'],
            'order_qty': qty,
            'total_price': total_price
        })

    conn.close()

    gst = round(subtotal * 0.18, 2)
    grand_total = round(subtotal + gst, 2)

    return render_template(
        'checkout.html',
        products=products,
        subtotal=subtotal,
        gst=gst,
        grand_total=grand_total
    )


@app.route('/place_order', methods=['POST'])
def place_order():
    cart=session.get('cart',{})
    if not cart:
        flash("your cart is empty")
        return redirect('/products')
        #form data
    name = request.form.get('name')
    phone = request.form.get('phone')
    address = request.form.get('address')
    payment = request.form.get('payment', 'COD')  # default COD
    
        # Connect DB
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get product details from DB for cart items
    product_ids = tuple(cart.keys())
    query = f"SELECT * FROM p_details WHERE p_id IN ({','.join(['%s']*len(product_ids))})"
    cursor.execute(query, product_ids)
    products = cursor.fetchall()
    
    total = 0

    for p in products:
        qty = cart[str(p['p_id'])]
        total += int(p['p_rate']) * qty

      # 1️⃣ insert into orders table
    cursor.execute("""
        INSERT INTO orders (user_id, name, phone, address, payment_method, total_amount)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        session.get('user_id'),
        name,
        phone,
        address,
        payment,
        total
    ))

    order_id = cursor.lastrowid   # 🔑 IMPORTANT

        # 2️⃣ insert into order_items table
    for p in products:
        qty = cart[str(p['p_id'])]

        cursor.execute("""
            INSERT INTO order_items
            (order_id, product_id, product_name, price, quantity)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            order_id,
            p['p_id'],
            p['p_name'],
            p['p_rate'],
            qty
        ))

    conn.commit()
    conn.close()
    session.pop('cart', None)   # ✅ cart clear
    flash(f"✅ Order placed successfully! Payment: {payment}")

    return redirect(url_for('order_success'))  # ✅ success page


@app.route('/order-success')
def order_success():
    return render_template('order_success.html')

@app.route('/order_summary')
def order_summary():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('view_cart'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    product_ids = list(cart.keys())
    placeholders = ','.join(['%s'] * len(product_ids))

    query = f"SELECT * FROM p_details WHERE p_id IN ({placeholders})"
    cursor.execute(query, product_ids)
    products = cursor.fetchall()

    subtotal = 0
    for p in products:
        qty = cart.get(str(p['p_id']), 0)
        p['qty'] = qty
        p['total'] = qty * p['p_rate']
        subtotal += p['total']

    gst = round(subtotal * 0.18, 2)
    grand_total = subtotal + gst

    return render_template(
        "order_summary.html",
        products=products,
        subtotal=subtotal,
        gst=gst,
        grand_total=grand_total
    )


@app.route('/myorders')
def myorders():


    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # get orders of this user
    cursor.execute("""
        SELECT * FROM orders
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (user_id,))
    orders = cursor.fetchall()

    # for each order, get its items
    for order in orders:
        cursor.execute("""
            SELECT * FROM order_items
            WHERE order_id = %s
        """, (order['id'],))
        order['items'] = cursor.fetchall()

    conn.close()

    return render_template('myorders.html', orders=orders)



if __name__ == "__main__":
    app.run(debug=True)
