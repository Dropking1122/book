import os
import json
import time
from flask import Flask, request, jsonify, send_file, abort
from PIL import Image

app = Flask(__name__, static_folder='.', static_url_path='')

IMAGES_DIR = 'images/book2'
PAGES_JSON = os.path.join(IMAGES_DIR, 'pages.json')


def load_pages():
    if os.path.exists(PAGES_JSON):
        with open(PAGES_JSON) as f:
            return json.load(f)
    return []


def save_pages(pages):
    with open(PAGES_JSON, 'w') as f:
        json.dump(pages, f, indent=2, ensure_ascii=False)


@app.route('/')
def index():
    return send_file('index.html')


@app.route('/admin')
def admin():
    return send_file('admin.html')


@app.route('/api/pages', methods=['GET'])
def get_pages():
    return jsonify(load_pages())


@app.route('/api/pages', methods=['POST'])
def update_pages():
    pages = request.get_json()
    if not isinstance(pages, list):
        return jsonify({'error': 'Expected a list'}), 400
    save_pages(pages)
    return jsonify({'success': True})


@app.route('/api/upload', methods=['POST'])
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
