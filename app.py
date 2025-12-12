import streamlit as st
import google.generativeai as genai
import pandas as pd
import time
import io
import requests
import re
import unicodedata

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bulk AI Processor", page_icon="✨", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .stApp { background-color: #FDFBF7; }
    h1, h2, h3 { color: #4A4E69; font-family: 'Helvetica', sans-serif; }
    [data-testid="stSidebar"] { background-color: #F2E9E4; }
    div.stButton > button:first-child {
        background-color: #B8E0D2; color: #4A4E69; border: none;
        border-radius: 12px; padding: 15px 30px; font-weight: bold;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05); transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #95B8D1; transform: translateY(-2px);
    }
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

# --- FUNCIONES DE UTILIDAD (MÓDULO 3) ---
def limpiar_texto(texto):
    """Elimina HTML, espacios extra y caracteres raros."""
    if not isinstance(texto, str):
        return ""
    # Eliminar etiquetas HTML
    clean = re.sub('<.*?>', '', texto)
    # Eliminar espacios múltiples
    clean = re.sub('\s+', ' ', clean).strip()
    return clean

def generar_handle(texto):
    """Crea un slug URL-friendly para Shopify (ej: 'Camisa Roja' -> 'camisa-roja')"""
    if not isinstance(texto, str):
        return ""
    # Normalizar (quitar tildes, ñ, etc)
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    texto = texto.lower()
    # Reemplazar todo lo que no sea letra/numero con guión
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-')

# --- FUNCIONES MÓDULOS ANTERIORES ---
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

def validar_url_imagen(url):
    try:
        if pd.isna(url) or url == "": return "❌ URL Vacía"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        if r.status_code == 200: return "✅ Activo"
        elif r.status_code == 404: return "🚫 No Encontrado (404)"
        else: return f"⚠️ Error {r.status_code}"
    except Exception: return "❓ Error Conexión"

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

# --- INTERFAZ PRINCIPAL ---
def main():
    st.title("✨ Fábrica de Contenido AI & Tools")
    
    st.sidebar.header("🛠️ Panel de Control")
    modo = st.sidebar.radio(
        "Selecciona una herramienta:",
        ("📝 Generador de Texto", "🔍 Auditor de Imágenes", "🧹 Limpiador CSV")
    )
    
    # Mensajes de ayuda contextual según el modo
    if modo == "📝 Generador de Texto":
        st.sidebar.info("Crea descripciones desde cero usando IA.")
    elif modo == "🔍 Auditor de Imágenes":
        st.sidebar.info("Verifica que los enlaces de imágenes no estén rotos.")
    elif modo == "🧹 Limpiador CSV":
        st.sidebar.info("Prepara tu archivo para Shopify: Genera Handles y limpia HTML sucio.")

    # Configuración de API solo necesaria para el generador de texto
    if modo == "📝 Generador de Texto":
        if not api_key:
            st.error("🔒 Por favor configura tu API Key.")
            return
        genai.configure(api_key=api_key)

    uploaded_file = st.file_uploader("Arrastra tu archivo Excel o CSV aquí", type=['csv', 'xlsx'])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"Archivo cargado: {len(df)} filas.")
            st.dataframe(df.head(3), use_container_width=True)

            # --- MÓDULO 1: GENERADOR DE TEXTO ---
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
                    model = genai.GenerativeModel('gemini-1.5-flash')

                    for index, row in df.iterrows():
                        status_text.text(f"Escribiendo {index + 1}/{len(df)}...")
                        desc = procesar_texto(row[columna_producto], tono, model)
                        resultados.append(desc)
                        progress_bar.progress((index + 1) / len(df))
                        time.sleep(1)

                    df['Descripción_IA'] = resultados
                    status_text.text("✅ ¡Listo!")
                    progress_bar.progress(100)
                    descargar_excel(df, "descripciones_generadas.xlsx")

            # --- MÓDULO 2: AUDITOR DE IMÁGENES ---
            elif modo == "🔍 Auditor de Imágenes":
                st.subheader("Auditoría Técnica de Enlaces")
                columna_url = st.selectbox("Columna de URLs de imágenes:", df.columns)

                if st.button("🔎 Auditar Enlaces"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    estados = []

                    for index, row in df.iterrows():
                        status_text.text(f"Verificando {index + 1}/{len(df)}...")
                        estado = validar_url_imagen(row[columna_url])
                        estados.append(estado)
                        progress_bar.progress((index + 1) / len(df))
                    
                    df['Estado_Imagen'] = estados
                    status_text.text("✅ Auditoría completada.")
                    progress_bar.progress(100)
                    descargar_excel(df, "reporte_imagenes.xlsx")

            # --- MÓDULO 3: LIMPIADOR CSV (NUEVO) ---
            elif modo == "🧹 Limpiador CSV":
                st.subheader("Limpieza y Estructuración para Shopify")
                st.markdown("Genera 'Handles' (URLs amigables) y limpia basura HTML de textos copiados.")
                
                col_titulo = st.selectbox("Columna de Títulos (para generar Handle):", df.columns)
                col_desc = st.selectbox("Columna de Descripción (para limpiar HTML):", ["Ninguna"] + list(df.columns))

                if st.button("✨ Limpiar y Estructurar"):
                    # 1. Generar Handles
                    st.write("⚙️ Generando Handles únicos...")
                    df['Handle'] = df[col_titulo].apply(generar_handle)
                    
                    # 2. Limpiar HTML si se seleccionó columna
                    if col_desc != "Ninguna":
                        st.write("🧼 Limpiando HTML y espacios...")
                        df[col_desc] = df[col_desc].apply(limpiar_texto)
                        # También normalizamos el título a "Title Case"
                        df[col_titulo] = df[col_titulo].astype(str).str.title()

                    st.success("✅ Archivo optimizado.")
                    st.dataframe(df[[col_titulo, 'Handle']].head()) # Mostrar preview de cambios
                    descargar_excel(df, "shopify_listo_para_importar.xlsx")

        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
