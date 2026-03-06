from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# ---------- CELDAS ----------
class CeldaOut(BaseModel):
    id: int
    codigo: str
    estado: str

    class Config:
        from_attributes = True


# ---------- INGRESO ----------
class IngresoIn(BaseModel):
    placa: str = Field(min_length=5, max_length=10)
    tipo_vehiculo: str
    celda_codigo: str
    operador_id: int


# ---------- SALIDA ----------
class SalidaIn(BaseModel):
    placa: str
    operador_id: int


# ---------- MOVIMIENTO (RESPUESTA) ----------
class MovimientoOut(BaseModel):
    id: int
    placa: str
    tipo_vehiculo: str
    celda_id: int
    operador_entrada_id: int
    entrada_at: datetime
    operador_salida_id: Optional[int] = None
    salida_at: Optional[datetime] = None
    permanencia_min: Optional[int] = None
    estado: str

    class Config:
        from_attributes = True


# ---------- CONSULTA ----------
class VehiculoEstadoOut(BaseModel):
    placa: str
    estado: str  # DENTRO / FUERA / NO_REGISTRADO
    celda_codigo: Optional[str] = None
    entrada_at: Optional[datetime] = None
    salida_at: Optional[datetime] = None
    permanencia_min: Optional[int] = None
    movimiento_id: Optional[int] = None


# ---------- NOVEDADES ----------
class NovedadIn(BaseModel):
    placa: str
    descripcion: str
    operador_id: int


class NovedadOut(BaseModel):
    id: int
    movimiento_id: int
    descripcion: str
    operador_id: int
    created_at: datetime

    class Config:
        from_attributes = True