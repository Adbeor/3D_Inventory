from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///filamentos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Crear la instancia de la base de datos
db = SQLAlchemy(app)

# Declaración base usando SQLAlchemy 3.x
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Filamento(Base):
    __tablename__ = 'filamentos'
    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(30), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    codigo_unico = db.Column(db.String(100), unique=True, nullable=False)

# Crear las tablas al iniciar la aplicación
with app.app_context():
    Base.metadata.create_all(db.engine)

@app.route('/')
def index():
    filamentos = db.session.query(Filamento).all()
    return render_template('index.html', filamentos=filamentos)

@app.route('/add', methods=['GET', 'POST'])
def add_filamento():
    if request.method == 'POST':
        marca = request.form['marca']
        color = request.form['color']
        tipo = request.form['tipo']
        codigo_unico = str(uuid.uuid4())
        nuevo_filamento = Filamento(marca=marca, color=color, tipo=tipo, codigo_unico=codigo_unico)
        db.session.add(nuevo_filamento)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_filamento(id):
    filamento = db.session.get(Filamento, id)
    if not filamento:
        return redirect(url_for('index'))
    if request.method == 'POST':
        filamento.marca = request.form['marca']
        filamento.color = request.form['color']
        filamento.tipo = request.form['tipo']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', filamento=filamento)

@app.route('/delete/<int:id>')
def delete_filamento(id):
    filamento = db.session.get(Filamento, id)
    if filamento:
        db.session.delete(filamento)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
