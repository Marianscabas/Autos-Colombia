from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from .database import Base, engine, get_db
from . import models, schemas, crud

app = FastAPI(title="Autos Colombia - Iteración 1")

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
    return crud.get_celdas(db)

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
        return crud.registrar_salida(db=db, placa=payload.placa, operador_id=payload.operador_id)
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