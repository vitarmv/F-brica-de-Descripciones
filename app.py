import streamlit as st
import google.generativeai as genai
import pandas as pd
import time
import io  

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bulk AI Processor", page_icon="✨", layout="centered")

# --- DISEÑO MINIMALISTA & PASTEL (CSS) ---
st.markdown("""
<style>
    /* Fondo general suave */
    .stApp {
        background-color: #FDFBF7;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #4A4E69;
        font-family: 'Helvetica', sans-serif;
    }
    
    /* Botón Principal (Pastel Blue) */
    div.stButton > button:first-child {
        background-color: #B8E0D2;
        color: #4A4E69;
        border: none;
        border-radius: 12px;
        padding: 15px 30px;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #95B8D1;
        transform: translateY(-2px);
    }

    /* Área de carga de archivos */
    .stFileUploader {
        border: 2px dashed #D6E2E9;
        border-radius: 15px;
        padding: 20px;
        background-color: #FFFFFF;
    }
    
    /* Cajas de éxito/aviso */
    .stSuccess {
        background-color: #DBE7E4;
        color: #2C3E50;
    }
</style>
""", unsafe_allow_html=True)

# --- TU CLAVE API ---
api_key = 'AIzaSyBlS31KHG75KBRUiuk5MJjz99uE8heuvko'  # <--- PEGA TU CLAVE REAL AQUÍ

# --- LÓGICA DE PROCESAMIENTO ---
def procesar_fila(producto, tono, model):
    """Esta función es el 'obrero' que procesa cada fila individualmente"""
    try:
        prompt = f"""
        Actúa como experto en E-commerce.
        TAREA: Escribe una descripción de producto corta (máx 50 palabras) para: {producto}.
        TONO: {tono}.
        
        REGLAS OBLIGATORIAS DE FORMATO:
        1. Entrega SOLAMENTE el texto de la descripción.
        2. NO repitas el nombre del producto al inicio.
        3. NO uses formato markdown (ni negritas **, ni guiones -).
        4. NO saludes ni des introducciones (ej: "Aquí tienes la descripción").
        5. Empieza directamente con el beneficio o característica.
        """
        
        response = model.generate_content(prompt)
        
        # Limpieza extra con Python (por si la IA desobedece)
        texto_limpio = response.text.replace('**', '').replace('##', '').strip()
        
        # Si la IA repitió el nombre al inicio, lo intentamos quitar (opcional)
        if texto_limpio.lower().startswith(producto.lower()):
            texto_limpio = texto_limpio[len(producto):].strip(" -:.")
            
        return texto_limpio
        
    except Exception as e:
        return "Error al generar"

# --- INTERFAZ DE USUARIO ---
st.title("✨ Fábrica de Contenido AI")
st.write("Sube tu lista de productos y genera descripciones masivas en segundos.")

if not api_key or api_key == "TU_CLAVE_AIza_AQUI":
    st.error("🔒 Por favor configura tu API Key en el código.")
else:
    genai.configure(api_key=api_key)
    
    # 1. SUBIDA DE ARCHIVO
    uploaded_file = st.file_uploader("Arrastra tu archivo Excel o CSV aquí", type=['csv', 'xlsx'])

    if uploaded_file is not None:
        # Detectar tipo de archivo y leer
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"¡Archivo cargado! Detectamos {len(df)} productos.")
            
            # Mostrar las primeras filas (Preview minimalista)
            st.dataframe(df.head(3), use_container_width=True)

            # 2. CONFIGURACIÓN
            col1, col2 = st.columns(2)
            with col1:
                # El usuario elige qué columna tiene el nombre del producto
                columna_producto = st.selectbox("¿En qué columna están los nombres?", df.columns)
            with col2:
                tono = st.selectbox("Elegir Tono:", ["Vendedor Persuasivo", "Minimalista y Lujoso", "Divertido", "Técnico"])

            # 3. BOTÓN DE ACCIÓN
            if st.button("🚀 Iniciar Procesamiento Masivo"):
                
                # Barra de progreso visual
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Lista para guardar resultados
                resultados = []
                
                # Configurar modelo (Usamos Flash por velocidad)
                model = genai.GenerativeModel('gemini-2.5-flash')

                # --- BUCLE DE PROCESAMIENTO (La parte Escalable) ---
                total_filas = len(df)
                
                for index, row in df.iterrows():
                    # Actualizar estado visual
                    status_text.text(f"Procesando producto {index + 1} de {total_filas}...")
                    
                    # Llamar a la IA
                    nombre_prod = row[columna_producto]
                    descripcion = procesar_fila(nombre_prod, tono, model)
                    resultados.append(descripcion)
                    
                    # Actualizar barra
                    progress_bar.progress((index + 1) / total_filas)
                    
                    # Pequeña pausa para no saturar la API (Rate Limits)
                    time.sleep(0.5) 

                # Guardar resultados en el DataFrame
                df['Descripción_IA'] = resultados
                
                status_text.text("✅ ¡Procesamiento completado!")
                progress_bar.progress(100)

               # 4. DESCARGA EN EXCEL (XLSX)
                st.balloons()
                st.write("### Tus resultados están listos:")
                
                # Crear un buffer de memoria para el Excel
                output = io.BytesIO()
                
                # Escribir el DataFrame en formato Excel nativo
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Descripciones_IA')
                
                # Obtener el valor binario
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Descargar Excel (.xlsx)",
                    data=excel_data,
                    file_name='productos_con_ia.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )

        except Exception as e:
            st.error(f"Hubo un error leyendo el archivo: {e}")
