from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

import crud
import models
import schemas
from database import Base, engine, get_db


app = FastAPI(title="Autos Colombia - API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def _seed_data() -> None:
    with Session(engine) as db:
        operador = db.execute(select(models.Operador).where(models.Operador.id == 1)).scalar_one_or_none()
        if not operador:
            db.add(models.Operador(id=1, nombre="Operador Demo", rol="OPERADOR"))

        celdas = db.execute(select(models.Celda)).scalars().all()
        if not celdas:
            for i in range(1, 11):
                db.add(models.Celda(codigo=f"A{i:02d}", estado="DISPONIBLE"))

        ahora = datetime.utcnow()
        demo_video = [
            {
                "nombre": "Mateo Ruiz",
                "identificacion": "VID-200001",
                "telefono": "3002000001",
                "placa": "VID001",
                "tipo_vehiculo": "CARRO",
                "color_vehiculo": "BLANCO",
                "fecha_ultimo_pago": ahora - timedelta(days=7),
                "fecha_vencimiento": ahora + timedelta(days=23),
            },
            {
                "nombre": "Sara León",
                "identificacion": "VID-200002",
                "telefono": "3002000002",
                "placa": "VID002",
                "tipo_vehiculo": "MOTO",
                "color_vehiculo": "NEGRO",
                "fecha_ultimo_pago": ahora - timedelta(days=5),
                "fecha_vencimiento": ahora + timedelta(days=25),
            },
            {
                "nombre": "Nicolás Vega",
                "identificacion": "VID-200003",
                "telefono": "3002000003",
                "placa": "VID003",
                "tipo_vehiculo": "CARRO",
                "color_vehiculo": "GRIS",
                "fecha_ultimo_pago": ahora - timedelta(days=2),
                "fecha_vencimiento": ahora + timedelta(days=28),
            },
            {
                "nombre": "Paula Ríos",
                "identificacion": "VID-200004",
                "telefono": "3002000004",
                "placa": "VID004",
                "tipo_vehiculo": "MOTO",
                "color_vehiculo": "ROJO",
                "fecha_ultimo_pago": ahora - timedelta(days=45),
                "fecha_vencimiento": ahora - timedelta(days=15),
            },
            {
                "nombre": "Diego Pardo",
                "identificacion": "VID-200005",
                "telefono": "3002000005",
                "placa": "VID005",
                "tipo_vehiculo": "CARRO",
                "color_vehiculo": "AZUL",
                "fecha_ultimo_pago": ahora - timedelta(days=38),
                "fecha_vencimiento": ahora - timedelta(days=8),
            },
        ]

        for data in demo_video:
            estado = "Pendiente/Vencido" if data["fecha_vencimiento"] < ahora else "Al día"
            existente = db.execute(
                select(models.Usuario).where(models.Usuario.identificacion == data["identificacion"])
            ).scalar_one_or_none()

            if existente:
                existente.nombre = data["nombre"]
                existente.telefono = data["telefono"]
                existente.placa = data["placa"]
                existente.tipo_vehiculo = data["tipo_vehiculo"]
                existente.color_vehiculo = data["color_vehiculo"]
                existente.estado_pago = estado
                existente.fecha_ultimo_pago = data["fecha_ultimo_pago"]
                existente.fecha_vencimiento = data["fecha_vencimiento"]
                continue

            db.add(
                models.Usuario(
                    nombre=data["nombre"],
                    identificacion=data["identificacion"],
                    telefono=data["telefono"],
                    placa=data["placa"],
                    tipo_vehiculo=data["tipo_vehiculo"],
                    color_vehiculo=data["color_vehiculo"],
                    estado_pago=estado,
                    fecha_ultimo_pago=data["fecha_ultimo_pago"],
                    fecha_vencimiento=data["fecha_vencimiento"],
                )
            )

        db.commit()


@app.on_event("startup")
def startup() -> None:
    _seed_data()


def _to_http_400(error: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(error))


@app.get("/")
def root():
    return {"mensaje": "API Autos Colombia funcionando"}


@app.get("/usuarios", response_model=list[schemas.UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    return crud.listar_usuarios(db)


@app.post("/usuarios", response_model=schemas.UsuarioOut)
def crear_usuario(payload: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    try:
        return crud.crear_usuario(
            db,
            nombre=payload.nombre,
            identificacion=payload.identificacion,
            telefono=payload.telefono,
            placa=payload.placa,
            tipo_vehiculo=payload.tipo_vehiculo,
            color_vehiculo=payload.color_vehiculo,
        )
    except ValueError as error:
        raise _to_http_400(error)


@app.put("/usuarios/{usuario_id}", response_model=schemas.UsuarioOut)
def actualizar_usuario(usuario_id: int, payload: schemas.UsuarioUpdate, db: Session = Depends(get_db)):
    try:
        return crud.actualizar_usuario(
            db,
            usuario_id=usuario_id,
            nombre=payload.nombre,
            identificacion=payload.identificacion,
            telefono=payload.telefono,
            placa=payload.placa,
            tipo_vehiculo=payload.tipo_vehiculo,
            color_vehiculo=payload.color_vehiculo,
        )
    except ValueError as error:
        raise _to_http_400(error)


@app.delete("/usuarios/{usuario_id}", response_model=schemas.MessageOut)
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    try:
        return crud.eliminar_usuario(db, usuario_id)
    except ValueError as error:
        raise _to_http_400(error)


@app.get("/celdas", response_model=list[schemas.CeldaOut])
def listar_celdas(db: Session = Depends(get_db)):
    celdas = crud.get_celdas(db)
    response = []

    for celda in celdas:
        usuario = crud.get_usuario(db, celda.usuario_actual_id) if celda.usuario_actual_id else None
        placa = usuario.placa if usuario else None
        if celda.estado == "OCUPADA" and not placa:
            movimiento = crud.get_movimiento_activo_por_celda(db, celda.id)
            placa = movimiento.placa if movimiento else None

        response.append(
            {
                "id": celda.id,
                "codigo": celda.codigo,
                "estado": celda.estado,
                "placa": placa,
                "usuario_id": usuario.id if usuario else None,
                "usuario_nombre": usuario.nombre if usuario else None,
                "usuario_identificacion": usuario.identificacion if usuario else None,
            }
        )

    return response


@app.post("/celdas/{celda_codigo}/asignar", response_model=schemas.CeldaOut)
def asignar_celda(celda_codigo: str, payload: schemas.AsignarCeldaIn, db: Session = Depends(get_db)):
    try:
        celda = crud.asignar_usuario_a_celda(db, celda_codigo, payload.usuario_id)
        usuario = crud.get_usuario(db, celda.usuario_actual_id) if celda.usuario_actual_id else None
        return {
            "id": celda.id,
            "codigo": celda.codigo,
            "estado": celda.estado,
            "placa": usuario.placa if usuario else None,
            "usuario_id": usuario.id if usuario else None,
            "usuario_nombre": usuario.nombre if usuario else None,
            "usuario_identificacion": usuario.identificacion if usuario else None,
        }
    except ValueError as error:
        raise _to_http_400(error)


@app.post("/celdas/{celda_codigo}/liberar", response_model=schemas.LiberarCeldaOut)
def liberar_celda(celda_codigo: str, db: Session = Depends(get_db)):
    try:
        return crud.liberar_celda_manual(db, celda_codigo)
    except ValueError as error:
        raise _to_http_400(error)


@app.get("/celdas/historial", response_model=list[schemas.HistorialCeldaOut])
def historial_celdas(db: Session = Depends(get_db)):
    return crud.listar_historial_celdas(db)


@app.get("/usuarios/{usuario_id}/recibo-mensual", response_model=schemas.ReciboMensualOut)
def recibo_mensual(usuario_id: int, db: Session = Depends(get_db)):
    try:
        return crud.generarRecibo(db, usuario_id)
    except ValueError as error:
        raise _to_http_400(error)


@app.post("/usuarios/{usuario_id}/pagos/manual", response_model=schemas.ReciboMensualOut)
def registrar_pago_manual(usuario_id: int, payload: schemas.PagoManualIn, db: Session = Depends(get_db)):
    try:
        return crud.registrar_pago_manual(db, usuario_id, payload.monto_cobrado)
    except ValueError as error:
        raise _to_http_400(error)


@app.get("/ingresos", response_model=list[schemas.MovimientoResumen])
def listar_ingresos(db: Session = Depends(get_db)):
    activos = crud.get_movimientos_activos(db)
    return [
        {
            "placa": movimiento.placa,
            "celda": db.get(models.Celda, movimiento.celda_id).codigo if db.get(models.Celda, movimiento.celda_id) else None,
            "hora_ingreso": movimiento.entrada_at,
        }
        for movimiento in activos
    ]


@app.post("/ingresos", response_model=schemas.MovimientoOut)
def crear_ingreso(payload: schemas.IngresoIn, db: Session = Depends(get_db)):
    try:
        return crud.registrar_ingreso(
            db,
            placa=payload.placa,
            tipo=payload.tipo_vehiculo,
            celda_codigo=payload.celda_codigo,
            operador_id=payload.operador_id,
        )
    except ValueError as error:
        raise _to_http_400(error)


@app.post("/salidas", response_model=schemas.MovimientoOut)
def crear_salida(payload: schemas.SalidaIn, db: Session = Depends(get_db)):
    try:
        return crud.registrar_salida(db, payload.placa)
    except ValueError as error:
        raise _to_http_400(error)


@app.get("/vehiculos/{placa}", response_model=schemas.VehiculoEstadoOut)
def consultar_vehiculo(placa: str, db: Session = Depends(get_db)):
    return crud.consultar_estado_vehiculo(db, placa)


@app.post("/novedades", response_model=schemas.NovedadOut)
def crear_novedad(payload: schemas.NovedadIn, db: Session = Depends(get_db)):
    try:
        return crud.registrar_novedad(db, payload.placa, payload.descripcion, payload.operador_id)
    except ValueError as error:
        raise _to_http_400(error)