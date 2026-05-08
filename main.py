import io
import zipfile
import gc
import re
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz  # PyMuPDF

app = FastAPI()

# --- INTERFAZ PROFESIONAL SDE ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TERMINAL SDE - EXTRACCIÓN PRO</title>
    <style>
        :root { --neon: #00f2ff; --bg: #0a0a0b; --card: #141417; }
        body {
            font-family: 'Courier New', monospace; background-color: var(--bg); color: white;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            min-height: 100vh; margin: 0;
        }
        .header { text-align: center; margin-bottom: 25px; }
        .monogram-container {
            width: 100px; height: 100px; border-radius: 50%;
            border: 2px solid var(--neon); box-shadow: 0 0 20px var(--neon);
            overflow: hidden; margin: 0 auto 15px; background: black;
            display: flex; align-items: center; justify-content: center;
        }
        .monogram-container img { width: 100%; height: 100%; object-fit: cover; }
        h1 { letter-spacing: 3px; font-weight: 300; text-shadow: 0 0 10px var(--neon); font-size: 1.3rem; }
        .container {
            background: var(--card); padding: 30px; border-radius: 10px;
            border: 1px solid #2d2d31; width: 90%; max-width: 450px;
            box-shadow: 0 10px 50px rgba(0,0,0,0.7);
        }
        label { display: block; margin-top: 15px; color: #888; font-size: 0.7rem; }
        input, select {
            width: 100%; padding: 12px; margin: 5px 0 15px 0;
            background: #000; border: 1px solid #333;
            color: var(--neon); border-radius: 4px; box-sizing: border-box;
        }
        button {
            width: 100%; padding: 15px; background: transparent;
            color: var(--neon); border: 1px solid var(--neon);
            cursor: pointer; font-weight: bold; margin-top: 10px;
            transition: 0.3s; letter-spacing: 2px;
        }
        button:hover { background: var(--neon); color: black; box-shadow: 0 0 20px var(--neon); }
        .info { font-size: 0.6rem; color: #555; line-height: 1.2; margin-bottom: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="monogram-container">
            <img src="https://raw.githubusercontent.com/gidodido815-sketch/cortador-pdf-web2/main/WhatsApp%20Image%202026-05-07%20at%2020.20.39.jpeg" alt="SDE LOGO">
        </div>
        <h1>SISTEMA DE EXTRACCIÓN DIGITAL</h1>
    </div>
    
    <div class="container">
        <form action="/procesar" method="post" enctype="multipart/form-data">
            <label>DOCUMENTO PDF DE ORIGEN</label>
            <input type="file" name="file" accept=".pdf" required>
            
            <label>SELECCIÓN DE PÁGINAS</label>
            <div class="info">Ejemplos: 1,4,8 (sueltas) | 1-5 (rango) | 1,3,5-10 (mixto)</div>
            <input type="text" name="pages" placeholder="Ej: 1,4,8" required>
            
            <label>MODO DE DESCARGA</label>
            <select name="format">
                <option value="single_pdf">Bloque Único (Un solo archivo PDF)</option>
                <option value="zip_pdf">Carpeta de Archivos (ZIP con PDFs individuales)</option>
                <option value="zip_jpg">Carpeta de Imágenes (ZIP con JPGs individuales)</option>
            </select>
            
            <button type="submit">EJECUTAR PROCESAMIENTO</button>
        </form>
    </div>
    <p style="margin-top: 20px; font-size: 0.6rem; color: #333;">AUDITORÍA DIGITAL - SANTIAGO DEL ESTERO</p>
</body>
</html>
"""

def parse_pages(pages_str, max_pages):
    """Convierte la entrada de texto en una lista de números de página válidos."""
    indices = set()
    parts = re.split(r'[,\s]+', pages_str)
    for part in parts:
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                indices.update(range(max(1, start), min(end, max_pages) + 1))
            except: continue
        else:
            try:
                p = int(part)
                if 1 <= p <= max_pages: indices.add(p)
            except: continue
    return sorted(list(indices))

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_CONTENT

@app.post("/procesar")
async def procesar(file: UploadFile = File(...), pages: str = Form(...), format: str = Form(...)):
    # Leer archivo
    content = await file.read()
    doc = fitz.open(stream=content, filetype="pdf")
    
    # Obtener lista de páginas solicitadas (ej: 1, 4, 8)
    target_pages = parse_pages(pages, len(doc))
    output = io.BytesIO()
    
    if format == "single_pdf":
        # Une todas las seleccionadas en un solo archivo PDF
        res_pdf = fitz.open()
        for p in target_pages:
            res_pdf.insert_pdf(doc, from_page=p-1, to_page=p-1)
        res_pdf.save(output)
        res_pdf.close()
        mimetype, filename = "application/pdf", "bloque_unificado.pdf"
        
    elif format == "zip_pdf":
        # Crea un ZIP donde cada página elegida es un archivo PDF separado
        with zipfile.ZipFile(output, "a") as zf:
            for p in target_pages:
                temp_pdf = fitz.open()
                temp_pdf.insert_pdf(doc, from_page=p-1, to_page=p-1)
                zf.writestr(f"pagina_{p}.pdf", temp_pdf.write())
                temp_pdf.close()
        mimetype, filename = "application/zip", "archivos_individuales.zip"
        
    else: # zip_jpg
        # Crea un ZIP con cada página convertida a imagen JPG
        with zipfile.ZipFile(output, "a") as zf:
            for p in target_pages:
                pix = doc[p-1].get_pixmap(matrix=fitz.Matrix(2, 2))
                zf.writestr(f"pagina_{p}.jpg", pix.tobytes("jpg"))
        mimetype, filename = "application/zip", "imagenes_individuales.zip"

    doc.close()
    gc.collect()
    output.seek(0)
    return StreamingResponse(output, media_type=mimetype, headers={"Content-Disposition": f"attachment; filename={filename}"})
