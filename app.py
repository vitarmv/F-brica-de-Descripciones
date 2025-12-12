import streamlit as st
import google.generativeai as genai
import pandas as pd
import time
import io
import requests
import re
import unicodedata
import os
from PIL import Image

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
    .stAlert { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# API Key
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = os.getenv("GEMINI_API_KEY")

# --- FUNCIONES DE UTILIDAD ---
def limpiar_texto(texto):
    if not isinstance(texto, str): return ""
    clean = re.sub('<.*?>', '', texto)
    clean = re.sub('\s+', ' ', clean).strip()
    return clean

def generar_handle(texto):
    if not isinstance(texto, str): return ""
    try:
        texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    except: pass
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-')

def descargar_imagen_pil(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, stream=True, timeout=5)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
    except Exception:
        return None
    return None

# --- FUNCIONES DE IA (TEXTO Y VISIÓN) ---
def procesar_texto(producto, tono, model):
    max_intentos = 3
    for intento in range(max_intentos):
        try:
            prompt = f"Actúa como experto E-commerce. Escribe descripción corta (máx 40 palabras) para: {producto}. Tono: {tono}. Sin markdown."
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            time.sleep(2)
            if intento == max_intentos - 1: return f"Error: {e}"
    return "Error"

def procesar_vision(imagen_pil, tono, model):
    if imagen_pil is None:
        return "Error: No se pudo descargar imagen"
    
    max_intentos = 3
    for intento in range(max_intentos):
        try:
            prompt = f"Eres un experto en ventas. Mira este producto y escribe una descripción atractiva para venta online (máx 40 palabras). Tono: {tono}. Describe material y estilo visual."
            response = model.generate_content([prompt, imagen_pil])
            return response.text.strip()
        except Exception as e:
            time.sleep(2)
            if intento == max_intentos - 1: return f"Error IA: {e}"
    return "Error"

def validar_url_imagen(url):
    try:
        if pd.isna(url) or url == "": return "❌ URL Vacía"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        return "✅ Activo" if r.status_code == 200 else f"⚠️ Error {r.status_code}"
    except Exception: return "❓ Error Conexión"

def descargar_excel(df, nombre_archivo):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button(label="📥 Descargar Resultados", data=output.getvalue(), file_name=nombre_archivo, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# --- INTERFAZ PRINCIPAL ---
def main():
    st.title("✨ Fábrica de Contenido AI & Tools")
    
    st.sidebar.header("🛠️ Panel de Control")
    modo = st.sidebar.radio(
        "Selecciona una herramienta:",
        ("📝 Generador de Texto", "👁️ Generador por Visión", "🔍 Auditor de Imágenes", "🧹 Limpiador CSV"),
        key="navegacion_principal"
    )

    st.sidebar.markdown("---")

    # --- AYUDA CONTEXTUAL ---
    if modo == "📝 Generador de Texto":
        st.sidebar.info("Crea descripciones desde cero usando el nombre del producto.")
    elif modo == "👁️ Generador por Visión":
        st.sidebar.info("La IA 'mira' la foto desde la URL y escribe la descripción.")
    elif modo == "🔍 Auditor de Imágenes":
        st.sidebar.info("Verifica que los enlaces no den error 404.")
    elif modo == "🧹 Limpiador CSV":
        st.sidebar.info("Genera Handles y limpia HTML sucio.")

    # Configurar API Key
    usando_ia = modo in ["📝 Generador de Texto", "👁️ Generador por Visión"]
    if usando_ia:
        if not api_key:
            st.error("🔒 Configura tu API Key.")
            return
        genai.configure(api_key=api_key)

    uploaded_file = st.file_uploader("Sube tu archivo (Excel/CSV)", type=['csv', 'xlsx'])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
            else: df = pd.read_excel(uploaded_file)
            
            st.success(f"Cargado: {len(df)} filas.")
            st.dataframe(df.head(3), use_container_width=True)

            # --- MÓDULO 1: TEXTO ---
            if modo == "📝 Generador de Texto":
                st.subheader("Generación Basada en Nombre")
                col_prod = st.selectbox("Columna Nombres:", df.columns)
                tono = st.selectbox("Tono:", ["Persuasivo", "Lujo", "Técnico"])
                if st.button("🚀 Iniciar"):
                    progreso = st.progress(0)
                    res = []
                    
                    # --- ACTUALIZACIÓN A GEMINI 2.5 FLASH ---
                    # Si 'gemini-2.5-flash' da error, intenta 'gemini-1.5-flash-latest' como fallback
                    try:
                        model = genai.GenerativeModel('gemini-2.5-flash')
                    except:
                        st.warning("Modelo 2.5 no detectado, usando 1.5-flash...")
                        model = genai.GenerativeModel('gemini-1.5-flash')

                    for i, row in df.iterrows():
                        res.append(procesar_texto(row[col_prod], tono, model))
                        progreso.progress((i+1)/len(df))
                    df['Desc_IA'] = res
                    descargar_excel(df, "descripciones_texto.xlsx")

            # --- MÓDULO 4: VISIÓN ---
            elif modo == "👁️ Generador por Visión":
                st.subheader("Generación 'Mirando' la Foto")
                col_url = st.selectbox("Columna URLs Imagen:", df.columns)
                tono = st.selectbox("Tono:", ["Moda/Estilo", "Descriptivo", "Minimalista"])
                
                if st.button("👁️ Analizar y Describir"):
                    progreso = st.progress(0)
                    estado = st.empty()
                    res = []
                    preview_img = st.empty()
                    
                    # --- ACTUALIZACIÓN A GEMINI 2.5 FLASH ---
                    try:
                        model = genai.GenerativeModel('gemini-2.5-flash')
                    except:
                        st.warning("Modelo 2.5 no detectado, usando 1.5-flash...")
                        model = genai.GenerativeModel('gemini-1.5-flash')

                    for i, row in df.iterrows():
                        url = row[col_url]
                        estado.text(f"Analizando imagen {i+1}/{len(df)}...")
                        img = descargar_imagen_pil(url)
                        
                        if img:
                            preview_img.image(img, caption=f"Procesando producto {i+1}", width=150)
                            desc = procesar_vision(img, tono, model)
                        else:
                            desc = "Error: Imagen inaccesible"
                        
                        res.append(desc)
                        progreso.progress((i+1)/len(df))
                    
                    df['Desc_Vision_IA'] = res
                    estado.text("✅ ¡Análisis visual completado!")
                    preview_img.empty()
                    descargar_excel(df, "descripciones_visuales.xlsx")

            # --- MÓDULO 2: AUDITOR ---
            elif modo == "🔍 Auditor de Imágenes":
                st.subheader("Auditoría de Enlaces")
                col_url = st.selectbox("Columna URLs:", df.columns)
                if st.button("🔎 Auditar"):
                    progreso = st.progress(0)
                    res = []
                    for i, row in df.iterrows():
                        res.append(validar_url_imagen(row[col_url]))
                        progreso.progress((i+1)/len(df))
                    df['Estado_Img'] = res
                    descargar_excel(df, "reporte_auditoria.xlsx")

            # --- MÓDULO 3: LIMPIADOR ---
            elif modo == "🧹 Limpiador CSV":
                st.subheader("Limpieza Shopify")
                col_tit = st.selectbox("Columna Títulos:", df.columns)
                col_desc = st.selectbox("Columna Descripción (Opcional):", ["Ninguna"] + list(df.columns))
                if st.button("✨ Limpiar"):
                    df['Handle'] = df[col_tit].apply(generar_handle)
                    if col_desc != "Ninguna":
                        df[col_desc] = df[col_desc].apply(limpiar_texto)
                        df[col_tit] = df[col_tit].astype(str).str.title()
                    descargar_excel(df, "csv_limpio.xlsx")

        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
