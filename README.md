# 🚗 Autos-Colombia

Sistema de gestión de parqueadero para la empresa **Autos Colombia**, desarrollado como proyecto académico para la asignatura **Diseño de Sistemas de Información**.

El sistema permite gestionar el ingreso y salida de vehículos dentro de un parqueadero, registrar novedades y controlar la disponibilidad de celdas.

---

# 🛠 Tecnologías utilizadas

- **Python 3**
- **FastAPI**
- **SQLAlchemy**
- **SQLite**
- **Uvicorn**
- **Git & GitHub**

Estas tecnologías permiten desarrollar una **API REST ligera**, con documentación automática y fácil de probar.

---

# ⚙️ Funcionalidades del sistema

El sistema permite:

✅ Registro de usuarios con datos personales y del vehículo (RFU-01)
✅ Asignación manual de celdas disponibles a usuarios registrados (RFC-03)
✅ Liberación manual de celdas ocupadas (RFC-04)
✅ Validación para evitar doble asignación de usuario o datos incompletos (CP-02)
✅ Historial de ocupación/liberación por celda (RFC-05)
✅ Generación de recibo mensual con folio, fecha y concepto fijo

---

# 🔌 Endpoints principales Iteración 2

- `POST /usuarios`
- `GET /usuarios`
- `GET /celdas`
- `POST /celdas/{celda_codigo}/asignar`
- `POST /celdas/{celda_codigo}/liberar`
- `GET /celdas/historial`
- `GET /usuarios/{usuario_id}/recibo-mensual`

---

# 🚀 Instalación y ejecución del proyecto

## 1. Clonar el repositorio

Primero debes clonar el repositorio desde GitHub.

```bash
git clone https://github.com/TU_USUARIO/Autos-Colombia.git
cd Autos-Colombia
```

---

## 2. Instalar dependencias necesarias

Es necesario instalar las librerías que utiliza el backend.

```bash
pip install fastapi uvicorn sqlalchemy
```

---

## 4. Encender el servidor

permitir la comunicación entre el **frontend** y el **backend**

⚠️ **IMPORTANTE:**
La terminal debe estar ubicada dentro de la carpeta:

```
backend/app
```

Luego ejecutar el siguiente comando:

```bash
cd backend/app
python -m uvicorn main:app --reload
```

Si todo funciona correctamente, el servidor se ejecutará en:

```
http://127.0.0.1:8000
```

---

# 📚 Proyecto académico

Proyecto desarrollado para la asignatura **Diseño de Sistemas de Información**.

Año **2026**
