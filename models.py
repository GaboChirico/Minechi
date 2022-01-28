import db
from datetime import date, timedelta
from sqlalchemy import Column, Integer, String, Boolean, REAL, ForeignKey, DATE, func, extract
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Usuario(UserMixin):

    """ Clase Usuario, padre de las clases Cliente y Proveedor.
    Hereda de la clase UserMixin del módulo flask-login, que nos permitira gestionar las sesiones.
    Se encuentra el constructor de los atributos en común de Cliete y Proveedor,
    Contiene las funciones que en funcion del tipo de Usuario (Admin, Proveedor o Cliente),
    nos devuelven los datos necesarios"""

    __tablename__ = 'usuario'
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String(25), unique=True, nullable=False)
    email = Column(String(60), unique=True, nullable=False)
    password = Column(String(25), nullable=False)
    avatar = Column(String(30), default='default.png')
    admin = Column(Boolean, default=False)
    telefono = Column(Integer)
    direccion = Column(String(100))
    ciudad = Column(String(50))
    pais = Column(String(50))

    def __init__(self, usuario, email, password, admin, telefono, direcccion, ciudad, pais):
        self.usuario = usuario
        self.email = email
        self.password = generate_password_hash(password)
        self.admin = admin
        self.telefono = telefono
        self.direccion = direcccion
        self.ciudad = ciudad
        self.pais = pais

    # Funciones de la documenmtacion Werkzeug
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    # Funcion que nos devuelve un booleano si el usuario es de la clase cliente.
    def cliente(self):
        return isinstance(self, Cliente)

    # Funcion que nos devuelve un booleano si el usuario es de la clase proveedor.
    def proveedor(self):
        return isinstance(self, Proveedor)

    # Nos devuelve la suma de todas las ventas netas.
    def ventas_totales(self):
        ventas = db.session.query(func.sum(Transaccion.total)).scalar()
        if ventas is None:
            return 0
        return ventas

    # Ganancia/Venta/Compra Mes del usuario.
    def transacciones_mes(self):
        mes = date.today().month
        if self.admin:  # Ganancias por mes (ADMIN)
            ganancias = db.session.query(func.sum(DetalleTransaccion.ganancia).filter(
                extract('month', DetalleTransaccion.fecha) == mes)).scalar()
            if ganancias is None:
                return 0.0
            return ganancias
        elif self.proveedor():  # Ventas por mes (PROVEEDOR)
            ventas_mes = 0.0
            for i in self.transaccion:
                if i.fecha.month == mes:
                    ventas_mes = ventas_mes + (i.subtotal - i.ganancia)
            return ventas_mes
        else:   # Compras por mes (CLIENTE)
            compras_mes = 0.0
            for i in self.transaccion:
                if i.fecha.month == mes:
                    compras_mes = compras_mes + i.total
            return compras_mes

    # Ganancia/Venta/Compra Total del usuario.
    def transacciones_total(self):
        if self.admin:  # Ganancias totales (ADMIN)
            ganancias = db.session.query(func.sum(DetalleTransaccion.ganancia)).scalar()
            if ganancias is None:
                return 0.0
            return ganancias
        elif self.proveedor():  # Ventas totales (PROVEEDOR)
            ventas = 0.0
            for i in self.transaccion:
                ventas = ventas + (i.subtotal - i.ganancia)
            return ventas
        else:   # Compras totales (CLIENTE)
            compras = 0.0
            for i in self.transaccion:
                compras = compras + i.total
            return compras

    # Ganancia/Venta/Compra Media del usuario.
    def transacciones_media(self):
        if self.admin:  # Ganancia media (ADMIN)
            transacciones = db.session.query(Transaccion).count()
            try:
                return self.transacciones_total() / transacciones
            except ZeroDivisionError:
                return 0.0
        elif self.proveedor():  # Venta media (PROVEEDOR)
            try:
                return self.transacciones_total() / len(self.transaccion)
            except ZeroDivisionError:
                return 0.0
        else:  # Compra media (CLIENTE)
            try:
                return self.transacciones_total() / len(self.transaccion)
            except ZeroDivisionError:
                return 0.0

    # Items Vendidos/Comprados.
    def transacciones_productos(self):
        if self.admin:  # Unidades Vendidas (ADMIN)
            items = db.session.query(func.sum(DetalleTransaccion.cantidad)).scalar()
            if items is None:
                return 0
            return items
        elif self.proveedor():  # Unidades Vendidas (PROVEEDOR)
            items = 0
            for i in self.transaccion:
                items = items + i.cantidad
            return items
        else:  # Unidades Compradas (CLIENTE)
            items = 0
            for x in self.transaccion:
                for i in x.detalle:
                    items = items + i.cantidad
            return items

    @property
    # Funcion que genera la lista de etiquetas MES-AÑO de la gráfica de barras.
    def etiquetas_grafica_meses(self):
        fecha_actual = date.today()
        ultimos_seis_meses = fecha_actual - timedelta(days=150)
        etiquetas = []
        for x in range(1, 7):
            etiquetas.append(ultimos_seis_meses.strftime('%B-%Y'))
            ultimos_seis_meses = ultimos_seis_meses + timedelta(days=30)
        return etiquetas

    # Funcion que genera la lista de valores (Ganancia/Ventas/Compras) la grafica de barras.
    def valores_grafica_meses(self):
        fecha_actual = date.today()
        ultimos_seis_meses = fecha_actual - timedelta(days=150)
        meses = []
        for x in range(1, 7):
            meses.append(ultimos_seis_meses.month)
            ultimos_seis_meses = ultimos_seis_meses + timedelta(days=30)
        if self.admin:  # Admin
            valores = []
            for mes in meses:
                total_mes = db.session.query(func.sum(DetalleTransaccion.ganancia)).filter(
                    extract('month', DetalleTransaccion.fecha) == mes).scalar()
                valores.append(total_mes)
            return valores
        elif self.proveedor():  # Proveedor
            valores = []
            for mes in meses:
                total_mes = db.session.query(
                    func.sum(DetalleTransaccion.subtotal - DetalleTransaccion.ganancia)).filter_by(
                    id_proveedor=self.id).filter(extract('month', DetalleTransaccion.fecha) == mes).scalar()
                valores.append(total_mes)
            return valores
        else:  # Cliente
            valores = []
            for mes in meses:
                total_mes = db.session.query(func.sum(Transaccion.total)).filter_by(id_cliente=self.id).filter(
                    extract('month', Transaccion.fecha) == mes).scalar()
                valores.append(total_mes)
            return valores

    # Funcion que nos devuelve una lista de productos en transacciones.
    def lista_productos_transaccion(self):
        if self.admin:  # Admin
            return db.session.query(Producto).all()
        elif self.proveedor():  # Proveedor
            return set(x.producto for x in self.transaccion)
        else:  # Cliente
            return set(x.producto for x in self.transaccion_detalles)

    # Genera una lista ordenada de productos en formato diccionario con cantidad y porcentaje.
    def productos_cantidades_porcentaje(self):
        if self.admin:  # Admin
            productos_vendidos_dict = []
            for producto in self.lista_productos_transaccion():
                cantidad = producto.veces_vendido()
                if self.transacciones_productos() == 0:
                    pass
                else:
                    productos_vendidos_dict.append({'producto': producto,
                                                    'cantidad': cantidad,
                                                    'porcentaje': (cantidad * 100) / self.transacciones_productos()})
            return sorted(productos_vendidos_dict, key=lambda d: d['cantidad'], reverse=True)
        elif self.proveedor():  # Proveedor
            productos_vendidos_dict = []
            for producto in self.lista_productos_transaccion():
                cantidad = db.session.query(func.sum(DetalleTransaccion.cantidad)).filter_by(
                    id_proveedor=self.id).filter(DetalleTransaccion.producto == producto).scalar()
                if self.transacciones_productos() == 0:
                    pass
                else:
                    productos_vendidos_dict.append({'producto': producto,
                                                    'cantidad': cantidad,
                                                    'porcentaje': (cantidad * 100) / self.transacciones_productos()})
            return sorted(productos_vendidos_dict, key=lambda d: d['cantidad'], reverse=True)
        else:   # Cliente
            productos_vendidos_dict = []
            for producto in self.lista_productos_transaccion():
                cantidad = db.session.query(func.sum(DetalleTransaccion.cantidad)).filter_by(
                    id_cliente=self.id).filter(DetalleTransaccion.producto == producto).scalar()
                if self.transacciones_productos() == 0:
                    pass
                else:
                    productos_vendidos_dict.append({'producto': producto,
                                                    'cantidad': cantidad,
                                                    'porcentaje': (cantidad * 100) / self.transacciones_productos()})
            return sorted(productos_vendidos_dict, key=lambda d: d['cantidad'], reverse=True)

    # Funcion calcula la ganancia segun el tipo de usuario, que se ha generado.
    def ganancia_generada(self):
        if self.admin:  # Ganancia total
            return self.transacciones_total()
        elif self.proveedor():  # Ganancias por Proveedor
            total = 0.0
            for item in self.transaccion:
                total = total + item.ganancia
            return total
        else:  # Ganancias por Cliente
            total = 0.0
            for item in self.transaccion_detalles:
                total = total + item.ganancia
            return total

    def __str__(self):
        return 'Usuario {}'.format(self.usuario)

    def __repr__(self):
        return 'Usuario {}'.format(self.usuario)


class Cliente(Usuario, db.Base):

    """ Clase Cliente que genera nuestra tabla cliente.
    Hereda de la clase Usuario los atributos necesarios para todos los usuarios.
    Contiene a diferencia de la clase proveedor, nombre, apellidos y la relacion con la clase Carrito """

    __tablename__ = 'cliente'
    nombre = Column(String(20), nullable=False)
    apellidos = Column(String(40), nullable=False)
    carrito = relationship('Carrito', lazy='subquery', backref='cliente')
    transaccion = relationship('Transaccion', lazy='subquery', backref='cliente')
    transaccion_detalles = relationship('DetalleTransaccion', lazy='subquery', backref='cliente')

    def __init__(self, usuario, email, password, admin, telefono,
                 direcccion, ciudad, pais, nombre, apellidos):
        super().__init__(usuario, email, password, admin, telefono, direcccion, ciudad, pais)
        self.nombre = nombre
        self.apellidos = apellidos

    # Funcion que nos devuelve la cantidad de items en el carrito.
    def items_carrito(self):
        total = 0
        for i in self.carrito:
            total = total + int(i.cantidad)
        return total

    # Funcion que nos devuelve el total del carrito del cliente.
    def total_carrito(self):
        total = 0.0
        for i in self.carrito:
            total = total + i.subtotal()
        return total


class Proveedor(Usuario, db.Base):

    """ Clase Proveedor que genera nuestra tabla proveedor.
    Hereda de la clase Usuario los atributos necesarios para todos los usuarios.
    Tiene los atributos, nombre de empresa, descuento y la relacion con la clase Producto """

    __tablename__ = 'proveedor'
    nombre_empresa = Column(String(50), nullable=False)
    descuento = Column(REAL, nullable=False)
    producto = relationship('Producto', lazy='subquery', backref='proveedor')
    transaccion = relationship('DetalleTransaccion', lazy='subquery', backref='proveedor')

    def __init__(self, usuario, email, password, admin, telefono,
                 direcccion, ciudad, pais, nombre_empresa, descuento):
        super().__init__(usuario, email, password, admin, telefono, direcccion, ciudad, pais)
        self.nombre_empresa = nombre_empresa
        self.descuento = descuento

    # Funcion que nos devuelve la cantidad de productos para reponer del proveedor.
    def productos_reponer(self):
        contador = 0
        for item in self.producto:
            if item.porcentaje_stock() <= 10:
                contador = contador + 1
        return contador


class Producto(db.Base):

    """ Clase Producto, genera nuestra tabla producto.
    Contiene las funciones para calcular datos de cada producto."""

    __tablename__ = 'producto'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(80), nullable=False)
    precio = Column(REAL, nullable=False)
    unidades_existentes = Column(Integer, nullable=False)
    capacidad_max = Column(Integer, nullable=False)
    id_proveedor = Column(Integer, ForeignKey('proveedor.id'))
    categoria = Column(String(40), nullable=False)
    imagen = Column(String(20), nullable=False)
    carrito = relationship('Carrito', lazy='subquery', backref='producto')
    transaccion = relationship('DetalleTransaccion', lazy='subquery', backref='producto')

    def __init__(self, nombre, precio, unidades_existentes, capacidad_max, proveedor, categoria, imagen):
        self.nombre = nombre
        self.precio = precio
        self.unidades_existentes = unidades_existentes
        self.capacidad_max = capacidad_max
        self.proveedor = proveedor
        self.categoria = categoria
        self.imagen = imagen

    # Devuelve la ganancia del producto.
    def ganancia(self):
        return self.precio * self.proveedor.descuento

    # Devuelve cuantas veces ha sido vendido/comprado un producto.
    def veces_vendido(self):
        vendidos = 0
        for i in self.transaccion:
            vendidos = vendidos + i.cantidad
        return vendidos

    # Devuelve el porcentaje de ventas, en funcion del usuario, de un producto.
    def porcentaje_ventas(self):
        try:
            return (self.veces_vendido() * 100) / self.proveedor.transacciones_productos()
        except ZeroDivisionError:
            return 0.0

    # Devuelve el porcentaje de stock segun su capacidad maxima.
    def porcentaje_stock(self):
        return (self.unidades_existentes * 100) / self.capacidad_max

    def ganancia_generada(self):
        gg = 0.0
        for d in self.transaccion:
            gg = gg + (d.producto.precio * d.cantidad) * self.proveedor.descuento
        return gg

    def __str__(self):
        return '{} - {:.2f}€'.format(self.nombre, self.precio)

    def __repr__(self):
        return '{} - {:.2f}€'.format(self.nombre, self.precio)


class Carrito(db.Base):

    """ Clase Carrito genera la tabla carrito.
    Esta clase está vinculada a la tabla cliente, y contiene todos los items del cliente en el carrito."""

    __tablename__ = 'carrito'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(Integer, ForeignKey('cliente.id'), nullable=False)
    id_producto = Column(Integer, ForeignKey('producto.id'), nullable=False)
    cantidad = Column(Integer, nullable=False)

    def __init__(self, id_cliente, id_producto, cantidad):
        self.id_cliente = id_cliente
        self.id_producto = id_producto
        self.cantidad = cantidad

    # Funcion que nos devuelve el subtotal del registro del carrito.
    def subtotal(self):
        total = float(self.producto.precio) * int(self.cantidad)
        return total

    # Funcion que nos devuelve la ganancia del registro del carrito.
    def ganancia(self):
        ganancia = self.producto.ganancia() * int(self.cantidad)
        return ganancia

    def __str__(self):
        return 'Producto: {} - Cantidad: {}'.format(self.id_producto, self.cantidad)

    def __repr__(self):
        return 'Producto: {} - Cantidad: {}'.format(self.id_producto, self.cantidad)


class Transaccion(db.Base):

    """ Clase Transaccion, genera la tabla transaccion.
    Genera las transacciones realizadas por los usuarios.
    Está relacionada con los clientes y con la tabla DetalleTransaccion."""

    __tablename__ = 'transaccion'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(Integer, ForeignKey('cliente.id'))
    total = Column(REAL, nullable=False)
    fecha = Column(DATE, nullable=False)
    detalle = relationship('DetalleTransaccion', lazy='subquery', backref='transaccion')

    def __init__(self, id_cliente, total, fecha):
        self.id_cliente = id_cliente
        self.total = total
        self.fecha = fecha

    # Devuele la ganancia de cada transaccion.
    def ganancia_transaccion(self):
        ganancia = 0.0
        for item in self.detalle:
            ganancia = ganancia + float(item.ganancia)
        return ganancia

    def __repr__(self):
        return 'Transaccion {} - Total {} - Fecha: {}'.format(self.id, self.total, self.fecha)

    def __str__(self):
        return 'Transaccion {} - Total {} - Fecha: {}'.format(self.id, self.total, self.fecha)


class DetalleTransaccion(db.Base):

    """ Clase DetalleTransaccion genera la tabla transaccion_detalle.
    Esta clase recopila los productos, cantidades, subtotal de cada registro de la tabla transaccion.
    Está relacionado con la tabla transaccion, cliente, proveedor y producto."""

    __tablename__ = 'transaccion_detalle'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_transaccion = Column(Integer, ForeignKey('transaccion.id'))
    id_cliente = Column(Integer, ForeignKey('cliente.id'))
    id_producto = Column(Integer, ForeignKey('producto.id'))
    id_proveedor = Column(Integer, ForeignKey('proveedor.id'))
    cantidad = Column(Integer, nullable=False)
    subtotal = Column(REAL, nullable=False)
    ganancia = Column(REAL, nullable=False)
    fecha = Column(DATE, nullable=False)

    def __init__(self, id_transaccion, id_cliente, id_proveedor, id_producto, cantidad, subtotal, ganancia, fecha):
        self.id_transaccion = id_transaccion
        self.id_cliente = id_cliente
        self.id_proveedor = id_proveedor
        self.id_producto = id_producto
        self.cantidad = cantidad
        self.subtotal = subtotal
        self.ganancia = ganancia
        self.fecha = fecha

    def __repr__(self):
        return '''Detalle de Transaccion {} - Total {} - Fecha: {}/{}/{}:
                    -Producto: {}
                    -Cantidad: {}
                    -Subtotal: {}
                  * Cliente: {}'''.format(self.id_transaccion, self.transaccion.total, self.fecha.day,
                                          self.fecha.month, self.fecha.year, self.producto.nombre,
                                          self.cantidad, self.subtotal, self.cliente.usuario)

    def __str__(self):
        return '''Detalle de Transaccion {} - Total {} - Fecha: {}/{}/{}:
                    -Producto: {}
                    -Cantidad: {}
                    -Subtotal: {}
                  * Cliente: {}'''.format(self.id_transaccion, self.transaccion.total, self.fecha.day,
                                          self.fecha.month, self.fecha.year, self.producto.nombre,
                                          self.cantidad, self.subtotal, self.cliente.usuario)


class Tarea(db.Base):

    """ Clase Tarea genera la tabla tarea.
    Guarda las tareas de los usuarios en el dashboard."""

    __tablename__ = "tarea"
    id = Column(Integer, primary_key=True)
    id_usuario = Column(Integer)
    contenido = Column(String(200), nullable=False)
    hecha = Column(Boolean)

    def __init__(self, id_usuario, contenido, hecha):
        self.id_usuario = id_usuario
        self.contenido = contenido
        self.hecha = hecha

    def __repr__(self):
        return "Tarea {}: {} ({})".format(self.id, self.contenido, self.hecha)

    def __str__(self):
        return "Tarea {}: {} ({})".format(self.id, self.contenido, self.hecha)
