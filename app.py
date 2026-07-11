import streamlit as st
import sqlite3

# ==========================================
# 1. EL CEREBRO MATEMÁTICO (Fórmulas)
# ==========================================
def calcular_plan_nutricional(peso, altura, edad, sexo, actividad, objetivo):
    if sexo == 'Masculino':
        tmb = (10 * peso) + (6.25 * altura) - (5 * edad) + 5
    else:
        tmb = (10 * peso) + (6.25 * altura) - (5 * edad) - 161
        
    factores = {'Sedentario': 1.2, 'Ligero': 1.375, 'Moderado': 1.55, 'Intenso': 1.725}
    get = tmb * factores.get(actividad, 1.2)

    if objetivo == 'Perder grasa':
        calorias = get * 0.80
    elif objetivo == 'Ganar masa':
        calorias = get * 1.15
    else:
        calorias = get

    prot = (calorias * 0.30) / 4
    grasa = (calorias * 0.30) / 9
    carbos = (calorias * 0.40) / 4

    return round(calorias), round(prot), round(grasa), round(carbos)

# ==========================================
# 2. EL MOTOR DE DATOS (Conexión SQL)
# ==========================================
def iniciar_base_datos():
    # Crea el archivo SQL y el puente de conexión
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    
    # Crea la tabla si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Alimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            calorias_100g REAL,
            proteinas_100g REAL,
            carbos_100g REAL,
            grasas_100g REAL
        )
    ''')
    
    # Verificamos si la base de datos está vacía
    cursor.execute("SELECT COUNT(*) FROM Alimentos")
    if cursor.fetchone()[0] == 0:
        # Si está vacía, le inyectamos 4 alimentos de prueba
        alimentos_basicos = [
            ('Pechuga de Pollo cruda', 120.0, 31.0, 0.0, 3.6),
            ('Arroz Blanco crudo', 350.0, 2.7, 80.0, 0.3),
            ('Avena Tradicional', 380.0, 13.0, 60.0, 7.0),
            ('Aceite de Oliva', 884.0, 0.0, 0.0, 100.0)
        ]
        cursor.executemany("INSERT INTO Alimentos (nombre, calorias_100g, proteinas_100g, carbos_100g, grasas_100g) VALUES (?, ?, ?, ?, ?)", alimentos_basicos)
        conexion.commit()
    
    conexion.close()

def obtener_lista_alimentos():
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT nombre FROM Alimentos ORDER BY nombre")
    # Sacamos los nombres de la base de datos y los guardamos en una lista
    nombres = [fila[0] for fila in cursor.fetchall()]
    conexion.close()
    return nombres

def buscar_macros_alimento(nombre):
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT calorias_100g, proteinas_100g, carbos_100g, grasas_100g FROM Alimentos WHERE nombre = ?", (nombre,))
    datos = cursor.fetchone()
    conexion.close()
    return datos

# ¡Encendemos la base de datos al iniciar la app!
iniciar_base_datos()

# ==========================================
# 3. LA CARA (Interfaz Visual)
# ==========================================
st.set_page_config(page_title="App de Nutrición", page_icon="🥗", layout="centered")

st.title("🥗 Mi App de Nutrición")
st.markdown("Calcula tus macros y consulta la base de datos.")

# --- SECCIÓN 1: CALCULADORA DE MACROS ---
st.subheader("1. Tu Plan Diario")
with st.expander("Haz clic aquí para ingresar tus datos"):
    c1, c2, c3 = st.columns(3)
    with c1: peso = st.number_input("Peso (kg):", value=75.0)
    with c2: altura = st.number_input("Altura (cm):", value=178.0)
    with c3: edad = st.number_input("Edad:", value=25)
    
    sexo = st.selectbox("Sexo:", ["Masculino", "Femenino"])
    actividad = st.selectbox("Actividad:", ["Sedentario", "Ligero", "Moderado", "Intenso"])
    objetivo = st.selectbox("Objetivo:", ["Perder grasa", "Mantener", "Ganar masa"])

    if st.button("Calcular Macros", type="primary"):
        cals, prot, grasas, carbos = calcular_plan_nutricional(peso, altura, edad, sexo, actividad, objetivo)
        st.success(f"🔥 Calorías: {cals} kcal | 🥩 Prot: {prot}g | 🥑 Grasas: {grasas}g | 🍚 Carbos: {carbos}g")

st.divider()

# --- SECCIÓN 2: BASE DE DATOS DE ALIMENTOS ---
st.subheader("2. Buscador de Alimentos")
st.info("Estos datos provienen de tu propia base de datos SQL.")

# Obtenemos la lista de la base de datos para el menú desplegable
lista_disponible = obtener_lista_alimentos()
alimento_elegido = st.selectbox("Selecciona un alimento:", lista_disponible)

# Un cuadro para que el usuario diga cuántos gramos va a comer
gramos_a_comer = st.number_input("¿Cuántos gramos vas a comer?", min_value=1.0, value=100.0, step=10.0)

# Buscamos los valores originales (por 100g) en la base de datos
datos = buscar_macros_alimento(alimento_elegido)

if datos:
    cal_100, prot_100, carb_100, grasas_100 = datos
    
    # Aplicamos regla de tres simple para calcular la porción exacta
    porcion_cal = (cal_100 / 100) * gramos_a_comer
    porcion_prot = (prot_100 / 100) * gramos_a_comer
    porcion_carb = (carb_100 / 100) * gramos_a_comer
    porcion_grasas = (grasas_100 / 100) * gramos_a_comer
    
    # Mostramos los resultados multiplicados
    st.markdown(f"**Valores nutricionales para {gramos_a_comer}g de {alimento_elegido}:**")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="Calorías", value=f"{porcion_cal:.1f}")
    m2.metric(label="Proteínas", value=f"{porcion_prot:.1f} g")
    m3.metric(label="Carbohidratos", value=f"{porcion_carb:.1f} g")
    m4.metric(label="Grasas", value=f"{porcion_grasas:.1f} g")
