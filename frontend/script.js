const API_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 8000;
const MESSAGE_TIMEOUT_MS = 60000;

const appState = {
  seccionActual: "",
  mensaje: { texto: "", exito: true },
  mensajeTimer: null,
  crudUsuarioEnProceso: false,
  usuariosCache: [],
};

const $ = (selector, parent = document) => parent.querySelector(selector);

function cancelarEvento(event) {
  if (!event) {
    return;
  }
  event.preventDefault?.();
  event.stopPropagation?.();
}

function asegurarVistaFormulario() {
  if (!appState.seccionActual) {
    return;
  }
  $("#menu-inicio")?.classList.add("oculto");
  $("#vista-formulario")?.classList.remove("oculto");
}

function limpiarMensaje() {
  if (appState.mensajeTimer) {
    clearTimeout(appState.mensajeTimer);
    appState.mensajeTimer = null;
  }

  appState.mensaje = { texto: "", exito: true };
  const mensaje = $("#mensaje");
  if (!mensaje) {
    return;
  }

  mensaje.innerHTML = "";
  mensaje.classList.remove("mensaje-ok", "mensaje-error");
}

function mostrarMensaje(texto, exito) {
  const mensaje = $("#mensaje");
  if (!mensaje) {
    return;
  }

  asegurarVistaFormulario();
  if (appState.mensajeTimer) {
    clearTimeout(appState.mensajeTimer);
    appState.mensajeTimer = null;
  }

  appState.mensaje = { texto, exito };
  mensaje.innerHTML = texto;
  mensaje.classList.toggle("mensaje-ok", Boolean(exito));
  mensaje.classList.toggle("mensaje-error", !exito);

  appState.mensajeTimer = setTimeout(() => {
    limpiarMensaje();
  }, MESSAGE_TIMEOUT_MS);
}

function restaurarMensaje() {
  if (!appState.mensaje.texto) {
    return;
  }
  mostrarMensaje(appState.mensaje.texto, appState.mensaje.exito);
}

async function mostrarAlertaConfirmacion(texto) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";

    overlay.innerHTML = `
      <div class="modal-contenido modal-contenido-sm">
        <h3 class="modal-titulo">Confirmación</h3>
        <p class="modal-texto">${texto}</p>
        <div class="modal-acciones" style="grid-template-columns: 1fr;">
          <button type="button" class="btn-confirmar" data-close-modal="true">Aceptar</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    const botonAceptar = $("button[data-close-modal='true']", overlay);

    const cerrar = () => {
      document.removeEventListener("keydown", onKeydown);
      overlay.remove();
      resolve();
    };

    const onKeydown = (event) => {
      if (event.key === "Enter" || event.key === "Escape") {
        cancelarEvento(event);
        cerrar();
      }
    };

    document.addEventListener("keydown", onKeydown);
    botonAceptar?.focus();
    botonAceptar?.addEventListener("click", (event) => {
      cancelarEvento(event);
      event.stopImmediatePropagation?.();
      cerrar();
    });
  });
}

async function apiRequest(endpoint, { method = "GET", body = null } = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const config = { method, signal: controller.signal, headers: {} };
    if (body !== null) {
      config.headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_URL}${endpoint}`, config);
    const raw = await response.text();

    let data = {};
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch {
        data = { detail: raw };
      }
    }

    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    if (error?.name === "AbortError") {
      return {
        ok: false,
        status: 408,
        data: {
          detail: "Tiempo de espera agotado al conectar con el servidor",
        },
      };
    }

    return {
      ok: false,
      status: 500,
      data: { detail: "Error de conexión con backend" },
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function obtenerLista(endpoint) {
  const respuesta = await apiRequest(endpoint);
  if (!respuesta.ok) {
    return [];
  }
  return Array.isArray(respuesta.data) ? respuesta.data : [];
}

const obtenerUsuarios = () => obtenerLista("/usuarios");
const obtenerCeldas = () => obtenerLista("/celdas");
const obtenerHistorial = () => obtenerLista("/celdas/historial");

function setCrudUsuarioEnProceso(enProceso, textoBoton = "Procesando...") {
  appState.crudUsuarioEnProceso = enProceso;

  const botones = document.querySelectorAll(
    'button[data-action="guardar-usuario"], button[data-action="editar-usuario"], button[data-action="eliminar-usuario"]',
  );

  botones.forEach((boton) => {
    if (enProceso) {
      boton.dataset.textoOriginal = boton.textContent;
      boton.textContent = textoBoton;
      boton.disabled = true;
      boton.style.opacity = "0.7";
      return;
    }

    boton.textContent = boton.dataset.textoOriginal || boton.textContent;
    boton.disabled = false;
    boton.style.opacity = "1";
    delete boton.dataset.textoOriginal;
  });
}

function htmlUsuariosRows(usuarios) {
  return usuarios
    .map(
      (usuario) => `
        <div class="fila fila-usuarios">
          <div>${usuario.nombre}</div>
          <div>${usuario.identificacion}</div>
          <div>${usuario.telefono}</div>
          <div>${usuario.placa}</div>
          <div class="${usuario.estado_pago === "Pendiente/Vencido" ? "error" : "ok"}">${usuario.estado_pago}</div>
          <div class="acciones-usuario">
            <button type="button" class="btn-mini" data-action="editar-usuario" data-usuario-id="${usuario.id}">Editar</button>
            <button type="button" class="btn-mini btn-liberar" data-action="eliminar-usuario" data-usuario-id="${usuario.id}">Eliminar</button>
          </div>
        </div>
      `,
    )
    .join("");
}

function htmlCeldasRows(celdas, opcionesUsuarios) {
  return celdas
    .map((celda) => {
      if (celda.estado === "DISPONIBLE") {
        return `
          <div class="fila">
            <div>${celda.codigo}</div>
            <div class="ok">DISPONIBLE</div>
            <div>
              <select id="usuario_celda_${celda.codigo}">
                <option value="">Seleccione usuario...</option>
                ${opcionesUsuarios}
              </select>
            </div>
            <div><button type="button" class="btn-mini" data-action="asignar-celda" data-celda="${celda.codigo}">Asignar</button></div>
          </div>
        `;
      }

      return `
        <div class="fila">
          <div>${celda.codigo}</div>
          <div class="error">OCUPADA</div>
          <div>${celda.usuario_nombre || "Sin vínculo"} ${celda.placa ? `(${celda.placa})` : ""}</div>
          <div><button type="button" class="btn-mini btn-liberar" data-action="liberar-celda" data-celda="${celda.codigo}">Liberar Celda</button></div>
        </div>
      `;
    })
    .join("");
}

function htmlHistorialRows(historial) {
  return historial
    .map(
      (item) => `
        <div class="fila">
          <div>${item.celda_codigo}</div>
          <div>${item.usuario_nombre}</div>
          <div>${item.placa}</div>
          <div>${new Date(item.ocupado_desde).toLocaleString()}</div>
          <div>${item.liberado_en ? new Date(item.liberado_en).toLocaleString() : "ACTIVA"}</div>
        </div>
      `,
    )
    .join("");
}

function htmlOpcionesUsuarios(usuarios) {
  return usuarios
    .map((u) => {
      const vencido = u.estado_pago === "Pendiente/Vencido";
      const estado = vencido ? "🔴 VENCIDO" : "🟢 AL DÍA";
      const clase = vencido ? "usuario-vencido" : "";
      return `<option class="${clase}" value="${u.id}" data-estado-pago="${u.estado_pago}">${estado} | ${u.nombre} - ${u.identificacion} - ${u.placa}</option>`;
    })
    .join("");
}

async function renderFormularioUsuario() {
  appState.usuariosCache = await obtenerUsuarios();
  const campos = $("#campos");
  if (!campos) {
    return;
  }

  campos.innerHTML = `
    <form id="form-usuario" class="panel-form" novalidate>
      <h3 class="panel-titulo">Registro de usuario</h3>
      <div class="campo-grid">
        <div class="campo-full">
          <label>Nombre</label>
          <input type="text" id="u_nombre" placeholder="Nombre completo" required>
        </div>

        <div>
          <label>ID / Identificación</label>
          <input type="text" id="u_identificacion" placeholder="Cédula o documento" required>
        </div>

        <div>
          <label>Teléfono</label>
          <input type="text" id="u_telefono" placeholder="3001234567" required>
        </div>

        <div>
          <label>Placa</label>
          <input type="text" id="u_placa" placeholder="ABC123" style="text-transform:uppercase" required>
        </div>

        <div>
          <label>Tipo de Vehículo</label>
          <select id="u_tipo" required>
            <option value="CARRO">Carro</option>
            <option value="MOTO">Moto</option>
          </select>
        </div>

        <div class="campo-full">
          <label>Color</label>
          <input type="text" id="u_color" placeholder="Blanco" required>
        </div>
      </div>

      <button type="submit" class="btn-confirmar" data-action="guardar-usuario">Guardar Usuario</button>
    </form>

    <div class="panel-form" style="margin-top: 14px;">
      <div class="usuarios-toolbar">
        <h3 class="panel-titulo" style="margin: 0;">Usuarios registrados</h3>
      </div>

      <div style="margin-top: 12px;">
        <div class="tabla-scroll">
          <div class="tabla-simple tabla-usuarios">
            <div class="fila fila-cabecera fila-usuarios">
              <div>Nombre</div>
              <div>ID</div>
              <div>Teléfono</div>
              <div>Placa</div>
              <div>Estado</div>
              <div>Acciones</div>
            </div>
            ${htmlUsuariosRows(appState.usuariosCache)}
          </div>
        </div>
      </div>
    </div>
  `;
}

async function renderModuloCeldas() {
  const campos = $("#campos");
  if (!campos) {
    return;
  }

  campos.innerHTML = "<p>Cargando celdas y usuarios...</p>";
  const [celdas, usuarios] = await Promise.all([
    obtenerCeldas(),
    obtenerUsuarios(),
  ]);

  campos.innerHTML = `
    <div class="panel-form">
      <h3 class="panel-titulo">Asignación y liberación manual de celdas</h3>
      <div class="tabla-scroll">
        <div class="tabla-simple">
          <div class="fila fila-cabecera">
            <div>Celda</div><div>Estado</div><div>Asignación Manual</div><div>Acción</div>
          </div>
          ${htmlCeldasRows(celdas, htmlOpcionesUsuarios(usuarios))}
        </div>
      </div>
    </div>
  `;

  restaurarMensaje();
}

async function renderHistorial() {
  const campos = $("#campos");
  if (!campos) {
    return;
  }

  campos.innerHTML = "<p>Cargando historial...</p>";
  const historial = await obtenerHistorial();

  if (!historial.length) {
    campos.innerHTML = "<p>No hay movimientos históricos todavía.</p>";
    return;
  }

  campos.innerHTML = `
    <div class="panel-form">
      <h3 class="panel-titulo">Movimientos históricos de celdas</h3>
      <div class="tabla-scroll">
        <div class="tabla-simple">
          <div class="fila fila-cabecera">
            <div>Celda</div><div>Usuario</div><div>Placa</div><div>Ocupó</div><div>Liberó</div>
          </div>
          ${htmlHistorialRows(historial)}
        </div>
      </div>
    </div>
  `;
}

async function renderRecibo() {
  const campos = $("#campos");
  if (!campos) {
    return;
  }

  const usuarios = await obtenerUsuarios();

  campos.innerHTML = `
    <form id="form-recibo" class="panel-form" novalidate>
      <h3 class="panel-titulo">Registro de pago mensual</h3>
      <div class="campo-grid">
        <div class="campo-full">
          <label>Seleccionar Usuario</label>
          <select id="usuario_recibo" required>
            <option value="">Seleccione...</option>
            ${usuarios.map((u) => `<option value="${u.id}">${u.nombre} - ${u.identificacion} (${u.estado_pago})</option>`).join("")}
          </select>
        </div>

        <div class="campo-full">
          <label>Monto cobrado</label>
          <input type="number" id="monto_cobrado" placeholder="Ej: 120000" min="1" step="1" required>
        </div>
      </div>

      <button type="submit" class="btn-confirmar" data-action="registrar-pago">Registrar Pago y Generar Recibo</button>
      <div id="resultado_recibo" style="margin-top:14px;"></div>
    </form>
  `;

  restaurarMensaje();
}

function leerPayloadUsuario() {
  return {
    nombre: $("#u_nombre")?.value.trim() || "",
    identificacion: $("#u_identificacion")?.value.trim() || "",
    telefono: $("#u_telefono")?.value.trim() || "",
    placa: $("#u_placa")?.value.trim().toUpperCase() || "",
    tipo_vehiculo: $("#u_tipo")?.value || "",
    color_vehiculo: $("#u_color")?.value.trim() || "",
  };
}

async function registrarUsuario() {
  if (appState.crudUsuarioEnProceso) {
    return;
  }

  const payload = leerPayloadUsuario();
  if (Object.values(payload).some((v) => !v)) {
    mostrarMensaje("❌ Completa todos los campos del usuario", false);
    return;
  }

  setCrudUsuarioEnProceso(true, "Guardando...");
  mostrarMensaje("⏳ Registrando usuario...", true);

  try {
    const respuesta = await apiRequest("/usuarios", {
      method: "POST",
      body: payload,
    });
    if (!respuesta.ok) {
      mostrarMensaje(
        `❌ Error: ${respuesta.data?.detail || "No fue posible registrar"}`,
        false,
      );
      return;
    }

    const texto = `✅ Usuario ${respuesta.data.nombre} registrado exitosamente`;
    mostrarMensaje(texto, true);
    await mostrarAlertaConfirmacion(texto);
  } finally {
    setCrudUsuarioEnProceso(false);
  }
}

async function editarUsuario(usuarioId) {
  if (appState.crudUsuarioEnProceso) {
    return;
  }

  const usuario = appState.usuariosCache.find((item) => item.id === usuarioId);
  if (!usuario) {
    mostrarMensaje("❌ Usuario no encontrado", false);
    return;
  }

  const nombre = prompt("Nombre", usuario.nombre);
  if (nombre === null) return;
  const identificacion = prompt("Identificación", usuario.identificacion);
  if (identificacion === null) return;
  const telefono = prompt("Teléfono", usuario.telefono);
  if (telefono === null) return;
  const placa = prompt("Placa", usuario.placa);
  if (placa === null) return;
  const tipo_vehiculo = prompt(
    "Tipo de vehículo (CARRO/MOTO)",
    usuario.tipo_vehiculo,
  );
  if (tipo_vehiculo === null) return;
  const color_vehiculo = prompt("Color", usuario.color_vehiculo);
  if (color_vehiculo === null) return;

  const payload = {
    nombre: nombre.trim(),
    identificacion: identificacion.trim(),
    telefono: telefono.trim(),
    placa: placa.trim().toUpperCase(),
    tipo_vehiculo: tipo_vehiculo.trim().toUpperCase(),
    color_vehiculo: color_vehiculo.trim().toUpperCase(),
  };

  if (Object.values(payload).some((v) => !v)) {
    mostrarMensaje("❌ Todos los campos son obligatorios para editar", false);
    return;
  }

  setCrudUsuarioEnProceso(true, "Guardando...");
  mostrarMensaje("⏳ Actualizando usuario...", true);

  try {
    const respuesta = await apiRequest(`/usuarios/${usuarioId}`, {
      method: "PUT",
      body: payload,
    });

    if (!respuesta.ok) {
      mostrarMensaje(
        `❌ Error: ${respuesta.data?.detail || "No fue posible actualizar"}`,
        false,
      );
      return;
    }

    const texto = `✅ Usuario ${respuesta.data.nombre} actualizado exitosamente`;
    mostrarMensaje(texto, true);
    await mostrarAlertaConfirmacion(texto);

    appState.usuariosCache = appState.usuariosCache.map((item) =>
      item.id === usuarioId ? { ...item, ...respuesta.data } : item,
    );

    const fila = document
      .querySelector(
        `button[data-action="editar-usuario"][data-usuario-id="${usuarioId}"]`,
      )
      ?.closest(".fila-usuarios");

    if (fila) {
      const columnas = fila.querySelectorAll(":scope > div");
      if (columnas.length >= 5) {
        columnas[0].textContent = respuesta.data.nombre;
        columnas[1].textContent = respuesta.data.identificacion;
        columnas[2].textContent = respuesta.data.telefono;
        columnas[3].textContent = respuesta.data.placa;
        columnas[4].textContent = respuesta.data.estado_pago;
        columnas[4].className =
          respuesta.data.estado_pago === "Pendiente/Vencido" ? "error" : "ok";
      }
    }
  } finally {
    setCrudUsuarioEnProceso(false);
  }
}

async function eliminarUsuario(usuarioId) {
  if (appState.crudUsuarioEnProceso) {
    return;
  }

  const usuario = appState.usuariosCache.find((item) => item.id === usuarioId);
  if (!usuario) {
    mostrarMensaje("❌ Usuario no encontrado", false);
    return;
  }

  if (!confirm(`¿Eliminar a ${usuario.nombre} (${usuario.identificacion})?`)) {
    return;
  }

  setCrudUsuarioEnProceso(true, "Eliminando...");
  mostrarMensaje("⏳ Eliminando usuario...", true);

  try {
    const respuesta = await apiRequest(`/usuarios/${usuarioId}`, {
      method: "DELETE",
    });

    if (!respuesta.ok) {
      mostrarMensaje(
        `❌ Error: ${respuesta.data?.detail || "No fue posible eliminar"}`,
        false,
      );
      return;
    }

    const texto = `✅ ${respuesta.data?.mensaje || "Usuario eliminado exitosamente"}`;
    mostrarMensaje(texto, true);
    await mostrarAlertaConfirmacion(texto);

    appState.usuariosCache = appState.usuariosCache.filter(
      (item) => item.id !== usuarioId,
    );

    const fila = document
      .querySelector(
        `button[data-action="eliminar-usuario"][data-usuario-id="${usuarioId}"]`,
      )
      ?.closest(".fila-usuarios");
    fila?.remove();
  } finally {
    setCrudUsuarioEnProceso(false);
  }
}

async function asignarCelda(celdaCodigo) {
  const selector = $(`#usuario_celda_${celdaCodigo}`);
  const usuarioId = Number(selector?.value);
  if (!usuarioId) {
    mostrarMensaje("❌ Selecciona un usuario para asignar", false);
    return;
  }

  const estadoPago =
    selector.options[selector.selectedIndex]?.dataset?.estadoPago;
  if (estadoPago === "Pendiente/Vencido") {
    mostrarMensaje(
      "❌ Usuario con mensualidad vencida. Debes registrar pago antes de asignar la celda.",
      false,
    );
    return;
  }

  const respuesta = await apiRequest(`/celdas/${celdaCodigo}/asignar`, {
    method: "POST",
    body: { usuario_id: usuarioId },
  });

  if (!respuesta.ok) {
    mostrarMensaje(
      `❌ Error: ${respuesta.data?.detail || "No fue posible asignar"}`,
      false,
    );
    return;
  }

  const texto = `✅ Celda ${celdaCodigo} asignada a ${respuesta.data.usuario_nombre}`;
  mostrarMensaje(texto, true);
  await mostrarAlertaConfirmacion(texto);
}

async function liberarCelda(celdaCodigo) {
  const respuesta = await apiRequest(`/celdas/${celdaCodigo}/liberar`, {
    method: "POST",
  });

  if (!respuesta.ok) {
    mostrarMensaje(
      `❌ Error: ${respuesta.data?.detail || "No fue posible liberar"}`,
      false,
    );
    return;
  }

  const texto = `✅ Celda ${celdaCodigo} liberada`;
  mostrarMensaje(texto, true);
  await mostrarAlertaConfirmacion(texto);
}

function renderReciboResultado(data) {
  return `
    <div class="vehiculo-info">
      <div class="recibo-grid">
        <div class="recibo-item"><b>Folio:</b> ${data.folio}</div>
        <div class="recibo-item"><b>Fecha:</b> ${new Date(data.fecha).toLocaleString()}</div>
        <div class="recibo-item recibo-item-full"><b>Cliente:</b> ${data.cliente.nombre} - ${data.cliente.identificacion}</div>
        <div class="recibo-item"><b>Teléfono:</b> ${data.cliente.telefono}</div>
        <div class="recibo-item"><b>Placa:</b> ${data.cliente.placa}</div>
        <div class="recibo-item recibo-item-full"><b>Vehículo:</b> ${data.cliente.tipo_vehiculo} ${data.cliente.color_vehiculo}</div>
        <div class="recibo-item"><b>Concepto:</b> ${data.concepto}</div>
        <div class="recibo-item"><b>Monto cobrado:</b> $${data.monto_cobrado}</div>
        <div class="recibo-item recibo-item-full"><b>Periodo de cobertura:</b> ${data.periodo_cobertura}</div>
        <div class="recibo-item"><b>Días restantes:</b> ${data.dias_restantes_proximo_pago}</div>
        <div class="recibo-item"><b>Vencimiento:</b> ${new Date(data.fecha_vencimiento).toLocaleDateString()}</div>
        <div class="recibo-item recibo-item-full"><b>Estado de pago:</b> ${data.cliente.estado_pago}</div>
      </div>
    </div>
  `;
}

async function generarReciboMensual() {
  const usuarioId = $("#usuario_recibo")?.value;
  const montoCobrado = Number($("#monto_cobrado")?.value);

  if (!usuarioId) {
    mostrarMensaje("❌ Selecciona un usuario", false);
    return;
  }

  if (!montoCobrado || montoCobrado <= 0) {
    mostrarMensaje(
      "❌ El monto cobrado es obligatorio y debe ser mayor que 0",
      false,
    );
    return;
  }

  const respuesta = await apiRequest(`/usuarios/${usuarioId}/pagos/manual`, {
    method: "POST",
    body: { monto_cobrado: montoCobrado },
  });

  if (!respuesta.ok) {
    mostrarMensaje(
      `❌ Error: ${respuesta.data?.detail || "No fue posible generar recibo"}`,
      false,
    );
    return;
  }

  const resultadoRecibo = $("#resultado_recibo");
  if (resultadoRecibo) {
    resultadoRecibo.innerHTML = renderReciboResultado(respuesta.data);
  }

  const texto = "✅ Recibo generado correctamente";
  mostrarMensaje(texto, true);
  await mostrarAlertaConfirmacion(texto);
}

async function abrirSeccion(tipo) {
  const config = {
    usuarios: {
      titulo: "Registro de Usuario (RFU-01)",
      render: renderFormularioUsuario,
    },
    celdas: {
      titulo: "Asignación/Liberación Manual (RFC-03 / RFC-04)",
      render: renderModuloCeldas,
    },
    historial: {
      titulo: "Historial de Celdas (RFC-05)",
      render: renderHistorial,
    },
    recibo: {
      titulo: "Generación de Recibo Mensual",
      render: renderRecibo,
    },
  }[tipo];

  if (!config) {
    return;
  }

  appState.seccionActual = tipo;
  sessionStorage.setItem("seccionActiva", tipo);

  $("#menu-inicio")?.classList.add("oculto");
  $("#vista-formulario")?.classList.remove("oculto");
  $("#titulo-form").innerText = config.titulo;
  $("#campos").innerHTML = "";
  limpiarMensaje();

  await config.render();
}

function regresar() {
  $("#menu-inicio")?.classList.remove("oculto");
  $("#vista-formulario")?.classList.add("oculto");
  appState.seccionActual = "";
  sessionStorage.removeItem("seccionActiva");
  limpiarMensaje();
}

async function manejarClickAccion(event) {
  const boton = event.target.closest("button[data-action]");
  if (!boton) {
    return;
  }

  cancelarEvento(event);

  const action = boton.dataset.action;
  switch (action) {
    case "guardar-usuario": {
      await registrarUsuario();
      return;
    }
    case "registrar-pago": {
      await generarReciboMensual();
      return;
    }
    case "editar-usuario": {
      const id = Number(boton.dataset.usuarioId);
      if (id) {
        await editarUsuario(id);
      }
      return;
    }
    case "eliminar-usuario": {
      const id = Number(boton.dataset.usuarioId);
      if (id) {
        await eliminarUsuario(id);
      }
      return;
    }
    case "asignar-celda": {
      const celda = boton.dataset.celda;
      if (celda) {
        await asignarCelda(celda);
      }
      return;
    }
    case "liberar-celda": {
      const celda = boton.dataset.celda;
      if (celda) {
        await liberarCelda(celda);
      }
      return;
    }
    default:
      return;
  }
}

async function manejarSubmit(event) {
  const form = event.target.closest("form");
  if (!form) {
    return;
  }

  cancelarEvento(event);

  if (form.id === "form-usuario") {
    await registrarUsuario();
    return;
  }

  if (form.id === "form-recibo") {
    await generarReciboMensual();
  }
}

async function inicializar() {
  document.querySelectorAll(".btn-menu[data-seccion]").forEach((boton) => {
    boton.addEventListener("click", async (event) => {
      cancelarEvento(event);
      const seccion = boton.dataset.seccion;
      if (seccion) {
        await abrirSeccion(seccion);
      }
    });
  });

  $("#btn-volver")?.addEventListener("click", (event) => {
    cancelarEvento(event);
    regresar();
  });

  const campos = $("#campos");
  campos?.addEventListener("click", manejarClickAccion);
  campos?.addEventListener("submit", manejarSubmit);

  const ultimaSeccion = sessionStorage.getItem("seccionActiva");
  if (ultimaSeccion) {
    await abrirSeccion(ultimaSeccion);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  inicializar();
});
