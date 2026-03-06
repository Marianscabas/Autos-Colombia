from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from . import models

def get_celdas(db: Session):
    return db.execute(select(models.Celda)).scalars().all()

def get_celda_by_codigo(db: Session, codigo: str):
    return db.execute(
        select(models.Celda).where(models.Celda.codigo == codigo)
    ).scalar_one_or_none()

def get_operador(db: Session, operador_id: int):
    return db.execute(
        select(models.Operador).where(models.Operador.id == operador_id)
    ).scalar_one_or_none()

def get_movimiento_activo_por_placa(db: Session, placa: str):
    return db.execute(
        select(models.Movimiento).where(
            models.Movimiento.placa == placa,
            models.Movimiento.estado == "ACTIVO"
        )
    ).scalar_one_or_none()

def registrar_ingreso(db: Session, placa: str, tipo: str, celda_codigo: str, operador_id: int):
    operador = get_operador(db, operador_id)
    if not operador:
        raise ValueError("Operador no existe")

    placa = placa.upper()
    if get_movimiento_activo_por_placa(db, placa):
        raise ValueError("Ya existe un ingreso activo para esta placa")

    celda = get_celda_by_codigo(db, celda_codigo)
    if not celda:
        raise ValueError("La celda no existe")
    if celda.estado != "DISPONIBLE":
        raise ValueError("La celda no está disponible")

    mov = models.Movimiento(
        placa=placa,
        tipo_vehiculo=tipo,
        celda_id=celda.id,
        operador_entrada_id=operador_id,
        entrada_at=datetime.utcnow(),
        estado="ACTIVO"
    )
    celda.estado = "OCUPADA"

    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov

def registrar_salida(db: Session, placa: str, operador_id: int):
    operador = get_operador(db, operador_id)
    if not operador:
        raise ValueError("Operador no existe")

    placa = placa.upper()
    mov = get_movimiento_activo_por_placa(db, placa)
    if not mov:
        raise ValueError("No existe un ingreso activo para esta placa")

    mov.salida_at = datetime.utcnow()
    mov.operador_salida_id = operador_id
    mov.estado = "CERRADO"

    delta = mov.salida_at - mov.entrada_at
    mov.permanencia_min = int(delta.total_seconds() // 60)

    celda = db.get(models.Celda, mov.celda_id)
    celda.estado = "DISPONIBLE"

    db.commit()
    db.refresh(mov)
    return mov

def consultar_estado_vehiculo(db: Session, placa: str):
    placa = placa.upper()
    mov_activo = get_movimiento_activo_por_placa(db, placa)

    if mov_activo:
        celda = db.get(models.Celda, mov_activo.celda_id)
        return {
            "placa": placa,
            "estado": "DENTRO",
            "celda_codigo": celda.codigo if celda else None,
            "entrada_at": mov_activo.entrada_at,
            "salida_at": None,
            "permanencia_min": None,
            "movimiento_id": mov_activo.id
        }

    ultimo = db.execute(
        select(models.Movimiento)
        .where(models.Movimiento.placa == placa)
        .order_by(models.Movimiento.id.desc())
    ).scalar_one_or_none()

    if not ultimo:
        return {
            "placa": placa,
            "estado": "NO_REGISTRADO"
        }

    celda = db.get(models.Celda, ultimo.celda_id)
    return {
        "placa": placa,
        "estado": "FUERA",
        "celda_codigo": celda.codigo if celda else None,
        "entrada_at": ultimo.entrada_at,
        "salida_at": ultimo.salida_at,
        "permanencia_min": ultimo.permanencia_min,
        "movimiento_id": ultimo.id
    }

def registrar_novedad(db: Session, placa: str, descripcion: str, operador_id: int):
    operador = get_operador(db, operador_id)
    if not operador:
        raise ValueError("Operador no existe")

    placa = placa.upper()
    mov = get_movimiento_activo_por_placa(db, placa)
    if not mov:
        raise ValueError("Solo se pueden registrar novedades si el vehículo está dentro")

    nov = models.Novedad(
        movimiento_id=mov.id,
        descripcion=descripcion,
        operador_id=operador_id
    )
    db.add(nov)
    db.commit()
    db.refresh(nov)
    return nov