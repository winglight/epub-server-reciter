from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS  # 导入 CORS
import os
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import uuid

app = Flask(__name__)
CORS(app)  # 为整个应用启用 CORS

FRONT_FOLDER = 'front'  # 新增前端文件夹
UPLOAD_FOLDER = FRONT_FOLDER + '/uploads'
PARSED_FOLDER = FRONT_FOLDER + '/parsed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PARSED_FOLDER'] = PARSED_FOLDER
app.config['FRONT_FOLDER'] = FRONT_FOLDER  # 配置前端文件夹

# 确保所需的目录都存在
for folder in [UPLOAD_FOLDER, PARSED_FOLDER, FRONT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.epub'):
        filename = file.filename #str(uuid.uuid4()) + '.epub'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        parse_epub(filepath, filename[:-5])
        return jsonify({'message': 'File uploaded and parsed successfully', 'filename': filename}), 200
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/books', methods=['GET'])
def get_books():
    books = []
    for filename in os.listdir(PARSED_FOLDER):
        if os.path.isdir(os.path.join(PARSED_FOLDER, filename)):
            books.append({
                'id': filename,
                'title': filename  # You might want to store and retrieve actual titles
            })
    return jsonify(books)

def parse_epub(filepath, book_id):
    book = epub.read_epub(filepath)
    book_folder = os.path.join(app.config['PARSED_FOLDER'], book_id)
    # os.makedirs(book_folder, exist_ok=True)
    os.makedirs(book_folder+"/images", exist_ok=True)

    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            chapter_title = soup.find('title').string if soup.find('title') else f"Chapter {len(chapters) + 1}"
            chapter_filename = f"{len(chapters):03d}.html"
            chapters.append({'title': chapter_title, 'file': chapter_filename})
            
            with open(os.path.join(book_folder, chapter_filename), 'w', encoding='utf-8') as f:
                f.write(str(soup))
        elif item.get_type() == ebooklib.ITEM_IMAGE:
            with open(os.path.join(book_folder, item.get_name()), 'wb') as f:
                f.write(item.get_content())

    # Generate table of contents
    toc_html = "<html><body><h1>Table of Contents</h1><ul>"
    for chapter in chapters:
        toc_html += f'<li><a href="{chapter["file"]}">{chapter["title"]}</a></li>'
    toc_html += "</ul></body></html>"
    
    with open(os.path.join(book_folder, 'toc.html'), 'w', encoding='utf-8') as f:
        f.write(toc_html)

# 新增用于服务前端文件的路由
@app.route('/front/<path:filename>')
def serve_front(filename):
    return send_from_directory(app.config['FRONT_FOLDER'], filename)

# 添加一个默认路由，当访问根路径时返回前端的index.html
@app.route('/')
def index():
    return send_from_directory(app.config['FRONT_FOLDER'], 'index.html')

if __name__ == '__main__':
    app.run(debug=True)