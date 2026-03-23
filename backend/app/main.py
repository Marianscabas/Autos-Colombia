from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from datetime import datetime, timedelta

from database import Base, engine, get_db
import models, schemas, crud

app = FastAPI(title="Autos Colombia - Iteración 2")

# configure CORS so that the frontend can communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def _ensure_iteracion2_schema():
    with engine.connect() as conn:
        columnas = conn.execute(text("PRAGMA table_info(celdas)")).fetchall()
        nombres = {col[1] for col in columnas}
        if "usuario_actual_id" not in nombres:
            conn.execute(text("ALTER TABLE celdas ADD COLUMN usuario_actual_id INTEGER"))

        columnas_usuario = conn.execute(text("PRAGMA table_info(usuarios)")).fetchall()
        nombres_usuario = {col[1] for col in columnas_usuario}

        if "estado_pago" not in nombres_usuario:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN estado_pago TEXT DEFAULT 'Al día'"))

        if "fecha_ultimo_pago" not in nombres_usuario:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN fecha_ultimo_pago DATETIME"))

        if "fecha_vencimiento" not in nombres_usuario:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN fecha_vencimiento DATETIME"))

        conn.execute(text("""
            UPDATE usuarios
            SET
                estado_pago = 'Al día',
                fecha_ultimo_pago = COALESCE(fecha_ultimo_pago, CURRENT_TIMESTAMP),
                fecha_vencimiento = COALESCE(fecha_vencimiento, datetime(CURRENT_TIMESTAMP, '+30 days'))
            WHERE fecha_vencimiento IS NULL
        """))

        conn.commit()

@app.on_event("startup")
def seed_data():
    _ensure_iteracion2_schema()
    # Celdas y operador demo para poder probar en Swagger
    with Session(engine) as db:
        op = db.execute(select(models.Operador).where(models.Operador.id == 1)).scalar_one_or_none()
        if not op:
            db.add(models.Operador(id=1, nombre="Operador Demo", rol="OPERADOR"))

        celdas = db.execute(select(models.Celda)).scalars().all()
        if len(celdas) == 0:
            for i in range(1, 11):
                db.add(models.Celda(codigo=f"A{i:02d}", estado="DISPONIBLE"))

        usuarios = db.execute(select(models.Usuario)).scalars().all()
        if len(usuarios) == 0:
            ahora = datetime.utcnow()
            usuarios_demo = [
                models.Usuario(
                    nombre="Carlos Mendoza",
                    identificacion="101001001",
                    telefono="3001001001",
                    placa="ABC101",
                    tipo_vehiculo="CARRO",
                    color_vehiculo="BLANCO",
                    estado_pago="Al día",
                    fecha_ultimo_pago=ahora - timedelta(days=5),
                    fecha_vencimiento=ahora + timedelta(days=25),
                ),
                models.Usuario(
                    nombre="Laura Gómez",
                    identificacion="101001002",
                    telefono="3001001002",
                    placa="XYZ202",
                    tipo_vehiculo="MOTO",
                    color_vehiculo="NEGRO",
                    estado_pago="Al día",
                    fecha_ultimo_pago=ahora - timedelta(days=3),
                    fecha_vencimiento=ahora + timedelta(days=27),
                ),
                models.Usuario(
                    nombre="Andrés Rojas",
                    identificacion="101001003",
                    telefono="3001001003",
                    placa="JKL303",
                    tipo_vehiculo="CARRO",
                    color_vehiculo="GRIS",
                    estado_pago="Al día",
                    fecha_ultimo_pago=ahora - timedelta(days=1),
                    fecha_vencimiento=ahora + timedelta(days=29),
                ),
                models.Usuario(
                    nombre="María Pineda",
                    identificacion="101001004",
                    telefono="3001001004",
                    placa="MNO404",
                    tipo_vehiculo="MOTO",
                    color_vehiculo="ROJO",
                    estado_pago="Pendiente/Vencido",
                    fecha_ultimo_pago=ahora - timedelta(days=45),
                    fecha_vencimiento=ahora - timedelta(days=15),
                ),
                models.Usuario(
                    nombre="Julián Castro",
                    identificacion="101001005",
                    telefono="3001001005",
                    placa="PQR505",
                    tipo_vehiculo="CARRO",
                    color_vehiculo="AZUL",
                    estado_pago="Pendiente/Vencido",
                    fecha_ultimo_pago=ahora - timedelta(days=38),
                    fecha_vencimiento=ahora - timedelta(days=8),
                ),
            ]
            db.add_all(usuarios_demo)

        db.commit()

@app.get("/")
def root():
    return {"mensaje": "API Autos Colombia funcionando"}

@app.get("/celdas", response_model=list[schemas.CeldaOut])
def listar_celdas(db: Session = Depends(get_db)):
    celdas = crud.get_celdas(db)
    resultado = []
    for c in celdas:
        placa = None
        usuario_id = None
        usuario_nombre = None
        usuario_identificacion = None

        if c.usuario_actual_id:
            usuario = crud.get_usuario(db, c.usuario_actual_id)
            if usuario:
                placa = usuario.placa
                usuario_id = usuario.id
                usuario_nombre = usuario.nombre
                usuario_identificacion = usuario.identificacion

        if c.estado == "OCUPADA":
            mov = crud.get_movimiento_activo_por_celda(db, c.id)
            if not placa:
                placa = mov.placa if mov else None
        resultado.append({
            "id": c.id,
            "codigo": c.codigo,
            "estado": c.estado,
            "placa": placa,
            "usuario_id": usuario_id,
            "usuario_nombre": usuario_nombre,
            "usuario_identificacion": usuario_identificacion,
        })
    return resultado


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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/usuarios/{usuario_id}", response_model=schemas.MessageOut)
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    try:
        return crud.eliminar_usuario(db, usuario_id=usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/celdas/{celda_codigo}/asignar", response_model=schemas.CeldaOut)
def asignar_celda_manual(celda_codigo: str, payload: schemas.AsignarCeldaIn, db: Session = Depends(get_db)):
    try:
        celda = crud.asignar_usuario_a_celda(db=db, celda_codigo=celda_codigo, usuario_id=payload.usuario_id)
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/celdas/{celda_codigo}/liberar", response_model=schemas.LiberarCeldaOut)
def liberar_celda(celda_codigo: str, db: Session = Depends(get_db)):
    try:
        return crud.liberar_celda_manual(db=db, celda_codigo=celda_codigo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/celdas/historial", response_model=list[schemas.HistorialCeldaOut])
def historial_celdas(db: Session = Depends(get_db)):
    return crud.listar_historial_celdas(db)


@app.get("/usuarios/{usuario_id}/recibo-mensual", response_model=schemas.ReciboMensualOut)
def generar_recibo_mensual(usuario_id: int, db: Session = Depends(get_db)):
    try:
        return crud.generarRecibo(db=db, usuarioId=usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/usuarios/{usuario_id}/pagos/manual", response_model=schemas.ReciboMensualOut)
def registrar_pago_manual(usuario_id: int, payload: schemas.PagoManualIn, db: Session = Depends(get_db)):
    try:
        return crud.registrar_pago_manual(db=db, usuario_id=usuario_id, monto_cobrado=payload.monto_cobrado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Lista de ingresos activos para la búsqueda frontend
@app.get("/ingresos", response_model=list[schemas.MovimientoResumen])
def listar_ingresos(db: Session = Depends(get_db)):
    movs = crud.get_movimientos_activos(db)
    resultado = []
    for m in movs:
        celda = db.get(models.Celda, m.celda_id)
        resultado.append({
            "placa": m.placa,
            "celda": celda.codigo if celda else None,
            "hora_ingreso": m.entrada_at,
        })
    return resultado

@app.post("/ingresos", response_model=schemas.MovimientoOut)
def crear_ingreso(payload: schemas.IngresoIn, db: Session = Depends(get_db)):
    try:
        return crud.registrar_ingreso(
            db=db,
            placa=payload.placa,
            tipo=payload.tipo_vehiculo,
            celda_codigo=payload.celda_codigo,
            operador_id=payload.operador_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/salidas", response_model=schemas.MovimientoOut)
def crear_salida(payload: schemas.SalidaIn, db: Session = Depends(get_db)):
    try:
        return crud.registrar_salida(db=db, placa=payload.placa)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/vehiculos/{placa}", response_model=schemas.VehiculoEstadoOut)
def consultar_vehiculo(placa: str, db: Session = Depends(get_db)):
    return crud.consultar_estado_vehiculo(db=db, placa=placa)

@app.post("/novedades", response_model=schemas.NovedadOut)
def crear_novedad(payload: schemas.NovedadIn, db: Session = Depends(get_db)):
    try:
        return crud.registrar_novedad(db=db, placa=payload.placa, descripcion=payload.descripcion, operador_id=payload.operador_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))