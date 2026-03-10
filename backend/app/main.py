from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import Base, engine, get_db
import models, schemas, crud

app = FastAPI(title="Autos Colombia - Iteración 1")

# configure CORS so that the frontend can communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def seed_data():
    # Celdas y operador demo para poder probar en Swagger
    with Session(engine) as db:
        op = db.execute(select(models.Operador).where(models.Operador.id == 1)).scalar_one_or_none()
        if not op:
            db.add(models.Operador(id=1, nombre="Operador Demo", rol="OPERADOR"))

        celdas = db.execute(select(models.Celda)).scalars().all()
        if len(celdas) == 0:
            for i in range(1, 11):
                db.add(models.Celda(codigo=f"A{i:02d}", estado="DISPONIBLE"))

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
        if c.estado == "OCUPADA":
            mov = crud.get_movimiento_activo_por_celda(db, c.id)
            placa = mov.placa if mov else None
        resultado.append({
            "id": c.id,
            "codigo": c.codigo,
            "estado": c.estado,
            "placa": placa,
        })
    return resultado

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