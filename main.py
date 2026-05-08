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
        .info { font-size: 0.6rem; color: #555; line-height: 1.2; }
    </style>
</head>
<body>
    <div class="header">
        <div class="monogram-container">
            <img src="https://raw.githubusercontent.com/gidodido815-sketch/cortador-pdf-web2/main/WhatsApp%20Image%202026-05-07%20at%2020.20.39.jpeg" alt="SDE">
        </div>
        <h1>SISTEMA DE EXTRACCIÓN PERICIAL</h1>
    </div>
    
    <div class="container">
        <form action="/procesar" method="post" enctype="multipart/form-data">
            <label>DOCUMENTO PDF</label>
            <input type="file" name="file" accept=".pdf" required>
            
            <label>CONFIGURACIÓN DE PÁGINAS</label>
            <div class="info">Sueltas: 1,4,8 | Rango: 1-5 | Mixto: 1-3,7</div>
            <input type="text" name="pages" placeholder="Ej: 1,3,5-8" required>
            
            <label>MODO DE SALIDA</label>
            <select name="format">
                <option value="single_pdf">Un solo bloque (Un solo PDF)</option>
                <option value="zip_pdf">Páginas individuales (Carpeta ZIP de PDFs)</option>
                <option value="zip_jpg">Imágenes individuales (Carpeta ZIP de JPGs)</option>
            </select>
            
            <button type="submit">EJECUTAR PROCESO</button>
        </form>
    </div>
    <p style="margin-top: 20px; font-size: 0.6rem; color: #333;">AUDITORÍA DIGITAL - SANTIAGO DEL ESTERO</p>
</body>
</html>
"""

def get_page_list(pages_str, max_pages):
    """Procesa la entrada del usuario para obtener una lista de números de página."""
    pages = set()
    parts = re.split(r'[,\s]+', pages_str)
    for part in parts:
        if '-' in part:
            try:
                s, e = map(int, part.split('-'))
                pages.update(range(max(1, s), min(e, max_pages) + 1))
            except: continue
        else:
            try:
                p = int(part)
                if 1 <= p <= max_pages: pages.add(p)
            except: continue
    return sorted(list(pages))

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_CONTENT

@app.post("/procesar")
async def procesar(file: UploadFile = File(...), pages: str = Form(...), format: str = Form(...)):
    data = await file.read()
    doc = fitz.open(stream=data, filetype="pdf")
    target_pages = get_page_list(pages, len(doc))
    
    output = io.BytesIO()
    
    if format == "single_pdf":
        # Opción: Todas las seleccionadas en un solo archivo
        new_pdf = fitz.open()
        for p in target_pages:
            new_pdf.insert_pdf(doc, from_page=p-1, to_page=p-1)
        new_pdf.save(output)
        new_pdf.close()
        mimetype, filename = "application/pdf", "seleccion_unificada.pdf"
        
    elif format == "zip_pdf":
        # Opción: Cada página un PDF separado dentro de un ZIP
        with zipfile.ZipFile(output, "a") as zf:
            for p in target_pages:
                temp_pdf = fitz.open()
                temp_pdf.insert_pdf(doc, from_page=p-1, to_page=p-1)
                zf.writestr(f"pagina_{p}.pdf", temp_pdf.write())
                temp_pdf.close()
        mimetype, filename = "application/zip", "paginas_individuales_pdf.zip"
        
    else: # zip_jpg
        # Opción: Cada página una imagen dentro de un ZIP
        with zipfile.ZipFile(output, "a") as zf:
            for p in target_pages:
                pix = doc[p-1].get_pixmap(matrix=fitz.Matrix(2, 2))
                zf.writestr(f"pagina_{p}.jpg", pix.tobytes("jpg"))
        mimetype, filename = "application/zip", "paginas_individuales_jpg.zip"

    doc.close()
    gc.collect()
    output.seek(0)
    return StreamingResponse(output, media_type=mimetype, headers={"Content-Disposition": f"attachment; filename={filename}"})
