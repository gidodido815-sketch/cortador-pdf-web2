import io
import zipfile
import gc
import re
from fastapi import FastAPI, UploadFile, File, Form, Response, Cookie
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz  # PyMuPDF

app = FastAPI()

# --- CONFIGURACIÓN DE MONETIZACIÓN ---
# ID de cliente extraído de tu captura de pantalla de verificación
ADSENSE_SCRIPT = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3283369890047945" crossorigin="anonymous"></script>'
ALIAS_PAGO = "Proyectos863"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>SDE - TERMINAL DE PROCESAMIENTO</title>
    {adsense_script}
    <style>
        :root {{ --neon: #00f2ff; --bg: #0a0a0b; }}
        body {{ font-family: 'Courier New', monospace; background: var(--bg); color: white; text-align: center; padding: 20px; }}
        .card {{ background: #141417; padding: 30px; border-radius: 12px; border: 1px solid #2d2d31; max-width: 480px; margin: auto; box-shadow: 0 0 20px rgba(0,0,0,0.5); }}
        .ad-box {{ background: #000; border: 1px dashed #444; margin: 15px 0; min-height: 100px; display: flex; align-items: center; justify-content: center; color: #555; font-size: 0.7rem; }}
        .btn {{ width: 100%; padding: 15px; background: transparent; color: var(--neon); border: 1px solid var(--neon); cursor: pointer; font-weight: bold; letter-spacing: 2px; }}
        .btn:hover {{ background: var(--neon); color: black; box-shadow: 0 0 20px var(--neon); }}
        input, select {{ width: 100%; padding: 12px; margin-bottom: 15px; background: #000; border: 1px solid #333; color: var(--neon); border-radius: 4px; }}
        #waiting {{ display: none; }}
        .pay-card {{ border: 1px solid #ffcc00; color: #ffcc00; padding: 20px; margin-top: 10px; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="card">
        <img src="https://raw.githubusercontent.com/gidodido815-sketch/cortador-pdf-web2/main/WhatsApp%20Image%202026-05-07%20at%2020.20.39.jpeg" width="80" style="border-radius:50%; border:2px solid var(--neon); margin-bottom:15px;">
        {content}
    </div>
    <script>
        function iniciarEspera() {{
            window.open('https://www.google.com', '_blank');
            document.getElementById('main-ui').style.display = 'none';
            document.getElementById('waiting').style.display = 'block';
            let s = 15;
            const t = setInterval(() => {{
                s--;
                document.getElementById('timer').innerText = s;
                if(s <= 0) {{
                    clearInterval(t);
                    document.forms[0].submit();
                    setTimeout(() => location.reload(), 3000);
                }}
            }}, 1000);
        }}
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home(uses: str = Cookie(None)):
    current_uses = int(uses) if uses else 0
    
    if current_uses >= 2:
        content = f"""
        <h2 style="color:red;">LÍMITE ALCANZADO</h2>
        <p>Has agotado tus 2 usos gratuitos de hoy.</p>
        <div class="pay-card">
            <strong>ACCESO ILIMITADO:</strong><br><br>
            Alias Mercado Pago:<br>
            <span style="font-size:1.3rem; background:#333; padding:5px;">{ALIAS_PAGO}</span><br><br>
            Envía el comprobante para activar.
        </div>
        """
    else:
        content = """
        <div id="main-ui">
            <h2>SISTEMA DE EXTRACCIÓN</h2>
            <div class="ad-box">ANUNCIO ADSENSE</div>
            <form action="/procesar" method="post" enctype="multipart/form-data" onsubmit="event.preventDefault(); iniciarEspera();">
                <input type="file" name="file" accept=".pdf" required>
                <input type="text" name="pages" placeholder="Páginas (ej: 1,3-5)" required>
                <select name="format">
                    <option value="single_pdf">Bloque Único (PDF)</option>
                    <option value="zip_pdf">Individuales (ZIP)</option>
                </select>
                <button type="submit" class="btn">EJECUTAR PROCESAMIENTO</button>
            </form>
            <div class="ad-box">ANUNCIO ADSENSE</div>
        </div>
        <div id="waiting">
            <h2 style="color:var(--neon);">PROCESANDO...</h2>
            <p>Prepare su descarga viendo los anuncios.</p>
            <div style="font-size:3rem; margin:20px 0;" id="timer">15</div>
            <div class="ad-box" style="min-height:250px;">ANUNCIO PREMIUM</div>
        </div>
        """
    return HTML_TEMPLATE.format(adsense_script=ADSENSE_SCRIPT, content=content)

@app.post("/procesar")
async def procesar(response: Response, file: UploadFile = File(...), pages: str = Form(...), format: str = Form(...), uses: str = Cookie(None)):
    current_uses = int(uses) if uses else 0
    content = await file.read()
    doc = fitz.open(stream=content, filetype="pdf")
    
    indices = []
    for p in re.split(r'[,\s]+', pages):
        if '-' in p:
            start, end = map(int, p.split('-'))
            indices.extend(range(start, end + 1))
        else: indices.append(int(p))
    
    output = io.BytesIO()
    if format == "single_pdf":
        res_pdf = fitz.open()
        for i in indices:
            if 0 < i <= len(doc): res_pdf.insert_pdf(doc, from_page=i-1, to_page=i-1)
        res_pdf.save(output)
        res_pdf.close()
        mimetype, filename = "application/pdf", "SDE_EXTRACCION.pdf"
    else:
        with zipfile.ZipFile(output, "a") as zf:
            for i in indices:
                if 0 < i <= len(doc):
                    tmp = fitz.open()
                    tmp.insert_pdf(doc, from_page=i-1, to_page=i-1)
                    zf.writestr(f"hoja_{i}.pdf", tmp.write())
                    tmp.close()
        mimetype, filename = "application/zip", "SDE_CARPETA.zip"

    doc.close()
    output.seek(0)
    
    response = StreamingResponse(output, media_type=mimetype, headers={"Content-Disposition": f"attachment; filename={filename}"})
    response.set_cookie(key="uses", value=str(current_uses + 1), max_age=86400)
    return response
