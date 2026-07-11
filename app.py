import streamlit as st

# ==========================================
# 1. EL CEREBRO (Nuestras fórmulas matemáticas)
# ==========================================
def calcular_plan_nutricional(peso, altura, edad, sexo, actividad, objetivo):
    # Cálculo de Tasa Metabólica Basal (Mifflin-St Jeor)
    if sexo == 'Masculino':
        tmb = (10 * peso) + (6.25 * altura) - (5 * edad) + 5
    else:
        tmb = (10 * peso) + (6.25 * altura) - (5 * edad) - 161
        
    # Gasto Energético Total
    factores_actividad = {
        'Sedentario': 1.2, 
        'Ligero': 1.375, 
        'Moderado': 1.55, 
        'Intenso': 1.725
    }
    factor = factores_actividad.get(actividad, 1.2)
    get = tmb * factor

    # Ajuste por objetivo
    if objetivo == 'Perder grasa':
        calorias_objetivo = get * 0.80
    elif objetivo == 'Ganar masa':
        calorias_objetivo = get * 1.15
    else:
        calorias_objetivo = get

    # Distribución de macros (30% prot, 30% grasa, 40% carbos)
    prot = (calorias_objetivo * 0.30) / 4
    grasa = (calorias_objetivo * 0.30) / 9
    carbos = (calorias_objetivo * 0.40) / 4

    return round(calorias_objetivo), round(prot), round(grasa), round(carbos)

# ==========================================
# 2. LA CARA Y EL PUENTE (Interfaz Visual con Streamlit)
# ==========================================

# Configuración básica de la página para celulares
st.set_page_config(page_title="App de Nutrición", page_icon="🥗", layout="centered")

# Título y encabezado
st.title("🥗 Mi App de Nutrición")
st.markdown("Calcula tus macros y calorías diarias automáticamente.")
st.divider() # Una línea horizontal para separar secciones

# Creación del formulario para ingresar datos
st.subheader("1. Tu Perfil")

# Usamos columnas para que no ocupe tanto espacio vertical en el celular
col_peso, col_altura = st.columns(2)
with col_peso:
    peso = st.number_input("Peso (kg):", min_value=30.0, max_value=250.0, value=75.0, step=0.1)
with col_altura:
    altura = st.number_input("Altura (cm):", min_value=100.0, max_value=250.0, value=178.0, step=1.0)

edad = st.number_input("Edad (años):", min_value=10, max_value=100, value=25, step=1)

st.subheader("2. Actividad y Objetivos")
sexo = st.selectbox("Sexo biológico:", ["Masculino", "Femenino"])
actividad = st.selectbox("Nivel de Actividad:", ["Sedentario", "Ligero", "Moderado", "Intenso"], index=2)
objetivo = st.selectbox("Tu objetivo principal:", ["Perder grasa", "Mantener", "Ganar masa"])

st.divider()

# El botón que dispara el cálculo
if st.button("Calcular mi Plan Nutricional", type="primary", use_container_width=True):
    
    # Llamamos a nuestra función matemática
    cals, prot, grasas, carbos = calcular_plan_nutricional(peso, altura, edad, sexo, actividad, objetivo)
    
    # Mostramos los resultados
    st.success("¡Plan calculado con éxito!")
    
    st.subheader("Tus Metas Diarias")
    
    # Usamos la función 'metric' de Streamlit que se ve muy bien en móviles
    st.metric(label="🔥 Calorías Totales", value=f"{cals} kcal")
    
    # Tres columnas para los macronutrientes
    m1, m2, m3 = st.columns(3)
    m1.metric(label="🥩 Proteínas", value=f"{prot} g")
    m2.metric(label="🥑 Grasas", value=f"{grasas} g")
    m3.metric(label="🍚 Carbos", value=f"{carbos} g")
    
    st.info("Recuerda que estos son valores estimados. Para la siguiente fase de desarrollo conectaremos la base de datos de alimentos.")
