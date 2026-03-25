import os
from werkzeug.utils import secure_filename
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for
from flask import session,flash
import json

from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime
from functools import wraps
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
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

# 🔐 LOGIN REQUIRED DECORATOR
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def make_session_non_permanent():
    session.permanent = False

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


        # 🔐 ADMIN LOGIN CHECK (FIRST)
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin'] = True
            
            # after successful login
            session['logged_in'] = True
            
            session['user_name'] = "Admin"
            flash("✅ Admin login successful")
            return redirect(url_for('admin'))   # 👉 admin page

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            
            session.clear()   # 🔥 MUST be FIRST
            # login success
            session['user_id'] = user['user_id']
            session['user_name'] = user['f_name']
            session['logged_in'] = True


            # 🔥 LOAD CART FROM DB
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                    "SELECT product_id, quantity FROM cart WHERE user_id=%s",
                    (user['user_id'],)
            )
            db_cart = cursor.fetchall()
            conn.close()

             # 🔐 INSERT LOGIN LOG
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
            """
            INSERT INTO login_logs (user_id, email, ip_address)
            VALUES (%s, %s, %s)
            """,
            (
                user['user_id'],
                user['email'],
                request.remote_addr
            )
            )

            conn.commit()
            conn.close()
        
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

    session.pop('cart', None)
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.clear()

    flash("Logged out successfully")
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
    
    print(request.files)
    print(request.form)

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
    query = request.args.get('query', '').strip()
    if query:
        cursor.execute("SELECT * FROM p_details WHERE p_name LIKE %s", ("%" + query + "%",))
    else:
        cursor.execute("SELECT * FROM p_details")

    return render_template("user_products.html", products=products)

@app.route('/add_to_cart/<p_id>')
@login_required
def add_to_cart(p_id):

    user_id = session['user_id']

    # DB
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO cart (user_id, product_id, quantity)
        VALUES (%s,%s,1)
        ON DUPLICATE KEY UPDATE quantity = quantity + 1
        """,
        (user_id, p_id)
    )
    conn.commit()
    conn.close()

    flash("Item added to cart 🛒")
    return redirect('/products')


@app.context_processor
def inject_cart_count():
    count = 0

    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM cart WHERE user_id = %s",
            (session['user_id'],)
        )
        count = cursor.fetchone()[0]
        conn.close()

    return dict(cart_count=count)


# ------------------- VIEW CART -------------------
@app.route('/cart')
@login_required
def view_cart():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.cart_id, p.p_id, p.p_name, p.p_rate, c.quantity,
               (p.p_rate * c.quantity) AS total_price, p.p_image
        FROM cart c
        JOIN p_details p ON c.product_id = p.p_id
        WHERE c.user_id = %s
    """, (user_id,))
    products = cursor.fetchall()
    conn.close()
    return render_template("cart.html", products=products)

@app.route('/update_cart/<cart_id>/<action>')
@login_required
def update_cart(cart_id, action):
    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch current quantity
    cursor.execute(
        "SELECT quantity FROM cart WHERE user_id=%s AND product_id=%s",
        (user_id, cart_id)  # use cart_id from URL
    )
    item = cursor.fetchone()

    if not item:
        conn.close()
        return redirect('/cart')

    qty = item['quantity']

    if action == 'increase':
        qty += 1
    elif action == 'decrease':
        qty -= 1

    if qty > 0:
        cursor.execute(
            "UPDATE cart SET quantity=%s WHERE user_id=%s AND product_id=%s",
            (qty, user_id, cart_id)
        )
    else:
        cursor.execute(
            "DELETE FROM cart WHERE user_id=%s AND product_id=%s",
            (user_id, cart_id)
        )

    conn.commit()
    conn.close()
    return redirect('/cart')

# ------------------- REMOVE FROM CART -------------------
@app.route('/remove/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE cart_id=%s AND user_id=%s", (cart_id, user_id))
    conn.commit()
    conn.close()
    flash("🗑️ Item removed from cart")
    return redirect(url_for('view_cart'))

# ------------------- PLACE ORDER -------------------
@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Fetch cart items from DB
    cursor.execute("""
        SELECT c.product_id, c.quantity, p.p_name, p.p_rate
        FROM cart c
        JOIN p_details p ON c.product_id = p.p_id
        WHERE c.user_id=%s
    """, (user_id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        flash("Your cart is empty 😢")
        conn.close()
        return redirect('/products')

    # 2️⃣ Calculate totals
    subtotal = sum(item['p_rate'] * item['quantity'] for item in cart_items)
    gst = round(subtotal * 0.18, 2)
    grand_total = subtotal + gst

    # 3️⃣ Insert into orders
    cursor.execute("""
        INSERT INTO orders (user_id, total_amount, gst, grand_total)
        VALUES (%s,%s,%s,%s)
    """, (user_id, subtotal, gst, grand_total))
    order_id = cursor.lastrowid

    # 4️⃣ Insert into order_items (include product_name)
    for item in cart_items:
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
            VALUES (%s, %s, %s, %s, %s)
        """, (order_id, item['product_id'], item['p_name'], item['quantity'], item['p_rate']))

    # 5️⃣ Clear cart
    cursor.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))
    conn.commit()
    conn.close()

    flash("✅ Order placed successfully!")
    return redirect(url_for('order_summary', order_id=order_id))




@app.route('/checkout')
@login_required
def checkout():

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.p_id, p.p_name, p.p_rate, c.quantity,
               (p.p_rate * c.quantity) AS total_price
        FROM cart c
        JOIN p_details p ON c.product_id = p.p_id
        WHERE c.user_id = %s
    """, (user_id,))

    products = cursor.fetchall()

    if not products:
        flash("Your cart is empty 😢")
        return redirect('/products')

    subtotal = sum(p['total_price'] for p in products)
    gst = round(subtotal * 0.18, 2)
    grand_total = round(subtotal + gst, 2)

    conn.close()

    return render_template(
        'checkout.html',
        products=products,
        subtotal=subtotal,
        gst=gst,
        grand_total=grand_total
    )

@app.route('/order_success')
def order_success():
    return render_template('order_success.html')

# ------------------- ORDER SUMMARY -------------------
@app.route('/order_summary/<int:order_id>')
@login_required
def order_summary(order_id):
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get order
    cursor.execute("SELECT * FROM orders WHERE id=%s AND user_id=%s", (order_id, user_id))
    order = cursor.fetchone()
    if not order:
        flash("Order not found")
        conn.close()
        return redirect('/products')

    # Get order items (with image)
    cursor.execute("""
        SELECT oi.product_name, oi.price, oi.quantity, p.p_image
        FROM order_items oi
        JOIN p_details p ON oi.product_id = p.p_id
        WHERE oi.order_id=%s
    """, (order_id,))
    items = cursor.fetchall()
    conn.close()

    subtotal = sum(item['price'] * item['quantity'] for item in items)
    gst = round(subtotal * 0.18, 2)
    grand_total = subtotal + gst

    return render_template("order_summary.html",
                           order=order, items=items,
                           subtotal=subtotal, gst=gst, grand_total=grand_total)

@app.route('/myorders')
def myorders():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # get all orders
    cursor.execute("""
        SELECT *
        FROM orders
        WHERE user_id = %s
        ORDER BY id DESC
    """, (user_id,))
    orders = cursor.fetchall()

    valid_orders = []

    for order in orders:
        cursor.execute("""
        SELECT
        oi.order_id,
        oi.product_id AS product_code,
        p_id AS product_int_id,
        p.p_name,
        p.p_rate,
        p.p_image,
        oi.quantity,
        r.ratings AS rating,   -- DB column 'ratings' use panni alias 'rating'
        r.comments AS comment  -- DB column 'comments' use panni alias 'comment'
    FROM order_items oi
    JOIN p_details p ON oi.product_id = p.p_id
    LEFT JOIN reviews r ON r.product_id = p.p_id AND r.user_id = %s
    WHERE oi.order_id = %s
""", (user_id, order['id']))


        items = cursor.fetchall()

        if items:
            order['items'] = items
            valid_orders.append(order)

    conn.close()

    return render_template("myorders.html", orders=valid_orders)

@app.route('/order/<int:order_id>')
def order_details(order_id):

    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Order details
    cursor.execute("""
        SELECT *
        FROM orders
        WHERE id = %s
    """, (order_id,))
    order = cursor.fetchone()

    if not order:
        conn.close()
        return "Order not found", 404

    # Order items
    cursor.execute("""
        SELECT 
            oi.product_name,
            oi.price,
            oi.quantity,
            p.p_image
        FROM order_items oi
        JOIN p_details p ON oi.product_id = p.p_id
        WHERE oi.order_id = %s
    """, (order_id,))

    items = cursor.fetchall()
    conn.close()

    return render_template(
        "order_details.html",
        order=order,
        items=items
    )

@app.route('/rate_product/<int:order_id>/<product_id>')
@login_required
def rate_product(order_id, product_id):
    print("Route hit!")
    print("order_id:", order_id)
    print("product_id:", product_id)
    print("user_id:", session.get('user_id'))
    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check: user ordered this product or not
    cursor.execute("""
    SELECT 
    p.p_id,
    p.p_name AS name,
    p.p_image AS image
    FROM order_items oi
    JOIN p_details p ON oi.product_id = p.p_id
    JOIN orders o ON oi.order_id = o.id
    WHERE o.id=%s AND o.user_id=%s AND p.p_id=%s
    """, (order_id, user_id, product_id))

    product = cursor.fetchone()

    if not product:
        flash("Invalid access ❌")
        return redirect(url_for('myorders'))

    # Already reviewed?
    cursor.execute("""
        SELECT * FROM reviews
        WHERE user_id=%s AND product_id=%s
    """, (user_id, product_id))

    existing_review = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'rate_product.html',
        product=product,
        order_id=order_id,
        review=existing_review
    )

#submit review route
@app.route('/submit_review/<int:order_id>/<product_id>', methods=['POST'])
@login_required
def submit_review(order_id, product_id):
    user_id = session['user_id']
    rating = request.form['rating']
    comment = request.form['comment']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert or Update
    cursor.execute("""
        SELECT id FROM reviews
        WHERE user_id=%s AND product_id=%s
    """, (user_id, product_id))

    exists = cursor.fetchone()

    if exists:
        cursor.execute("""
            UPDATE reviews
            SET ratings=%s, comments=%s
            WHERE user_id=%s AND product_id=%s
        """, (rating, comment, user_id, product_id))
    else:
        cursor.execute("""
            INSERT INTO reviews (user_id, product_id, ratings, comments)
            VALUES (%s, %s, %s, %s)
        """, (user_id, product_id, rating, comment))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Review saved successfully ✅")
    return redirect(url_for('myorders'))


if __name__ == "__main__":
    app.run(debug=True,port=50001)
