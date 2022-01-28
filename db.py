from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Creamos el engine, que nos conecta a nuestra base de datos.
engine = create_engine("sqlite:///database/minechi.db",
                       connect_args={'check_same_thread': False})

# Ahora creamos la sesion, lo que nos permite realizar operaciones dentro de nuesta BD.
Session = sessionmaker(bind=engine, expire_on_commit=False)
session = Session()
Base = declarative_base()
