import streamlit as st
import pandas as pd
import hashlib
import os
import pathlib
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Conectar a Google Sheets localmente con tu archivo .json ===
def conectar_google_libro(nombre_archivo, ruta_credenciales="credenciales.json"):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(ruta_credenciales, scope)
    client = gspread.authorize(credentials)
    return client.open(nombre_archivo)  # ✅ Devuelve el libro completo



st.set_page_config(page_title="QOMI - Iniciar sesión", layout="centered")

if "vista" not in st.session_state:
    st.session_state.vista = "login"
    
@st.cache_data(ttl=60)
def cargar_usuarios():
    hoja = sheet_usuarios.sheet1
    return pd.DataFrame(hoja.get_all_records())

SHEET_NAME = "usuarios"  # nombre del archivo en Google Sheets
sheet_usuarios = conectar_google_libro(SHEET_NAME)
hoja_usuarios = sheet_usuarios.sheet1
df_usuarios = cargar_usuarios()



import hashlib

def autenticar(usuario, password):
    hash_pw = hashlib.sha256(password.encode()).hexdigest()
    user = df_usuarios[df_usuarios["usuario"] == usuario]
    return not user.empty and user.iloc[0]["password_hash"] == hash_pw


def registrar_usuario(usuario, password):
    if usuario in df_usuarios["usuario"].values:
        return False, "El usuario ya existe."

    hash_pw = hashlib.sha256(password.encode()).hexdigest()
    hoja_usuarios = sheet_usuarios.sheet1  # ✅ Accedemos a la hoja real
    hoja_usuarios.append_row([usuario, hash_pw])  # ✅ Guardamos el nuevo usuario
    st.cache_data.clear()  # 🧠 Limpiamos la caché para que se recargue
    return True, "Usuario registrado correctamente."


# CSS estilo enlace
st.markdown("""
<style>
.link-button > button {
    color: #1a73e8;
    background: none!important;
    border: none;
    padding: 0!important;
    font-size: 14px;
    text-decoration: underline;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.custom-red > button {
    background-color: #f44336 !important;
    color: white !important;
    font-size: 16px !important;
    padding: 10px 24px !important;
    border-radius: 10px !important;
    border: none !important;
    cursor: pointer;
}
.custom-red > button:hover {
    background-color: #d32f2f !important;
}
</style>
""", unsafe_allow_html=True)

# LOGIN
if st.session_state.vista == "login":
    st.markdown("<h2 style='text-align: center; font-size: 32px; margin-bottom: 20px;'>INICIAR SESION</h2>", unsafe_allow_html=True)

    st.write("¿Es tu primera vez?")
    if st.button("Regístrate", key="to_register", help="Ir a registro", type="primary"):
        st.session_state.vista = "registro"
        st.rerun()

    usuario = st.text_input("Email *")
    password = st.text_input("Contraseña *", type="password")

    if st.button("¿Olvidaste tu contraseña?", key="to_recover", help="Ir a recuperación"):
        st.session_state.vista = "recuperar"
        st.rerun()
        
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        st.markdown('<div class="custom-red">', unsafe_allow_html=True)
        if st.button("Iniciar sesión"):
            if not usuario or not password:
                st.warning("⚠️ Completa todos los campos.")
            elif autenticar(usuario, password):
                if autenticar(usuario, password):
                    st.success("Bienvenido.")
                    st.session_state.usuario = usuario
                    st.session_state.vista = "panel"
                    st.rerun()

            else:
                st.error("❌ Usuario o contraseña incorrectos.")
        st.markdown('</div>', unsafe_allow_html=True)


# REGISTRO
elif st.session_state.vista == "registro":
    st.markdown("## Crear cuenta")

    nuevo_usuario = st.text_input("Email *", key="new_user")
    nueva_pass = st.text_input("Contraseña *", type="password", key="new_pass")

    if st.button("Registrarme"):
        if not nuevo_usuario or not nueva_pass:
            st.warning("Completa todos los campos.")
        else:
            ok, msg = registrar_usuario(nuevo_usuario, nueva_pass)
            if ok:
                st.success(msg)
                st.session_state.vista = "login"
                st.rerun()
            else:
                st.warning(msg)

    if st.button("⬅ Volver al inicio", key="back_login1"):
        st.session_state.vista = "login"
        st.rerun()

# ========== RECUPERAR CONTRASEÑA ==========
elif st.session_state.vista == "recuperar":
    st.markdown("## Recuperar contraseña")

    email = st.text_input("Correo registrado *")

    if st.button("Verificar"):
        if email in df_usuarios["usuario"].values:
            st.session_state.recuperar_usuario = email
            st.session_state.vista = "reset_password"
            st.rerun()
        else:
            st.warning("⛔ Correo no registrado.")

    if st.button("⬅ Volver al inicio", key="back_login2"):
        st.session_state.vista = "login"
        st.rerun()

# ========== CAMBIAR CONTRASEÑA ==========
elif st.session_state.vista == "reset_password":
    st.markdown("## Restablecer contraseña")
    st.markdown(f"**Usuario:** {st.session_state.recuperar_usuario}")

    nueva_pass = st.text_input("Nueva contraseña", type="password")
    confirmar_pass = st.text_input("Confirmar contraseña", type="password")

    if st.button("Guardar nueva contraseña"):
        if not nueva_pass or not confirmar_pass:
            st.warning("⚠️ Completa todos los campos.")
        elif len(nueva_pass) < 3:
            st.warning("🔐 La contraseña debe tener al menos 6 caracteres.")
        elif nueva_pass != confirmar_pass:
            st.error("❌ Las contraseñas no coinciden.")
        else:
            # Actualizar contraseña en el Excel
            nueva_hash = hashlib.sha256(nueva_pass.encode()).hexdigest()
            hoja_usuarios = sheet_usuarios.sheet1  # accede a la hoja real
            registros = hoja_usuarios.get_all_records()

            for i, fila in enumerate(registros):
                if fila["usuario"] == st.session_state.recuperar_usuario:
                    hoja_usuarios.update_cell(i + 2, 2, nueva_hash)  # fila + 2 por cabecera y 1-based index
                    st.cache_data.clear()  # limpia el cache si usas @st.cache_data
                    break



            st.success("✅ Contraseña actualizada correctamente.")
            st.session_state.vista = "login"
            st.session_state.recuperar_usuario = None
            st.rerun()

    if st.button("⬅ Cancelar"):
        st.session_state.vista = "login"
        st.session_state.recuperar_usuario = None
        st.rerun()

TIENDAS = [
    {"nombre": "Cafetería Piso 6", "imagen": "img/tienda2.jpg"},
    {"nombre": "Restaurante Piso 2", "imagen": "img/tienda2.jpg"},
    {"nombre": "Cafeteria piso 10", "imagen": "img/tienda2.jpg"},
    {"nombre": "Cafeteria piso 1", "imagen": "img/tienda2.jpg"}
]

#-------------------------------------

SHEET_RESERVAS = conectar_google_libro("reservas")

from datetime import datetime

def registrar_reserva_en_google(tienda, usuario, total, hora_recojo, carrito):
    try:
        hoja = SHEET_RESERVAS.worksheet(tienda)
        productos_texto = ', '.join([f"{p['nombre']} x{p['cantidad']}" for p in carrito])
        nueva_fila = [
            usuario,
            total,
            hora_recojo.strftime("%H:%M"),
            datetime.now().strftime("%d/%m/%Y"),
            productos_texto
        ]
        hoja.append_row(nueva_fila)
    except Exception as e:
        st.error(f"Error al guardar reserva: {e}")


# Conexión a Google Sheets
SHEET_STOCK = conectar_google_libro("stock_restaurantes")

import time

@st.cache_data(ttl=60)
def cargar_reservas_por_tienda(nombre_hoja):
    try:
        hoja = SHEET_RESERVAS.worksheet(nombre_hoja)
        time.sleep(0.3)  # evita error 429
        df = pd.DataFrame(hoja.get_all_records())
        return df
    except Exception as e:
        st.warning(f"No se pudo acceder a la hoja '{nombre_hoja}': {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def cargar_stock_desde_google():
    datos = {}
    for tienda in TIENDAS:
        nombre = tienda["nombre"]
        try:
            hoja = SHEET_STOCK.worksheet(nombre)
            df = pd.DataFrame(hoja.get_all_records())
            datos[nombre] = df
            time.sleep(0.3)  # evita error 429
        except Exception as e:
            st.warning(f"No se pudo leer la hoja '{nombre}': {e}")
    return datos

stock_data = cargar_stock_desde_google()


#-------------------------------------

def formatear_nombre(nombre):
    return nombre.lower() \
        .replace(" ", "") \
        .replace("á", "a").replace("é", "e").replace("í", "i") \
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")




def obtener_menu_tienda(tienda):
    if tienda in stock_data:
        df = stock_data[tienda]
        return [
            {
                "nombre": row["producto"],
                "precio": float(row["precio"]),
                "stock": int(row["stock"]),
                "imagen": f"img/{formatear_nombre(row['producto'])}.jpeg"
            }
            for _, row in df.iterrows()
        ]
    return []

def actualizar_stock_google(nombre_tienda, carrito):
    try:
        hoja = SHEET_STOCK.worksheet(nombre_tienda)
        df = pd.DataFrame(hoja.get_all_records())

        for item in carrito:
            producto = item["nombre"]
            cantidad = item.get("cantidad", 1)
            idx = df[df["producto"] == producto].index
            if not idx.empty:
                i = idx[0]
                df.at[i, "stock"] = max(0, df.at[i, "stock"] - cantidad)

        hoja.clear()
        hoja.update([df.columns.values.tolist()] + df.values.tolist())

    except Exception as e:
        st.error(f"Error al actualizar el stock: {e}")


#---------------------------------------

#-------------------


if st.session_state.vista == "panel":
    
    # ========== NAVBAR CSS ==========
    st.markdown("""
    <style>
    .navbar {
        display: flex;
        justify-content: center;
        gap: 40px;
        font-family: 'Segoe UI', sans-serif;
        margin-top: 10px;
        margin-bottom: 30px;
    }
    .nav-item {
        color: #888;
        font-size: 16px;
        cursor: pointer;
        position: relative;
        transition: all 0.2s ease-in-out;
    }
    .nav-item:hover {
        color: #f44336;
    }
    .nav-item.active {
        color: #f44336;
    }
    .nav-item.active::after {
        content: '';
        position: absolute;
        width: 6px;
        height: 6px;
        background: #f44336;
        border-radius: 50%;
        bottom: -8px;
        left: 50%;
        transform: translateX(-50%);
    }
    </style>
    """, unsafe_allow_html=True)

    # Inicializar si no existe
    if "nav" not in st.session_state:
        st.session_state.nav = "Inicio"
    if "tienda_seleccionada" not in st.session_state:
        st.session_state.tienda_seleccionada = None

    # ====== NAVEGACIÓN CON RADIO ======
    menu_items = ["Inicio", "Tiendas", "Reservas", "Servicios", "Carrito"]

    selected = st.radio(
        label="",
        options=menu_items,
        horizontal=True,
        index=menu_items.index(st.session_state.nav)
    )
    st.session_state.nav = selected
        

    if selected == "Inicio":
        st.markdown(f"<h2 style='text-align:center;'> Bienvenido a Qomi, {st.session_state.usuario}</h2>", unsafe_allow_html=True)

        st.markdown("""
        <p style='text-align:center; font-size:18px;'>
            Somos una app donde encontrarás <strong>una variedad de comida</strong>,<br>
            disponible en nuestras tiendas universitarias y asociadas.
        </p>
        """, unsafe_allow_html=True)

        # ✅ Mostrar imagen centrada con Streamlit
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            st.image("logoqomi.png", width=200)  # Asegúrate de que esté en la misma carpeta que tu .py

        st.markdown("<hr>", unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Cerrar sesión"):
                st.session_state.vista = "login"
                st.session_state.usuario = None
                st.session_state.nav = "Inicio"
                st.rerun()
        with col2:
            st.markdown("""
            <div style="text-align:right;">
            📬 <strong>Contacto:</strong> qomi@gmail.com<br>
            ☎️ <strong>Teléfono:</strong> 972 948 119
            </div>
            """, unsafe_allow_html=True)

#------------------------------------------------------------------------------------------

        # Asegurar estados
    if "tienda_seleccionada" not in st.session_state:
        st.session_state.tienda_seleccionada = None
    if "vista_tiendas" not in st.session_state:
        st.session_state.vista_tiendas = "catalogo"  # puede ser "catalogo" o "menu"

    # ===================== SECCIÓN TIENDAS =====================
    if selected == "Tiendas":

        # ----------- CATÁLOGO DE TIENDAS -----------
        if st.session_state.vista_tiendas == "catalogo":
            st.markdown("<h2 style='text-align:center;'>Nuestras Tiendas</h2>", unsafe_allow_html=True)
            st.write("Selecciona una tienda para continuar:")

            cols = st.columns(2)

            for i, tienda in enumerate(TIENDAS):
                with cols[i % 2]:
                    st.image(tienda["imagen"], width=300, caption=tienda["nombre"])
                    if st.button(f"Seleccionar {tienda['nombre']}", key=f"btn_tienda_{i}"):
                        st.session_state.tienda_seleccionada = tienda["nombre"]
                        st.session_state.vista_tiendas = "menu"
                        st.rerun()

        # ----------- MENÚ DE LA TIENDA -----------
        elif st.session_state.vista_tiendas == "menu":
            tienda = st.session_state.tienda_seleccionada
            productos = obtener_menu_tienda(tienda)

            st.markdown(f"<h2 style='text-align:center;'>🍽️ Menú de {tienda}</h2>", unsafe_allow_html=True)

            if productos:
                for i in range(0, len(productos), 3):
                    row = productos[i:i+3]
                    cols = st.columns(len(row))

                    for j, producto in enumerate(row):
                        with cols[j]:
                            st.markdown("""
                                <div style="background:#fff; border-radius:15px; padding:15px; text-align:center;
                                            box-shadow:0 4px 10px rgba(0,0,0,0.05); margin-bottom:25px;">
                            """, unsafe_allow_html=True)

                            if os.path.exists(producto["imagen"]):
                                st.image(producto["imagen"], width=130)
                            else:
                                st.warning("Sin imagen")
                            
                            st.markdown(f"""
                                <h4 style="margin:10px 0;">{producto['nombre']}</h4>
                                <p style="font-size:18px; margin:5px 0; color:#f44336;">
                                    <strong>S/. {producto['precio']:.2f}</strong>
                                </p>
                                <p style="font-size:14px; color:#555;">🟢 Stock: {producto['stock']} unidades</p>
                            """, unsafe_allow_html=True)

                            
                            if st.button(f"Agregar {producto['nombre']}", key=f"add_{producto['nombre']}"):
                                # Ver cuántas veces ya está ese producto en el carrito
                                cantidad_en_carrito = sum(p["cantidad"] for p in st.session_state.carrito if p["nombre"] == producto["nombre"])

                                if cantidad_en_carrito >= producto["stock"]:
                                    st.error("⛔ Ya has agregado todas las unidades disponibles de este producto.")
                                else:
                                    agregado = False
                                    # Buscar si ya está en el carrito
                                    for p in st.session_state.carrito:
                                        if p["nombre"] == producto["nombre"]:
                                            p["cantidad"] += 1
                                            agregado = True
                                            break
                                    if not agregado:
                                        producto_copia = producto.copy()
                                        producto_copia["cantidad"] = 1
                                        st.session_state.carrito.append(producto_copia)

                                    st.success(f"🛒 {producto['nombre']} agregado al carrito")


                            st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning("Esta tienda aún no tiene menú definido.")


            if st.button("⬅ Volver a las tiendas"):
                st.session_state.vista_tiendas = "catalogo"
                st.session_state.tienda_seleccionada = None
                st.rerun()



        # Inicialización de estados
    if "carrito" not in st.session_state:
        st.session_state.carrito = []
    if "vista_carrito" not in st.session_state:
        st.session_state.vista_carrito = "resumen"

    # =============== VISTA: CARRITO ===============
    if selected == "Carrito" and st.session_state.vista_carrito == "resumen":
        st.markdown("<h2 style='text-align:center;'>🛒 Tu Carrito</h2>", unsafe_allow_html=True)

        if "carrito" not in st.session_state or not st.session_state.carrito:
            st.info("Tu carrito está vacío.")
        else:
            tienda = st.session_state.get("tienda_seleccionada")
            stock_df = stock_data.get(tienda, pd.DataFrame()) if tienda else pd.DataFrame()

            # Agrupar productos por nombre con cantidades
            items = {}
            for p in st.session_state.carrito:
                if p['nombre'] in items:
                    items[p['nombre']]['cantidad'] += 1
                else:
                    items[p['nombre']] = {**p, 'cantidad': 1}

            total = 0
            for i, (nombre, prod) in enumerate(items.items()):
                cantidad = prod['cantidad']
                subtotal = prod['precio'] * cantidad
                total += subtotal

                # Obtener stock disponible desde el Excel
                stock_disponible = stock_df.loc[stock_df["producto"] == nombre, "stock"].values[0] if not stock_df.empty and nombre in stock_df["producto"].values else None

                col1, col2, col3, col4, col5 = st.columns([2, 1, 3, 1, 2])
                with col1:
                    st.markdown(f"**{nombre}**")
                with col2:
                    st.markdown(f"S/. {prod['precio']:.2f}")
                with col3:
                    col_plus, col_cant, col_minus = st.columns([1, 2, 1])
                    with col_plus:
                        if stock_disponible is None or cantidad < stock_disponible:
                            if st.button("➕", key=f"plus_{i}"):
                                st.session_state.carrito.append(prod)
                                st.rerun()
                        else:
                            st.button("➕", key=f"plus_{i}", disabled=True)
                    with col_cant:
                        st.markdown(f"<p style='text-align:center; margin-top:7px;'>{cantidad}</p>", unsafe_allow_html=True)
                    with col_minus:
                        if st.button("➖", key=f"minus_{i}"):
                            for idx, item in enumerate(st.session_state.carrito):
                                if item["nombre"] == nombre:
                                    del st.session_state.carrito[idx]
                                    break
                            st.rerun()
                with col4:
                    if st.button("🗑️", key=f"delete_{i}"):
                        st.session_state.carrito = [item for item in st.session_state.carrito if item["nombre"] != nombre]
                        st.rerun()
                with col5:
                    st.markdown(f"<p style='margin-top:7px;'>🧾 Stock: {stock_disponible if stock_disponible is not None else 'N/D'}</p>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='text-align:right;'>Total: <span style='color:#f44336;'>S/. {total:.2f}</span></h4>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💳 Pagar"):
                    st.session_state.vista_carrito = "pago"
                    st.rerun()
            with col2:
                if st.button("🧹 Vaciar carrito"):
                    st.session_state.carrito = []
                    st.rerun()



    # =============== VISTA: MÉTODO DE PAGO ===============
    elif selected == "Carrito" and st.session_state.vista_carrito == "pago":
        st.markdown("<h2 style='text-align:center;'> Método de Pago</h2>", unsafe_allow_html=True)

        metodo = st.radio(
            "Selecciona una opción:",
            ["Yape", "Efectivo"],
            horizontal=True,
            key="metodo_pago"
        )

        if metodo == "Yape":
            st.markdown("#### 📱 Escanea este código QR con Yape:")
            st.image("img/qr.jpeg", width=200)
            st.markdown("**Número:** 947 651 798")

        elif metodo == "Efectivo":
            st.markdown("#### 💵 Pagarás al momento de recoger tu pedido.")
            st.markdown("Recuerda llevar sencillo.")

        if st.button("✅ Confirmar pedido"):
            tienda = st.session_state.get("tienda_seleccionada")
            
            if tienda:
                # Verificamos que no se supere el stock antes de continuar
                productos_actuales = stock_data.get(tienda)
                if productos_actuales is not None:
                    error_stock = False
                    for item in st.session_state.carrito:
                        nombre = item["nombre"]
                        cantidad = item.get("cantidad", 1)
                        fila = productos_actuales[productos_actuales["producto"] == nombre]
                        if not fila.empty:
                            stock_disponible = fila.iloc[0]["stock"]
                            if cantidad > stock_disponible:
                                st.error(f"❌ No hay stock suficiente para {nombre}. Disponible: {stock_disponible}")
                                error_stock = True
                                break

                    if not error_stock:
                        actualizar_stock_google(tienda, st.session_state.carrito)
                        st.session_state.vista_carrito = "horario"
                        st.rerun()
                else:
                    st.error("⛔ No se encontró la hoja de stock para la tienda.")
            else:
                st.error("⛔ No hay tienda seleccionada.")


        if st.button("⬅ Volver al carrito"):
            st.session_state.vista_carrito = "resumen"
            st.rerun()
            
    # =============== VISTA: HORARIO DE RECOJO ===============
    elif selected == "Carrito" and st.session_state.vista_carrito == "horario":
        st.markdown("<h2 style='text-align:center;'>⏰ Selecciona tu horario de recojo</h2>", unsafe_allow_html=True)

        hora_min = datetime.strptime("11:00", "%H:%M").time()
        hora_max = datetime.strptime("15:00", "%H:%M").time()
        hora_recojo = st.time_input("🕒 Hora de recojo", value=hora_min)

        if st.button("✅ Finalizar pedido"):
            if hora_min <= hora_recojo <= hora_max:
                tienda = st.session_state.get("tienda_seleccionada", "")
                usuario = st.session_state.get("usuario", "Desconocido")

                # Agrupar productos
                productos = {}
                for p in st.session_state.carrito:
                    if p['nombre'] in productos:
                        productos[p['nombre']]['cantidad'] += 1
                    else:
                        productos[p['nombre']] = {**p, 'cantidad': 1}

                total = sum(p['precio'] * p['cantidad'] for p in productos.values())
                fecha = datetime.now().strftime("%d/%m/%Y")
                hora_str = hora_recojo.strftime('%H:%M')

                # 📝 Registrar en Excel
                registrar_reserva_en_google(
                    tienda=tienda,
                    usuario=usuario,
                    total=total,
                    hora_recojo=hora_recojo,
                    carrito=list(productos.values())
                )


                # ✅ Registrar en la sesión para boleta y reservas
                reserva = {
                    "fecha": fecha,
                    "hora": hora_str,
                    "productos": productos,
                    "total": total
                }

                if "reservas" not in st.session_state:
                    st.session_state.reservas = []
                st.session_state.reservas.append(reserva)

                # Limpiar y continuar
                st.session_state.carrito = []
                st.session_state.vista_carrito = "boleta"
                st.rerun()
            else:
                st.error("⛔ Solo puedes elegir una hora entre las 11:00 y 15:00.")

        if st.button("⬅ Volver a método de pago"):
            st.session_state.vista_carrito = "pago"
            st.rerun()


            
            
    elif selected == "Carrito" and st.session_state.vista_carrito == "boleta":
        st.markdown("<h2 style='text-align:center;'>🧾 Boleta de Pedido</h2>", unsafe_allow_html=True)

        if "reservas" in st.session_state and st.session_state.reservas:
            boleta = st.session_state.reservas[-1]

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<div style='font-size:18px;'><b>📅 Fecha:</b> {boleta['fecha']}</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='font-size:18px;'><b>⏰ Hora de recojo:</b> {boleta['hora']}</div>", unsafe_allow_html=True)

            st.markdown("---")

            for nombre, p in boleta["productos"].items():
                st.write(f"🔹 {nombre} x{p['cantidad']} - S/. {p['precio'] * p['cantidad']:.2f}")

            st.markdown(f"<h4 style='text-align:right;'>Total: <span style='color:#f44336;'>S/. {boleta['total']:.2f}</span></h4>", unsafe_allow_html=True)

            if st.button("🔙 Volver al inicio"):
                st.session_state.vista_carrito = "resumen"
                st.session_state.nav = "Inicio"
                st.rerun()
        else:
            st.warning("No hay boletas registradas.")

    # ==================== VISTA RESERVAS ====================

    if selected == "Reservas":
        st.markdown("<h2 style='text-align:center;'>📋 Historial de Reservas</h2>", unsafe_allow_html=True)

        usuario_actual = st.session_state.get("usuario", "")
        if not usuario_actual:
            st.warning("Debes iniciar sesión para ver tus reservas.")
        else:
            reservas_usuario = []

            for tienda in TIENDAS:
                nombre_hoja = tienda["nombre"]
                df = cargar_reservas_por_tienda(nombre_hoja)

                if "usuario" in df.columns:
                    df_filtrado = df[df["usuario"] == usuario_actual]
                    for _, fila in df_filtrado.iterrows():
                        reservas_usuario.append({
                            "tienda": nombre_hoja,
                            "fecha": fila["fecha"],
                            "hora": fila["hora"],
                            "productos": fila["productos"],
                            "total": fila["total"]
                        })

            if not reservas_usuario:
                st.info("No tienes reservas registradas.")
            else:
                reservas_usuario.sort(key=lambda r: (r["fecha"], r["hora"]), reverse=True)
                for i, r in enumerate(reservas_usuario, 1):
                    st.markdown(f"### 🧾 Reserva #{i}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"- 🏬 **Tienda:** {r['tienda']}")
                        st.markdown(f"- 📅 **Fecha:** {r['fecha']}")
                    with col2:
                        st.markdown(f"- ⏰ **Hora:** {r['hora']}")

                    st.markdown(f"**🧾 Productos:** {r['productos']}")
                    st.markdown(f"**💵 Total: S/. {r['total']}**")
                    st.markdown("---")


    
    # ==================== VISTA SERVICIOS ====================
    elif selected == "Servicios":
        
        if "plan_usuario" not in st.session_state:
            st.session_state.plan_usuario = "Basic"

        if "vista_servicios" not in st.session_state:
            st.session_state.vista_servicios = "planes"

    # ==================== VISTA PLANES ====================
        if st.session_state.vista_servicios == "planes":
            st.markdown("<h2 style='text-align:center;'>🛎️ Servicios de Membresía</h2>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)

            with col1:
                resaltado = "border: 4px solid #0f0;" if st.session_state.plan_usuario == "Basic" else "border: 2px solid green;"
                st.markdown(f"""
                <div style='{resaltado} border-radius: 10px; padding: 10px; text-align: center;'>
                    <div style='background: linear-gradient(to right, #004080, #0073e6); color: white; padding: 6px 0; border-radius: 5px; font-weight: bold;'>Usuario Basic</div>
                    <div style='font-size:50px; color: #f3caa3; margin-top:10px;'>🛍️</div>
                    <p style='font-size: 16px;'>• Cobro adicional por compra de menú</p>
                    <div style='background: #fde7d9; padding: 6px; font-weight: bold; border-radius: 5px;'>s/. 0</div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Activar Basic"):
                    st.session_state.plan_usuario = "Basic"
                    st.success("✅ Plan Basic activado")

            with col2:
                resaltado = "border: 4px solid #0f0;" if st.session_state.plan_usuario == "Premium" else "border: 2px solid green;"
                st.markdown(f"""
                <div style='{resaltado} border-radius: 10px; padding: 10px; text-align: center;'>
                    <div style='background: linear-gradient(to right, #004080, #0073e6); color: white; padding: 6px 0; border-radius: 5px; font-weight: bold;'>Usuario Premium</div>
                    <div style='font-size:50px; color: #91c3f2; margin-top:10px;'>🧑‍💼⭐</div>
                    <p style='font-size: 16px;'>• Acceso a reservas sin restricciones</p>
                    <div style='background: #0073e6; color:white; padding: 6px; font-weight: bold; border-radius: 5px;'>s/. 4</div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Activar Premium"):
                    st.session_state.vista_servicios = "pago"

        # ==================== VISTA PAGO PREMIUM ====================
        elif st.session_state.vista_servicios == "pago":
            
            st.markdown("<h2 style='text-align:center;'>💳 Pago para Usuario Premium</h2>", unsafe_allow_html=True)
            st.markdown("Escanea este código QR para pagar la suscripción vía Yape:")
            st.image("img/qr.jpeg", width=200)
            st.markdown("**Número:** 947 651 798")

            if st.button("✅ Confirmar suscripción"):
                st.session_state.plan_usuario = "Premium"
                st.session_state.vista_servicios = "planes"
                st.success("🌟 Plan Premium activado correctamente.")
                st.rerun()

            if st.button("⬅ Volver sin pagar"):
                st.session_state.vista_servicios = "planes"
                st.rerun()
