from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from datetime import datetime, timedelta
import models

VALOR_MENSUAL_FIJO = 120000

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


def get_movimiento_activo_por_celda(db: Session, celda_id: int):
    """Return the active movement occupying a specific celda, or None."""
    return db.execute(
        select(models.Movimiento).where(
            models.Movimiento.celda_id == celda_id,
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

def registrar_salida(db: Session, placa: str):
    # el sistema usa operador demo (id=1) para salir
    operador_id = 1

    placa = placa.upper().strip()
    mov = get_movimiento_activo_por_placa(db, placa)
    if not mov:
        raise ValueError("No existe un ingreso activo para esta placa")

    mov.salida_at = datetime.utcnow()
    mov.operador_salida_id = operador_id
    mov.estado = "CERRADO"

    delta = mov.salida_at - mov.entrada_at
    mov.permanencia_min = int(delta.total_seconds() // 60)

    celda = db.get(models.Celda, mov.celda_id)
    if celda:
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


# nuevo helper para listar ingresos activos (para búsqueda rápida en frontend)

def get_movimientos_activos(db: Session):
    """Devuelve todos los movimientos que todavía están en estado ACTIVO."""
    return db.execute(
        select(models.Movimiento).where(models.Movimiento.estado == "ACTIVO")
    ).scalars().all()


# ---------- ITERACIÓN 2: USUARIOS + ASIGNACIÓN MANUAL ----------
def _normalizar_usuario_data(data: dict):
    return {
        "nombre": data["nombre"].strip(),
        "identificacion": data["identificacion"].strip(),
        "telefono": data["telefono"].strip(),
        "placa": data["placa"].strip().upper(),
        "tipo_vehiculo": data["tipo_vehiculo"].strip().upper(),
        "color_vehiculo": data["color_vehiculo"].strip().upper(),
    }


def usuario_tiene_datos_completos(usuario: models.Usuario):
    campos = [
        usuario.nombre,
        usuario.identificacion,
        usuario.telefono,
        usuario.placa,
        usuario.tipo_vehiculo,
        usuario.color_vehiculo,
    ]
    return all(valor is not None and str(valor).strip() != "" for valor in campos)


def actualizar_estado_pago_usuario(usuario: models.Usuario):
    ahora = datetime.utcnow()

    if not usuario.fecha_vencimiento:
        nuevo_estado = "Al día"
    elif ahora > usuario.fecha_vencimiento:
        nuevo_estado = "Pendiente/Vencido"
    else:
        nuevo_estado = "Al día"

    if usuario.estado_pago != nuevo_estado:
        usuario.estado_pago = nuevo_estado
        return True
    return False


def listar_usuarios(db: Session):
    usuarios = db.execute(select(models.Usuario).order_by(models.Usuario.nombre.asc())).scalars().all()
    hubo_cambios = False
    for usuario in usuarios:
        if actualizar_estado_pago_usuario(usuario):
            hubo_cambios = True

    if hubo_cambios:
        db.commit()
    return usuarios


def get_usuario(db: Session, usuario_id: int):
    usuario = db.execute(select(models.Usuario).where(models.Usuario.id == usuario_id)).scalar_one_or_none()
    if usuario and actualizar_estado_pago_usuario(usuario):
        db.commit()
    return usuario


def crear_usuario(db: Session, **kwargs):
    data = _normalizar_usuario_data(kwargs)
    ahora = datetime.utcnow()
    fecha_vencimiento = ahora + timedelta(days=30)

    existe_identificacion = db.execute(
        select(models.Usuario).where(models.Usuario.identificacion == data["identificacion"])
    ).scalar_one_or_none()
    if existe_identificacion:
        raise ValueError("Ya existe un usuario con esa identificación")

    existe_placa = db.execute(
        select(models.Usuario).where(models.Usuario.placa == data["placa"])
    ).scalar_one_or_none()
    if existe_placa:
        raise ValueError("Ya existe un usuario registrado con esa placa")

    nuevo = models.Usuario(
        **data,
        estado_pago="Al día",
        fecha_ultimo_pago=ahora,
        fecha_vencimiento=fecha_vencimiento,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_usuario(db: Session, usuario_id: int, **kwargs):
    usuario = get_usuario(db, usuario_id)
    if not usuario:
        raise ValueError("El usuario no existe")

    data = _normalizar_usuario_data(kwargs)

    existe_identificacion = db.execute(
        select(models.Usuario).where(
            models.Usuario.identificacion == data["identificacion"],
            models.Usuario.id != usuario_id,
        )
    ).scalar_one_or_none()
    if existe_identificacion:
        raise ValueError("Ya existe otro usuario con esa identificación")

    existe_placa = db.execute(
        select(models.Usuario).where(
            models.Usuario.placa == data["placa"],
            models.Usuario.id != usuario_id,
        )
    ).scalar_one_or_none()
    if existe_placa:
        raise ValueError("Ya existe otro usuario registrado con esa placa")

    usuario.nombre = data["nombre"]
    usuario.identificacion = data["identificacion"]
    usuario.telefono = data["telefono"]
    usuario.placa = data["placa"]
    usuario.tipo_vehiculo = data["tipo_vehiculo"]
    usuario.color_vehiculo = data["color_vehiculo"]

    db.commit()
    db.refresh(usuario)
    return usuario


def eliminar_usuario(db: Session, usuario_id: int):
    usuario = get_usuario(db, usuario_id)
    if not usuario:
        raise ValueError("El usuario no existe")

    if get_historial_activo_por_usuario(db, usuario_id):
        raise ValueError("No se puede eliminar: el usuario tiene una celda activa")

    celdas_ocupadas = db.execute(
        select(models.Celda).where(models.Celda.usuario_actual_id == usuario_id)
    ).scalars().all()

    if celdas_ocupadas:
        raise ValueError("No se puede eliminar: el usuario está asignado a una celda")

    db.execute(
        delete(models.HistorialCelda).where(
            models.HistorialCelda.usuario_id == usuario_id,
        )
    )

    db.delete(usuario)
    db.commit()

    return {"mensaje": "Usuario eliminado correctamente"}


def get_historial_activo_por_usuario(db: Session, usuario_id: int):
    return db.execute(
        select(models.HistorialCelda).where(
            models.HistorialCelda.usuario_id == usuario_id,
            models.HistorialCelda.liberado_en.is_(None)
        )
    ).scalar_one_or_none()


def get_historial_activo_por_celda(db: Session, celda_id: int):
    return db.execute(
        select(models.HistorialCelda).where(
            models.HistorialCelda.celda_id == celda_id,
            models.HistorialCelda.liberado_en.is_(None)
        )
    ).scalar_one_or_none()


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

    if get_historial_activo_por_usuario(db, usuario_id):
        raise ValueError("El usuario ya ocupa una celda")

    historial = models.HistorialCelda(
        celda_id=celda.id,
        usuario_id=usuario.id,
        ocupado_desde=datetime.utcnow(),
        liberado_en=None,
    )

    celda.estado = "OCUPADA"
    celda.usuario_actual_id = usuario.id

    db.add(historial)
    db.commit()
    db.refresh(celda)
    return celda


def liberar_celda_manual(db: Session, celda_codigo: str):
    celda = get_celda_by_codigo(db, celda_codigo)
    if not celda:
        raise ValueError("La celda no existe")
    if celda.estado != "OCUPADA":
        raise ValueError("La celda no está ocupada")

    historial_activo = get_historial_activo_por_celda(db, celda.id)
    usuario_liberado = celda.usuario_actual_id

    if historial_activo:
        historial_activo.liberado_en = datetime.utcnow()

    celda.estado = "DISPONIBLE"
    celda.usuario_actual_id = None

    db.commit()

    return {
        "celda_codigo": celda.codigo,
        "estado": celda.estado,
        "usuario_id_liberado": usuario_liberado,
        "liberado_en": historial_activo.liberado_en if historial_activo else datetime.utcnow(),
    }


def listar_historial_celdas(db: Session):
    registros = db.execute(
        select(models.HistorialCelda).order_by(models.HistorialCelda.ocupado_desde.desc())
    ).scalars().all()

    resultado = []
    for item in registros:
        celda = db.get(models.Celda, item.celda_id)
        usuario = db.get(models.Usuario, item.usuario_id)
        if not celda or not usuario:
            continue
        resultado.append({
            "id": item.id,
            "celda_codigo": celda.codigo,
            "usuario_id": usuario.id,
            "usuario_nombre": usuario.nombre,
            "usuario_identificacion": usuario.identificacion,
            "placa": usuario.placa,
            "ocupado_desde": item.ocupado_desde,
            "liberado_en": item.liberado_en,
        })
    return resultado


def generar_recibo(db: Session, usuario_id: int):
    return registrar_pago_manual(db=db, usuario_id=usuario_id, monto_cobrado=VALOR_MENSUAL_FIJO)


def _validar_campos_recibo(usuario: models.Usuario, monto_cobrado: int, fecha_inicio: datetime, fecha_vencimiento: datetime):
    if not usuario:
        raise ValueError("El usuario no existe")

    if not usuario_tiene_datos_completos(usuario):
        raise ValueError("No se puede generar recibo: datos incompletos del usuario")

    if monto_cobrado is None or monto_cobrado <= 0:
        raise ValueError("El monto cobrado es obligatorio y debe ser mayor que cero")

    if not fecha_inicio or not fecha_vencimiento:
        raise ValueError("Las fechas del recibo son obligatorias")


def registrar_pago_manual(db: Session, usuario_id: int, monto_cobrado: int):
    usuario = get_usuario(db, usuario_id)
    ahora = datetime.utcnow()
    fecha_vencimiento = ahora + timedelta(days=30)
    _validar_campos_recibo(usuario, monto_cobrado, ahora, fecha_vencimiento)

    usuario.fecha_ultimo_pago = ahora
    usuario.fecha_vencimiento = fecha_vencimiento
    usuario.estado_pago = "Al día"
    db.commit()
    db.refresh(usuario)

    folio = f"REC-{ahora.strftime('%Y%m%d%H%M%S')}-{usuario.id:05d}"
    periodo_cobertura = f"{ahora.strftime('%d/%m/%Y')} al {fecha_vencimiento.strftime('%d/%m/%Y')}"
    dias_restantes = max(0, (fecha_vencimiento.date() - ahora.date()).days)

    return {
        "folio": folio,
        "fecha": ahora,
        "concepto": "Mensualidad Parqueadero",
        "monto_cobrado": monto_cobrado,
        "periodo_cobertura": periodo_cobertura,
        "fecha_vencimiento": fecha_vencimiento,
        "dias_restantes_proximo_pago": dias_restantes,
        "cliente": usuario,
    }


def generarRecibo(db: Session, usuarioId: int):
    """Alias solicitado por el requerimiento funcional."""
    return generar_recibo(db=db, usuario_id=usuarioId)
