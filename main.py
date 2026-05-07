import io
import zipfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz  # PyMuPDF
from PIL import Image

app = FastAPI()

# --- INTERFAZ DE USUARIO (HTML/CSS) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cortador de PDF - SDE</title>
    <style>
        :root {
            --neon-cyan: #00f2ff;
            --dark-bg: #0a0a0b;
            --panel-bg: #141417;
        }
        body {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
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
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: 2px solid var(--neon-cyan);
            box-shadow: 0 0 15px var(--neon-cyan);
            overflow: hidden;
            margin: 0 auto 15px;
            background: black;
        }
        .monogram-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        h1 {
            letter-spacing: 3px;
            font-weight: 300;
            margin: 10px 0;
            text-shadow: 0 0 10px rgba(0, 242, 255, 0.5);
        }
        .container {
            background: var(--panel-bg);
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            border: 1px solid #2d2d31;
            width: 90%;
            max-width: 450px;
            text-align: center;
        }
        input[type="file"], input[type="text"] {
            width: 100%;
            padding: 12px;
            margin: 15px 0;
            background: #1c1c1f;
            border: 1px solid #3f3f46;
            color: white;
            border-radius: 5px;
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
            letter-spacing: 2px;
            transition: 0.3s;
            margin-top: 10px;
        }
        button:hover {
            background: var(--neon-cyan);
            color: black;
            box-shadow: 0 0 20px var(--neon-cyan);
        }
        footer {
            margin-top: 40px;
            font-size: 0.8rem;
            color: #666;
            letter-spacing: 1px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="monogram-container">
            <img src="https://raw.githubusercontent.com/gidodido815-sketch/cortador-pdf-web2/be9f2f2beb1668769284ead42528a837484ef865/WhatsApp%20Image%202026-05-07%20at%2020.20.39.jpeg" alt="Logo">
        </div>
        <h1>TERMINAL DE PROCESAMIENTO</h1>
    </div>
    
    <div class="container">
        <form action="/procesar" method="post" enctype="multipart/form-data">
            <label>CARGAR ARCHIVO PDF</label>
            <input type="file" name="file" accept=".pdf" required>
            
            <label>RANGO DE PÁGINAS (EJ: 1-5)</label>
            <input type="text" name="pages" value="1-5" required>
            
            <button type="submit">EJECUTAR CORTE DIGITAL</button>
        </form>
    </div>

    <footer>SANTIAGO DEL ESTERO | 2026</footer>
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
    
    # Lógica de rango
    try:
        start, end = map(int, pages.split('-'))
    except:
        start, end = 1, len(doc)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for page_num in range(start-1, min(end, len(doc))):
            page = doc[page_num]
            
            # Definir rectángulos de recorte (Ajustar según necesidad)
            rects = [
                fitz.Rect(0, 0, page.rect.width, page.rect.height/2),  # R1
                fitz.Rect(0, page.rect.height/2, page.rect.width, page.rect.height) # R2
            ]

            for i, rect in enumerate(rects):
                pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                zip_file.writestr(f"pág_{page_num+1}_recorte_{i+1}.png", img_data)

    doc.close()
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer, 
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=recortes_procesados.zip"}
    )
