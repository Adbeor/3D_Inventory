from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import tempfile
import shutil
from datetime import date
from datetime import datetime
from sqlalchemy import Enum



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///filamentos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Marca(db.Model):
    __tablename__ = 'marcas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

class Tipo(db.Model):
    __tablename__ = 'tipos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

class Color(db.Model):
    __tablename__ = 'colores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)  # Nombre del color
    hex_color = db.Column(db.String(7), unique=True, nullable=False)  # Valor hexadecimal (ej. #FF5733)

class Filamento(db.Model):
    __tablename__ = 'filamentos'
    id = db.Column(db.Integer, primary_key=True)
    marca_id = db.Column(db.Integer, db.ForeignKey('marcas.id'), nullable=False)
    tipo_id = db.Column(db.Integer, db.ForeignKey('tipos.id'), nullable=False)
    color_id = db.Column(db.Integer, db.ForeignKey('colores.id'), nullable=False)
    codigo_unico = db.Column(db.String(20), unique=True, nullable=False)

    marca = db.relationship('Marca', backref='filamentos')
    tipo = db.relationship('Tipo', backref='filamentos')
    color = db.relationship('Color', backref='filamentos')
    peso_spool = db.Column(db.Integer)
    peso_actual = db.Column(db.Integer)
    fecha_apertura = db.Column(db.Date, default=date.today, nullable=False)
    estado = db.Column(Enum('Nuevo', 'En uso', 'Agotado', name='estado_enum'), default='Nuevo', nullable=False)

with app.app_context():
    db.create_all()

# Para generar un código único más corto
def generar_codigo_unico():
    filamentos_count = Filamento.query.count()
    return f"F{filamentos_count + 1:04d}"

@app.route('/')
def index():
    filamentos = db.session.query(Filamento).all()
    fecha_hoy = date.today()
    return render_template('index.html', filamentos=filamentos,fecha_hoy = fecha_hoy)

@app.route('/add', methods=['GET', 'POST'])
def add_filamento():
    marcas = Marca.query.all()
    tipos = Tipo.query.all()
    colores = Color.query.all()
    if request.method == 'POST':
        marca_id = request.form['marca']
        tipo_id = request.form['tipo']
        color_id = request.form['color']
        peso_spool = request.form['peso_spool']
        peso_actual = request.form['peso_actual']
        fecha_str = request.form['fecha_compra']
        fecha_apertura = datetime.strptime(fecha_str, '%Y-%m-%d').date()  # Convierte a tipo date
        estado = request.form['estado']
        
        print(estado)
        print(type(estado))
        codigo_unico = generar_codigo_unico()
        nuevo_filamento = Filamento(marca_id=marca_id, tipo_id=tipo_id, color_id=color_id, codigo_unico=codigo_unico,peso_spool=peso_spool,fecha_apertura =fecha_apertura, peso_actual = peso_actual,estado = estado)
        db.session.add(nuevo_filamento)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_filament.html', marcas=marcas, tipos=tipos, colores=colores)

@app.route('/generate_qr_pdf')
def generate_qr_pdf():
    # Crear PDF con códigos QR
    filamentos = db.session.query(Filamento).all()
    file_path = "qrs_filamentos.pdf"
    
    c = canvas.Canvas(file_path, pagesize=letter)
    y_position = 700  # Posición inicial para los QR

    for filamento in filamentos:
        qr_data = filamento.codigo_unico
        qr_img = qrcode.make(qr_data)

        print(int(filamento.codigo_unico[-1]))
        if int(filamento.codigo_unico[-1]) % 2 == 0:
            x_position = 350
            salto = 120
        else:
            x_position = 100
            salto = 0
        
        # Guardar la imagen del QR en un archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_qr_file:
            qr_img.save(temp_qr_file)
            temp_qr_file_path = temp_qr_file.name

        # Insertar QR en el PDF
        c.drawImage(temp_qr_file_path, x_position, y_position, width=100, height=100)
        c.drawString(x_position + 10, y_position - 10, f"{filamento.codigo_unico} - {filamento.marca.nombre} - {filamento.color.nombre}")
        y_position -= salto  # Mover hacia abajo para el siguiente QR

        if y_position < 100:
            c.showPage()  # Crear una nueva página si se acaba el espacio
            y_position = 700  # Restablecer la posición

        # Eliminar el archivo temporal después de usarlo
        os.remove(temp_qr_file_path)

    c.save()

    return redirect(url_for('download_pdf', filename=file_path))

@app.route('/download_pdf/<filename>')
def download_pdf(filename):
    return send_from_directory(os.getcwd(), filename)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_filamento(id):
    filamento = db.session.get(Filamento, id)
    marcas = Marca.query.all()
    tipos = Tipo.query.all()
    colores = Color.query.all()
    if not filamento:
        return redirect(url_for('index'))
    if request.method == 'POST':
        filamento.estado = request.form['estado']
        filamento.peso_actual = request.form['peso_actual']
        filamento.peso_spool = request.form['peso_spool']
        fecha_str = request.form['fecha_apertura']
        filamento.fecha_apertura = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', filamento=filamento, marcas=marcas, tipos=tipos, colores=colores)

@app.route('/delete/<int:id>')
def delete_filamento(id):
    filamento = db.session.get(Filamento, id)
    if filamento:
        db.session.delete(filamento)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_marca', methods=['GET', 'POST'])
def add_marca():
    marcas = Marca.query.all()
    if request.method == 'POST':
        nombre = request.form['nombre']
        nueva_marca = Marca(nombre=nombre)
        db.session.add(nueva_marca)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_marca.html',marcas = marcas)

@app.route('/add_tipo', methods=['GET', 'POST'])
def add_tipo():
    tipos = Tipo.query.all()
    if request.method == 'POST':
        nombre = request.form['nombre']
        nuevo_tipo = Tipo(nombre=nombre)
        db.session.add(nuevo_tipo)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_tipo.html',tipos = tipos)

@app.route('/add_color', methods=['GET', 'POST'])
def add_color():
    if request.method == 'POST':
        nombre = request.form['nombre']  # El nombre del color
        hex_color = request.form['hex_color']  # El valor hexadecimal del color
        nuevo_color = Color(nombre=nombre, hex_color=hex_color)
        db.session.add(nuevo_color)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_color.html')

if __name__ == '__main__':
    app.run(debug=True)
