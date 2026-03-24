from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CeldaOut(OrmModel):
    id: int
    codigo: str
    estado: str
    placa: str | None = None
    usuario_id: int | None = None
    usuario_nombre: str | None = None
    usuario_identificacion: str | None = None


class AsignarCeldaIn(BaseModel):
    usuario_id: int


class LiberarCeldaOut(BaseModel):
    celda_codigo: str
    estado: str
    usuario_id_liberado: int | None = None
    liberado_en: datetime


class HistorialCeldaOut(BaseModel):
    id: int
    celda_codigo: str
    usuario_id: int
    usuario_nombre: str
    usuario_identificacion: str
    placa: str
    ocupado_desde: datetime
    liberado_en: datetime | None = None


class IngresoIn(BaseModel):
    placa: str = Field(min_length=5, max_length=10)
    tipo_vehiculo: str
    celda_codigo: str
    operador_id: int


class SalidaIn(BaseModel):
    placa: str


class MovimientoOut(OrmModel):
    id: int
    placa: str
    tipo_vehiculo: str
    celda_id: int
    operador_entrada_id: int
    entrada_at: datetime
    operador_salida_id: int | None = None
    salida_at: datetime | None = None
    permanencia_min: int | None = None
    estado: str


class VehiculoEstadoOut(BaseModel):
    placa: str
    estado: str
    celda_codigo: str | None = None
    entrada_at: datetime | None = None
    salida_at: datetime | None = None
    permanencia_min: int | None = None
    movimiento_id: int | None = None


class NovedadIn(BaseModel):
    placa: str
    descripcion: str
    operador_id: int


class NovedadOut(OrmModel):
    id: int
    movimiento_id: int
    descripcion: str
    operador_id: int
    created_at: datetime


class MovimientoResumen(BaseModel):
    placa: str
    celda: str | None
    hora_ingreso: datetime


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


class UsuarioOut(UsuarioBase, OrmModel):
    id: int
    estado_pago: str
    fecha_ultimo_pago: datetime | None = None
    fecha_vencimiento: datetime | None = None


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
