import io, zipfile, gc
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz  # Se instala como pymupdf
from PIL import Image

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head>
            <title>Cortador de PDF - SDE</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: sans-serif; text-align: center; padding: 20px; background-color: #f4f4f9; }
                .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-block; max-width: 400px; }
                input, select { margin: 10px 0; padding: 10px; width: 100%; border: 1px solid #ccc; border-radius: 5px; }
                button { background-color: #007bff; color: white; border: none; padding: 12px; width: 100%; border-radius: 5px; cursor: pointer; font-size: 16px; }
                button:hover { background-color: #0056b3; }
                .options { text-align: left; margin: 15px 0; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>✂️ Cortador Pro</h1>
                <p>Corta rangos y elige el formato de salida.</p>
                <form action="/procesar" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" accept=".pdf" required>
                    <input type="text" name="rango" placeholder="Ejemplo: 1-5" required>
                    
                    <div class="options">
                        <label><b>Formato de descarga:</b></label><br>
                        <input type="radio" name="formato" value="pdf" checked> PDF (Original)<br>
                        <input type="radio" name="formato" value="jpg"> Imágenes (JPG)
                    </div>
                    
                    <button type="submit">Procesar y Descargar ZIP</button>
                </form>
            </div>
        </body>
    </html>
    """

@app.post("/procesar")
async def procesar_pdf(file: UploadFile = File(...), rango: str = Form(...), formato: str = Form(...)):
    pdf_content = await file.read()
    doc = fitz.open(stream=pdf_content, filetype="pdf")
    
    # Validar rango
    try:
        start, end = map(int, rango.split("-"))
    except:
        return {"error": "Formato de rango inválido. Usa ej: 1-5"}

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
                zip_file.writestr(f"pagina_{page_num+1}.pdf", pdf_bytes)
                new_pdf.close()
            else:
                # Generar Imagen JPG
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Alta calidad
                img_data = pix.tobytes("jpg")
                zip_file.writestr(f"pagina_{page_num+1}.jpg", img_data)

    doc.close()
    gc.collect()
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer, 
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=recortes_sde.zip"}
    )
