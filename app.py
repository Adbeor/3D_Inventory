from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///filamentos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Crear la instancia de la base de datos
db = SQLAlchemy(app)

# Usar db.Model en lugar de Base
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
    nombre = db.Column(db.String(30), unique=True, nullable=False)

class Filamento(db.Model):
    __tablename__ = 'filamentos'
    id = db.Column(db.Integer, primary_key=True)
    marca_id = db.Column(db.Integer, db.ForeignKey('marcas.id'), nullable=False)
    tipo_id = db.Column(db.Integer, db.ForeignKey('tipos.id'), nullable=False)
    color_id = db.Column(db.Integer, db.ForeignKey('colores.id'), nullable=False)
    codigo_unico = db.Column(db.String(100), unique=True, nullable=False)

    # Relaciones con las tablas de opciones
    marca = db.relationship('Marca', backref='filamentos')
    tipo = db.relationship('Tipo', backref='filamentos')
    color = db.relationship('Color', backref='filamentos')

# Crear las tablas al iniciar la aplicación
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    filamentos = db.session.query(Filamento).all()
    return render_template('index.html', filamentos=filamentos)

@app.route('/add', methods=['GET', 'POST'])
def add_filamento():
    marcas = Marca.query.all()
    tipos = Tipo.query.all()
    colores = Color.query.all()
    if request.method == 'POST':
        marca_id = request.form['marca']
        tipo_id = request.form['tipo']
        color_id = request.form['color']
        codigo_unico = str(uuid.uuid4())
        nuevo_filamento = Filamento(marca_id=marca_id, tipo_id=tipo_id, color_id=color_id, codigo_unico=codigo_unico)
        db.session.add(nuevo_filamento)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html', marcas=marcas, tipos=tipos, colores=colores)

@app.route('/add_marca', methods=['GET', 'POST'])
def add_marca():
    if request.method == 'POST':
        nombre = request.form['nombre']
        nueva_marca = Marca(nombre=nombre)
        db.session.add(nueva_marca)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_marca.html')

@app.route('/add_tipo', methods=['GET', 'POST'])
def add_tipo():
    if request.method == 'POST':
        nombre = request.form['nombre']
        nuevo_tipo = Tipo(nombre=nombre)
        db.session.add(nuevo_tipo)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_tipo.html')

@app.route('/add_color', methods=['GET', 'POST'])
def add_color():
    if request.method == 'POST':
        nombre = request.form['nombre']
        nuevo_color = Color(nombre=nombre)
        db.session.add(nuevo_color)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_color.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_filamento(id):
    filamento = db.session.get(Filamento, id)
    marcas = Marca.query.all()
    tipos = Tipo.query.all()
    colores = Color.query.all()
    if not filamento:
        return redirect(url_for('index'))
    if request.method == 'POST':
        filamento.marca_id = request.form['marca']
        filamento.tipo_id = request.form['tipo']
        filamento.color_id = request.form['color']
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

if __name__ == '__main__':
    app.run(debug=True)
