import io, zipfile, gc
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from starlette.status import HTTP_413_REQUEST_ENTITY_TOO_LARGE
import fitz  # Se instala como pymupdf
from PIL import Image

app = FastAPI()

# Configuración del límite de tamaño del archivo (2GB en bytes)
# 2 * 1024 * 1024 * 1024 = 2,147,483,648 bytes
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024

# HTML con diseño sofisticado e informático, y validación JavaScript
@app.get("/", response_class=HTMLResponse)
async def home():
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cortador de PDF - SDE [PRO]</title>
        <style>
            :root {{
                --bg-color: #121212;
                --text-color: #E0E0E0;
                --accent-color: #00E5FF; /* Azul Eléctrico */
                --secondary-bg: #1F1F1F;
                --error-color: #FF5252;
                --font-family: 'Open Sans', sans-serif;
                --mono-family: 'Fira Code', monospace;
            }}

            body {{
                font-family: var(--font-family);
                background-color: var(--bg-color);
                color: var(--text-color);
                margin: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }}

            .header {{
                margin-bottom: 40px;
                text-align: center;
            }}

            .monogram {{
                width: 120px;
                height: 120px;
                border-radius: 50%;
                background-color: transparent;
                border: 2px solid var(--accent-color);
                padding: 10px;
                box-shadow: 0 0 15px var(--accent-color);
                margin-bottom: 15px;
            }}

            h1 {{
                font-family: var(--mono-family);
                font-weight: 300;
                font-size: 1.8em;
                margin: 0;
                color: var(--accent-color);
            }}

            .sophisticated-tag {{
                font-size: 0.8em;
                color: var(--accent-color);
                opacity: 0.7;
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-top: 5px;
            }}

            .main-card {{
                background-color: var(--secondary-bg);
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                width: 100%;
                max-width: 500px;
                display: flex;
                flex-direction: column;
                border: 1px solid #333;
            }}

            .form-group {{
                margin-bottom: 25px;
            }}

            label {{
                display: block;
                font-size: 0.9em;
                margin-bottom: 8px;
                color: #aaa;
                font-weight: 600;
            }}

            . технические-детали {{
                font-family: var(--mono-family);
                font-size: 0.8em;
                color: #888;
                margin-bottom: 5px;
            }}

            input[type="file"],
            input[type="text"] {{
                width: 100%;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #444;
                background-color: #1A1A1A;
                color: var(--text-color);
                box-sizing: border-box;
                font-size: 1em;
            }}

            input[type="file"]:focus,
            input[type="text"]:focus {{
                border-color: var(--accent-color);
                outline: none;
                box-shadow: 0 0 5px var(--accent-color);
            }}

            .options-group {{
                display: flex;
                flex-direction: column;
                margin-top: 10px;
                color: #aaa;
            }}

            .options-group label {{
                display: flex;
                align-items: center;
                font-weight: normal;
                margin-bottom: 10px;
                color: #eee;
            }}

            .options-group input {{
                margin-right: 15px;
            }}

            button {{
                background-color: var(--accent-color);
                color: #121212;
                border: none;
                padding: 15px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 1.1em;
                font-weight: 700;
                transition: background-color 0.3s, transform 0.1s;
                margin-top: 20px;
                width: 100%;
            }}

            button:hover {{
                background-color: #00B2CC; /* Un azul más oscuro en hover */
            }}

            button:active {{
                transform: scale(0.98);
            }}

            #fileError, #submitError {{
                color: var(--error-color);
                font-size: 0.9em;
                margin-top: 5px;
                display: none;
            }}

            .footer {{
                margin-top: 50px;
                font-size: 0.8em;
                color: #777;
                font-family: var(--mono-family);
            }}
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;500&family=Open+Sans:wght@400;600&display=swap" rel="stylesheet">
    </head>
    <body>
        <div class="header">
            <img src="https://gidodido815-boceto.github.io/cortador-pdf-web2/monogram.png" alt="Monograma Sofisticado" class="monogram">
            <h1>CORTADOR DE PDF [SDE]</h1>
            <div class="sophisticated-tag">OPERACIONES INTELECTUALES DIGITALES</div>
        </div>

        <div class="main-card">
            <form id="cutForm" action="/procesar" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="file">SELECCIONAR ARCHIVO PDF</label>
                    <div class="технические-детали">Límite de tamaño: 2.0 GB (2,147,483,648 bytes)</div>
                    <input type="file" id="file" name="file" accept=".pdf" required>
                    <div id="fileError">El archivo excede el límite de 2GB.</div>
                </div>

                <div class="form-group">
                    <label for="rango">RANGO DE PÁGINAS</label>
                    <div class="технические-детали">Formato de consola: INICIO-FIN (ej. 1-12)</div>
                    <input type="text" id="rango" name="rango" placeholder="console.input(RANGO)" required>
                </div>
                
                <div class="form-group">
                    <label>FORMATO DE SALIDA DE ARCHIVOS</label>
                    <div class="options-group">
                        <label><input type="radio" name="formato" value="pdf" checked>PDF (PRESERVACIÓN DIGITAL ORIGINAL)</label>
                        <label><input type="radio" name="formato" value="jpg">JPG (COMPRESIÓN DE IMAGEN DE ALTA CALIDAD)</label>
                    </div>
                </div>
                
                <button type="submit">GENERAR Y DESCARGAR ARCHIVO ZIP</button>
                <div id="submitError">Error al enviar el formulario. Verifica los campos.</div>
            </form>
        </div>

        <div class="footer">
            [SISTEMA DESARROLLADO EN SANTIAGO DEL ESTERO, ARGENTINA]
        </div>

        <script>
            // Límite de tamaño en bytes (2GB)
            const MAX_FILE_SIZE = {MAX_FILE_SIZE_BYTES};
            const fileInput = document.getElementById('file');
            const fileError = document.getElementById('fileError');
            const submitForm = document.getElementById('cutForm');
            const submitError = document.getElementById('submitError');

            fileInput.addEventListener('change', function() {{
                const file = this.files[0];
                if (file && file.size > MAX_FILE_SIZE) {{
                    fileError.style.display = 'block';
                    this.value = ''; // Limpiar la selección
                } else {{
                    fileError.style.display = 'none';
                }
            }});

            submitForm.addEventListener('submit', function(event) {{
                const file = fileInput.files[0];
                if (!file || file.size > MAX_FILE_SIZE) {{
                    submitError.style.display = 'block';
                    submitError.textContent = "Error: Archivo inválido o demasiado grande (máx 2GB).";
                    event.preventDefault(); // Detener el envío
                } else {{
                    submitError.style.display = 'none';
                }
            }});
        </script>
    </body>
    </html>
    """

# Validación del lado del servidor para el tamaño del archivo
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/procesar":
        content_length = request.headers.get('content-length')
        if content_length:
            content_length = int(content_length)
            if content_length > MAX_FILE_SIZE_BYTES:
                return JSONResponse(
                    content={{"detail": f"Request body too large. Maximum size allowed is {MAX_FILE_SIZE_BYTES} bytes."}},
                    status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )
    
    response = await call_next(request)
    return response

@app.post("/procesar")
async def procesar_pdf(file: UploadFile = File(...), rango: str = Form(...), formato: str = Form(...)):
    # Doble validación en el servidor
    if file.size > MAX_FILE_SIZE_BYTES:
         raise HTTPException(status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large. Max 2GB.")

    pdf_content = await file.read()
    doc = fitz.open(stream=pdf_content, filetype="pdf")
    
    # Validar rango
    try:
        start, end = map(int, rango.split("-"))
    except:
        return {{"error": "Formato de rango inválido. Usa ej: 1-5"}}

    # Limitar rango a lo que tiene el PDF
    start = max(1, start)
    end = min(len(doc), end)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
        for page_num in range(start - 1, end):
            if formato == "pdf":
                # Generar PDF de una sola página
                new_pdf = fitz.open()
                new_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)
                pdf_bytes = new_pdf.write()
                zip_file.writestr(f"pagina_{{page_num+1}}.pdf", pdf_bytes)
                new_pdf.close()
            else:
                # Generar Imagen JPG
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Alta calidad
                img_data = pix.tobytes("jpg")
                zip_file.writestr(f"pagina_{{page_num+1}}.jpg", img_data)

    doc.close()
    gc.collect()
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer, 
        media_type="application/x-zip-compressed",
        headers={{"Content-Disposition": "attachment; filename=recortes_sde_pro.zip"}}
    )
