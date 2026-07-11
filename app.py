import streamlit as st
import sqlite3
import requests
import csv
from datetime import date

# ==========================================
# 1. EL MOTOR SQL (Memoria Local)
# ==========================================
def iniciar_base_datos():
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Alimentos (
            id_alimento INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL,
            categoria TEXT, calorias_100g REAL, proteinas_100g REAL, carbos_100g REAL, grasas_100g REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Registro_Diario (
            id_registro INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, comida TEXT,
            alimento_nombre TEXT, gramos REAL, calorias_totales REAL, prot_totales REAL, 
            carb_totales REAL, grasas_totales REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Mi_Perfil (
            id INTEGER PRIMARY KEY AUTOINCREMENT, calorias REAL, prot REAL, carbos REAL, grasas REAL)''')
    conexion.commit()

    # --- NUEVO: ABSORCIÓN DE ARGENFOODS ---
    try:
        with open('argenfoods.csv', newline='', encoding='utf-8') as archivo:
            lector = csv.DictReader(archivo)
            alimentos_a_guardar = []
            for fila in lector:
                # Agregamos la etiqueta para saber que vienen de la UNLu
                nombre = f"{fila['nombre']} (ARGENFOODS)"
                cal = float(fila['calorias'])
                prot = float(fila['proteinas'])
                carb = float(fila['carbohidratos'])
                grasas = float(fila['grasas'])
                alimentos_a_guardar.append((nombre, 'Regional', cal, prot, carb, grasas))
            with open(´argenfoods.csv´, newline=´´, encoding=´utf-8-sig´) as archivo:
            # Usamos INSERT OR IGNORE para que si ya los guardó ayer, no los duplique hoy
            cursor.executemany("""
                INSERT OR IGNORE INTO Alimentos 
                (nombre, categoria, calorias_100g, proteinas_100g, carbos_100g, grasas_100g) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, alimentos_a_guardar)
            conexion.commit()
    except FileNotFoundError:
        pass # Si el archivo no está, la app sigue funcionando normal
        
    conexion.close()

def obtener_perfil():
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT calorias, prot, carbos, grasas FROM Mi_Perfil ORDER BY id DESC LIMIT 1")
    datos = cursor.fetchone()
    conexion.close()
    return datos if datos else (2000, 150, 200, 65)

def guardar_alimento_local(nombre, categoria, cal, prot, carb, grasas):
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    try:
        cursor.execute("INSERT INTO Alimentos (nombre, categoria, calorias_100g, proteinas_100g, carbos_100g, grasas_100g) VALUES (?, ?, ?, ?, ?, ?)", 
                       (nombre, categoria, cal, prot, carb, grasas))
        conexion.commit(); exito = True
    except sqlite3.IntegrityError: exito = False
    conexion.close()
    return exito

def registrar_consumo(fecha, comida, nombre_alimento, gramos):
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT calorias_100g, proteinas_100g, carbos_100g, grasas_100g FROM Alimentos WHERE nombre = ?", (nombre_alimento,))
    datos = cursor.fetchone()
    if datos:
        cal = (datos[0]/100)*gramos; prot = (datos[1]/100)*gramos; carb = (datos[2]/100)*gramos; grasas = (datos[3]/100)*gramos
        cursor.execute("INSERT INTO Registro_Diario (fecha, comida, alimento_nombre, gramos, calorias_totales, prot_totales, carb_totales, grasas_totales) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                       (fecha, comida, nombre_alimento, gramos, cal, prot, carb, grasas))
        conexion.commit()
    conexion.close()

def eliminar_consumo(id_registro):
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM Registro_Diario WHERE id_registro = ?", (id_registro,))
    conexion.commit()
    conexion.close()

iniciar_base_datos()

# ==========================================
# 2. CONEXIÓN A MULTIPLES APIS (USDA + OFF)
# ==========================================
@st.cache_data
def buscar_multiples_bases(termino):
    resultados = []
    
    # 1. Buscar en USDA (Estados Unidos - Excelente para alimentos genéricos)
    try:
        url_usda = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={termino}&api_key=DEMO_KEY&pageSize=3"
        res_usda = requests.get(url_usda)
        if res_usda.status_code == 200:
            for p in res_usda.json().get("foods", []):
                nom = p.get("description", "")
                nutrientes = p.get("foodNutrients", [])
                
                # Extraemos macros buscando por el ID del nutriente del USDA
                cal = next((n["value"] for n in nutrientes if n["nutrientNumber"] == "208"), 0)
                prot = next((n["value"] for n in nutrientes if n["nutrientNumber"] == "203"), 0)
                carb = next((n["value"] for n in nutrientes if n["nutrientNumber"] == "205"), 0)
                grasa = next((n["value"] for n in nutrientes if n["nutrientNumber"] == "204"), 0)
                
                if float(cal) > 0:
                    resultados.append({"nombre": f"{nom} (USDA)", "cal": round(cal,1), "prot": round(prot,1), "carb": round(carb,1), "grasas": round(grasa,1)})
    except: pass

    # 2. Buscar en Open Food Facts (Mundo - Excelente para productos de supermercado)
    try:
        res_off = requests.get("https://world.openfoodfacts.org/cgi/search.pl", 
                           params={"search_terms": termino, "search_simple": "1", "action": "process", "json": "1", "page_size": "5"},
                           headers={"User-Agent": "MiAppDeNutricion/4.0"})
        if res_off.status_code == 200:
            for p in res_off.json().get("products", []):
                nom = p.get("product_name", "")
                if not nom: continue
                nut = p.get("nutriments", {})
                cal = nut.get("energy-kcal_100g", nut.get("energy_100g", 0))
                if cal and float(cal) > 0:
                    resultados.append({"nombre": f"{nom} (OFF)", "cal": round(float(cal),1), "prot": round(float(nut.get("proteins_100g", 0) or 0),1),
                                       "carb": round(float(nut.get("carbohydrates_100g", 0) or 0),1), "grasas": round(float(nut.get("fat_100g", 0) or 0),1)})
    except: pass
    
    return resultados

# ==========================================
# 3. INTERFAZ VISUAL
# ==========================================
st.set_page_config(page_title="NutriApp", page_icon="💪", layout="centered")
fecha_hoy = str(date.today())

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Agregar Alimentos")
    st.info("Busca en la base mundial (USDA + OFF) o crea manual.")
    t1, t2 = st.tabs(["🌍 Multibuscador", "➕ Manual"])
    with t1:
        b = st.text_input("Ej: Pollo, Manzana, Oreo...", key="buscador")
        if b:
            for prod in buscar_multiples_bases(b):
                with st.expander(f"🛒 {prod['nombre']}"):
                    st.caption(f"Por 100g: {prod['cal']} kcal | {prod['prot']} P | {prod['carb']} C | {prod['grasas']} G")
                    if st.button("Guardar en App", key=f"btn_{prod['nombre']}"):
                        if guardar_alimento_local(prod['nombre'], "Nube", prod['cal'], prod['prot'], prod['carb'], prod['grasas']):
                            st.success("Guardado. Recargando...")
                            st.rerun() # SOLUCIÓN: Esto hace que aparezca inmediatamente en el diario
                        else: st.warning("Ya existe")
    with t2:
        nom = st.text_input("Nombre:")
        cat = st.selectbox("Categoría:", ["Alimento", "Bebida", "Suplemento"])
        c1, c2 = st.columns(2)
        with c1: cal = st.number_input("Kcal:", 0.0); prot = st.number_input("Prot(g):", 0.0)
        with c2: carb = st.number_input("Carb(g):", 0.0); grasa = st.number_input("Grasa(g):", 0.0)
        if st.button("Guardar", type="primary") and nom:
            if guardar_alimento_local(nom, cat, cal, prot, carb, grasa):
                st.success("Guardado"); st.rerun()

# --- PANTALLA PRINCIPAL ---
st.title("💪 NutriApp Pro")
meta_cal, meta_prot, meta_carb, meta_grasa = obtener_perfil()

tab_diario, tab_perfil = st.tabs(["📝 Diario", "👤 Mi Perfil"])

with tab_diario:
    st.markdown(f"**Fecha:** {fecha_hoy}")
    
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT nombre FROM Alimentos ORDER BY nombre")
    lista_alimentos = [fila[0] for fila in cursor.fetchall()]
    conexion.close()

    total_cal, total_prot, total_carb, total_grasa = 0.0, 0.0, 0.0, 0.0

    for comida in ["Desayuno", "Almuerzo", "Cena", "Snacks"]:
        st.subheader(f"🍽️ {comida}")
        conexion = sqlite3.connect('alimentos.db')
        cursor = conexion.cursor()
        # Modificamos la consulta para traer también el ID del registro y poder borrarlo
        cursor.execute("SELECT alimento_nombre, gramos, calorias_totales, prot_totales, carb_totales, grasas_totales, id_registro FROM Registro_Diario WHERE fecha=? AND comida=?", (fecha_hoy, comida))
        registros = cursor.fetchall()
        conexion.close()
        
        if registros:
            for reg in registros:
                col_texto, col_boton = st.columns([8, 1])
                with col_texto:
                    st.markdown(f"✔️ **{reg[1]}g de {reg[0]}** (*{reg[2]:.0f} kcal*)")
                with col_boton:
                    # El botón de la basura, usamos el ID único para no borrar otra comida por error
                    if st.button("🗑️", key=f"del_{reg[6]}", help="Eliminar este alimento"):
                        eliminar_consumo(reg[6])
                        st.rerun()
                        
                total_cal += reg[2]; total_prot += reg[3]; total_carb += reg[4]; total_grasa += reg[5]
                
        with st.expander(f"➕ Agregar a {comida}"):
            if lista_alimentos:
                sel = st.selectbox("Mis Productos:", lista_alimentos, key=f"s_{comida}")
                g = st.number_input("Gramos/ml:", 1.0, 1000.0, 100.0, step=10.0, key=f"g_{comida}")
                if st.button(f"Agregar", key=f"b_{comida}"):
                    registrar_consumo(fecha_hoy, comida, sel, g); st.rerun()
            else: st.caption("Busca alimentos en el menú lateral primero.")
        st.divider()

    # --- BARRAS DE PROGRESO ---
    st.subheader("📊 Tu Progreso de Hoy")
    p_cal = min(total_cal / meta_cal, 1.0) if meta_cal > 0 else 0.0
    p_prot = min(total_prot / meta_prot, 1.0) if meta_prot > 0 else 0.0
    p_carb = min(total_carb / meta_carb, 1.0) if meta_carb > 0 else 0.0
    p_grasa = min(total_grasa / meta_grasa, 1.0) if meta_grasa > 0 else 0.0

    st.markdown(f"**Calorías:** {total_cal:.0f} / {meta_cal:.0f} kcal")
    st.progress(p_cal)
    
    c1, c2, c3 = st.columns(3)
    with c1: st.caption(f"🥩 Prot: {total_prot:.0f}/{meta_prot:.0f}g"); st.progress(p_prot)
    with c2: st.caption(f"🍚 Carb: {total_carb:.0f}/{meta_carb:.0f}g"); st.progress(p_carb)
    with c3: st.caption(f"🥑 Gras: {total_grasa:.0f}/{meta_grasa:.0f}g"); st.progress(p_grasa)

with tab_perfil:
    st.subheader("Configuración en desarrollo")
    st.info("Tus metas actuales están configuradas en: " + f"{meta_cal:.0f} kcal | {meta_prot:.0f}g Prot | {meta_carb:.0f}g Carb | {meta_grasa:.0f}g Grasa")
