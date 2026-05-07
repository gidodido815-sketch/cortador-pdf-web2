import io, zipfile, gc
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz  # PyMuPDF
from PIL import Image

app = FastAPI()

# ESTO ES LO QUE FALTA: La página que ve el usuario al entrar
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head><title>Cortador de PDF - SDE</title></head>
        <body style="font-family:sans-serif; text-align:center; padding:50px;">
            <h1>✂️ Cortador de PDF Automático</h1>
            <p>Sube tu PDF para procesar los recortes de R1 y R2</p>
            <form action="/procesar" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".pdf" required><br><br>
                <label>Rango de páginas (ej: 1-5):</label><br>
                <input type="text" name="rango" value="1-5"><br><br>
                <button type="submit" style="padding:10px 20px; background:blue; color:white; border:none; cursor:pointer;">
                    Procesar y Descargar ZIP
                </button>
            </form>
            <p style="margin-top:50px; color:gray;">Desarrollado en Santiago del Estero</p>
        </body>
    </html>
    """

@app.post("/procesar")
async def procesar_pdf(file: UploadFile = File(...), rango: str = Form("1-5")):
    contenido = await file.read()
    doc = fitz.open(stream=contenido, filetype="pdf")
    total_paginas = len(doc)
    inicio, fin = 0, total_paginas
    if rango != "all":
        partes = rango.split("-")
        inicio = max(0, int(partes[0]) - 1)
        fin = min(total_paginas, int(partes[1]))

    buffer_zip = io.BytesIO()
    with zipfile.ZipFile(buffer_zip, "a", zipfile.ZIP_DEFLATED) as zip_file:
        for i in range(inicio, fin):
            pagina = doc.load_page(i)
            pix = pagina.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img = Image.open(io.BytesIO(pix.tobytes()))
            w, h = img.size
            cortes = [((40, 90, 410, h//2-20), "R1"), ((40, h//2+90, 410, h-20), "R2")]
            for corte, ref in cortes:
                reg = img.crop(corte)
                img_byte_arr = io.BytesIO()
                reg.save(img_byte_arr, format='JPEG', quality=75)
                zip_file.writestr(f"pagina_{i+1}_{ref}.jpg", img_byte_arr.getvalue())
            del pix, img
            if i % 50 == 0: gc.collect()
    doc.close()
    buffer_zip.seek(0)
    return StreamingResponse(buffer_zip, media_type="application/x-zip-compressed",
                             headers={"Content-Disposition": "attachment; filename=recortes.zip"})
