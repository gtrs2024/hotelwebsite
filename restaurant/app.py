import os
import uuid
from datetime import datetime, date
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'elara-lonavala-luxury-2024-secret')
app.config['WTF_CSRF_ENABLED'] = True
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'images', 'gallery')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
VALID_ADMIN_STATUSES = ('New', 'Accepted', 'Countered', 'Declined', 'Contacted', 'Pending')

csrf = CSRFProtect(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ── Helpers ────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def customer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'customer_id' not in session:
            flash('Please sign in to access your dashboard.', 'info')
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_globals():
    current_customer = None
    if 'customer_id' in session:
        db = get_db()
        current_customer = db.execute(
            'SELECT id, name, email, phone FROM customers WHERE id = ?',
            (session['customer_id'],)
        ).fetchone()
        db.close()
    return {
        'current_year': datetime.now().year,
        'current_customer': current_customer,
    }


# ── Public Routes ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    menu_preview = db.execute(
        "SELECT * FROM menu_items WHERE category IN ('Starters','Main Course') LIMIT 6"
    ).fetchall()
    gallery_preview = db.execute("SELECT * FROM gallery LIMIT 6").fetchall()
    db.close()
    return render_template('index.html', menu_preview=menu_preview, gallery_preview=gallery_preview)


@app.route('/menu')
def menu():
    db = get_db()
    categories = ['Starters', 'Main Course', 'Desserts', 'Beverages']
    menu = {cat: db.execute(
        'SELECT * FROM menu_items WHERE category = ? ORDER BY name', (cat,)
    ).fetchall() for cat in categories}
    db.close()
    return render_template('menu.html', menu=menu, categories=categories)


@app.route('/gallery')
def gallery():
    db = get_db()
    images = db.execute('SELECT * FROM gallery ORDER BY id DESC').fetchall()
    db.close()
    return render_template('gallery.html', images=images)


@app.route('/reservation', methods=['GET', 'POST'])
def reservation():
    # Pre-fill from logged-in customer
    prefill = {}
    if 'customer_id' in session:
        db = get_db()
        cust = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
        db.close()
        if cust:
            prefill = {'customer_name': cust['name'], 'email': cust['email'], 'phone': cust['phone'] or ''}

    if request.method == 'POST':
        name    = request.form.get('customer_name', '').strip()
        phone   = request.form.get('phone', '').strip()
        email   = request.form.get('email', '').strip()
        pref_date = request.form.get('preferred_date', '').strip()
        pref_time = request.form.get('preferred_time', '').strip()
        guests  = request.form.get('guests', '').strip()
        special = request.form.get('special_requests', '').strip()

        errors = []
        if not name:   errors.append('Full name is required.')
        if not phone:  errors.append('Phone number is required.')
        if not email or '@' not in email: errors.append('A valid email is required.')
        if not pref_date: errors.append('Preferred date is required.')
        if not pref_time: errors.append('Preferred time is required.')
        if not guests or not guests.isdigit(): errors.append('Number of guests is required.')

        if errors:
            return render_template('reservation.html', errors=errors, form=request.form, success=False)

        cust_id = session.get('customer_id')
        db = get_db()
        db.execute(
            '''INSERT INTO reservations
               (customer_id, customer_name, phone, email, preferred_date,
                preferred_time, guests, special_requests)
               VALUES (?,?,?,?,?,?,?,?)''',
            (cust_id, name, phone, email, pref_date, pref_time, int(guests), special)
        )
        db.commit()
        db.close()

        if cust_id:
            flash('Your reservation request has been submitted. We will contact you shortly.', 'success')
            return redirect(url_for('customer_dashboard'))

        return render_template('reservation.html', success=True, errors=[])

    return render_template('reservation.html', success=False, errors=[], form=prefill)


@app.route('/contact')
def contact():
    return render_template('contact.html')


# ── Customer Auth ──────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def customer_register():
    if 'customer_id' in session:
        return redirect(url_for('customer_dashboard'))

    errors = []
    form = {}
    if request.method == 'POST':
        form = request.form
        name     = form.get('name', '').strip()
        email    = form.get('email', '').strip()
        phone    = form.get('phone', '').strip()
        password = form.get('password', '')
        confirm  = form.get('confirm_password', '')

        if not name:   errors.append('Full name is required.')
        if not email or '@' not in email: errors.append('A valid email is required.')
        if not password or len(password) < 6: errors.append('Password must be at least 6 characters.')
        if password != confirm: errors.append('Passwords do not match.')

        if not errors:
            db = get_db()
            existing = db.execute('SELECT id FROM customers WHERE email = ?', (email,)).fetchone()
            if existing:
                errors.append('An account with this email already exists.')
                db.close()
            else:
                db.execute(
                    'INSERT INTO customers (name, email, phone, password_hash) VALUES (?,?,?,?)',
                    (name, email, phone, generate_password_hash(password))
                )
                db.commit()
                customer = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
                db.close()
                session['customer_id']   = customer['id']
                session['customer_name'] = customer['name']
                flash(f'Welcome to Elara, {name}! Your account has been created.', 'success')
                return redirect(url_for('customer_dashboard'))

    return render_template('auth/register.html', errors=errors, form=form)


@app.route('/login', methods=['GET', 'POST'])
def customer_login():
    if 'customer_id' in session:
        return redirect(url_for('customer_dashboard'))

    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        customer = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
        db.close()
        if customer and check_password_hash(customer['password_hash'], password):
            session['customer_id']   = customer['id']
            session['customer_name'] = customer['name']
            flash(f'Welcome back, {customer["name"]}!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('customer_dashboard'))
        error = 'Invalid email or password.'

    return render_template('auth/login.html', error=error)


@app.route('/logout', methods=['POST'])
def customer_logout():
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    flash('You have been signed out.', 'info')
    return redirect(url_for('index'))


# ── Customer Dashboard ─────────────────────────────────────────────────────

@app.route('/dashboard')
@customer_required
def customer_dashboard():
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    reservations = db.execute(
        'SELECT * FROM reservations WHERE customer_id = ? ORDER BY created_at DESC',
        (session['customer_id'],)
    ).fetchall()
    db.close()

    active_statuses = ('New', 'Accepted', 'Countered', 'Contacted', 'Pending')
    active = [r for r in reservations if r['status'] in active_statuses]
    history = [r for r in reservations if r['status'] in ('Declined',)]
    # Separate into current (upcoming) and past
    today = date.today().isoformat()
    upcoming = [r for r in reservations if r['preferred_date'] >= today and r['status'] not in ('Declined',)]
    past = [r for r in reservations if r['preferred_date'] < today or r['status'] == 'Declined']

    return render_template('customer/dashboard.html',
                           customer=customer,
                           reservations=reservations,
                           upcoming=upcoming,
                           past=past)


@app.route('/dashboard/profile', methods=['GET', 'POST'])
@customer_required
def customer_profile():
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()

    errors = []
    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not name: errors.append('Name is required.')
        if new_pw and len(new_pw) < 6: errors.append('New password must be at least 6 characters.')
        if new_pw and new_pw != confirm_pw: errors.append('Passwords do not match.')

        if not errors:
            if new_pw:
                db.execute('UPDATE customers SET name=?, phone=?, password_hash=? WHERE id=?',
                           (name, phone, generate_password_hash(new_pw), session['customer_id']))
            else:
                db.execute('UPDATE customers SET name=?, phone=? WHERE id=?',
                           (name, phone, session['customer_id']))
            db.commit()
            session['customer_name'] = name
            flash('Profile updated successfully.', 'success')
            db.close()
            return redirect(url_for('customer_dashboard'))

    db.close()
    return render_template('customer/profile.html', customer=customer, errors=errors)


# ── Admin Auth ─────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        admin = db.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()
        db.close()
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_id']       = admin['id']
            session['admin_username'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid credentials. Please try again.'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout', methods=['POST'])
@admin_required
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))


# ── Admin Dashboard ────────────────────────────────────────────────────────

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    today = date.today().isoformat()
    stats = {
        'total_reservations': db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0],
        'today_reservations': db.execute(
            "SELECT COUNT(*) FROM reservations WHERE DATE(created_at) = ?", (today,)).fetchone()[0],
        'new_reservations': db.execute(
            "SELECT COUNT(*) FROM reservations WHERE status = 'New'").fetchone()[0],
        'total_customers': db.execute('SELECT COUNT(*) FROM customers').fetchone()[0],
        'total_menu':      db.execute('SELECT COUNT(*) FROM menu_items').fetchone()[0],
        'total_gallery':   db.execute('SELECT COUNT(*) FROM gallery').fetchone()[0],
    }
    recent = db.execute(
        '''SELECT r.*, c.name AS cust_name FROM reservations r
           LEFT JOIN customers c ON r.customer_id = c.id
           ORDER BY r.created_at DESC LIMIT 8'''
    ).fetchall()
    db.close()
    return render_template('admin/dashboard.html', stats=stats, recent=recent)


# ── Admin Reservations ─────────────────────────────────────────────────────

@app.route('/admin/reservations')
@admin_required
def admin_reservations():
    db = get_db()
    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = '''SELECT r.*, c.name AS cust_name, c.id AS cust_id
               FROM reservations r LEFT JOIN customers c ON r.customer_id = c.id
               WHERE 1=1'''
    params = []
    if search:
        query += ' AND (r.customer_name LIKE ? OR r.email LIKE ? OR r.phone LIKE ?)'
        like = f'%{search}%'
        params += [like, like, like]
    if status_filter:
        query += ' AND r.status = ?'
        params.append(status_filter)
    query += ' ORDER BY r.created_at DESC'

    reservations = db.execute(query, params).fetchall()
    db.close()
    return render_template('admin/reservations.html', reservations=reservations,
                           search=search, status_filter=status_filter,
                           valid_statuses=VALID_ADMIN_STATUSES)


@app.route('/admin/reservations/<int:res_id>/action', methods=['POST'])
@admin_required
def reservation_action(res_id):
    action = request.form.get('action', '').strip()
    counter_msg = request.form.get('counter_message', '').strip()
    admin_note  = request.form.get('admin_note', '').strip()

    status_map = {
        'accept':  'Accepted',
        'decline': 'Declined',
        'counter': 'Countered',
        'pending': 'Pending',
        'contacted': 'Contacted',
    }
    new_status = status_map.get(action)
    if not new_status:
        abort(400)

    db = get_db()
    db.execute(
        'UPDATE reservations SET status=?, counter_message=?, admin_note=? WHERE id=?',
        (new_status, counter_msg if action == 'counter' else None, admin_note or None, res_id)
    )
    db.commit()
    db.close()
    flash(f'Reservation #{res_id} marked as {new_status}.', 'success')
    return redirect(url_for('admin_reservations'))


@app.route('/admin/reservations/<int:res_id>/delete', methods=['POST'])
@admin_required
def delete_reservation(res_id):
    db = get_db()
    db.execute('DELETE FROM reservations WHERE id = ?', (res_id,))
    db.commit()
    db.close()
    flash('Reservation deleted.', 'success')
    return redirect(url_for('admin_reservations'))


@app.route('/admin/customers')
@admin_required
def admin_customers():
    db = get_db()
    customers = db.execute(
        '''SELECT c.*, COUNT(r.id) as reservation_count
           FROM customers c LEFT JOIN reservations r ON c.id = r.customer_id
           GROUP BY c.id ORDER BY c.created_at DESC'''
    ).fetchall()
    db.close()
    return render_template('admin/customers.html', customers=customers)


@app.route('/admin/customers/<int:cust_id>')
@admin_required
def admin_customer_detail(cust_id):
    db = get_db()
    customer = db.execute('SELECT * FROM customers WHERE id = ?', (cust_id,)).fetchone()
    if not customer:
        abort(404)
    reservations = db.execute(
        'SELECT * FROM reservations WHERE customer_id = ? ORDER BY created_at DESC', (cust_id,)
    ).fetchall()
    db.close()
    return render_template('admin/customer_detail.html', customer=customer, reservations=reservations)


# ── Admin Menu ─────────────────────────────────────────────────────────────

@app.route('/admin/menu')
@admin_required
def admin_menu():
    db = get_db()
    categories = ['Starters', 'Main Course', 'Desserts', 'Beverages']
    items = db.execute('SELECT * FROM menu_items ORDER BY category, name').fetchall()
    db.close()
    return render_template('admin/menu.html', items=items, categories=categories)


@app.route('/admin/menu/add', methods=['POST'])
@admin_required
def admin_menu_add():
    category = request.form.get('category', '').strip()
    name     = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price    = request.form.get('price', '0').strip()
    if not all([category, name, price]):
        flash('Category, name, and price are required.', 'error')
        return redirect(url_for('admin_menu'))
    try:
        price = float(price)
    except ValueError:
        flash('Invalid price.', 'error')
        return redirect(url_for('admin_menu'))
    db = get_db()
    db.execute('INSERT INTO menu_items (category, name, description, price) VALUES (?,?,?,?)',
               (category, name, description, price))
    db.commit()
    db.close()
    flash('Menu item added.', 'success')
    return redirect(url_for('admin_menu'))


@app.route('/admin/menu/<int:item_id>/edit', methods=['POST'])
@admin_required
def admin_menu_edit(item_id):
    category = request.form.get('category', '').strip()
    name     = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price    = request.form.get('price', '0').strip()
    try:
        price = float(price)
    except ValueError:
        flash('Invalid price.', 'error')
        return redirect(url_for('admin_menu'))
    db = get_db()
    db.execute('UPDATE menu_items SET category=?, name=?, description=?, price=? WHERE id=?',
               (category, name, description, price, item_id))
    db.commit()
    db.close()
    flash('Menu item updated.', 'success')
    return redirect(url_for('admin_menu'))


@app.route('/admin/menu/<int:item_id>/delete', methods=['POST'])
@admin_required
def admin_menu_delete(item_id):
    db = get_db()
    db.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))
    db.commit()
    db.close()
    flash('Menu item deleted.', 'success')
    return redirect(url_for('admin_menu'))


# ── Admin Gallery ──────────────────────────────────────────────────────────

@app.route('/admin/gallery')
@admin_required
def admin_gallery():
    db = get_db()
    images = db.execute('SELECT * FROM gallery ORDER BY id DESC').fetchall()
    db.close()
    return render_template('admin/gallery.html', images=images)


@app.route('/admin/gallery/upload', methods=['POST'])
@admin_required
def admin_gallery_upload():
    caption   = request.form.get('caption', '').strip()
    image_url = request.form.get('image_url', '').strip()

    if image_url:
        db = get_db()
        db.execute('INSERT INTO gallery (image_path, caption) VALUES (?,?)', (image_url, caption))
        db.commit()
        db.close()
        flash('Image added.', 'success')
        return redirect(url_for('admin_gallery'))

    if 'image' not in request.files or request.files['image'].filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin_gallery'))

    file = request.files['image']
    if file and allowed_file(file.filename):
        ext      = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_path = url_for('static', filename=f'images/gallery/{filename}')
        db = get_db()
        db.execute('INSERT INTO gallery (image_path, caption) VALUES (?,?)', (image_path, caption))
        db.commit()
        db.close()
        flash('Image uploaded.', 'success')
    else:
        flash('Invalid file type.', 'error')
    return redirect(url_for('admin_gallery'))


@app.route('/admin/gallery/<int:img_id>/delete', methods=['POST'])
@admin_required
def admin_gallery_delete(img_id):
    db = get_db()
    db.execute('DELETE FROM gallery WHERE id = ?', (img_id,))
    db.commit()
    db.close()
    flash('Image removed.', 'success')
    return redirect(url_for('admin_gallery'))


# ── Entry Point ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
