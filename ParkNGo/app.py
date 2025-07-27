from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from database import init_db, get_db

app = Flask(__name__)
app.secret_key = 'your-secret-key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        contact = request.form['contact']
        
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password, name, contact) VALUES (?, ?, ?, ?)',
                      (username, password, name, contact))
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()

    # 1. My listed spaces
    cur.execute('SELECT * FROM parking_spaces WHERE user_id = ?', (user_id,))
    spaces = cur.fetchall()

    # 2. My bookings
    cur.execute('''
        SELECT b.id, b.hours, b.booking_date, p.title, p.address, p.city
        FROM bookings b
        JOIN parking_spaces p ON b.space_id = p.id
        WHERE b.user_id = ?
    ''', (user_id,))
    bookings = cur.fetchall()

    # 3. Bookings on my listed spaces by others
    cur.execute('''
        SELECT b.id, b.hours, b.booking_date, u.name, u.contact, p.title
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN parking_spaces p ON b.space_id = p.id
        WHERE p.user_id = ? AND b.user_id != ?
    ''', (user_id, user_id))
    bookings_on_my_spaces = cur.fetchall()

    conn.close()

    return render_template('dashboard.html',
                           spaces=spaces,
                           bookings=bookings,
                           bookings_on_my_spaces=bookings_on_my_spaces)


@app.route('/delete_space/<int:space_id>', methods=['POST'])
def delete_space(space_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    cur.execute('DELETE FROM parking_spaces WHERE id = ? AND user_id = ?', (space_id, session['user_id']))
    conn.commit()

    flash("Parking space deleted successfully.")
    return redirect(url_for('dashboard'))


@app.route('/add_space', methods=['GET', 'POST'])
def add_space():
    if not session.get('user_id'):
        flash('Please login to add a parking space.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        address = request.form['address']
        city = request.form['city']
        area = request.form['area']
        price = float(request.form['price'])
        total_slots = int(request.form['total_slots'])
        description = request.form['description']
        file = request.files['image']
        
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        db = get_db()
        db.execute('''INSERT INTO parking_spaces 
                     (user_id, title, address, city, area, price_per_hour, total_slots, available_slots, description, image)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (session['user_id'], title, address, city, area, price, total_slots, total_slots, description, filename))
        db.commit()
        flash('Parking space added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    cities = ['New York', 'Los Angeles', 'Chicago']
    areas = {
        'New York': ['Manhattan', 'Brooklyn', 'Queens'],
        'Los Angeles': ['Downtown', 'Hollywood', 'Santa Monica'],
        'Chicago': ['Loop', 'Lincoln Park', 'Wicker Park']
    }
    return render_template('add_space.html', cities=cities, areas=areas)

@app.route('/search', methods=['GET', 'POST'])
def search():
    db = get_db()
    spaces = []
    cities = ['New York', 'Los Angeles', 'Chicago']
    areas = {
        'New York': ['Manhattan', 'Brooklyn', 'Queens'],
        'Los Angeles': ['Downtown', 'Hollywood', 'Santa Monica'],
        'Chicago': ['Loop', 'Lincoln Park', 'Wicker Park']
    }
    
    if request.method == 'POST':
        city = request.form['city']
        area = request.form['area']
        query = 'SELECT * FROM parking_spaces WHERE city = ? AND area = ? AND available_slots > 0'
        spaces = db.execute(query, (city, area)).fetchall()
    
    return render_template('search.html', spaces=spaces, cities=cities, areas=areas)


@app.route('/space/<int:space_id>', methods=['GET', 'POST'])
def space_details(space_id):
    db = get_db()
    space = db.execute('SELECT * FROM parking_spaces WHERE id = ?', (space_id,)).fetchone()

    if not space:
        return "Space not found", 404

    user_id = session.get('user_id')
    error = None

    if request.method == 'POST':
        if not user_id:
            return redirect(url_for('login'))
        if space['user_id'] == user_id:
            error = "You cannot book your own space."
        else:
            hours = int(request.form['hours'])
            booking_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            db.execute(
                'INSERT INTO bookings (user_id, space_id, hours, booking_date) VALUES (?, ?, ?, ?)',
                (user_id, space_id, hours, booking_date)
            )
            db.execute(
                'UPDATE parking_spaces SET available_slots = available_slots - 1 WHERE id = ? AND available_slots > 0',
                (space_id,)
            )
            db.commit()
            return redirect(url_for('dashboard'))

    return render_template('space_details.html', space=space, error=error)

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    db = get_db()
    booking = db.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()

    if booking and booking['user_id'] == session.get('user_id'):
        # Refund slot
        db.execute('UPDATE parking_spaces SET available_slots = available_slots + 1 WHERE id = ?', (booking['space_id'],))
        db.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
        db.commit()

    return redirect(url_for('dashboard'))

@app.route('/reject_booking/<int:booking_id>', methods=['POST'])
def reject_booking(booking_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT space_id FROM bookings WHERE id = ?", (booking_id,))
    booking = cur.fetchone()

    if booking:
        space_id = booking['space_id']
        cur.execute("UPDATE parking_spaces SET available_slots = available_slots + 1 WHERE id = ?", (space_id,))
        cur.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        conn.commit()

    return redirect('/dashboard')

@app.route('/book/<int:space_id>', methods=['GET', 'POST'])
def book_space(space_id):
    if not session.get('user_id'):
        flash('Please login to book a parking space.', 'error')
        return redirect(url_for('login'))
    
    db = get_db()
    space = db.execute('SELECT * FROM parking_spaces WHERE id = ?', (space_id,)).fetchone()
    
    if space['user_id'] == session['user_id']:
        flash('You cannot book your own parking space.', 'error')
        return redirect(url_for('search'))
    
    if request.method == 'POST':
        hours = int(request.form['hours'])
        booking_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.execute('INSERT INTO bookings (user_id, space_id, hours, booking_date) VALUES (?, ?, ?, ?)',
                  (session['user_id'], space_id, hours, booking_date))
        db.execute('UPDATE parking_spaces SET available_slots = available_slots - 1 WHERE id = ?', (space_id,))
        db.commit()
        flash('Parking space booked successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('book_space.html', space=space, user=user)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
