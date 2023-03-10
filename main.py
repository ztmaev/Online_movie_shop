import sqlite3
import datetime
from flask import Flask, g, request, session, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('users.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

# Sample users
with app.app_context():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, is_admin INTEGER)')
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    result = cursor.fetchone()
    if result is None:
        password = generate_password_hash('password')
        cursor.execute('INSERT INTO users VALUES (?, ?, ?)', ('admin', password, 1))
        db.commit()


# Add a custom error handler for 404 (page not found) errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
def index():
    if 'username' in session:
        if session['admin']:
            return redirect(url_for('admin_dashboard'))
        else:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()

            # Get all items from the stock table
            cursor.execute('SELECT * FROM stock')
            items = cursor.fetchall()

            # Check if user has already bought the movie
            cursor.execute('SELECT item_id FROM history WHERE user_id = ?', (session['username'],))
            purchased_items = [r[0] for r in cursor.fetchall()]

            # Add purchased items to session
            session['purchased_items'] = purchased_items

            conn.close()
            print(purchased_items)
            return render_template('index.html', items=items, purchased_items=purchased_items)


    else:
        return redirect(url_for('login'))

@app.route('/owned')
def owned():
    if 'username' in session:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM history WHERE user_id = ?', (session['username'],))
        items = cursor.fetchall()
        #remove duplicates
        items = list(set(items))
        conn.close()
        return render_template('owned.html', items=items)
    else:
        return redirect(url_for('login'))

@app.route('/search/')
def search():
    search_term = request.args.get('search_term')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stock WHERE moviename LIKE ?', ('%{}%'.format(search_term),))
    movies = cursor.fetchall()
    conn.close()
    return render_template('search.html', movies=movies)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password1 = request.form['password1']
        password2 = request.form['password2']
        email = request.form['email']

        errors = []

        # Check if username already exists
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
        if cursor.fetchone() is not None:
            errors.append('Username already exists')

        # Check if username has at least 3 characters
        if len(username) < 3:
            errors.append('Username must have at least 3 characters')

        # Check if passwords match
        if password1 != password2:
            errors.append('Passwords do not match')

        # If there are errors, render the signup page with the errors
        if errors:
            return render_template('signup.html', errors=errors)

        # If there are no errors, hash the password and insert the new user into the database
        hashed_password = generate_password_hash(password1)
        is_admin = 0
        cursor.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (username, hashed_password, email, is_admin))
        conn.commit()
        conn.close()

        session['username'] = username
        session['admin'] = False
        return redirect(url_for('index'))
    else:
        return render_template('signup.html')

@app.route('/changepassword', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password1 = request.form['password1']
        password2 = request.form['password2']

        conn = get_db()
        cursor = conn.cursor()

        # Check if username and email match a user in the database
        cursor.execute('SELECT username FROM users WHERE username = ? AND email = ?', (username, email))
        result = cursor.fetchone()

        if result is None:
            flash('Invalid username or email')
            return redirect(url_for('change_password'))

        # Check if passwords match
        if password1 != password2:
            flash('Passwords do not match')
            return redirect(url_for('change_password'))

        # Hash the new password and update the user's password in the database
        hashed_password = generate_password_hash(password1)
        cursor.execute('UPDATE users SET password = ? WHERE username = ?', (hashed_password, username))
        conn.commit()
        conn.close()

        flash('Password updated successfully')
        return redirect(url_for('login'))
    else:
        return render_template('change_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        if result is not None and check_password_hash(result['password'], password):
            session['username'] = username
            session['admin'] = result['is_admin']
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password'
            return render_template('login.html', error=error)
    else:
        return render_template('login.html')



@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.pop('username', None)
        session.pop('admin', None)
        return redirect(url_for('login'))
    else:
        return redirect(url_for('index'))


@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' in session and session['admin']:
        conn = get_db()
        cursor = conn.cursor()

        if request.method == 'POST':
            # Handle edit/delete user request
            if 'edit-user' in request.form:
                # Get the username and new admin status from the form
                username = request.form['username']
                is_admin = True if request.form.get('is_admin') else False

                # Update the user's admin status in the database
                cursor.execute('UPDATE users SET is_admin = ? WHERE username = ?', (is_admin, username))
                conn.commit()
                flash('User information updated successfully.')

                # Update the session variable for the user's role
                session['admin'] = is_admin if username == session['username'] else session['admin']

            elif 'delete-user' in request.form:
                # Get the username to be deleted from the form
                username = request.form['username']

                # Delete the user from the database
                cursor.execute('DELETE FROM users WHERE username = ?', (username,))
                conn.commit()
                flash('User deleted successfully.')

            elif 'new-item' in request.form:
                # Get the new item details from the form
                moviename = request.form['moviename']
                price = request.form['price']
                description = request.form['description']

                # Insert the new item into the stock table
                cursor.execute('INSERT INTO stock (moviename, price, description) VALUES (?, ?, ?)', (moviename, price, description))
                conn.commit()
                flash('New item added successfully.')

        # Get the list of users from the database
        cursor.execute('SELECT username, is_admin FROM users')
        users = cursor.fetchall()

        # Get all items from the stock table
        cursor.execute('SELECT * FROM stock')
        items = cursor.fetchall()

        conn.close()

        return render_template('admin_dashboard.html', users=users, items=items)
    else:
        return redirect(url_for('login'))

@app.route('/admin/new_item', methods=['GET', 'POST'])
def new_item():
    if 'username' in session and session['admin']:
        conn = get_db()
        cursor = conn.cursor()

        if request.method == 'POST':
            # Get the new item details from the form
            moviename = request.form['moviename']
            description = request.form['description']
            price = request.form['price']
            trailer_link = request.form['trailer']
            poster = request.form['image']
            cast_names = request.form['cast']

            # Insert the new item into the stock table
            cursor.execute('INSERT INTO stock (moviename, description, price, trailer_link, poster, cast_names) VALUES (?, ?, ?, ?, ?, ?)',
                           (moviename, description, price, trailer_link, poster, cast_names))
            conn.commit()
            flash('New item added successfully.')

            return redirect(url_for('admin_dashboard'))

        conn.close()

        return render_template('new_item.html')
    else:
        return redirect(url_for('login'))


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'username' in session:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Get the item id and user id
        item_id = request.form['item_id']
        user_id = session['username']

        # Check if the item already exists in the user's cart
        cursor.execute('SELECT * FROM cart WHERE user_id=? AND item_id=?', (user_id, item_id))
        cart_item = cursor.fetchone()

        if cart_item:
            # Item already exists in the cart, redirect the user to the cart page
            conn.close()
        else:
            # Item doesn't exist in the cart, insert a new record
            cursor.execute('INSERT INTO cart (user_id, item_id) VALUES (?, ?)', (user_id, item_id))
            conn.commit()

        conn.close()

        return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))


@app.route('/cart')
def cart():
    if 'username' in session:
        username = session['username']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT stock.item_id, stock.moviename, stock.price FROM cart JOIN stock ON cart.item_id=stock.item_id WHERE cart.user_id=?', (username,))
        items = cursor.fetchall()
        item_id = cursor.fetchone()
        session['cart_items'] = items
        cursor.execute('SELECT stock.price FROM cart JOIN stock ON cart.item_id=stock.item_id WHERE cart.user_id=?',
                       (username,))
        prices = cursor.fetchall()
        total = sum([int(price[0].replace('$', '')) for price in prices])
        conn.close()
        return render_template('cart.html', items=items, total=total, item_id=item_id)
    else:
        return redirect(url_for('login'))

@app.route('/remove-from-cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if 'username' in session:
        username = session['username']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE user_id = ? AND item_id = ?', (username, item_id,))
        conn.commit()
        conn.close()
        flash('Item removed from cart!', 'success')
        return redirect(url_for('cart'))
    else:
        return redirect(url_for('login'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'username' in session:
        username = session['username']
        cart_items = session.get('cart_items', [])
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT stock.price FROM cart JOIN stock ON cart.item_id=stock.item_id WHERE cart.user_id=?', (username,))
        prices = cursor.fetchall()
        total = sum([int(price[0].replace('$', '')) for price in prices])
        conn.close()
        return render_template('checkout.html', items=cart_items, total=total)
    else:
        return redirect(url_for('login'))

@app.route('/complete_checkout', methods=['POST'])
def complete_checkout():
    if 'username' in session:
        username = session['username']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(
            'SELECT stock.item_id, stock.moviename, stock.price FROM cart JOIN stock ON cart.item_id=stock.item_id WHERE cart.user_id=?',
            (username,))
        cart_items = cursor.fetchall()
        for item in cart_items:
            item_id = item[0]
            quantity = 1 # assuming quantity is always 1 for now
            price = int(item[2].replace('$', ''))
            total_price = price * quantity
            date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO history (user_id, item_id, quantity, price, total_price, date) VALUES (?, ?, ?, ?, ?, ?)', (username, item_id, quantity, price, total_price, date))
            conn.commit()
        conn.close()
        flash('Order placed successfully!', 'success')
        # Remove all items from the cart
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE user_id = ?', (username,))
        conn.commit()
        conn.close()
        return redirect(url_for('cart'))
    else:
        return redirect(url_for('login'))


@app.route('/history')
def history():
    if 'username' in session:
        username = session['username']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT stock.moviename, stock.price, history.date FROM history INNER JOIN stock ON history.item_id = stock.item_id WHERE history.user_id = ?', (username,))
        items = cursor.fetchall()
        conn.close()
        return render_template('history.html', items=items)
    else:
        return redirect(url_for('login'))


@app.context_processor
def cart_count():
    def get_cart_count():
        if 'username' in session:
            username = session['username']
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM cart WHERE user_id=?', (username,))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        else:
            return 0
    return dict(cart_count=get_cart_count)

@app.route('/admin/edit_item/<int:item_id>', methods=['GET', 'POST'])
def item_edit(item_id):
    print(request.form)
    if 'username' in session and session['admin']:
        conn = get_db()
        cursor = conn.cursor()

        # Get the current values of the item from the database
        cursor.execute('SELECT * FROM stock WHERE item_id=?', (item_id,))
        item = cursor.fetchone()

        if request.method == 'POST':
            # Get the new values from the form
            moviename = request.form['moviename']
            description = request.form['description']
            cast_names = request.form['cast_names']
            price = request.form['price']
            poster = request.form['poster']
            trailer_link = request.form['trailer_link']

            # Update the item in the database
            cursor.execute('UPDATE stock SET moviename=?, description=?, cast_names=?, price=?, poster=?, trailer_link=? WHERE item_id=?',
                           (moviename, description, cast_names, price, poster, trailer_link, item_id))
            conn.commit()
            flash('Item updated successfully.')

            # Redirect to the stock list page
            return redirect(url_for('admin_dashboard'))

        conn.close()

        return render_template('item_edit.html', item=item)
    else:
        return redirect(url_for('login'))

@app.route('/admin/delete_item/<int:item_id>', methods=['POST'])
def item_delete(item_id):
    if 'username' in session and session['admin']:
        conn = get_db()
        cursor = conn.cursor()

        # Delete the item from the database
        cursor.execute('DELETE FROM stock WHERE item_id=?', (item_id,))
        conn.commit()
        flash('Item deleted successfully.')

        conn.close()

        # Redirect to the stock list page
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/item/<int:item_id>')
def item(item_id):
    conn = get_db()
    cursor = conn.cursor()

    # Get the movie details from the database
    cursor.execute('SELECT * FROM stock WHERE item_id = ?', (item_id,))
    item = cursor.fetchone()

    conn.close()

    if item:
        return render_template('item.html', item=item)
    else:
        flash('Item not found.')
        return redirect(url_for('index'))

#run the app
if __name__ == '__main__':
    app.run(port=5000, debug=True)
