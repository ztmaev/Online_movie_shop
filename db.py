import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Create users table
cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, email TEXT, is_admin INTEGER)')

# Insert default admin account
username = 'admin'
password = 'password'
hashed_password = generate_password_hash(password)
email = 'admin@maev.site'
is_admin = 1
cursor.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (username, hashed_password, email, is_admin))

# Insert a new user
username = 'maev'
password = 'Alph4'
hashed_password = generate_password_hash(password)
email = 'maev@maev.site'
is_admin = 1
cursor.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (username, hashed_password, email, is_admin))

# Create stock table
cursor.execute('CREATE TABLE IF NOT EXISTS stock (item_id INTEGER PRIMARY KEY, moviename TEXT, description TEXT, poster TEXT, trailer_link TEXT, cast_names TEXT, price TEXT)')

# Insert stock items
cursor.execute('INSERT INTO stock VALUES (?, ?, ?, ?, ?, ?, ?)', (1, 'The Shawshank Redemption', 'Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.', 'https://www.imdb.com/title/tt0111161/mediaviewer/rm2115405312/', 'https://www.youtube.com/watch?v=6hB3S9bIaco', 'Tim Robbins, Morgan Freeman, Bob Gunton', '2$'))
cursor.execute('INSERT INTO stock VALUES (?, ?, ?, ?, ?, ?, ?)', (2, 'The Godfather', 'The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.', 'https://www.imdb.com/title/tt0068646/mediaviewer/rm3647096576/', 'https://www.youtube.com/watch?v=sY1S34973zA', 'Marlon Brando, Al Pacino, James Caan', '3$'))
cursor.execute('INSERT INTO stock VALUES (?, ?, ?, ?, ?, ?, ?)', (3, 'The Dark Knight', 'When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.', 'https://www.imdb.com/title/tt0468569/mediaviewer/rm1181878528/', 'https://www.youtube.com/watch?v=EXeTwQWrcwY', 'Christian Bale, Heath Ledger, Aaron Eckhart', '4$'))

# Create cart table
cursor.execute('CREATE TABLE IF NOT EXISTS cart (user_id INTEGER, item_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(username), FOREIGN KEY (item_id) REFERENCES stock(item_id))')

# Insert items into user carts
cursor.execute('INSERT INTO cart VALUES (?, ?)', ('user', 1))
cursor.execute('INSERT INTO cart VALUES (?, ?)', ('user', 2))
cursor.execute('INSERT INTO cart VALUES (?, ?)', ('user', 3))

conn.commit()
conn.close()
