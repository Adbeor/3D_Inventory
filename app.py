from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
import qrcode
import os
import tempfile
from datetime import date
from datetime import datetime
from sqlalchemy import Enum
import cairo

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///filamentos.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


class Marca(db.Model):
    __tablename__ = "marcas"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    def __init__(self, nombre):
        self.nombre = nombre


class Tipo(db.Model):
    __tablename__ = "tipos"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    def __init__(self, nombre):
        self.nombre = nombre


class Color(db.Model):
    __tablename__ = "colores"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)  # Nombre del color
    hex_color = db.Column(
        db.String(7), unique=True, nullable=False
    )  # Valor hexadecimal (ej. #FF5733)
    silk = db.Column(db.Boolean, default=False)

    def __init__(self, nombre, hex_color, silk=False):
        self.nombre = nombre
        self.hex_color = hex_color
        self.silk = silk


class Filamento(db.Model):
    __tablename__ = "filamentos"
    id = db.Column(db.Integer, primary_key=True)
    marca_id = db.Column(db.Integer, db.ForeignKey("marcas.id"), nullable=False)
    tipo_id = db.Column(db.Integer, db.ForeignKey("tipos.id"), nullable=False)
    color_id = db.Column(db.Integer, db.ForeignKey("colores.id"), nullable=False)
    codigo_unico = db.Column(db.String(20), unique=True, nullable=False)

    marca = db.relationship("Marca", backref="filamentos")
    tipo = db.relationship("Tipo", backref="filamentos")
    color = db.relationship("Color", backref="filamentos")
    peso_spool = db.Column(db.Float)
    peso_actual = db.Column(db.Float)
    fecha_apertura = db.Column(db.Date, default=date.today, nullable=False)
    estado = db.Column(
        Enum("Nuevo", "En uso", "Agotado", name="estado_enum"),
        default="Nuevo",
        nullable=False,
    )

    def __init__(
        self,
        marca_id,
        tipo_id,
        color_id,
        codigo_unico,
        peso_spool=0.0,
        peso_actual=0.0,
        fecha_apertura=None,
        estado="Nuevo",
    ):
        self.marca_id = marca_id
        self.tipo_id = tipo_id
        self.color_id = color_id
        self.codigo_unico = codigo_unico
        self.peso_spool = peso_spool
        self.peso_actual = peso_actual
        self.fecha_apertura = fecha_apertura if fecha_apertura else date.today()
        self.estado = estado


with app.app_context():
    db.create_all()


# Para generar un código único más corto
def generar_codigo_unico():
    filamentos_count = Filamento.query.count()
    return f"F{filamentos_count + 1:04d}"


@app.route("/")
def index():
    filamentos = db.session.query(Filamento).all()
    marcas = Marca.query.all()
    tipos = Tipo.query.all()
    fecha_hoy = date.today()
    return render_template(
        "index.html",
        filamentos=filamentos,
        fecha_hoy=fecha_hoy,
        marcas=marcas,
        tipos=tipos,
    )


@app.route("/add", methods=["GET", "POST"])
def add_filamento():
    marcas = Marca.query.all()
    tipos = Tipo.query.all()
    colores = Color.query.all()
    if request.method == "POST":
        marca_id = request.form["marca"]
        tipo_id = request.form["tipo"]
        color_id = request.form["color"]
        peso_spool = request.form["peso_spool"]
        peso_actual = request.form["peso_actual"]
        fecha_str = request.form["fecha_compra"]
        fecha_apertura = datetime.strptime(
            fecha_str, "%Y-%m-%d"
        ).date()  # Convierte a tipo date
        estado = request.form["estado"]
        codigo_unico = generar_codigo_unico()
        nuevo_filamento = Filamento(
            marca_id=marca_id,
            tipo_id=tipo_id,
            color_id=color_id,
            codigo_unico=codigo_unico,
            peso_spool=float(peso_spool),
            fecha_apertura=fecha_apertura,
            peso_actual=float(peso_actual),
            estado=estado,
        )
        db.session.add(nuevo_filamento)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template(
        "add_filament.html", marcas=marcas, tipos=tipos, colores=colores
    )


@app.route("/generate_qr_pdf")
def generate_qr_pdf():
    # Crear PDF con Cairo
    filamentos = db.session.query(Filamento).all()
    file_path = "qrs_filamentos.pdf"
    qr_size = 100  # Tamaño del QR (más pequeño)
    # Configurar el tamaño de la página
    width, height = 612, 792  # Tamaño carta (letter) en puntos (72 puntos por pulgada)
    surface = cairo.PDFSurface(file_path, width, height)
    ctx = cairo.Context(surface)

    y_position = 20  # Posición inicial para los QR

    for filamento in filamentos:
        qr_data = filamento.codigo_unico
        qr_img = qrcode.make(qr_data)

        # Determinar posición y salto según el código único
        if int(filamento.codigo_unico[-1]) % 2 == 0:
            x_position = 210
            salto = 100
        else:
            x_position = 10
            salto = 0

        # Guardar la imagen del QR en un archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_qr_file:
            qr_img.save(temp_qr_file)
            temp_qr_file_path = temp_qr_file.name

        # Cargar e insertar la imagen del QR en el PDF con tamaño reducido
        qr_surface = cairo.ImageSurface.create_from_png(temp_qr_file_path)
        qr_width = qr_surface.get_width()
        qr_height = qr_surface.get_height()

        # Escalar el QR para que tenga el tamaño deseado
        scale_x = qr_size / qr_width
        scale_y = qr_size / qr_height
        ctx.save()  # Guardar el estado del contexto
        ctx.translate(x_position, y_position)  # Mover a la posición deseada
        ctx.scale(scale_x, scale_y)  # Escalar el QR
        ctx.set_source_surface(qr_surface, 0, 0)
        ctx.paint()
        ctx.restore()  # Restaurar el estado original del contexto

        # Dibujar texto
        ctx.set_source_rgb(0, 0, 0)  # Color negro
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(10)
        ctx.move_to(x_position + 10, y_position + 100)
        ctx.show_text(
            f"{filamento.codigo_unico} - {filamento.marca.nombre} - {filamento.color.nombre}"
        )

        hex_color = filamento.color.hex_color
        rgb_color = hex_to_rgb(hex_color)
        print("----------------")
        print(rgb_color)

        # Crear un rectángulo con degradado si silk es True
        if filamento.color.silk:
            gradient = cairo.LinearGradient(
                x_position + 60,
                y_position + 14.5,
                x_position + 75 + 71,
                y_position + 14.5 + 71,
            )
            gradient.add_color_stop_rgb(
                0.8, rgb_color[0] / 255, rgb_color[1] / 255, rgb_color[2] / 255
            )  # Azul
            gradient.add_color_stop_rgb(0, 1, 1, 1)  # Blanco
            ctx.set_source(gradient)
        else:
            ctx.set_source_rgb(
                rgb_color[0] / 255, rgb_color[1] / 255, rgb_color[2] / 255
            )  # Negro sólido

        ctx.rectangle(x_position + 100, y_position + 14.5, 15, 71)
        ctx.fill()

        y_position += salto  # Mover hacia abajo para el siguiente QR

        if y_position > 600:
            surface.show_page()  # Crear una nueva página si se acaba el espacio
            y_position = 20  # Restablecer la posición

        # Eliminar el archivo temporal después de usarlo
        os.remove(temp_qr_file_path)

    surface.finish()  # Finalizar el PDF

    return redirect(url_for("download_pdf", filename=file_path))


@app.route("/download_pdf/<filename>")
def download_pdf(filename):
    return send_from_directory(os.getcwd(), filename)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_filamento(id):
    filamento = db.session.get(Filamento, id)
    if not filamento:
        return redirect(url_for("index"))
    if request.method == "POST":
        filamento.estado = request.form["estado"]
        filamento.peso_actual = request.form["peso_actual"]
        filamento.peso_spool = request.form["peso_spool"]
        fecha_str = request.form["fecha_apertura"]
        filamento.fecha_apertura = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("edit.html", filamento=filamento)


@app.route("/job/<int:id>", methods=["GET", "POST"])
def job_filament(id):
    filamento = db.session.get(Filamento, id)
    if not filamento:
        return redirect(url_for("index"))
    if request.method == "POST":
        peso_neto = filamento.peso_actual - filamento.peso_spool
        g_pieza = request.form["g_pieza"]
        n_piezas = request.form["n_piezas"]
        g_total = float(g_pieza) * float(n_piezas)
        print("gramos total: ", g_total)
        print("gramos finales: ", filamento.peso_actual - g_total)
        if peso_neto - g_total >= 0:
            filamento.peso_actual = filamento.peso_actual - g_total
        peso_neto = filamento.peso_actual - filamento.peso_spool
        if peso_neto == 0:
            filamento.estado = "Agotado"
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("job.html", filamento=filamento)


@app.route("/job_mini/<int:id>", methods=["GET", "POST"])
def job_mini(id):
    filamento = db.session.get(Filamento, id)
    if not filamento:
        return redirect(url_for("index"))
    if request.method == "POST":
        peso_neto = filamento.peso_actual - filamento.peso_spool
        g_pieza = request.form["g_pieza"]
        n_piezas = request.form["n_piezas"]
        g_total = float(g_pieza) * float(n_piezas)
        if peso_neto - g_total > 0:
            filamento.peso_actual = filamento.peso_actual - g_total
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("job2.html", filamento=filamento)


@app.route("/delete/<int:id>")
def delete_filamento(id):
    filamento = db.session.get(Filamento, id)
    if filamento:
        db.session.delete(filamento)
        db.session.commit()
    return redirect(url_for("index"))


@app.route("/add_marca", methods=["GET", "POST"])
def add_marca():
    marcas = Marca.query.all()
    if request.method == "POST":
        nombre = request.form["nombre"]
        nueva_marca = Marca(nombre=nombre)
        db.session.add(nueva_marca)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("add_marca.html", marcas=marcas)


@app.route("/add_tipo", methods=["GET", "POST"])
def add_tipo():
    tipos = Tipo.query.all()
    if request.method == "POST":
        nombre = request.form["nombre"]
        nuevo_tipo = Tipo(nombre=nombre)
        db.session.add(nuevo_tipo)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("add_tipo.html", tipos=tipos)


@app.route("/add_color", methods=["GET", "POST"])
def add_color():
    if request.method == "POST":
        nombre = request.form["nombre"]  # El nombre del color
        hex_color = request.form["hex_color"]  # El valor hexadecimal del color
        try:
            silk = request.form["silk"] == "on"
        except:
            silk = False
        print(type(silk))
        print(silk)
        nuevo_color = Color(nombre=nombre, hex_color=hex_color, silk=silk)
        db.session.add(nuevo_color)
        db.session.commit()
        return redirect(url_for("add_color"))
    colores = Color.query.all()
    return render_template("add_color.html", colores=colores)


@app.route("/test")
def test():
    filamentos = db.session.query(Filamento).all()
    fecha_hoy = date.today()
    return render_template("pruebas.html", filamentos=filamentos, fecha_hoy=fecha_hoy)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
