import streamlit as st
import sqlite3
import requests
from datetime import date

# ==========================================
# 1. EL MOTOR SQL (Memoria Local y Perfil)
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
    # Nueva tabla para guardar tu meta diaria
    cursor.execute('''CREATE TABLE IF NOT EXISTS Mi_Perfil (
            id INTEGER PRIMARY KEY AUTOINCREMENT, calorias REAL, prot REAL, carbos REAL, grasas REAL)''')
    conexion.commit()
    conexion.close()

# Funciones de base de datos
def guardar_perfil(cal, prot, carb, grasas):
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM Mi_Perfil") # Borramos la meta anterior
    cursor.execute("INSERT INTO Mi_Perfil (calorias, prot, carbos, grasas) VALUES (?, ?, ?, ?)", (cal, prot, carb, grasas))
    conexion.commit()
    conexion.close()

def obtener_perfil():
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT calorias, prot, carbos, grasas FROM Mi_Perfil ORDER BY id DESC LIMIT 1")
    datos = cursor.fetchone()
    conexion.close()
    return datos if datos else (2000, 150, 200, 65) # Valores por defecto si no hay perfil

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

iniciar_base_datos()

# ==========================================
# 2. CÁLCULO Y OPTIMIZACIÓN (El Cerebro)
# ==========================================
def calcular_plan_nutricional(peso, altura, edad, sexo, actividad, objetivo):
    tmb = (10*peso) + (6.25*altura) - (5*edad) + (5 if sexo == 'Masculino' else -161)
    factores = {'Sedentario': 1.2, 'Ligero': 1.375, 'Moderado': 1.55, 'Intenso': 1.725}
    get = tmb * factores.get(actividad, 1.2)
    calorias = get * 0.80 if objetivo == 'Perder grasa' else get * 1.15 if objetivo == 'Ganar masa' else get
    return round(calorias), round((calorias*0.30)/4), round((calorias*0.30)/9), round((calorias*0.40)/4)

def optimizador_porciones(obj_prot, obj_carb, obj_grasa, datos_prot, datos_carb, datos_grasa):
    # Matemáticas de restas en cascada (Algoritmo Fitia)
    try:
        g_carb = obj_carb / (datos_carb[2] / 100) if datos_carb[2] > 0 else 0
        prot_restante = obj_prot - (g_carb * (datos_carb[1] / 100))
        g_prot = prot_restante / (datos_prot[1] / 100) if datos_prot[1] > 0 else 0
        grasa_restante = obj_grasa - (g_prot * (datos_prot[3] / 100)) - (g_carb * (datos_carb[3] / 100))
        g_grasa = grasa_restante / (datos_grasa[3] / 100) if datos_grasa[3] > 0 else 0
        return max(0, round(g_prot)), max(0, round(g_carb)), max(0, round(g_grasa))
    except: return 0, 0, 0

@st.cache_data
def buscar_en_base_mundial(termino):
    try:
        res = requests.get("https://world.openfoodfacts.org/cgi/search.pl", 
                           params={"search_terms": termino, "search_simple": "1", "action": "process", "json": "1", "page_size": "10"},
                           headers={"User-Agent": "MiAppDeNutricion/3.0"})
        datos = res.json()
        resultados = []
        for p in datos.get("products", []):
            nom = p.get("product_name", "")
            if not nom: continue
            nut = p.get("nutriments", {})
            cal = nut.get("energy-kcal_100g", nut.get("energy_100g", 0))
            if cal and float(cal) > 0:
                resultados.append({"nombre": nom, "cal": float(cal), "prot": float(nut.get("proteins_100g", 0) or 0),
                                   "carb": float(nut.get("carbohydrates_100g", 0) or 0), "grasas": float(nut.get("fat_100g", 0) or 0)})
        return resultados
    except: return []

# ==========================================
# 3. INTERFAZ VISUAL (La Cara)
# ==========================================
st.set_page_config(page_title="NutriApp", page_icon="💪", layout="centered")
fecha_hoy = str(date.today())

# Barra Lateral: Nube y Manual
with st.sidebar:
    st.header("⚙️ Agregar Alimentos")
    t1, t2 = st.tabs(["🌍 Nube", "➕ Manual"])
    with t1:
        st.caption("Escribe y presiona Enter:")
        b = st.text_input("Ej: Avena, Pollo...", key="buscador")
        if b:
            for prod in buscar_en_base_mundial(b):
                with st.expander(f"🛒 {prod['nombre']}"):
                    st.caption(f"{prod['cal']} kcal | {prod['prot']} P | {prod['carb']} C | {prod['grasas']} G")
                    if st.button("Guardar en App", key=f"btn_{prod['nombre']}"):
                        if guardar_alimento_local(prod['nombre'], "Nube", prod['cal'], prod['prot'], prod['carb'], prod['grasas']):
                            st.success("Guardado")
                        else: st.warning("Ya existe")
    with t2:
        nom = st.text_input("Nombre:")
        cat = st.selectbox("Categoría:", ["Alimento", "Bebida", "Suplemento"])
        c1, c2 = st.columns(2)
        with c1: cal = st.number_input("Kcal:", 0.0); prot = st.number_input("Prot(g):", 0.0)
        with c2: carb = st.number_input("Carb(g):", 0.0); grasa = st.number_input("Grasa(g):", 0.0)
        if st.button("Guardar", type="primary") and nom:
            guardar_alimento_local(nom, cat, cal, prot, carb, grasa)
            st.success("Guardado")

# Pestañas Principales
st.title("💪 NutriApp Pro")
tab_diario, tab_optimizador, tab_perfil = st.tabs(["📝 Diario", "🧠 Calculadora Inteligente", "👤 Mi Perfil"])

# --- PESTAÑA 3: PERFIL ---
with tab_perfil:
    st.subheader("Tus Metas Nutricionales")
    st.info("Calcula tus macros aquí. La app los recordará para tus barras de progreso.")
    c1, c2, c3 = st.columns(3)
    with c1: peso = st.number_input("Peso(kg):", 75.0)
    with c2: altura = st.number_input("Altura(cm):", 178.0)
    with c3: edad = st.number_input("Edad:", 25)
    sexo = st.selectbox("Sexo:", ["Masculino", "Femenino"])
    act = st.selectbox("Actividad:", ["Sedentario", "Ligero", "Moderado", "Intenso"])
    obj = st.selectbox("Objetivo:", ["Perder grasa", "Mantener", "Ganar masa"])
    
    if st.button("Calcular y Guardar Mi Meta", type="primary"):
        m_cal, m_prot, m_grasa, m_carb = calcular_plan_nutricional(peso, altura, edad, sexo, act, obj)
        guardar_perfil(m_cal, m_prot, m_carb, m_grasa)
        st.success(f"Metas actualizadas: {m_cal} kcal | {m_prot}g Prot | {m_carb}g Carb | {m_grasa}g Grasa")

# Cargamos las metas guardadas en la base de datos
meta_cal, meta_prot, meta_carb, meta_grasa = obtener_perfil()

# --- PESTAÑA 1: DIARIO Y BARRAS DE PROGRESO ---
with tab_diario:
    st.markdown(f"**Fecha:** {fecha_hoy}")
    
    # Obtenemos alimentos de SQL
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
        cursor.execute("SELECT alimento_nombre, gramos, calorias_totales, prot_totales, carb_totales, grasas_totales FROM Registro_Diario WHERE fecha=? AND comida=?", (fecha_hoy, comida))
        registros = cursor.fetchall()
        conexion.close()
        
        if registros:
            for reg in registros:
                st.markdown(f"✔️ **{reg[1]}g de {reg[0]}** (*{reg[2]:.0f} kcal*)")
                total_cal += reg[2]; total_prot += reg[3]; total_carb += reg[4]; total_grasa += reg[5]
                
        with st.expander(f"➕ Agregar a {comida}"):
            if lista_alimentos:
                sel = st.selectbox("Mis Productos:", lista_alimentos, key=f"s_{comida}")
                g = st.number_input("Gramos:", 1.0, 100.0, 10.0, key=f"g_{comida}")
                if st.button(f"Agregar", key=f"b_{comida}"):
                    registrar_consumo(fecha_hoy, comida, sel, g); st.rerun()
            else: st.caption("Busca alimentos en el menú lateral primero.")
        st.divider()

    # BARRAS DE PROGRESO
    st.subheader("📊 Tu Progreso de Hoy")
    
    # Calculamos porcentajes (evitando errores si la meta es 0) y capamos a 1.0 (100%)
    p_cal = min(total_cal / meta_cal, 1.0) if meta_cal > 0 else 0.0
    p_prot = min(total_prot / meta_prot, 1.0) if meta_prot > 0 else 0.0
    p_carb = min(total_carb / meta_carb, 1.0) if meta_carb > 0 else 0.0
    p_grasa = min(total_grasa / meta_grasa, 1.0) if meta_grasa > 0 else 0.0

    st.markdown(f"**Calorías:** {total_cal:.0f} / {meta_cal:.0f} kcal")
    st.progress(p_cal)
    
    c1, c2, c3 = st.columns(3)
    with c1: st.caption(f"🥩 Prot: {total_prot:.0f}/{meta_prot:.0f}g"); st.progress(p_prot)
    with c2: st.caption(f"🍚 Carb: {total_carb:.0f}/{meta_carb:.0f}g"); st.progress(p_carb)
    with c3: st.caption(f"🥑 Grasas: {total_grasa:.0f}/{meta_grasa:.0f}g"); st.progress(p_grasa)

# --- PESTAÑA 2: EL OPTIMIZADOR FITIA ---
with tab_optimizador:
    st.subheader("🧠 Creador de Platos Inteligente")
    st.markdown("Dile a la app qué te falta comer y qué ingredientes tienes. La app calculará la porción exacta.")
    
    if len(lista_alimentos) >= 3:
        st.markdown("**1. ¿Qué macros quieres alcanzar en esta comida?**")
        col1, col2, col3 = st.columns(3)
        with col1: obj_p = st.number_input("Proteína (g)", value=40)
        with col2: obj_c = st.number_input("Carbos (g)", value=50)
        with col3: obj_g = st.number_input("Grasas (g)", value=15)
        
        st.markdown("**2. ¿Qué ingredientes vas a usar?**")
        f_prot = st.selectbox("Fuente principal de Proteína:", lista_alimentos, key="opt_p")
        f_carb = st.selectbox("Fuente principal de Carbohidratos:", lista_alimentos, key="opt_c")
        f_grasa = st.selectbox("Fuente principal de Grasa:", lista_alimentos, key="opt_g")
        
        if st.button("🪄 Generar Porciones Exactas", type="primary"):
            conexion = sqlite3.connect('alimentos.db')
            c = conexion.cursor()
            c.execute("SELECT calorias_100g, proteinas_100g, carbos_100g, grasas_100g FROM Alimentos WHERE nombre=?", (f_prot,))
            d_prot = c.fetchone()
            c.execute("SELECT calorias_100g, proteinas_100g, carbos_100g, grasas_100g FROM Alimentos WHERE nombre=?", (f_carb,))
            d_carb = c.fetchone()
            c.execute("SELECT calorias_100g, proteinas_100g, carbos_100g, grasas_100g FROM Alimentos WHERE nombre=?", (f_grasa,))
            d_grasa = c.fetchone()
            conexion.close()
            
            # Ejecutamos el algoritmo matemático
            g_prot, g_carb, g_grasa = optimizador_porciones(obj_p, obj_c, obj_g, d_prot, d_carb, d_grasa)
            
            st.success("¡Plato optimizado matemáticamente!")
            st.markdown(f"- ⚖️ Sirve **{g_prot}g** de {f_prot}")
            st.markdown(f"- ⚖️ Sirve **{g_carb}g** de {f_carb}")
            st.markdown(f"- ⚖️ Sirve **{g_grasa}g** de {f_grasa}")
    else:
        st.warning("Necesitas tener al menos 3 alimentos guardados en tu base de datos para usar el Optimizador.")
