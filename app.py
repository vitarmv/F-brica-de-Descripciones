import streamlit as st
import google.generativeai as genai
import pandas as pd
import time
import io
import requests
import re
import unicodedata
import os
import html 
import ftfy 
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
    texto = ftfy.fix_text(texto)
    texto = html.unescape(texto)
    texto = re.sub(r'<[^>]+>', ' ', texto) 
    texto = texto.replace('\xa0', ' ')
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

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

# --- FUNCIONES DE IA (PROMPTS DINÁMICOS POR IDIOMA) ---
def procesar_texto(producto, tono, model, idioma):
    max_intentos = 3
    
    # LÓGICA DE PROMPT SEGÚN IDIOMA
    if "English" in idioma:
        role_instruction = """
        ROLE: You are a Senior E-commerce Copywriter with NATIVE US English proficiency.
        GOAL: Write a persuasive, SEO-optimized product description (max 40 words).
        RULES:
        1. OUTPUT LANGUAGE: STRICTLY Professional US English.
        2. TRANSLATION: If the INPUT is in Spanish or another language, translate and adapt it to English internally.
        3. GRAMMAR: Perfect grammar, no broken English.
        4. STRUCTURE: Start directly with the description. No "Here is...", no intros.
        """
    else: # Español
        role_instruction = """
        ROL: Eres un Redactor Senior de E-commerce experto en Español Neutro (Latinoamérica/España).
        OBJETIVO: Escribir una descripción atractiva y optimizada para SEO (máx 40 palabras).
        REGLAS:
        1. IDIOMA DE SALIDA: Español Neutro (evita jerga local excesiva).
        2. Si el INPUT está en otro idioma, tradúcelo y adáptalo al español.
        3. ESTRUCTURA: Empieza DIRECTAMENTE con la descripción. Sin saludos ni introducciones.
        """

    for intento in range(max_intentos):
        try:
            prompt = f"""
            {role_instruction}
            ----------------
            INPUT PRODUCT: {producto}
            TONE: {tono}
            """
            response = model.generate_content(prompt)
            return response.text.strip().replace('"', '').replace("Here is a description:", "")
        except Exception as e:
            time.sleep(2)
            if intento == max_intentos - 1: return f"Error: {e}"
    return "Error"

def procesar_vision(imagen_pil, tono, model, idioma):
    if imagen_pil is None:
        return "Error: No se pudo descargar imagen"
    
    # LÓGICA DE PROMPT SEGÚN IDIOMA (VISIÓN)
    if "English" in idioma:
        role_instruction = """
        ROLE: You are an expert AI Visual Merchandiser for online stores.
        TASK: Analyze the image and write a sales description (max 40 words).
        RULES:
        1. OUTPUT LANGUAGE: STRICTLY Professional US English.
        2. ACCURACY: Describe exactly what you see (color, material, style).
        3. GRAMMAR: Native-level US English.
        4. No intros like "This image shows". Start describing the item immediately.
        """
    else: # Español
        role_instruction = """
        ROL: Eres un experto en Visual Merchandising e Inteligencia Artificial.
        TAREA: Analiza la imagen y escribe una descripción de venta (máx 40 palabras).
        REGLAS:
        1. IDIOMA DE SALIDA: Español Neutro.
        2. PRECISIÓN: Describe exactamente lo que ves (color, material, estilo).
        3. Sin introducciones como "En la imagen veo". Empieza describiendo el producto.
        """

    max_intentos = 3
    for intento in range(max_intentos):
        try:
            prompt = f"""
            {role_instruction}
            ----------------
            TONE: {tono}
            """
            response = model.generate_content([prompt, imagen_pil])
            return response.text.strip().replace('"', '').replace("Here is a description:", "")
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
    
    # NUEVO: SELECTOR DE IDIOMA
    idioma_salida = st.sidebar.selectbox(
        "🏳️ Idioma de Salida / Output Language",
        ["English (Professional US)", "Español (Neutro)"]
    )

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
        st.sidebar.info("Genera Handles, limpia HTML sucio y arregla texto roto.")

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
                    
                    try:
                        model = genai.GenerativeModel('gemini-2.5-flash')
                    except:
                        st.warning("Usando gemini-1.5-flash...")
                        model = genai.GenerativeModel('gemini-1.5-flash')

                    for i, row in df.iterrows():
                        # AQUI PASAMOS EL IDIOMA
                        res.append(procesar_texto(row[col_prod], tono, model, idioma_salida))
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
                    
                    try:
                        model = genai.GenerativeModel('gemini-2.5-flash')
                    except:
                        st.warning("Usando gemini-1.5-flash...")
                        model = genai.GenerativeModel('gemini-1.5-flash')

                    for i, row in df.iterrows():
                        url = row[col_url]
                        estado.text(f"Analizando imagen {i+1}/{len(df)}...")
                        img = descargar_imagen_pil(url)
                        
                        if img:
                            preview_img.image(img, caption=f"Procesando producto {i+1}", width=150)
                            # AQUI PASAMOS EL IDIOMA
                            desc = procesar_vision(img, tono, model, idioma_salida)
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
