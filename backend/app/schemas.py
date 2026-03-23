from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# ---------- CELDAS ----------
class CeldaOut(BaseModel):
    id: int
    codigo: str
    estado: str
    placa: Optional[str] = None  # si la celda está ocupada, muestra la placa del vehículo
    usuario_id: Optional[int] = None
    usuario_nombre: Optional[str] = None
    usuario_identificacion: Optional[str] = None

    class Config:
        from_attributes = True


class AsignarCeldaIn(BaseModel):
    usuario_id: int


class LiberarCeldaOut(BaseModel):
    celda_codigo: str
    estado: str
    usuario_id_liberado: Optional[int] = None
    liberado_en: datetime


class HistorialCeldaOut(BaseModel):
    id: int
    celda_codigo: str
    usuario_id: int
    usuario_nombre: str
    usuario_identificacion: str
    placa: str
    ocupado_desde: datetime
    liberado_en: Optional[datetime] = None


# ---------- INGRESO ----------
class IngresoIn(BaseModel):
    placa: str = Field(min_length=5, max_length=10)
    tipo_vehiculo: str
    celda_codigo: str
    operador_id: int


# ---------- SALIDA ----------
class SalidaIn(BaseModel):
    placa: str
    # El operador se fija internamente (demo) en el servidor


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


# ---------- UTILIDADES PARA FRONEND ----------
class MovimientoResumen(BaseModel):
    placa: str
    celda: str
    hora_ingreso: datetime


# ---------- USUARIOS (ITERACIÓN 2) ----------
class UsuarioBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    identificacion: str = Field(min_length=3, max_length=30)
    telefono: str = Field(min_length=7, max_length=30)
    placa: str = Field(min_length=5, max_length=10)
    tipo_vehiculo: str = Field(min_length=3, max_length=30)
    color_vehiculo: str = Field(min_length=3, max_length=40)


class UsuarioCreate(UsuarioBase):
    pass


class UsuarioUpdate(UsuarioBase):
    pass


class UsuarioOut(UsuarioBase):
    id: int
    estado_pago: str
    fecha_ultimo_pago: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- RECIBOS ----------
class PagoManualIn(BaseModel):
    monto_cobrado: int = Field(gt=0)


class ReciboMensualOut(BaseModel):
    folio: str
    fecha: datetime
    concepto: str
    monto_cobrado: int
    periodo_cobertura: str
    fecha_vencimiento: datetime
    dias_restantes_proximo_pago: int
    cliente: UsuarioOut


class MessageOut(BaseModel):
    mensaje: str
