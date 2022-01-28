from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

import db
from models import Cliente

# Mensajes para los errores en los formularios.
campo_obligatorio = DataRequired(message='El campo es obligatorio.')
campo_email = Email(message='Interoduce una dicreccion de correo electronico valida.')
campo_password = EqualTo('password', message='Las contraseñas no coinciden.')


class FormularioRegistro(FlaskForm):

    """ Clase que hereda de FlaskForm, y define el formulario de registro de clientes."""

    nombre = StringField('Nombre', validators=[campo_obligatorio], render_kw={"placeholder": "Nombre"})
    apellidos = StringField('Apellidos', validators=[campo_obligatorio], render_kw={"placeholder": "Apellidos"})
    usuario = StringField('Usuario', validators=[campo_obligatorio], render_kw={"placeholder": "Usuario"})
    telefono = IntegerField('Telefono', validators=[campo_obligatorio], render_kw={"placeholder": "Teléfono"})
    email = StringField('Email', validators=[campo_obligatorio, campo_email],
                        render_kw={"placeholder": "Correo Electrónico"})
    password = PasswordField('Contaseña', validators=[campo_obligatorio], render_kw={"placeholder": "Contraseña"})
    confirmar_password = PasswordField('Repetir Contaseña', validators=[campo_obligatorio, campo_password],
                                       render_kw={"placeholder": "Repetir Contraseña"})
    submit = SubmitField('Registar')

    # Metodos de la clase para validar usuario y email no esten ya registrados
    def validate_username(self, usuario):
        user = db.session.query(Cliente).filter_by(usuario=usuario.data).first()
        if user:
            raise ValidationError('El nombre de Usuario ya existe.')

    def validate_email(self, email):
        user = db.session.query(Cliente).filter_by(email=email.data).first()
        if user:
            raise ValidationError('El Correo Electronico ya existe.')


class FormularioIngreso(FlaskForm):

    """ Clase que hereda de FlaskForm, y define el formulario de ingreso para porveedores y clientes."""

    email = StringField('Email', validators=[campo_obligatorio, campo_email],
                        render_kw={"placeholder": "Correo Electrónico"})
    password = PasswordField('Contaseña', validators=[campo_obligatorio], render_kw={"placeholder": "Contraseña"})
    recordar = BooleanField('Recordar')
    submit = SubmitField('Ingresar')
