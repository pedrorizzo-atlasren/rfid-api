# app/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


load_dotenv()   

DATABASE_URL = os.getenv('POSTGRES_URL')

# URL de conexão (puxe de uma variável de ambiente em produção)


# Cria a engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# Cada SessionLocal() gera uma nova sessão
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Classe base para todos os models
Base = declarative_base()

from models import product, item, logs


# Dependência para obter uma sessão e fechá-la ao final da requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
