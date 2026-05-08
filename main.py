import io
import zipfile
import gc
import re
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz  # PyMuPDF

app = FastAPI()

# --- INTERFAZ SOFISTICADA ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TERMINAL SDE - PROCESAMIENTO</title>
    <style>
        :root { --neon-cyan: #00f2ff; --dark-bg: #0a0a0b; --panel-bg: #141417; }
        body {
            font-family: 'Courier New', monospace;
            background-color: var(--dark-bg); color: white;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            min-height: 100vh; margin: 0;
        }
        .header { text-align: center; margin-bottom: 30px; }
        .monogram-container {
            width: 100px; height: 100px; border-radius: 50%;
            border: 2px solid var(--neon-cyan); box-shadow: 0 0 20px var(--neon-cyan);
            overflow: hidden; margin: 0 auto 15px; background: black;
            display: flex; align-items: center; justify-content: center;
        }
        .monogram-container img { width: 100%; height: 100%; object-fit: cover; }
        h1 { letter-spacing: 4px; font-weight: 300; text-shadow: 0 0 10px var(--neon-cyan); font-size: 1.5rem; }
        .container {
            background: var(--panel-bg); padding: 30px; border-radius: 10px;
            border: 1px solid #2d2d31; width: 90%; max-width: 450px;
            box-shadow: 0 10px 50px rgba(0,0,0,0.7);
        }
        label { display: block; margin-top: 15px; color: #888; font-size: 0.75rem; text-transform: uppercase; }
        .hint { color: #555; font-size: 0.65rem; margin-bottom: 5px; }
        input, select {
            width: 100%; padding: 12px; margin: 5px 0 15px 0;
            background: #000; border: 1px solid #333;
            color: var(--neon-cyan); border-radius: 4px; box-sizing: border-box;
        }
        button {
            width: 100%; padding: 15px; background: transparent;
            color: var(--neon-cyan); border: 1px solid var(--neon-cyan);
            cursor: pointer; font-weight: bold; margin-top: 10px;
            transition: 0.3s; letter-spacing: 2px;
        }
        button:hover { background: var(--neon-cyan); color: black; box-shadow: 0 0 20px var(--neon-cyan); }
    </style>
</head>
<body>
    <div class="header">
        <div class="monogram-container">
            <img src="https://raw.githubusercontent.com/gidodido815-sketch/cortador-pdf-web2/main/WhatsApp%20Image%202026-05-07%20at%2020.20.39.jpeg" alt="Logo SDE">
        </div>
        <h1>TERMINAL DE EXTRACCIÓN</h1>
    </div>
    
    <div class="container">
        <form action="/procesar" method="post" enctype="multipart/form-data">
            <label>Archivo de Origen</label>
            <input type="file" name="file" accept=".pdf" required>
            
            <label>Selección de Páginas</label>
            <div class="hint">Ejemplos: 1-3 (bloque), 1,4,6 (sueltas), 1-2,5 (mixto)</div>
            <input type="text" name="pages" placeholder="1-3, 5" required>
            
            <label>Formato de Salida</label>
            <select name="format">
                <option value="pdf">Unir en un solo PDF</option>
                <option value="jpg">Imágenes Individuales (ZIP)</option>
            </select>
            
            <button type="submit">INICIAR EXTRACCIÓN</button>
        </form>
    </div>
    <p style="margin-top: 20px; font-size: 0.6rem; color: #444;">SANTIAGO DEL ESTERO | SISTEMA DE AUDITORÍA</p>
</body>
</html>
"""

def parse_pages(pages_str, total_pages):
    """Convierte strings como '1-3, 5' en una lista de índices [0, 1, 2, 4]"""
    indices = set()
    parts = re.split(r'[,\s]+', pages_str)
    for part in parts:
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                indices.update(range(max(1, start)-1, min(end, total_pages)))
            except: continue
        else:
            try:
                val = int(part)
                if 1 <= val <= total_pages:
                    indices.add(val - 1)
            except: continue
    return sorted(list(indices))

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_CONTENT

@app.post("/procesar")
async def procesar_pdf(file: UploadFile = File(...), pages: str = Form(...), format: str = Form(...)):
    pdf_bytes = await file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = len(doc)
    
    # Obtener lista de páginas solicitadas
    selected_indices = parse_pages(pages, total)
    if not selected_indices:
        selected_indices = list(range(total)) # Si hay error, procesar todo

    output_buffer = io.BytesIO()
    
    if format == "jpg":
        with zipfile.ZipFile(output_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
            for idx in selected_indices:
                page = doc[idx]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                zip_file.writestr(f"pagina_{idx+1}.jpg", pix.tobytes("jpg"))
        filename = "SDE_EXTRACCION.zip"
        mimetype = "application/zip"
    else:
        new_pdf = fitz.open()
        new_pdf.insert_pdf(doc, from_page=0, to_page=total-1, annots=True)
        # Eliminar las páginas que NO fueron seleccionadas (en orden inverso)
        all_indices = set(range(total))
        to_delete = sorted(list(all_indices - set(selected_indices)), reverse=True)
        for idx in to_delete:
            new_pdf.delete_page(idx)
        
        new_pdf.save(output_buffer)
        new_pdf.close()
        filename = "SDE_EXTRACCION.pdf"
        mimetype = "application/pdf"

    doc.close()
    gc.collect()
    output_buffer.seek(0)
    
    return StreamingResponse(
        output_buffer, 
        media_type=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
