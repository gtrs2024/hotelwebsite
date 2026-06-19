import os
import uuid
from datetime import datetime, date
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, abort)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'elara-lonavala-luxury-2024-secret')
app.config['WTF_CSRF_ENABLED'] = True
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'images', 'gallery')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

csrf = CSRFProtect(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ── Helpers ────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}


# ── Public Routes ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    menu_preview = db.execute(
        "SELECT * FROM menu_items WHERE category IN ('Starters','Main Course') LIMIT 6"
    ).fetchall()
    gallery_preview = db.execute(
        "SELECT * FROM gallery LIMIT 6"
    ).fetchall()
    db.close()
    return render_template('index.html', menu_preview=menu_preview, gallery_preview=gallery_preview)


@app.route('/menu')
def menu():
    db = get_db()
    categories = ['Starters', 'Main Course', 'Desserts', 'Beverages']
    menu = {}
    for cat in categories:
        menu[cat] = db.execute(
            'SELECT * FROM menu_items WHERE category = ? ORDER BY name', (cat,)
        ).fetchall()
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
    if request.method == 'POST':
        name = request.form.get('customer_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        pref_date = request.form.get('preferred_date', '').strip()
        pref_time = request.form.get('preferred_time', '').strip()
        guests = request.form.get('guests', '').strip()
        special = request.form.get('special_requests', '').strip()

        errors = []
        if not name: errors.append('Full name is required.')
        if not phone: errors.append('Phone number is required.')
        if not email or '@' not in email: errors.append('A valid email is required.')
        if not pref_date: errors.append('Preferred date is required.')
        if not pref_time: errors.append('Preferred time is required.')
        if not guests or not guests.isdigit(): errors.append('Number of guests is required.')

        if errors:
            return render_template('reservation.html', errors=errors,
                                   form=request.form, success=False)

        db = get_db()
        db.execute(
            '''INSERT INTO reservations
               (customer_name, phone, email, preferred_date, preferred_time, guests, special_requests)
               VALUES (?,?,?,?,?,?,?)''',
            (name, phone, email, pref_date, pref_time, int(guests), special)
        )
        db.commit()
        db.close()
        return render_template('reservation.html', success=True, errors=[])

    return render_template('reservation.html', success=False, errors=[], form={})


@app.route('/contact')
def contact():
    return render_template('contact.html')


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
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid credentials. Please try again.'

    return render_template('admin/login.html', error=error)


@app.route('/admin/logout', methods=['POST'])
@login_required
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


# ── Admin Dashboard ────────────────────────────────────────────────────────

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    db = get_db()
    today = date.today().isoformat()
    stats = {
        'total_reservations': db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0],
        'today_reservations': db.execute(
            "SELECT COUNT(*) FROM reservations WHERE DATE(created_at) = ?", (today,)
        ).fetchone()[0],
        'new_reservations': db.execute(
            "SELECT COUNT(*) FROM reservations WHERE status = 'New'"
        ).fetchone()[0],
        'total_menu': db.execute('SELECT COUNT(*) FROM menu_items').fetchone()[0],
        'total_gallery': db.execute('SELECT COUNT(*) FROM gallery').fetchone()[0],
    }
    recent = db.execute(
        'SELECT * FROM reservations ORDER BY created_at DESC LIMIT 5'
    ).fetchall()
    db.close()
    return render_template('admin/dashboard.html', stats=stats, recent=recent)


# ── Admin Reservations ─────────────────────────────────────────────────────

@app.route('/admin/reservations')
@login_required
def admin_reservations():
    db = get_db()
    search = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = 'SELECT * FROM reservations WHERE 1=1'
    params = []
    if search:
        query += ' AND (customer_name LIKE ? OR email LIKE ? OR phone LIKE ?)'
        like = f'%{search}%'
        params += [like, like, like]
    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)
    query += ' ORDER BY created_at DESC'

    reservations = db.execute(query, params).fetchall()
    db.close()
    return render_template('admin/reservations.html', reservations=reservations,
                           search=search, status_filter=status_filter)


@app.route('/admin/reservations/<int:res_id>/status', methods=['POST'])
@login_required
def update_reservation_status(res_id):
    status = request.form.get('status')
    if status not in ('New', 'Contacted', 'Pending'):
        abort(400)
    db = get_db()
    db.execute('UPDATE reservations SET status = ? WHERE id = ?', (status, res_id))
    db.commit()
    db.close()
    flash(f'Status updated to {status}.', 'success')
    return redirect(url_for('admin_reservations'))


@app.route('/admin/reservations/<int:res_id>/delete', methods=['POST'])
@login_required
def delete_reservation(res_id):
    db = get_db()
    db.execute('DELETE FROM reservations WHERE id = ?', (res_id,))
    db.commit()
    db.close()
    flash('Reservation deleted.', 'success')
    return redirect(url_for('admin_reservations'))


# ── Admin Menu ─────────────────────────────────────────────────────────────

@app.route('/admin/menu')
@login_required
def admin_menu():
    db = get_db()
    categories = ['Starters', 'Main Course', 'Desserts', 'Beverages']
    items = db.execute('SELECT * FROM menu_items ORDER BY category, name').fetchall()
    db.close()
    return render_template('admin/menu.html', items=items, categories=categories)


@app.route('/admin/menu/add', methods=['POST'])
@login_required
def admin_menu_add():
    category = request.form.get('category', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price = request.form.get('price', '0').strip()

    if not all([category, name, price]):
        flash('Category, name, and price are required.', 'error')
        return redirect(url_for('admin_menu'))

    try:
        price = float(price)
    except ValueError:
        flash('Invalid price.', 'error')
        return redirect(url_for('admin_menu'))

    db = get_db()
    db.execute(
        'INSERT INTO menu_items (category, name, description, price) VALUES (?,?,?,?)',
        (category, name, description, price)
    )
    db.commit()
    db.close()
    flash('Menu item added.', 'success')
    return redirect(url_for('admin_menu'))


@app.route('/admin/menu/<int:item_id>/edit', methods=['POST'])
@login_required
def admin_menu_edit(item_id):
    category = request.form.get('category', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price = request.form.get('price', '0').strip()
    try:
        price = float(price)
    except ValueError:
        flash('Invalid price.', 'error')
        return redirect(url_for('admin_menu'))

    db = get_db()
    db.execute(
        'UPDATE menu_items SET category=?, name=?, description=?, price=? WHERE id=?',
        (category, name, description, price, item_id)
    )
    db.commit()
    db.close()
    flash('Menu item updated.', 'success')
    return redirect(url_for('admin_menu'))


@app.route('/admin/menu/<int:item_id>/delete', methods=['POST'])
@login_required
def admin_menu_delete(item_id):
    db = get_db()
    db.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))
    db.commit()
    db.close()
    flash('Menu item deleted.', 'success')
    return redirect(url_for('admin_menu'))


# ── Admin Gallery ──────────────────────────────────────────────────────────

@app.route('/admin/gallery')
@login_required
def admin_gallery():
    db = get_db()
    images = db.execute('SELECT * FROM gallery ORDER BY id DESC').fetchall()
    db.close()
    return render_template('admin/gallery.html', images=images)


@app.route('/admin/gallery/upload', methods=['POST'])
@login_required
def admin_gallery_upload():
    caption = request.form.get('caption', '').strip()
    image_url = request.form.get('image_url', '').strip()

    if image_url:
        db = get_db()
        db.execute('INSERT INTO gallery (image_path, caption) VALUES (?,?)', (image_url, caption))
        db.commit()
        db.close()
        flash('Image added.', 'success')
        return redirect(url_for('admin_gallery'))

    if 'image' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('admin_gallery'))

    file = request.files['image']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin_gallery'))

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
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
@login_required
def admin_gallery_delete(img_id):
    db = get_db()
    img = db.execute('SELECT * FROM gallery WHERE id = ?', (img_id,)).fetchone()
    if img:
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
