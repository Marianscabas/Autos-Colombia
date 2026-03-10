const API_URL = "http://127.0.0.1:8000";

/**
 * 1. NAVEGACIÓN ENTRE VISTAS
 */
async function abrirSeccion(tipo) {
  const menu = document.getElementById("menu-inicio");
  const vista = document.getElementById("vista-formulario");
  const titulo = document.getElementById("titulo-form");
  const campos = document.getElementById("campos");
  const mensaje = document.getElementById("mensaje");

  // Limpiar pantalla
  menu.classList.add("oculto");
  vista.classList.remove("oculto");
  mensaje.innerText = "";
  campos.innerHTML = "";

  if (tipo === "entrada") {
    titulo.innerText = "Registrar Entrada";
    campos.innerHTML = "<p>Cargando celdas disponibles...</p>";

    const celdas = await obtenerCeldas();
    const disponibles = celdas.filter((c) => c.estado === "DISPONIBLE");

    campos.innerHTML = `
            <label>Placa del Vehículo</label>
            <input type="text" id="placa" placeholder="ABC123" style="text-transform:uppercase">
            
            <label>Tipo de Vehículo</label>
            <select id="tipo_v">
                <option value="CARRO">Carro</option>
                <option value="MOTO">Moto</option>
            </select>
            
            <label>Seleccionar Celda</label>
            <select id="celda">
                ${disponibles.map((c) => `<option value="${c.codigo}">${c.codigo}</option>`).join("") || '<option value="">No hay celdas libres</option>'}
            </select>
            
            <button class="btn-confirmar" onclick="ejecutarEntrada()">Confirmar Ingreso</button>
        `;
  } else if (tipo === "salida") {
    titulo.innerText = "Registrar Salida";
    campos.innerHTML = `
            <label>Placa del Vehículo</label>
            <input type="text" id="placa_salida" placeholder="ABC123" style="text-transform:uppercase">
            <button class="btn-confirmar" style="background:#dc3545" onclick="ejecutarSalida()">Liquidar y Salir</button>
        `;
  } else if (tipo === "estado") {
    titulo.innerText = "Estado de Celdas";
    const celdas = await obtenerCeldas();
    campos.innerHTML = `
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                ${celdas
                  .map(
                    (c) => `
                    <div class="celda-item" style="background:${c.estado === "DISPONIBLE" ? "#d4edda" : "#f8d7da"}; padding:10px; border-radius:10px; font-size:12px; font-weight:bold;">
                        ${c.codigo}<br><small>${c.estado}${c.placa ? ` – ${c.placa}` : ""}</small>
                    </div>
                `,
                  )
                  .join("")}
            </div>
            <div/><span style="font-size:12px; color:#555; margin-top:10px;">CELDAS LIBRES<span style="color:#28a745;"> VERDE</span> | CELDAS OCUPADAS <span style="color:#dc3545;">ROJO</span></div>
        `;
  } else if (tipo === "buscar") {
    titulo.innerText = "Buscar Vehículo";
    campos.innerHTML = `
            <input type="text" id="busqueda" placeholder="PLACA O CELDA" style="text-transform:uppercase">
            <button class="btn-confirmar" onclick="ejecutarBusqueda()">Buscar</button>
            <div id="resultado" style="margin-top:20px; text-align:left; border-top:1px solid #eee; padding-top:10px;"></div>
        `;
  }
}

function regresar() {
  document.getElementById("menu-inicio").classList.remove("oculto");
  document.getElementById("vista-formulario").classList.add("oculto");
}

/**
 * 2. FUNCIONES DE API (HABLAR CON PYTHON)
 */

async function obtenerCeldas() {
  try {
    const res = await fetch(`${API_URL}/celdas`);
    return await res.json();
  } catch (e) {
    return [];
  }
}

async function ejecutarEntrada() {
  // eliminar espacios accidentales y normalizar
  const placa = document.getElementById("placa").value.trim().toUpperCase();
  const tipo = document.getElementById("tipo_v").value;
  const celda = document.getElementById("celda").value.trim();

  if (!placa || !celda) return mostrarMensaje("❌ Completa los campos", false);

  try {
    // la API espera el payload en el cuerpo como JSON, no en query params
    const payload = {
      placa,
      tipo_vehiculo: tipo,
      celda_codigo: celda,
      operador_id: 1, // usando operador demo
    };
    console.log("POST /ingresos", payload);
    const res = await fetch(`${API_URL}/ingresos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    console.log("respuesta ingresos", res.status, data);

    if (res.ok) {
      mostrarMensaje(`✅ Vehículo ${placa} registrado en ${celda}`, true);
    } else {
      // AQUÍ CORREGIMOS EL [object Object]
      const errorTxt = data.detail || "Error en el registro";
      mostrarMensaje(`❌ Error: ${errorTxt}`, false);
    }
  } catch (e) {
    mostrarMensaje("⚠️ El servidor Python no responde", false);
  }
}

async function ejecutarSalida() {
  const placa = document
    .getElementById("placa_salida")
    .value.trim()
    .toUpperCase();
  if (!placa) return mostrarMensaje("❌ Escribe la placa", false);

  try {
    const payload = { placa };
    console.log("POST /salidas", payload);
    const res = await fetch(`${API_URL}/salidas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    console.log("respuesta salidas", res.status, data);

    if (res.ok) {
      mostrarMensaje(
        `✅ Salida exitosa.<br>Total a pagar: $${data.valor_pagar}`,
        true,
      );
    } else {
      mostrarMensaje(`❌ Error: ${data.detail}`, false);
    }
  } catch (e) {
    mostrarMensaje("⚠️ Error de conexión", false);
  }
}

async function ejecutarBusqueda() {
  const term = document.getElementById("busqueda").value.trim().toUpperCase();
  const res = await fetch(`${API_URL}/ingresos`);
  const ingresos = await res.json();
  console.log("GET /ingresos =>", ingresos);
  const v = ingresos.find((i) => i.placa === term || i.celda === term);

  const div = document.getElementById("resultado");
  if (v) {
    div.innerHTML = `
    <div class="vehiculo-info" >
   <div style="font-size:18px; font-weight:bold; margin-bottom:10px;">Información del Vehículo</div>
      <p><b>Placa:</b> ${v.placa}</p>
      <p><b>Celda:</b> ${v.celda}</p>
      <p><b>Estado:</b> Activo</p>
      <p><b>Ingreso:</b> ${new Date(v.hora_ingreso).toLocaleString()}</p> 
      

      </div>
    `;
  } else {
    div.innerHTML = "<p style='color:red'>No se encontró registro activo.</p>";
  }
}

function mostrarMensaje(texto, exito) {
  const m = document.getElementById("mensaje");
  m.innerHTML = texto;
  m.style.color = exito ? "#28a745" : "#dc3545";
  if (exito) setTimeout(regresar, 3000);
}
