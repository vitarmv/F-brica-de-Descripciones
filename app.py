import streamlit as st
import google.generativeai as genai
import pandas as pd
import time
import io
import requests  # NUEVA LIBRERÍA PARA VALIDAR IMÁGENES

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bulk AI Processor", page_icon="✨", layout="wide") # Cambié a 'wide' para ver mejor las tablas

# --- DISEÑO MINIMALISTA & PASTEL (CSS) ---
st.markdown("""
<style>
    /* Fondo general suave */
    .stApp { background-color: #FDFBF7; }
    
    /* Títulos */
    h1, h2, h3 { color: #4A4E69; font-family: 'Helvetica', sans-serif; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #F2E9E4; }
    
    /* Botones */
    div.stButton > button:first-child {
        background-color: #B8E0D2; color: #4A4E69; border: none;
        border-radius: 12px; padding: 15px 30px; font-weight: bold;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05); transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #95B8D1; transform: translateY(-2px);
    }

    /* Área de carga */
    .stFileUploader {
        border: 2px dashed #D6E2E9; border-radius: 15px;
        padding: 20px; background-color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)

import os
# API Key
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = os.getenv("GEMINI_API_KEY")

# --- FUNCIÓN 1: GENERACIÓN DE TEXTO (GEMINI) ---
def procesar_texto(producto, tono, model):
    max_intentos = 3
    for intento in range(max_intentos):
        try:
            prompt = f"""
            Actúa como experto en E-commerce.
            TAREA: Escribe una descripción de producto corta (máx 50 palabras) para: {producto}.
            TONO: {tono}.
            REGLAS: Solo texto, sin repetir título, sin markdown, directo al beneficio.
            """
            response = model.generate_content(prompt)
            texto = response.text.replace('**', '').replace('##', '').strip()
            if texto.lower().startswith(producto.lower()):
                texto = texto[len(producto):].strip(" -:.")
            return texto
        except Exception as e:
            time.sleep((intento + 1) * 2)
            if intento == max_intentos - 1: return f"Error: {e}"
    return "Error desconocido"

# --- FUNCIÓN 2: VALIDACIÓN DE IMÁGENES (NUEVA) ---
def validar_url_imagen(url):
    """
    Realiza una petición HEAD (más ligera que descargar la imagen)
    para ver si el enlace funciona.
    """
    try:
        if pd.isna(url) or url == "":
            return "❌ URL Vacía"
        
        # Simula ser un navegador real para evitar bloqueos
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # Timeout de 3 segundos para que no se cuelgue
        r = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        
        if r.status_code == 200:
            return "✅ Activo"
        elif r.status_code == 404:
            return "🚫 No Encontrado (404)"
        elif r.status_code == 403:
            return "🔒 Acceso Prohibido (403)"
        else:
            return f"⚠️ Error {r.status_code}"
            
    except requests.exceptions.Timeout:
        return "🐢 Timeout (Lento)"
    except requests.exceptions.ConnectionError:
        return "🔌 Error Conexión"
    except Exception as e:
        return "❓ Error Formato"

# --- INTERFAZ PRINCIPAL ---
def main():
    st.title("✨ Fábrica de Contenido AI & Tools")
    
    # --- SIDEBAR: SELECCIÓN DE MÓDULO ---
    st.sidebar.header("🛠️ Panel de Control")
    modo = st.sidebar.radio(
        "Selecciona una herramienta:",
        ("📝 Generador de Texto", "🔍 Auditor de Imágenes")
    )
    
    st.sidebar.info("💡 Usa el 'Auditor' para validar enlaces rotos antes de cargar a Shopify.")

    if not api_key:
        st.error("🔒 Por favor configura tu API Key.")
        return

    genai.configure(api_key=api_key)

    # SUBIDA DE ARCHIVO (Común para ambos módulos)
    uploaded_file = st.file_uploader("Arrastra tu archivo Excel o CSV aquí", type=['csv', 'xlsx'])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"Archivo cargado: {len(df)} filas.")
            st.dataframe(df.head(3), use_container_width=True)

            # --- LÓGICA MÓDULO 1: GENERADOR DE TEXTO ---
            if modo == "📝 Generador de Texto":
                st.subheader("Configuración de Redacción")
                col1, col2 = st.columns(2)
                with col1:
                    columna_producto = st.selectbox("Columna de Nombres:", df.columns)
                with col2:
                    tono = st.selectbox("Tono:", ["Persuasivo", "Lujo", "Divertido", "Técnico"])

                if st.button("🚀 Generar Descripciones"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    resultados = []
                    model = genai.GenerativeModel('gemini-1.5-flash') # Usando modelo estándar flash

                    for index, row in df.iterrows():
                        status_text.text(f"Escribiendo {index + 1}/{len(df)}...")
                        desc = procesar_texto(row[columna_producto], tono, model)
                        resultados.append(desc)
                        progress_bar.progress((index + 1) / len(df))
                        time.sleep(1) # Rate limit preventivo

                    df['Descripción_IA'] = resultados
                    status_text.text("✅ ¡Listo!")
                    progress_bar.progress(100)
                    descargar_excel(df, "descripciones_generadas.xlsx")

            # --- LÓGICA MÓDULO 2: AUDITOR DE IMÁGENES ---
            elif modo == "🔍 Auditor de Imágenes":
                st.subheader("Auditoría Técnica de Enlaces")
                st.markdown("""
                Este módulo verificará que los enlaces de tus imágenes funcionen.
                **Ideal para el paquete 'Premium' en Fiverr.**
                """)
                
                columna_url = st.selectbox("¿En qué columna están las URLs de las imágenes?", df.columns)

                if st.button("magnifying_glass_tilted_left: Auditar Enlaces"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    estados = []

                    for index, row in df.iterrows():
                        status_text.text(f"Verificando enlace {index + 1}/{len(df)}...")
                        estado = validar_url_imagen(row[columna_url])
                        estados.append(estado)
                        progress_bar.progress((index + 1) / len(df))
                        # No necesitamos sleep aquí, requests es rápido, pero cuidado con bloquear la IP si son miles
                    
                    df['Estado_Imagen'] = estados
                    
                    # Conteo de errores
                    errores = df[df['Estado_Imagen'] != "✅ Activo"].shape[0]
                    if errores > 0:
                        st.warning(f"⚠️ Se encontraron {errores} enlaces rotos o con problemas.")
                    else:
                        st.success("🎉 ¡Todos los enlaces funcionan perfectamente!")

                    status_text.text("✅ Auditoría completada.")
                    progress_bar.progress(100)
                    descargar_excel(df, "reporte_imagenes.xlsx")

        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")

def descargar_excel(df, nombre_archivo):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button(
        label="📥 Descargar Resultados",
        data=output.getvalue(),
        file_name=nombre_archivo,
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == "__main__":
    main()
