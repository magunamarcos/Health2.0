import streamlit as st
import sqlite3
import requests # ¡La nueva herramienta para conectarnos a internet!
from datetime import date

# ==========================================
# 1. LA CONEXIÓN A LA NUBE (Open Food Facts)
# ==========================================
def buscar_en_base_mundial(termino_busqueda):
    # Le pedimos a la API los primeros 5 resultados que coincidan
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={termino_busqueda}&json=1&page_size=5"
    
    try:
        respuesta = requests.get(url)
        datos = respuesta.json()
        resultados = []
        
        for producto in datos.get("products", []):
            nombre = producto.get("product_name", "")
            # Si el producto no tiene nombre, lo saltamos
            if not nombre:
                continue
                
            nutrientes = producto.get("nutriments", {})
            # Usamos .get(..., 0) para que si falta un dato ponga un cero
            calorias = nutrientes.get("energy-kcal_100g", 0)
            proteinas = nutrientes.get("proteins_100g", 0)
            carbos = nutrientes.get("carbohydrates_100g", 0)
            grasas = nutrientes.get("fat_100g", 0)
            
            # Filtramos productos que no tengan calorías cargadas
            if calorias is not None and calorias > 0:
                resultados.append({
                    "nombre": nombre,
                    "calorias": calorias,
                    "proteinas": proteinas,
                    "carbos": carbos,
                    "grasas": grasas
                })
        return resultados
    except:
        return [] # Si hay error de internet, devolvemos una lista vacía

# ==========================================
# 2. EL MOTOR SQL (Memoria Local)
# ==========================================
def iniciar_base_datos():
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Alimentos (
            id_alimento INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            calorias_100g REAL, proteinas_100g REAL, carbos_100g REAL, grasas_100g REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Registro_Diario (
            id_registro INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, comida TEXT,
            alimento_nombre TEXT, gramos REAL, calorias_totales REAL, prot_totales REAL, 
            carb_totales REAL, grasas_totales REAL)''')
    conexion.commit()
    conexion.close()

def guardar_alimento_local(nombre, cal, prot, carb, grasas):
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    try:
        cursor.execute("INSERT INTO Alimentos (nombre, calorias_100g, proteinas_100g, carbos_100g, grasas_100g) VALUES (?, ?, ?, ?, ?)", 
                       (nombre, cal, prot, carb, grasas))
        conexion.commit()
        exito = True
    except sqlite3.IntegrityError:
        exito = False # El alimento ya estaba guardado
    conexion.close()
    return exito

def registrar_consumo(fecha, comida, nombre_alimento, gramos):
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT calorias_100g, proteinas_100g, carbos_100g, grasas_100g FROM Alimentos WHERE nombre = ?", (nombre_alimento,))
    datos = cursor.fetchone()
    if datos:
        cal_tot = (datos[0] / 100) * gramos; prot_tot = (datos[1] / 100) * gramos
        carb_tot = (datos[2] / 100) * gramos; grasas_tot = (datos[3] / 100) * gramos
        cursor.execute("INSERT INTO Registro_Diario (fecha, comida, alimento_nombre, gramos, calorias_totales, prot_totales, carb_totales, grasas_totales) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                       (fecha, comida, nombre_alimento, gramos, cal_tot, prot_tot, carb_tot, grasas_tot))
        conexion.commit()
    conexion.close()

# Inicializamos
iniciar_base_datos()

# ==========================================
# 3. LA INTERFAZ VISUAL (La Cara)
# ==========================================
st.set_page_config(page_title="Mi Diario", page_icon="📝", layout="centered")
fecha_hoy = str(date.today())

st.title("📝 Tu Diario de Comidas")
st.markdown(f"**Fecha:** {fecha_hoy}")

# --- LA BARRA LATERAL: CONEXIÓN AL MUNDO ---
with st.sidebar:
    st.header("🌍 Buscar en la Nube")
    st.markdown("Busca cualquier producto en la base de datos mundial para guardarlo en tu app.")
    
    busqueda = st.text_input("Ej: Avena Quaker, Leche Serenisima...")
    
    if st.button("Buscar en Internet", type="primary"):
        if busqueda:
            with st.spinner("Buscando en todo el mundo..."):
                resultados = buscar_en_base_mundial(busqueda)
                
            if resultados:
                st.success(f"Encontramos {len(resultados)} resultados:")
                # Mostramos los resultados que trajo internet
                for prod in resultados:
                    # Usamos un expander para mostrar la información nutricional de cada uno
                    with st.expander(f"🛒 {prod['nombre']}"):
                        st.caption(f"Por 100g: {prod['calorias']} kcal | {prod['proteinas']}g Prot | {prod['carbos']}g Carb | {prod['grasas']}g Grasas")
                        # Un botón para guardar este alimento específico en nuestra SQL
                        if st.button(f"Guardar {prod['nombre']} en mi App", key=prod['nombre']):
                            if guardar_alimento_local(prod['nombre'], prod['calorias'], prod['proteinas'], prod['carbos'], prod['grasas']):
                                st.success("¡Guardado! Ya puedes usarlo en tu diario.")
                            else:
                                st.warning("Este alimento ya estaba en tu base de datos.")
            else:
                st.error("No se encontraron resultados.")

# --- EL DIARIO (Desayuno, Almuerzo, Cena) ---
# Obtenemos la lista de alimentos que YA están descargados en nuestra SQL
conexion = sqlite3.connect('alimentos.db')
cursor = conexion.cursor()
cursor.execute("SELECT nombre FROM Alimentos ORDER BY nombre")
lista_alimentos_locales = [fila[0] for fila in cursor.fetchall()]
conexion.close()

comidas_del_dia = ["Desayuno", "Almuerzo", "Cena", "Snacks"]
total_cal, total_prot, total_carb, total_grasa = 0.0, 0.0, 0.0, 0.0

for comida in comidas_del_dia:
    st.subheader(f"🍽️ {comida}")
    
    # 1. Mostramos lo comido
    conexion = sqlite3.connect('alimentos.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT alimento_nombre, gramos, calorias_totales, prot_totales, carb_totales, grasas_totales FROM Registro_Diario WHERE fecha = ? AND comida = ?", (fecha_hoy, comida))
    registros = cursor.fetchall()
    conexion.close()
    
    if registros:
        for reg in registros:
            st.markdown(f"✔️ **{reg[1]}g de {reg[0]}** (*{reg[2]:.0f} kcal*)")
            total_cal += reg[2]; total_prot += reg[3]; total_carb += reg[4]; total_grasa += reg[5]
    else:
        st.caption("Aún no agregaste nada aquí.")

    # 2. Agregar desde nuestra base de datos local
    if lista_alimentos_locales:
        with st.expander(f"➕ Agregar al {comida}"):
            seleccion = st.selectbox("Mis Alimentos Guardados:", lista_alimentos_locales, key=f"sel_{comida}")
            gramos = st.number_input("Gramos / ml consumidos:", min_value=1.0, value=100.0, step=10.0, key=f"g_{comida}")
            
            if st.button(f"Agregar a {comida}", key=f"btn_{comida}"):
                registrar_consumo(fecha_hoy, comida, seleccion, gramos)
                st.rerun()
    else:
        st.info("👈 Busca alimentos en la nube (menú lateral) para agregarlos a tu lista.")

    st.divider()

# --- RESUMEN FINAL ---
st.subheader("📊 Resumen del Día")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Kcal Totales", f"{total_cal:.0f}")
m2.metric("Proteínas", f"{total_prot:.0f} g")
m3.metric("Carbohidratos", f"{total_carb:.0f} g")
m4.metric("Grasas", f"{total_grasa:.0f} g")
