from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import models


VALOR_MENSUAL_FIJO = 120000


def _utcnow() -> datetime:
    return datetime.utcnow()


def _normalizar_placa(placa: str) -> str:
    return placa.strip().upper()


def _normalizar_usuario_payload(data: dict) -> dict:
    return {
        "nombre": data["nombre"].strip(),
        "identificacion": data["identificacion"].strip(),
        "telefono": data["telefono"].strip(),
        "placa": _normalizar_placa(data["placa"]),
        "tipo_vehiculo": data["tipo_vehiculo"].strip().upper(),
        "color_vehiculo": data["color_vehiculo"].strip().upper(),
    }


def usuario_tiene_datos_completos(usuario: models.Usuario) -> bool:
    return all(
        [
            usuario.nombre and usuario.nombre.strip(),
            usuario.identificacion and usuario.identificacion.strip(),
            usuario.telefono and usuario.telefono.strip(),
            usuario.placa and usuario.placa.strip(),
            usuario.tipo_vehiculo and usuario.tipo_vehiculo.strip(),
            usuario.color_vehiculo and usuario.color_vehiculo.strip(),
        ]
    )


def actualizar_estado_pago_usuario(usuario: models.Usuario) -> bool:
    ahora = _utcnow()
    estado_objetivo = "Al día"
    if usuario.fecha_vencimiento and ahora > usuario.fecha_vencimiento:
        estado_objetivo = "Pendiente/Vencido"

    if usuario.estado_pago != estado_objetivo:
        usuario.estado_pago = estado_objetivo
        return True
    return False


def get_celdas(db: Session):
    return db.execute(select(models.Celda).order_by(models.Celda.codigo.asc())).scalars().all()


def get_celda_by_codigo(db: Session, codigo: str):
    return db.execute(select(models.Celda).where(models.Celda.codigo == codigo)).scalar_one_or_none()


def get_usuario(db: Session, usuario_id: int):
    usuario = db.execute(select(models.Usuario).where(models.Usuario.id == usuario_id)).scalar_one_or_none()
    if usuario and actualizar_estado_pago_usuario(usuario):
        db.commit()
    return usuario


def listar_usuarios(db: Session):
    usuarios = db.execute(select(models.Usuario).order_by(models.Usuario.nombre.asc())).scalars().all()
    hubo_cambios = any(actualizar_estado_pago_usuario(usuario) for usuario in usuarios)
    if hubo_cambios:
        db.commit()
    return usuarios


def crear_usuario(db: Session, **kwargs):
    data = _normalizar_usuario_payload(kwargs)
    ahora = _utcnow()

    existe_id = db.execute(
        select(models.Usuario).where(models.Usuario.identificacion == data["identificacion"])
    ).scalar_one_or_none()
    if existe_id:
        raise ValueError("Ya existe un usuario con esa identificación")

    existe_placa = db.execute(
        select(models.Usuario).where(models.Usuario.placa == data["placa"])
    ).scalar_one_or_none()
    if existe_placa:
        raise ValueError("Ya existe un usuario registrado con esa placa")

    usuario = models.Usuario(
        **data,
        estado_pago="Al día",
        fecha_ultimo_pago=ahora,
        fecha_vencimiento=ahora + timedelta(days=30),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_usuario(db: Session, usuario_id: int, **kwargs):
    usuario = get_usuario(db, usuario_id)
    if not usuario:
        raise ValueError("El usuario no existe")

    data = _normalizar_usuario_payload(kwargs)

    existe_id = db.execute(
        select(models.Usuario).where(
            models.Usuario.identificacion == data["identificacion"],
            models.Usuario.id != usuario_id,
        )
    ).scalar_one_or_none()
    if existe_id:
        raise ValueError("Ya existe otro usuario con esa identificación")

    existe_placa = db.execute(
        select(models.Usuario).where(
            models.Usuario.placa == data["placa"],
            models.Usuario.id != usuario_id,
        )
    ).scalar_one_or_none()
    if existe_placa:
        raise ValueError("Ya existe otro usuario registrado con esa placa")

    for key, value in data.items():
        setattr(usuario, key, value)

    db.commit()
    db.refresh(usuario)
    return usuario


def get_historial_activo_por_usuario(db: Session, usuario_id: int):
    return db.execute(
        select(models.HistorialCelda).where(
            models.HistorialCelda.usuario_id == usuario_id,
            models.HistorialCelda.liberado_en.is_(None),
        )
    ).scalar_one_or_none()


def get_historial_activo_por_celda(db: Session, celda_id: int):
    return db.execute(
        select(models.HistorialCelda).where(
            models.HistorialCelda.celda_id == celda_id,
            models.HistorialCelda.liberado_en.is_(None),
        )
    ).scalar_one_or_none()


def eliminar_usuario(db: Session, usuario_id: int):
    usuario = get_usuario(db, usuario_id)
    if not usuario:
        raise ValueError("El usuario no existe")

    if get_historial_activo_por_usuario(db, usuario_id):
        raise ValueError("No se puede eliminar: el usuario tiene una celda activa")

    celda_asignada = db.execute(
        select(models.Celda).where(models.Celda.usuario_actual_id == usuario_id)
    ).scalar_one_or_none()
    if celda_asignada:
        raise ValueError("No se puede eliminar: el usuario está asignado a una celda")

    db.execute(delete(models.HistorialCelda).where(models.HistorialCelda.usuario_id == usuario_id))
    db.delete(usuario)
    db.commit()
    return {"mensaje": "Usuario eliminado correctamente"}


def asignar_usuario_a_celda(db: Session, celda_codigo: str, usuario_id: int):
    celda = get_celda_by_codigo(db, celda_codigo)
    if not celda:
        raise ValueError("La celda no existe")
    if celda.estado != "DISPONIBLE":
        raise ValueError("La celda no está disponible")

    usuario = get_usuario(db, usuario_id)
    if not usuario:
        raise ValueError("El usuario no existe")
    if not usuario_tiene_datos_completos(usuario):
        raise ValueError("El usuario no tiene todos los datos completos")
    if usuario.estado_pago == "Pendiente/Vencido":
        raise ValueError("El usuario tiene mensualidad vencida")
    if get_historial_activo_por_usuario(db, usuario.id):
        raise ValueError("El usuario ya ocupa una celda")

    registro = models.HistorialCelda(
        celda_id=celda.id,
        usuario_id=usuario.id,
        ocupado_desde=_utcnow(),
    )
    celda.estado = "OCUPADA"
    celda.usuario_actual_id = usuario.id

    db.add(registro)
    db.commit()
    db.refresh(celda)
    return celda


def liberar_celda_manual(db: Session, celda_codigo: str):
    celda = get_celda_by_codigo(db, celda_codigo)
    if not celda:
        raise ValueError("La celda no existe")
    if celda.estado != "OCUPADA":
        raise ValueError("La celda no está ocupada")

    historial = get_historial_activo_por_celda(db, celda.id)
    ahora = _utcnow()
    usuario_id_liberado = celda.usuario_actual_id

    if historial:
        historial.liberado_en = ahora

    celda.estado = "DISPONIBLE"
    celda.usuario_actual_id = None

    db.commit()

    return {
        "celda_codigo": celda.codigo,
        "estado": celda.estado,
        "usuario_id_liberado": usuario_id_liberado,
        "liberado_en": historial.liberado_en if historial else ahora,
    }


def listar_historial_celdas(db: Session):
    registros = db.execute(
        select(models.HistorialCelda).order_by(models.HistorialCelda.ocupado_desde.desc())
    ).scalars().all()

    resultado = []
    for item in registros:
        usuario = db.get(models.Usuario, item.usuario_id)
        celda = db.get(models.Celda, item.celda_id)
        if not usuario or not celda:
            continue
        resultado.append(
            {
                "id": item.id,
                "celda_codigo": celda.codigo,
                "usuario_id": usuario.id,
                "usuario_nombre": usuario.nombre,
                "usuario_identificacion": usuario.identificacion,
                "placa": usuario.placa,
                "ocupado_desde": item.ocupado_desde,
                "liberado_en": item.liberado_en,
            }
        )
    return resultado


def generar_recibo(db: Session, usuario_id: int):
    return registrar_pago_manual(db=db, usuario_id=usuario_id, monto_cobrado=VALOR_MENSUAL_FIJO)


def registrar_pago_manual(db: Session, usuario_id: int, monto_cobrado: int):
    usuario = get_usuario(db, usuario_id)
    if not usuario:
        raise ValueError("El usuario no existe")
    if not usuario_tiene_datos_completos(usuario):
        raise ValueError("No se puede generar recibo: datos incompletos del usuario")
    if monto_cobrado <= 0:
        raise ValueError("El monto cobrado es obligatorio y debe ser mayor que cero")

    ahora = _utcnow()
    fecha_vencimiento = ahora + timedelta(days=30)

    usuario.fecha_ultimo_pago = ahora
    usuario.fecha_vencimiento = fecha_vencimiento
    usuario.estado_pago = "Al día"

    db.commit()
    db.refresh(usuario)

    return {
        "folio": f"REC-{ahora.strftime('%Y%m%d%H%M%S')}-{usuario.id:05d}",
        "fecha": ahora,
        "concepto": "Mensualidad Parqueadero",
        "monto_cobrado": monto_cobrado,
        "periodo_cobertura": f"{ahora.strftime('%d/%m/%Y')} al {fecha_vencimiento.strftime('%d/%m/%Y')}",
        "fecha_vencimiento": fecha_vencimiento,
        "dias_restantes_proximo_pago": max(0, (fecha_vencimiento.date() - ahora.date()).days),
        "cliente": usuario,
    }


def generarRecibo(db: Session, usuarioId: int):
    return generar_recibo(db=db, usuario_id=usuarioId)


def get_operador(db: Session, operador_id: int):
    return db.execute(select(models.Operador).where(models.Operador.id == operador_id)).scalar_one_or_none()


def get_movimiento_activo_por_placa(db: Session, placa: str):
    placa = _normalizar_placa(placa)
    return db.execute(
        select(models.Movimiento).where(
            models.Movimiento.placa == placa,
            models.Movimiento.estado == "ACTIVO",
        )
    ).scalar_one_or_none()


def get_movimiento_activo_por_celda(db: Session, celda_id: int):
    return db.execute(
        select(models.Movimiento).where(
            models.Movimiento.celda_id == celda_id,
            models.Movimiento.estado == "ACTIVO",
        )
    ).scalar_one_or_none()


def get_movimientos_activos(db: Session):
    return db.execute(select(models.Movimiento).where(models.Movimiento.estado == "ACTIVO")).scalars().all()


def registrar_ingreso(db: Session, placa: str, tipo: str, celda_codigo: str, operador_id: int):
    operador = get_operador(db, operador_id)
    if not operador:
        raise ValueError("Operador no existe")

    placa = _normalizar_placa(placa)
    if get_movimiento_activo_por_placa(db, placa):
        raise ValueError("Ya existe un ingreso activo para esta placa")

    celda = get_celda_by_codigo(db, celda_codigo)
    if not celda:
        raise ValueError("La celda no existe")
    if celda.estado != "DISPONIBLE":
        raise ValueError("La celda no está disponible")

    movimiento = models.Movimiento(
        placa=placa,
        tipo_vehiculo=tipo,
        celda_id=celda.id,
        operador_entrada_id=operador_id,
        entrada_at=_utcnow(),
        estado="ACTIVO",
    )

    celda.estado = "OCUPADA"
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


def registrar_salida(db: Session, placa: str):
    movimiento = get_movimiento_activo_por_placa(db, placa)
    if not movimiento:
        raise ValueError("No existe un ingreso activo para esta placa")

    salida = _utcnow()
    movimiento.salida_at = salida
    movimiento.operador_salida_id = 1
    movimiento.estado = "CERRADO"
    movimiento.permanencia_min = int((salida - movimiento.entrada_at).total_seconds() // 60)

    celda = db.get(models.Celda, movimiento.celda_id)
    if celda:
        celda.estado = "DISPONIBLE"

    db.commit()
    db.refresh(movimiento)
    return movimiento


def consultar_estado_vehiculo(db: Session, placa: str):
    placa = _normalizar_placa(placa)
    activo = get_movimiento_activo_por_placa(db, placa)
    if activo:
        celda = db.get(models.Celda, activo.celda_id)
        return {
            "placa": placa,
            "estado": "DENTRO",
            "celda_codigo": celda.codigo if celda else None,
            "entrada_at": activo.entrada_at,
            "salida_at": None,
            "permanencia_min": None,
            "movimiento_id": activo.id,
        }

    ultimo = db.execute(
        select(models.Movimiento)
        .where(models.Movimiento.placa == placa)
        .order_by(models.Movimiento.id.desc())
    ).scalar_one_or_none()

    if not ultimo:
        return {"placa": placa, "estado": "NO_REGISTRADO"}

    celda = db.get(models.Celda, ultimo.celda_id)
    return {
        "placa": placa,
        "estado": "FUERA",
        "celda_codigo": celda.codigo if celda else None,
        "entrada_at": ultimo.entrada_at,
        "salida_at": ultimo.salida_at,
        "permanencia_min": ultimo.permanencia_min,
        "movimiento_id": ultimo.id,
    }


def registrar_novedad(db: Session, placa: str, descripcion: str, operador_id: int):
    operador = get_operador(db, operador_id)
    if not operador:
        raise ValueError("Operador no existe")

    movimiento = get_movimiento_activo_por_placa(db, placa)
    if not movimiento:
        raise ValueError("Solo se pueden registrar novedades si el vehículo está dentro")

    novedad = models.Novedad(
        movimiento_id=movimiento.id,
        descripcion=descripcion,
        operador_id=operador_id,
    )
    db.add(novedad)
    db.commit()
    db.refresh(novedad)
    return novedad
