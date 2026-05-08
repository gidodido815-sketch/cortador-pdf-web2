import io
import zipfile
import gc
import re
from fastapi import FastAPI, UploadFile, File, Form, Response, Cookie
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz  # PyMuPDF
from datetime import datetime, timedelta

app = FastAPI()

# --- CONFIGURACIÓN ---
ADSENSE_ID = "ca-pub-XXXXXXXXXXXX" # Tu ID de AdSense verificado
ALIAS_PAGO = "tu.billetera.sde" # Tu alias para recibir pagos

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>TERMINAL SDE - PROCESAMIENTO</title>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ads_id}" crossorigin="anonymous"></script>
    <style>
        :root {{ --neon: #00f2ff; --bg: #0a0a0b; }}
        body {{ font-family: 'Courier New', monospace; background: var(--bg); color: white; text-align: center; padding: 20px; }}
        .card {{ background: #141417; padding: 30px; border-radius: 12px; border: 1px solid #2d2d31; max-width: 480px; margin: auto; }}
        .ad-box {{ background: #000; border: 1px dashed #444; margin: 15px 0; min-height: 100px; display: flex; align-items: center; justify-content: center; color: #555; font-size: 0.7rem; }}
        .btn {{ width: 100%; padding: 15px; background: transparent; color: var(--neon); border: 1px solid var(--neon); cursor: pointer; font-weight: bold; }}
        .btn:hover {{ background: var(--neon); color: black; box-shadow: 0 0 20px var(--neon); }}
        #waiting {{ display: none; }}
        .pay-info {{ color: #ffcc00; border: 1px solid #ffcc00; padding: 15px; margin-top: 20px; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <div class="card">
        <img src="https://raw.githubusercontent.com/gidodido815-sketch/cortador-pdf-web2/main/WhatsApp%20Image%202026-05-07%20at%2020.20.39.jpeg" width="90" style="border-radius:50%; border:2px solid var(--neon); margin-bottom:10px;">
        
        {content}
        
    </div>
    <p style="font-size:0.6rem; color:#444; margin-top:20px;">SANTIAGO DEL ESTERO | SISTEMA MONETIZADO</p>
</body>
</html>
"""

FORM_HTML = """
<div id="ui">
    <h2>SISTEMA DE EXTRACCIÓN</h2>
    <div class="ad-box">ANUNCIO ADSENSE (BANNER)</div>
    <form action="/procesar" method="post" enctype="multipart/form-data" onsubmit="iniciar();">
        <input type="file" name="file" accept=".pdf" required style="width:100%; margin-bottom:10px; background:#000; color:white; padding:10px; border:1px solid #333;">
        <input type="text" name="pages" placeholder="Páginas: 1,4,8" required style="width:100%; margin-bottom:10px; background:#000; color:var(--neon); padding:10px; border:1px solid #333;">
        <select name="format" style="width:100%; margin-bottom:20px; background:#000; color:var(--neon); padding:10px; border:1px solid #333;">
            <option value="single_pdf">Bloque Único (PDF)</option>
            <option value="zip_pdf">Carpeta (ZIP)</option>
        </select>
        <button type="submit" class="btn">EJECUTAR Y VER ANUNCIOS</button>
    </form>
    <div class="ad-box">ANUNCIO ADSENSE (BANNER)</div>
</div>

<div id="waiting">
    <h2 style="color:var(--neon);">PREPARANDO DESCARGA...</h2>
    <p>Por favor, observe la publicidad mientras procesamos. <br>Tiempo restante: <span id="timer">15</span>s</p>
    <div class="ad-box" style="min-height:250px;">ANUNCIO PREMIUM (VIDEO/NATIVO)</div>
</div>

<script>
    function iniciar() {{
        // Abrir publicidad en otra pestaña
        window.open('https://www.google.com', '_blank');
        document.getElementById('ui').style.display = 'none';
        document.getElementById('waiting').style.display = 'block';
        let s = 15;
        const t = setInterval(() => {{
            s--;
            document.getElementById('timer').innerText = s;
            if(s <= 0) {{ clearInterval(t); document.forms[0].submit(); setTimeout(() => location.reload(), 2000); }}
        }}, 1000);
    }}
</script>
"""

LIMIT_HTML = f"""
<h2 style="color:red;">LÍMITE DIARIO ALCANZADO</h2>
<p>Has agotado tus 2 usos gratuitos de hoy.</p>
<div class="pay-info">
    <strong>PARA ACCESO ILIMITADO:</strong><br>
    Envía el pago a nuestro ALIAS:<br>
    <span style="font-size:1.2rem; letter-spacing:1px;">{ALIAS_PAGO}</span><br>
    Luego envía el comprobante.
</div>
<p style="font-size:0.7rem; color:#888; margin-top:15px;">O vuelve mañana para otros 2 usos con publicidad.</p>
"""

@app.get("/", response_class=HTMLResponse)
async def home(uses: str = Cookie(None)):
    current_uses = int(uses) if uses else 0
    content = FORM_HTML if current_uses < 2 else LIMIT_HTML
    return HTML_TEMPLATE.format(ads_id=ADSENSE_ID, content=content)

@app.post("/procesar")
async def procesar(response: Response, file: UploadFile = File(...), pages: str = Form(...), format: str = Form(...), uses: str = Cookie(None)):
    # Incrementar contador en la Cookie (expira en 24hs)
    current_uses = int(uses) if uses else 0
    new_uses = current_uses + 1
    
    # Procesamiento real del PDF
    content = await file.read()
    doc = fitz.open(stream=content, filetype="pdf")
    
    # Lógica de páginas (simplificada para el bloque)
    indices = []
    for p in re.split(r'[,\s]+', pages):
        if '-' in p:
            s, e = map(int, p.split('-'))
            indices.extend(range(s, e + 1))
        else: indices.append(int(p))
    
    output = io.BytesIO()
    if format == "single_pdf":
        res = fitz.open()
        for idx in indices:
            if 0 < idx <= len(doc): res.insert_pdf(doc, from_page=idx-1, to_page=idx-1)
        res.save(output)
        res.close()
        mimetype, filename = "application/pdf", "SDE_PROCESADO.pdf"
    else:
        with zipfile.ZipFile(output, "a") as zf:
            for idx in indices:
                if 0 < idx <= len(doc):
                    tmp = fitz.open()
                    tmp.insert_pdf(doc, from_page=idx-1, to_page=idx-1)
                    zf.writestr(f"hoja_{idx}.pdf", tmp.write())
                    tmp.close()
        mimetype, filename = "application/zip", "SDE_CARPETA.zip"

    doc.close()
    output.seek(0)
    
    # Guardar el uso en la cookie del navegador del usuario
    response = StreamingResponse(output, media_type=mimetype, headers={{"Content-Disposition": f"attachment; filename={{filename}}"}} )
    response.set_cookie(key="uses", value=str(new_uses), max_age=86400) # 86400 seg = 24 horas
    return response
