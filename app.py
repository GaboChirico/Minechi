from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename

import db
import os
from datetime import date
import locale
from forms import FormularioIngreso, FormularioRegistro
from models import Cliente, Proveedor, Producto, Carrito, Transaccion, DetalleTransaccion, Tarea

# Configuramos locale en Español-España
locale.setlocale(locale.LC_ALL, 'es_ES')

# Ruta para el almacenamiento de avatar de los usuarios.
UPLOAD_FOLDER = 'static/img/avatars'
# Almacena las extenciones de archivos que aceptamos.
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask('Minechi')   # En app se encuentra nuestro servidor web de Flask
# SECRET_KEY de la sesion generada con "secrets.token_hex()" gracias al modulo secrets.
app.config['SECRET_KEY'] = "6950250d718d29564e35674b10c6ee3d1e657b70d3dda7a24034e5d482ecdaa5"
# Configuramos la carpeta donde se almacenan los avatars.
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Establecemos login_manager, extension de Flask en gestion de usuarios.
login_manager = LoginManager(app)
# La página que carga cuando se intenta acceder a una página que necesita sesión de usuario.
login_manager.login_view = "ingreso"
# Mensaje y categoria que necesita inciar sesión para acceder a la página en concreto.
login_manager.login_message = "Para acceder debe de iniciar cesion"
login_manager.login_message_category = "danger"


def archivos_permitidos(archivo):
    """ Función de la documentacion Flask, para determinar si la extension del archivo subido por el usuario está
    dentro de las extensiones permitidas."""
    return '.' in archivo and \
           archivo.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def db_guardar():
    """ Función para guardar registros en nuestra base de datos.
        Controlando errores en SQLAlchemy haciendo rollback()"""
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(str(e), 'danger')
    finally:
        db.session.close()


def get_producto(id_producto):
    """ Función para obtener un producto por su id """
    return db.session.query(Producto).filter_by(id=id_producto).first()


def set_passwords():
    """ Función para designar las contraseńas de los usuarios y esten encriptadas """
    for usuario in (db.session.query(Cliente).all() + db.session.query(Proveedor).all()):
        if usuario.admin:
            usuario.set_password("admin")
        else:
            usuario.set_password("minechi")
    db_guardar()


@login_manager.user_loader
def load_user(id_usuario):
    """ Función del módulo flask_login, para determinar el usuario en sesión. """
    clientes = db.session.query(Cliente).all()
    proveedores = db.session.query(Proveedor).all()
    for usuario in clientes + proveedores:
        if usuario.id == int(id_usuario):
            return usuario
    return None


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(404)
def pagina_no_encontrada(e):
    if current_user.is_authenticated:
        sesion = True
    else:
        sesion = False
    return render_template('404.html', sesion=sesion, usuario=current_user), 404


@app.route('/ingreso', methods=['GET', 'POST'])
def ingreso():
    # Si el usuario sigue en sesión gracias a flask_login
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    # Formulario de Ingreso, que creamos con la libreria flask_wtf (Formularios).
    form = FormularioIngreso()
    # Validacion del formulario, ingresando o mostrando errores.
    if form.validate_on_submit():
        usuario = db.session.query(Cliente).filter_by(email=form.email.data).first()
        if usuario is not None and usuario.check_password(form.password.data):
            login_user(usuario, remember=form.recordar.data)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('dashboard')
            return redirect(next_page)
        else:
            flash('Usuario/Contraseña son incorrectos.', 'danger')
    return render_template('ingreso.html', form=form)


@app.route('/ingreso_proveedor', methods=['GET', 'POST'])
def ingreso_proveedor():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = FormularioIngreso()
    if form.validate_on_submit():
        usuario = db.session.query(Proveedor).filter_by(email=form.email.data).first()
        if usuario is not None and usuario.check_password(form.password.data):
            login_user(usuario, remember=form.recordar.data)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('dashboard')
            return redirect(next_page)
        else:
            flash('Usuario/Contraseña son incorrectos.', 'danger')
    return render_template('ingreso_proveedor.html', form=form)


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    # Formulario de Registro, que creamos con la libreria flask_wtf (Formularios).
    form = FormularioRegistro()
    # Validacion del formulario, creando cuenta o mostrando errores.
    if form.validate_on_submit():
        # Creamos el nuevo usuario usando la información del formulario al constructor de la clase.
        nuevo_cliente = Cliente(nombre=form.nombre.data,
                                apellidos=form.apellidos.data,
                                usuario=form.usuario.data,
                                telefono=form.telefono.data,
                                email=form.email.data,
                                password=form.password.data,
                                admin=False, direcccion='', ciudad='', pais='')
        db.session.add(nuevo_cliente)
        db.session.commit()
        # Creamos una tarea de completar datos del perfil al nuevo ususario.
        tarea = Tarea(id_usuario=nuevo_cliente.id,
                      contenido='Completar datos del perfil',
                      hecha=False)
        db.session.add(tarea)
        db_guardar()
        flash('Registro Exitoso!', 'success')
        return redirect(url_for('index'))
    return render_template('registro.html', form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route("/dashboard")
@login_required
def dashboard():
    # Cargamos las tareas del ususario
    tareas = db.session.query(Tarea).filter_by(id_usuario=current_user.id).all()
    return render_template('dashboard.html', usuario=current_user, tareas=tareas)


@app.route('/dashboard/crear_tarea', methods=['POST'])
def crear_tarea():
    tarea = Tarea(id_usuario=current_user.id,
                  contenido=request.form['contenido_tarea'],
                  hecha=False)
    db.session.add(tarea)
    db_guardar()
    return redirect(url_for('dashboard'))


@app.route('/dashboard/eliminar_tarea/<id_tarea>')
def eliminar_tarea(id_tarea):
    tarea = db.session.query(Tarea).filter_by(id=int(id_tarea)).first()
    flash(f'Tarea: "{tarea.contenido}" eliminada', 'info')
    db.session.query(Tarea).filter_by(id=int(id_tarea)).delete()
    db_guardar()
    return redirect(url_for('dashboard'))


@app.route('/dashboard/tarea_hecha/<id_tarea>')
def tarea_hecha(id_tarea):
    tarea = db.session.query(Tarea).filter_by(id=int(id_tarea)).first()
    tarea.hecha = not tarea.hecha
    db_guardar()
    return redirect(url_for('dashboard'))


@app.route("/perfil", methods=['GET', 'POST'])
@login_required
def perfil():
    # Cargamos al usuario segun si es proveedor o cliente
    if current_user.proveedor():
        usuario = db.session.query(Proveedor).filter_by(id=current_user.id).first()
    else:
        usuario = db.session.query(Cliente).filter_by(id=current_user.id).first()
    if request.method == 'POST':
        if request.form['btn'] == 'avatar':   # Cambio de Avatar (La funcion es de la documentación de Flask)
            file = request.files['file']
            if file.filename == '':
                flash('ERROR: Seleccione un archivo.', 'danger')
                return redirect(url_for('perfil'))
            if file and archivos_permitidos(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # Cambiamos el avatar del usuario y guardamos.
                usuario.avatar = filename
                db.session.commit()
                flash('Avatar cambiado exitosamente.', 'success')
            else:
                flash("ERROR: Seleccione un archivo 'png', 'jpg', 'jpeg'", 'danger')
                return redirect(url_for('perfil'))
        if request.form['btn'] == 'datos':  # Cambio de datos del usuario.
            # Cambio Nombre de Empresa
            if not request.form.get('nombre_empresa'):
                pass
            else:
                usuario.nombre_empresa = request.form.get('nombre_empresa')
            # Cambio Nombre
            if not request.form.get('nombre'):
                pass
            else:
                usuario.nombre = request.form.get('nombre')
            # Cambio Apellidos
            if not request.form.get('apellidos'):
                pass
            else:
                usuario.apellidos = request.form.get('apellidos')
            # Cambio Correo Electronico
            if not request.form.get('email'):
                pass
            else:
                usuario.email = request.form.get('email')
            # Cambio Telefono
            if not request.form.get('telefono'):
                pass
            else:
                usuario.telefono = request.form.get('telefono')
            # Cambio Direccion
            if not request.form.get('direccion'):
                pass
            else:
                usuario.direccion = request.form.get('direccion')
            # Cambio Ciudad
            if not request.form.get('ciudad'):
                pass
            else:
                usuario.ciudad = request.form.get('ciudad')
            # Cambio Pais
            if not request.form.get('pais'):
                pass
            else:
                usuario.pais = request.form.get('pais')
            db.session.commit()
            flash('Cambios guardados exitosamente.', 'success')
    db_guardar()
    return render_template('perfil.html', usuario=current_user)


@app.route("/perfil/restablecer_passwords")
def restablecer_passwords():
    set_passwords()
    flash('Las Contraseñas se han reiniciado', 'info')
    return redirect(url_for('perfil'))


@app.route("/perfil/eliminar_transacciones")
def eliminar_transacciones():
    db.session.query(Transaccion).delete()
    db.session.query(DetalleTransaccion).delete()
    db_guardar()
    flash('Se han eliminado las Transacciones y sus Detalles', 'info')
    return redirect(url_for('perfil'))


@app.route("/productos", methods=['POST', 'GET'])
@login_required
def productos():
    # Buscador
    buscar = request.args.get('buscar')
    if buscar:
        if current_user.proveedor():
            lista_productos = db.session.query(Producto).filter_by(id_proveedor=current_user.id).filter(
                Producto.nombre.contains(buscar) | Producto.categoria.contains(buscar)).all()
            flash(f'Busqueda por "{buscar}". Resultados {len(lista_productos)}.', 'info')
        else:
            lista_productos = db.session.query(Producto).filter(Producto.nombre.contains(buscar)
                                                                | Producto.categoria.contains(buscar)).all()
            flash(f'Busqueda por "{buscar}". Resultados {len(lista_productos)}.', 'info')
    else:
        # Lista de productos segun el tipo de usuario.
        if current_user.proveedor():
            lista_productos = db.session.query(Producto).filter_by(id_proveedor=current_user.id).all()
        else:
            lista_productos = db.session.query(Producto).all()
    # Agregar productos al carrito.
    if request.method == 'POST':
        id_producto = request.form.get('agregar')
        cantidad = request.form[f'{id_producto}']
        producto = get_producto(id_producto)
        if producto.unidades_existentes == 0:
            # Si el producto no tiene unidades existentes.
            flash(f'Producto: "{producto.nombre}" está agotado.', 'danger')
        elif db.session.query(Carrito).filter_by(id_cliente=current_user.id, id_producto=id_producto).count() > 0:
            # Si el item ya está en el carrito, agregamos las cantidades a ese registro.
            item = db.session.query(Carrito).filter_by(id_cliente=current_user.id, id_producto=id_producto).first()
            item.cantidad = item.cantidad + int(cantidad)
            # Restamos las unidades del stock.
            producto.unidades_existentes = producto.unidades_existentes - int(cantidad)
            db.session.commit()
            flash(f'Producto: "{producto.nombre}" agregado exitosamente. Cantidad: {cantidad}', 'success')
        else:
            # Agregamos el producto al carrito con sus cantidades, este objeto estara relacionado con el cliente.
            agregar_carrito = Carrito(id_cliente=current_user.id,
                                      id_producto=id_producto,
                                      cantidad=cantidad)
            # Restamos las unidades del stock.
            producto.unidades_existentes = producto.unidades_existentes - int(cantidad)
            db.session.add(agregar_carrito)
            db.session.commit()
            flash(f'Producto: "{producto.nombre}" fue agregado exitosamente. Cantidad: {cantidad}', 'success')
        return redirect(url_for('productos'))
    return render_template('productos.html', usuario=current_user, lista_productos=lista_productos)


@app.route("/productos/rellenar_stock")
def rellenar_stock():
    for producto in db.session.query(Producto).all():
        producto.unidades_existentes = int(producto.capacidad_max)
    db_guardar()
    flash('El Stock de los productos esta al maximo.', 'info')
    return redirect(url_for('productos'))


@app.route("/productos/vaciar_stock")
def vaciar_stock():
    for producto in db.session.query(Producto).all():
        producto.unidades_existentes = 0
    db_guardar()
    flash('El Stock de los productos esta al minimo.', 'info')
    return redirect(url_for('productos'))


@app.route("/carrito", methods=['POST', 'GET'])
@login_required
def carrito():
    # Solo tiene acceso los usuarios de la clase Cliente.
    if not current_user.cliente():
        return redirect(url_for('dashboard'))
    else:
        if request.method == 'POST':
            # Al confirmar el carrito generamos el objeto de la clase Transaccion.
            transaccion = Transaccion(id_cliente=current_user.id,
                                      total=current_user.total_carrito(),
                                      fecha=date.today())
            db.session.add(transaccion)
            db.session.commit()
            # Por cada Producto en el carrito, generamos un objeto de la clase DetalleTransaccion, que esta ralacionada
            # a la tabla 'transaccion', que desglosa los productos, cantidades, subtotal, ganancia de la Transaccion.
            for item in current_user.carrito:
                detalles = DetalleTransaccion(id_transaccion=transaccion.id,
                                              id_cliente=current_user.id,
                                              id_proveedor=item.producto.proveedor.id,
                                              id_producto=item.producto.id,
                                              cantidad=item.cantidad,
                                              subtotal=item.subtotal(),
                                              ganancia=item.ganancia(),
                                              fecha=date.today())
                db.session.add(detalles)
                del detalles
            # Al procesar el carrito, eliminamos todos los registros del carrito, vaciandolo.
            db.session.query(Carrito).filter_by(id_cliente=current_user.id).delete()
            db_guardar()
            flash('Compra exitosa! Muchas Gracias!', 'success')
            return redirect(url_for('carrito'))
    return render_template('carrito.html', usuario=current_user)


@app.route("/carrito/eliminar/<id_producto>")
@login_required
def eliminar_carrito(id_producto):
    item_carrito = db.session.query(Carrito).filter_by(id=int(id_producto)).first()
    # Al eliminar el producto del carrito, devolvemos las cantidades al su atributo unidades_existentes
    item_carrito.producto.unidades_existentes = item_carrito.producto.unidades_existentes + item_carrito.cantidad
    db.session.query(Carrito).filter_by(id=int(id_producto)).delete()
    db_guardar()
    flash(f'Producto: "{item_carrito.producto.nombre}" - Cantidad: {item_carrito.cantidad}, ha sido eliminado '
          f'exitosamente', 'success')
    return redirect(url_for('carrito'))


@app.route("/reponer", methods=['POST', 'GET'])
@login_required
def reponer():
    # Solo tiene acceso los usuarios de la clase Proveedor.
    if not current_user.proveedor():
        return redirect(url_for('dashboard'))
    else:
        if request.method == 'POST':
            id_productos = request.form.getlist("producto")
            for i in id_productos:
                print(request.form[f'{i}'])
                producto = get_producto(i)
                if int(request.form[f'{i}']) == 0:
                    flash(f'Seleccione una cantidad para reponer el producto {producto.nombre}', 'danger')
                else:
                    # Realizamos la reposicion del producto, agregando las cantidades del formulario.
                    producto.unidades_existentes = producto.unidades_existentes + int(request.form[f'{i}'])
                    db_guardar()
                    flash(f'Reposición: {producto.nombre}, Cantidad: {request.form[i]}. Muchas Gracias!', 'success')
            return redirect(url_for('reponer'))
    return render_template('reponer.html', usuario=current_user)


@app.route("/usuarios")
@login_required
def usuarios():
    # Solo tiene acceso el usuario Administrador.
    if not current_user.admin:
        return redirect(url_for('dashboard'))
    else:
        clientes = db.session.query(Cliente).all()
        proveedores = db.session.query(Proveedor).all()
        transacciones = db.session.query(Transaccion).all()
        return render_template('usuarios.html', usuario=current_user, clientes=clientes,
                               proveedores=proveedores, transacciones=transacciones)


@app.route("/historial")
@login_required
def historial():
    transacciones = db.session.query(Transaccion).all()
    return render_template('historial.html', usuario=current_user, transacciones=transacciones)


if __name__ == '__main__':
    # Inicializamos la base de datos, si esta no existe.
    db.Base.metadata.create_all(db.engine)

    # OPCIONES DEBUG
    # set_passwords()

    # Ejecutamos nuestra app.
    app.run(debug=True)
