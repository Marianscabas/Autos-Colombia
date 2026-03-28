from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Celda(Base):
    __tablename__ = "celdas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    estado: Mapped[str] = mapped_column(String(20), default="DISPONIBLE")
    usuario_actual_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=True,
    )

    usuario_actual: Mapped["Usuario | None"] = relationship(back_populates="celdas_ocupadas")
    movimientos: Mapped[list["Movimiento"]] = relationship(back_populates="celda")
    historial: Mapped[list["HistorialCelda"]] = relationship(back_populates="celda")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    identificacion: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    telefono: Mapped[str] = mapped_column(String(30))
    placa: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    tipo_vehiculo: Mapped[str] = mapped_column(String(30))
    color_vehiculo: Mapped[str] = mapped_column(String(40))
    estado_pago: Mapped[str] = mapped_column(String(30), default="Al día")
    fecha_ultimo_pago: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fecha_vencimiento: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    celdas_ocupadas: Mapped[list[Celda]] = relationship(back_populates="usuario_actual")
    historial_celdas: Mapped[list["HistorialCelda"]] = relationship(back_populates="usuario")


class Operador(Base):
    __tablename__ = "operadores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(20), default="OPERADOR")


class Movimiento(Base):
    __tablename__ = "movimientos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    placa: Mapped[str] = mapped_column(String(10), index=True)
    tipo_vehiculo: Mapped[str] = mapped_column(String(30))
    celda_id: Mapped[int] = mapped_column(ForeignKey("celdas.id"))
    operador_entrada_id: Mapped[int] = mapped_column(ForeignKey("operadores.id"))
    entrada_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    operador_salida_id: Mapped[int | None] = mapped_column(ForeignKey("operadores.id"), nullable=True)
    salida_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    permanencia_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(10), default="ACTIVO")

    celda: Mapped[Celda] = relationship(back_populates="movimientos")
    novedades: Mapped[list["Novedad"]] = relationship(back_populates="movimiento")


class Novedad(Base):
    __tablename__ = "novedades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    movimiento_id: Mapped[int] = mapped_column(ForeignKey("movimientos.id"))
    descripcion: Mapped[str] = mapped_column(Text)
    operador_id: Mapped[int] = mapped_column(ForeignKey("operadores.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    movimiento: Mapped[Movimiento] = relationship(back_populates="novedades")


class HistorialCelda(Base):
    __tablename__ = "historial_celdas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    celda_id: Mapped[int] = mapped_column(ForeignKey("celdas.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    ocupado_desde: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    liberado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    celda: Mapped[Celda] = relationship(back_populates="historial")
    usuario: Mapped[Usuario] = relationship(back_populates="historial_celdas")