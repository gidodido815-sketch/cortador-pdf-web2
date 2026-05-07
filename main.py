from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
import io
from PyPDF2 import PdfReader, PdfWriter

app = FastAPI()

@app.post("/cortar-pdf/")
async def cortar_pdf(file: UploadFile = File(...), inicio: int = 0, fin: int = 1):
    # Leer el archivo que subió el usuario
    contenido = await file.read()
    lector = PdfReader(io.BytesIO(contenido))
    escritor = PdfWriter()

    # Lógica para cortar (ajusta según necesites)
    for i in range(inicio, min(fin, len(lector.pages))):
        escritor.add_page(lector.pages[i])

    # Guardar el resultado en memoria para enviarlo de vuelta
    salida = io.BytesIO()
    escritor.write(salida)
    salida.seek(0)
    
    return StreamingResponse(salida, media_type="application/pdf", 
                             headers={"Content-Disposition": "attachment; filename=cortado.pdf"})