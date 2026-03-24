# Autos Colombia

Aplicación web de gestión de parqueadero con frontend en JavaScript vanilla y backend en FastAPI.

## Funcionalidad principal

- Registro, edición y eliminación de usuarios.
- Asignación y liberación manual de celdas.
- Historial de ocupación/liberación de celdas.
- Registro de pago mensual y generación de recibo.
- Endpoints auxiliares para ingresos, salidas, consulta de vehículos y novedades.

## Stack

- Python 3.10+
- FastAPI
- SQLAlchemy (SQLite)
- JavaScript, HTML y CSS

## Estructura

- `backend/app`: API, lógica de negocio y base de datos SQLite.
- `frontend`: interfaz de usuario (archivo estático).

## Ejecutar backend

1. Crear entorno virtual (opcional pero recomendado).
2. Instalar dependencias:

```bash
pip install -r backend/requirements.txt
```

3. Levantar API:

```bash
cd backend/app
python -m uvicorn main:app --reload
```

La API queda en `http://127.0.0.1:8000`.

## Ejecutar frontend

Abre `frontend/index.html` con tu servidor estático favorito (por ejemplo Five Server en VS Code).

## Endpoints clave

- `GET /usuarios`
- `POST /usuarios`
- `PUT /usuarios/{usuario_id}`
- `DELETE /usuarios/{usuario_id}`
- `GET /celdas`
- `POST /celdas/{celda_codigo}/asignar`
- `POST /celdas/{celda_codigo}/liberar`
- `GET /celdas/historial`
- `POST /usuarios/{usuario_id}/pagos/manual`
