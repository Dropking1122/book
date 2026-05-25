import os
import json
import time
import secrets
from functools import wraps
from flask import Flask, request, jsonify, send_file, redirect, url_for, session

from PIL import Image

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

IMAGES_DIR = 'images/book2'
PAGES_JSON = os.path.join(IMAGES_DIR, 'pages.json')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

MP3_DIR = 'mp3'
MUSIC_FILE = os.path.join(MP3_DIR, 'lagu.mp3')
MUSIC_INFO_FILE = os.path.join(MP3_DIR, 'music_info.json')
ALLOWED_AUDIO = {'.mp3', '.ogg', '.wav', '.m4a'}


def load_pages():
    if os.path.exists(PAGES_JSON):
        with open(PAGES_JSON) as f:
            return json.load(f)
    return []


def save_pages(pages):
    with open(PAGES_JSON, 'w') as f:
        json.dump(pages, f, indent=2, ensure_ascii=False)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ── Public routes ──────────────────────────────────────────────

@app.route('/')
def index():
    return send_file('index.html')


@app.route('/api/pages', methods=['GET'])
def get_pages():
    return jsonify(load_pages())


# ── Auth routes ────────────────────────────────────────────────

@app.route('/login')
def login_page():
    if session.get('logged_in'):
        return redirect(url_for('admin'))
    return send_file('login.html')


@app.route('/login', methods=['POST'])
def do_login():
    password = request.form.get('password', '')
    if password == ADMIN_PASSWORD:
        session['logged_in'] = True
        return redirect(url_for('admin'))
    return redirect(url_for('login_page') + '?error=1')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


# ── Protected admin routes ─────────────────────────────────────

@app.route('/admin')
@login_required
def admin():
    return send_file('admin.html')


@app.route('/api/pages', methods=['POST'])
@api_login_required
def update_pages():
    pages = request.get_json()
    if not isinstance(pages, list):
        return jsonify({'error': 'Expected a list'}), 400
    save_pages(pages)
    return jsonify({'success': True})


@app.route('/api/upload', methods=['POST'])
@api_login_required
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    title = request.form.get('title', '').strip()

    pages = load_pages()
    ts = int(time.time() * 1000)
    filename = f'page_{ts}.png'
    thumb_filename = f'thumb_{ts}.png'

    img = Image.open(file.stream).convert('RGB')
    img.save(os.path.join(IMAGES_DIR, filename))

    thumb = img.copy()
    thumb.thumbnail((200, 300))
    thumb.save(os.path.join(IMAGES_DIR, thumb_filename))

    if not title:
        title = f'Halaman {len(pages) + 1}'

    page = {
        'src': f'images/book2/{filename}',
        'thumb': f'images/book2/{thumb_filename}',
        'title': title
    }
    pages.append(page)
    save_pages(pages)

    return jsonify({'success': True, 'page': page, 'index': len(pages) - 1})


@app.route('/api/pages/<int:idx>', methods=['DELETE'])
@api_login_required
def delete_page(idx):
    pages = load_pages()
    if idx < 0 or idx >= len(pages):
        return jsonify({'error': 'Invalid index'}), 400

    page = pages[idx]
    for key in ['src', 'thumb']:
        path = page.get(key, '')
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    pages.pop(idx)
    save_pages(pages)
    return jsonify({'success': True})


@app.route('/api/music/info', methods=['GET'])
@api_login_required
def music_info():
    name = 'lagu.mp3'
    if os.path.exists(MUSIC_INFO_FILE):
        with open(MUSIC_INFO_FILE) as f:
            name = json.load(f).get('name', 'lagu.mp3')
    size = os.path.getsize(MUSIC_FILE) if os.path.exists(MUSIC_FILE) else 0
    return jsonify({'name': name, 'size': size})


@app.route('/api/music', methods=['POST'])
@api_login_required
def upload_music():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_AUDIO:
        return jsonify({'error': 'Format tidak didukung. Gunakan MP3, OGG, WAV, atau M4A.'}), 400

    file.save(MUSIC_FILE)
    with open(MUSIC_INFO_FILE, 'w') as f:
        json.dump({'name': file.filename}, f)

    return jsonify({'success': True, 'name': file.filename})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
