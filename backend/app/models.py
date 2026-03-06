from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Celda(Base):
    __tablename__ = "celdas"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(10), unique=True, nullable=False, index=True)
    estado = Column(String(20), nullable=False, default="DISPONIBLE")  # DISPONIBLE/OCUPADA/DESHABILITADA
    movimientos = relationship("Movimiento", back_populates="celda")

class Operador(Base):
    __tablename__ = "operadores"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    rol = Column(String(20), nullable=False, default="OPERADOR")  # OPERADOR/ADMIN

class Movimiento(Base):
    __tablename__ = "movimientos"
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(10), nullable=False, index=True)
    tipo_vehiculo = Column(String(30), nullable=False)

    celda_id = Column(Integer, ForeignKey("celdas.id"), nullable=False)
    operador_entrada_id = Column(Integer, ForeignKey("operadores.id"), nullable=False)
    entrada_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    operador_salida_id = Column(Integer, ForeignKey("operadores.id"), nullable=True)
    salida_at = Column(DateTime, nullable=True)
    permanencia_min = Column(Integer, nullable=True)

    estado = Column(String(10), nullable=False, default="ACTIVO")  # ACTIVO/CERRADO

    celda = relationship("Celda", back_populates="movimientos")
    novedades = relationship("Novedad", back_populates="movimiento")

class Novedad(Base):
    __tablename__ = "novedades"
    id = Column(Integer, primary_key=True, index=True)
    movimiento_id = Column(Integer, ForeignKey("movimientos.id"), nullable=False)
    descripcion = Column(Text, nullable=False)
    operador_id = Column(Integer, ForeignKey("operadores.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    movimiento = relationship("Movimiento", back_populates="novedades")