import io
import zipfile
import gc
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz  # PyMuPDF
from PIL import Image

app = FastAPI()

# --- INTERFAZ SOFISTICADA SDE ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TERMINAL SDE - PROCESAMIENTO</title>
    <style>
        :root {
            --neon-cyan: #00f2ff;
            --dark-bg: #0a0a0b;
            --panel-bg: #141417;
        }
        body {
            font-family: 'Courier New', monospace;
            background-color: var(--dark-bg);
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .monogram-container {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 2px solid var(--neon-cyan);
            box-shadow: 0 0 20px var(--neon-cyan);
            overflow: hidden;
            margin: 0 auto 15px;
            background: black;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .monogram-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        h1 {
            letter-spacing: 4px;
            font-weight: 300;
            text-shadow: 0 0 10px var(--neon-cyan);
        }
        .container {
            background: var(--panel-bg);
            padding: 40px;
            border-radius: 10px;
            border: 1px solid #2d2d31;
            width: 90%;
            max-width: 450px;
            box-shadow: 0 10px 50px rgba(0,0,0,0.7);
        }
        label { display: block; margin-top: 20px; color: #888; font-size: 0.8rem; }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            background: #000;
            border: 1px solid #333;
            color: var(--neon-cyan);
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 15px;
            background: transparent;
            color: var(--neon-cyan);
            border: 1px solid var(--neon-cyan);
            cursor: pointer;
            font-weight: bold;
            margin-top: 20px;
            transition: 0.3s;
        }
        button:hover {
            background: var(--neon-cyan);
            color: black;
            box-shadow: 0 0 20px var(--neon-cyan);
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="monogram-container">
            <img src="https://raw.githubusercontent.com/gidodido815-sketch/cortador-pdf-web2/main/WhatsApp%20Image%202026-05-07%20at%2020.20.39.jpeg" alt="SDE Logo">
        </div>
        <h1>TERMINAL DE PROCESAMIENTO</h1>
    </div>
    
    <div class="container">
        <form action="/procesar" method="post" enctype="multipart/form-data">
            <label>SISTEMA DE ENTRADA: PDF</label>
            <input type="file" name="file" accept=".pdf" required>
            
            <label>RANGO DINÁMICO (EJ: 1-10)</label>
            <input type="text" name="pages" placeholder="1-5" required>
            
            <button type="submit">EJECUTAR CORTE DIGITAL</button>
        </form>
    </div>
    <p style="margin-top: 30px; font-size: 0.7rem; color: #444;">SANTIAGO DEL ESTERO | ARGENTINA</p>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_CONTENT

@app.post("/procesar")
async def procesar_pdf(file: UploadFile = File(...), pages: str = Form(...)):
    pdf_bytes = await file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    try:
        start, end = map(int, pages.split('-'))
    except:
        start, end = 1, len(doc)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
        for page_num in range(max(0, start-1), min(end, len(doc))):
            page = doc[page_num]
            # Recorte mitad superior (R1) y mitad inferior (R2)
            rects = [
                fitz.Rect(0, 0, page.rect.width, page.rect.height/2),
                fitz.Rect(0, page.rect.height/2, page.rect.width, page.rect.height)
            ]
            for i, rect in enumerate(rects):
                pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                zip_file.writestr(f"pág_{page_num+1}_recorte_{i+1}.png", img_data)

    doc.close()
    gc.collect()
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer, 
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=SDE_PROCESADO.zip"}
    )
