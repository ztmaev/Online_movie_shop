import datetime
import json
import sqlite3

import requests
from flask import Flask, g, request, session, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'

API_KEY = "d96c51d9aa944073eb95ae3cdccb11af"


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

            # Check if the movie is in the cart
            cursor.execute('SELECT item_id FROM cart WHERE user_id = ?', (session['username'],))
            cart_items = [r[0] for r in cursor.fetchall()]

            # Add purchased items to session
            session['purchased_items'] = purchased_items

            # 1 random movie
            cursor.execute('SELECT * FROM stock ORDER BY RANDOM() LIMIT 1')
            banner = cursor.fetchone()

            conn.close()
            return render_template('index.html', items=items, purchased_items=purchased_items, cart_items=cart_items,
                                   banner=banner)


    else:
        return redirect(url_for('login'))


@app.route('/owned')
def owned():
    if 'username' in session:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM history WHERE user_id = ?', (session['username'],))
        items = cursor.fetchall()
        # remove duplicates
        items = list(set(items))
        # get the movie info from the id in items
        # get the movie info from the id in items
        item_info_list = []
        for item in items:
            item_id = item[1]
            cursor.execute('SELECT * FROM stock WHERE item_id = ?', (item_id,))
            item_info = cursor.fetchone()
            if item_info is not None:
                # append the item_id to the tuple
                item_info_list.append((item_id,) + item_info)
        # get total number of items
        cursor.execute('SELECT COUNT(*) FROM stock')
        total_items = cursor.fetchone()
        item_count = total_items[0]

        # get total number of movies owned by user
        user_id = session['username']
        cursor.execute('SELECT COUNT(*) FROM history WHERE user_id = ?', (user_id,))
        total_items = cursor.fetchone()
        owned = total_items[0]

        # get the total amount spent by user
        cursor.execute('SELECT SUM(price) FROM history WHERE user_id = ?', (user_id,))
        total_items = cursor.fetchone()
        spend = total_items[0]
        conn.close()
        return render_template('owned.html', items=item_info_list, item_count=item_count, owned=owned, spend=spend)
    else:
        return redirect(url_for('login'))


@app.route('/search/')
def search():
    search_term = request.args.get('search_term')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stock WHERE moviename LIKE ?', ('%{}%'.format(search_term),))
    movies = cursor.fetchall()
    # get total number of items
    cursor.execute('SELECT COUNT(*) FROM stock')
    total_items = cursor.fetchone()
    item_count = total_items[0]

    # get total number of movies owned by user
    user_id = session['username']
    cursor.execute('SELECT COUNT(*) FROM history WHERE user_id = ?', (user_id,))
    total_items = cursor.fetchone()
    owned = total_items[0]

    # get the total amount spent by user
    cursor.execute('SELECT SUM(price) FROM history WHERE user_id = ?', (user_id,))
    total_items = cursor.fetchone()
    spend = total_items[0]

    # get the items in the user's cart
    cursor.execute('SELECT item_id FROM cart WHERE user_id = ?', (user_id,))
    cart_items = [r[0] for r in cursor.fetchall()]
    session['cart_items'] = cart_items

    # get a list of movies owned by user
    cursor.execute('SELECT item_id FROM history WHERE user_id = ?', (user_id,))
    purchased_items = [r[0] for r in cursor.fetchall()]
    session['purchased_items'] = purchased_items

    conn.close()

    return render_template('search.html', movies=movies, search_term=search_term, item_count=item_count, owned=owned,
                           spend=spend, purchased_items=purchased_items, cart_items=cart_items)


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
        # login
        session['username'] = username
        session['admin'] = False
        return redirect(url_for('index'))
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
        # Get the 7 last purchases from the history table
        cursor.execute('SELECT * FROM history ORDER BY date DESC LIMIT 7')
        purchases = cursor.fetchall()

        # Get 8 most repeated item_id from the history table
        cursor.execute(
            'SELECT history.item_id, stock.moviename, COUNT(*) AS count FROM history INNER JOIN stock ON history.item_id = stock.item_id GROUP BY history.item_id, stock.moviename ORDER BY count DESC LIMIT 8')
        most_purchased = cursor.fetchall()

        times_purchased = []
        movies_purchased = []

        for item in most_purchased:
            times_purchased.append(item[2])
            movies_purchased.append(item[1])

        # get movie name of most purchased items from stock table

        # get total number of users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()
        user_count = total_users[0]

        # get total number of items
        cursor.execute('SELECT COUNT(*) FROM stock')
        total_items = cursor.fetchone()
        item_count = total_items[0]

        # get total amount in purchases
        cursor.execute('SELECT SUM(price) FROM history')
        total_purchases = cursor.fetchone()
        purchase_count = total_purchases[0]

        # Get the list of users from the database
        cursor.execute('SELECT username, is_admin FROM users')
        users = cursor.fetchall()

        # Get all items from the stock table
        cursor.execute('SELECT * FROM stock')
        items = cursor.fetchall()

        conn.close()

        return render_template('admin_dashboard.html', users=users, items=items, purchases=purchases,
                               user_count=user_count, item_count=item_count, purchase_count=purchase_count,
                               most_purchased=most_purchased)
    else:
        return redirect(url_for('login'))


@app.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
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
                return redirect(url_for('admin_users'))

            elif 'delete-user' in request.form:
                # Get the username to be deleted from the form
                username = request.form['username']

                # Delete the user from the database
                cursor.execute('DELETE FROM users WHERE username = ?', (username,))
                conn.commit()
                flash('User deleted successfully.')
                return redirect(url_for('admin_users'))

        # get total number of items
        cursor.execute('SELECT COUNT(*) FROM stock')
        total_items = cursor.fetchone()
        item_count = total_items[0]
        # Get the list of users from the database
        cursor.execute('SELECT username, is_admin FROM users')
        users = cursor.fetchall()
        # get total amount in purchases
        cursor.execute('SELECT SUM(price) FROM history')
        total_purchases = cursor.fetchone()
        purchase_count = total_purchases[0]
        # get total number of users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()
        user_count = total_users[0]
        # top 3 users with most purchases
        cursor.execute(
            'SELECT user_id, SUM(price) AS total_purchases FROM history GROUP BY user_id ORDER BY total_purchases DESC LIMIT 3;')
        top_users = cursor.fetchall()

        # get the number of purchases for each user
        for index, user in enumerate(top_users):
            user_id = user[0]
            cursor.execute('SELECT COUNT(*) FROM history WHERE user_id = ?', (user_id,))
            purchase_count = cursor.fetchone()[0]
            top_users[index] = (user[0], user[1], purchase_count)

        return render_template('admin_users.html', users=users, user_count=user_count, top_users=top_users,
                               item_count=item_count, purchase_count=purchase_count)
    else:
        return redirect(url_for('login'))


@app.route('/admin/stock', methods=['GET', 'POST'])
def admin_stock():
    if 'username' in session and session['admin']:
        conn = get_db()
        cursor = conn.cursor()

        if request.method == 'POST':
            if 'new-item' in request.form:
                # Get the new item details from the form
                moviename = request.form['moviename']
                price = request.form['price']
                description = request.form['description']

                # Insert the new item into the stock table
                cursor.execute('INSERT INTO stock (moviename, price, description) VALUES (?, ?, ?)',
                               (moviename, price, description))
                conn.commit()
                flash('New item added successfully.')
                return redirect(url_for('admin_stock'))

        # Get all items from the stock table
        cursor.execute('SELECT * FROM stock')
        items = cursor.fetchall()
        # get total number of items
        cursor.execute('SELECT COUNT(*) FROM stock')
        total_items = cursor.fetchone()
        item_count = total_items[0]
        # get total number of users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()
        user_count = total_users[0]
        # get total amount in purchases
        cursor.execute('SELECT SUM(price) FROM history')
        total_purchases = cursor.fetchone()
        purchase_count = total_purchases[0]
        conn.close()

        return render_template('admin_stock.html', items=items, item_count=item_count, user_count=user_count,
                               purchase_count=purchase_count)
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
            tmdb = request.form['tmdb']

            # Insert the new item into the stock table
            cursor.execute(
                'INSERT INTO stock (moviename, description, price, trailer_link, poster, cast_names, tmdb) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (moviename, description, price, trailer_link, poster, cast_names, tmdb))
            conn.commit()
            flash('New item added successfully.')

            return redirect(url_for('admin_stock'))

        # get total number of items
        cursor.execute('SELECT COUNT(*) FROM stock')
        total_items = cursor.fetchone()
        item_count = total_items[0]
        # get total number of users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()
        user_count = total_users[0]
        # get total amount in purchases
        cursor.execute('SELECT SUM(price) FROM history')
        total_purchases = cursor.fetchone()
        purchase_count = total_purchases[0]
        conn.close()

        return render_template('new_item.html', item_count=item_count, user_count=user_count,
                               purchase_count=purchase_count)
    else:
        return redirect(url_for('login'))


@app.route('/admin/tmdb', methods=['GET', 'POST'])
def new_item_tmdb():
    if 'username' in session and session['admin']:
        movie_details = None
        if request.method == "POST":
            movie_id = request.form["tmdb"]
            # Build the API URL
            url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US&append_to_response=credits,videos,keywords"

            # Send a GET request to the API
            response = requests.get(url)

            # Check if the response was successful
            if response.status_code == 200:
                # Convert the response JSON data to a Python dictionary
                movie_data = json.loads(response.content)

                # Extract the movie details
                name = movie_data["title"]
                description = movie_data["overview"]
                poster = f"https://image.tmdb.org/t/p/original{movie_data['poster_path']}"
                cast = []
                for cast_member in movie_data["credits"]["cast"][:5]:
                    # Get the cast member's details
                    person_url = f"https://api.themoviedb.org/3/person/{cast_member['id']}?api_key={API_KEY}&language=en-US"
                    person_response = requests.get(person_url)
                    person_data = json.loads(person_response.content)

                    # Get the cast member's image
                    profile_path = person_data["profile_path"]
                    if profile_path is not None:
                        profile_image = f"https://image.tmdb.org/t/p/original{profile_path}"
                    else:
                        profile_image = None

                    # Add the cast member's name and image to the list
                    cast.append({"name": cast_member["name"], "image": profile_image})
                trailer = f"https://www.youtube.com/watch?v={movie_data['videos']['results'][0]['key']}"
                tags = []
                for keyword in movie_data["keywords"]["keywords"]:
                    tags.append(keyword["name"])
                categories = []
                for genre in movie_data["genres"]:
                    categories.append(genre["name"])

                tmdb = movie_id

                # Return the movie details as a dictionary
                movie_details = {"name": name, "description": description, "poster": poster, "cast": cast,
                                 "trailer": trailer, "tags": tags, "categories": categories, "tmdb": tmdb}
            else:
                flash("Error fetching movie details.")
                return redirect(url_for("new_item"))
                print("Error fetching movie details.")

        conn = get_db()
        cursor = conn.cursor()
        # get total number of items
        cursor.execute('SELECT COUNT(*) FROM stock')
        total_items = cursor.fetchone()
        item_count = total_items[0]
        # get total number of users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()
        user_count = total_users[0]
        # get total amount in purchases
        cursor.execute('SELECT SUM(price) FROM history')
        total_purchases = cursor.fetchone()
        purchase_count = total_purchases[0]
        conn.close()
        return render_template("new_item.html", movie_details=movie_details, item_count=item_count,
                               user_count=user_count, purchase_count=purchase_count)
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

        return redirect(url_for('cart'))
    else:
        return redirect(url_for('login'))


@app.route('/cart')
def cart():
    if 'username' in session:
        username = session['username']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(
            'SELECT stock.item_id, stock.moviename, stock.poster, stock.description, stock.price, stock.trailer_link FROM cart JOIN stock ON cart.item_id=stock.item_id WHERE cart.user_id=?',
            (username,))
        items = cursor.fetchall()
        item_id = cursor.fetchone()
        session['cart_items'] = items
        cursor.execute('SELECT stock.price FROM cart JOIN stock ON cart.item_id=stock.item_id WHERE cart.user_id=?',
                       (username,))
        prices = cursor.fetchall()
        total = sum([int(price[0].replace('$', '')) for price in prices])
        # get total number of items
        cursor.execute('SELECT COUNT(*) FROM stock')
        total_items = cursor.fetchone()
        item_count = total_items[0]

        # get total number of movies owned by user
        user_id = session['username']
        cursor.execute('SELECT COUNT(*) FROM history WHERE user_id = ?', (user_id,))
        total_items = cursor.fetchone()
        owned = total_items[0]

        # get the total amount spent by user
        cursor.execute('SELECT SUM(price) FROM history WHERE user_id = ?', (user_id,))
        total_items = cursor.fetchone()
        spend = total_items[0]

        conn.close()
        return render_template('cart.html', items=items, total=total, item_id=item_id, item_count=item_count,
                               owned=owned, spend=spend)
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
            quantity = 1  # assuming quantity is always 1 for now
            price = int(item[2].replace('$', ''))
            total_price = price * quantity
            date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                'INSERT INTO history (user_id, item_id, quantity, price, total_price, date) VALUES (?, ?, ?, ?, ?, ?)',
                (username, item_id, quantity, price, total_price, date))
            conn.commit()
        conn.close()
        flash('Order placed successfully!', 'success')
        # Remove all items from the cart
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE user_id = ?', (username,))
        conn.commit()
        conn.close()
        return redirect(url_for('owned'))
    else:
        return redirect(url_for('login'))


@app.route('/history')
def history():
    if 'username' in session:
        username = session['username']
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(
            'SELECT stock.moviename, stock.price, stock.description, stock.poster, stock.item_id, history.date '
            'FROM history '
            'INNER JOIN stock ON history.item_id = stock.item_id '
            'WHERE history.user_id = ?',
            (username,))
        items = cursor.fetchall()

        # get total number of items
        cursor.execute('SELECT COUNT(*) FROM stock')
        total_items = cursor.fetchone()
        item_count = total_items[0]

        # get total number of movies owned by user
        cursor.execute('SELECT COUNT(*) FROM history WHERE user_id = ?', (username,))
        total_items = cursor.fetchone()
        owned = total_items[0]

        # get the total amount spent by user
        cursor.execute('SELECT SUM(price) FROM history WHERE user_id = ?', (username,))
        total_items = cursor.fetchone()
        spend = total_items[0]

        conn.close()
        return render_template('history.html', items=items, item_count=item_count, owned=owned, spend=spend)
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
            cursor.execute(
                'UPDATE stock SET moviename=?, description=?, cast_names=?, price=?, poster=?, trailer_link=? WHERE item_id=?',
                (moviename, description, cast_names, price, poster, trailer_link, item_id))
            conn.commit()
            flash('Item updated successfully.')

            # Redirect to the stock list page
            return redirect(url_for('admin_stock'))

        # get total number of items
        cursor.execute('SELECT COUNT(*) FROM stock')
        total_items = cursor.fetchone()
        item_count = total_items[0]
        # get total number of users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()
        user_count = total_users[0]
        # get total amount in purchases
        cursor.execute('SELECT SUM(price) FROM history')
        total_purchases = cursor.fetchone()
        purchase_count = total_purchases[0]
        conn.close()

        return render_template('item_edit.html', item=item, item_count=item_count, user_count=user_count,
                               purchase_count=purchase_count)
    else:
        return redirect(url_for('login'))


@app.route('/admin/delete_item/<int:item_id>', methods=['POST'])
def item_delete(item_id):
    if 'username' in session and session['admin']:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Delete the item from the database
        cursor.execute('DELETE FROM stock WHERE item_id=?', (item_id,))
        conn.commit()
        flash('Item deleted successfully.')

        cursor.close()
        conn.close()

        # Redirect to the stock list page
        return redirect(url_for('admin_stock'))
    else:
        return redirect(url_for('login'))


@app.route('/item/<int:item_id>')
def item(item_id):
    conn = get_db()
    cursor = conn.cursor()

    # Get the movie details from the database
    cursor.execute('SELECT * FROM stock WHERE item_id = ?', (item_id,))
    item = cursor.fetchone()
    # get a list of owned movies
    cursor.execute('SELECT item_id FROM history WHERE user_id = ?', (session['username'],))
    owned = cursor.fetchall()
    owned_movie_ids = []
    for movie in owned:
        owned_movie_ids.append(movie[0])

    # get items in cart
    cursor.execute('SELECT item_id FROM cart WHERE user_id = ?', (session['username'],))
    cart = cursor.fetchall()
    cart_movie_ids = []
    for movie in cart:
        cart_movie_ids.append(movie[0])





    conn.close()

    if item:
        return render_template('item.html', item=item, owned=owned_movie_ids, cart=cart_movie_ids)
    else:
        flash('Item not found.')
        return redirect(url_for('index'))


# run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
