from datetime import datetime
import io
import zipfile
import re
from fastapi import FastAPI, UploadFile, File, Form, Response, Cookie
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz 

app = FastAPI()

# --- CONFIGURACIÓN DE MONETIZACIÓN ---
ADSENSE_SCRIPT = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3283369890047945" crossorigin="anonymous"></script>'
ALIAS_PAGO = "Proyectos863"

def generar_codigo_seguro():
    # Fórmula pactada: Día del mes * 863
    # Ejemplo: Si hoy es día 7, el código es 6041
    return str(datetime.now().day * 863)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>SDE - TERMINAL DIGITAL</title>
    {adsense_script}
    <style>
        :root {{ --neon: #00f2ff; --bg: #0a0a0b; }}
        body {{ font-family: 'Courier New', monospace; background: var(--bg); color: white; text-align: center; padding: 20px; }}
        .card {{ background: #141417; padding: 30px; border-radius: 12px; border: 1px solid #2d2d31; max-width: 480px; margin: auto; box-shadow: 0 0 20px rgba(0,0,0,0.5); }}
        .ad-box {{ background: #000; border: 1px dashed #444; margin: 15px 0; min-height: 100px; display: flex; align-items: center; justify-content: center; color: #555; font-size: 0.7rem; }}
        .btn {{ width: 100%; padding: 15px; background: transparent; color: var(--neon); border: 1px solid var(--neon); cursor: pointer; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; }}
        .btn:hover {{ background: var(--neon); color: black; box-shadow: 0 0 20px var(--neon); }}
        input, select {{ width: 100%; padding: 12px; margin-bottom: 15px; background: #000; border: 1px solid #333; color: var(--neon); border-radius: 4px; box-sizing: border-box; }}
        #waiting {{ display: none; }}
        .pay-card {{ border: 1px solid #ffcc00; color: #ffcc00; padding: 20px; margin-top: 15px; border-radius: 8px; background: rgba(255,204,0,0.05); }}
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
    
    # Si current_uses es -1, significa que el pago de 6hs está activo
    if current_uses >= 2:
        content = f"""
        <h2 style="color:red;">LÍMITE EXCEDIDO</h2>
        <p>Has agotado tus 2 extracciones gratuitas diarias.</p>
        <div class="pay-card">
            <h3 style="margin-top:0;">PASE RÁPIDO (6 HORAS)</h3>
            <p style="font-size:1.2rem;">Precio: <strong>$500 ARS</strong></p>
            <p>Alias Personal Pay:<br><span style="background:#333; padding:5px; color:white;">{ALIAS_PAGO}</span></p>
            <p style="font-size:0.8rem;">Envía el comprobante para recibir tu código.</p>
            <hr style="border:0.5px solid #444; margin:15px 0;">
            <form action="/desbloquear" method="post">
                <input type="text" name="codigo" placeholder="Ingresar código de 4 dígitos" required>
                <button type="submit" class="btn">ACTIVAR PASE</button>
            </form>
        </div>
        """
    else:
        content = """
        <div id="main-ui">
            <h2>EXTRACCIÓN PROFESIONAL</h2>
            <div class="ad-box">ANUNCIO ADSENSE</div>
            <form action="/procesar" method="post" enctype="multipart/form-data" onsubmit="event.preventDefault(); iniciarEspera();">
                <input type="file" name="file" accept=".pdf" required>
                <input type="text" name="pages" placeholder="Páginas (ej: 1, 3-6)" required>
                <select name="format">
                    <option value="single_pdf">Documento Único (PDF)</option>
                    <option value="zip_pdf">Archivos Separados (ZIP)</option>
                </select>
                <button type="submit" class="btn">INICIAR PROCESO</button>
            </form>
            <div class="ad-box">ANUNCIO ADSENSE</div>
        </div>
        <div id="waiting">
            <h2 style="color:var(--neon);">PREPARANDO DESCARGA</h2>
            <p>Por favor, aguarde mientras se procesan los anuncios.</p>
            <div style="font-size:3rem; margin:20px 0;" id="timer">15</div>
            <div class="ad-box" style="min-height:250px;">ANUNCIO PREMIUM</div>
        </div>
        """
    return HTML_TEMPLATE.format(adsense_script=ADSENSE_SCRIPT, content=content)

@app.post("/desbloquear")
async def desbloquear(response: Response, codigo: str = Form(...)):
    if codigo == generar_codigo_seguro():
        # Seteamos el valor a -1 para que no aplique el bloqueo de >= 2
        # max_age = 21600 segundos (6 horas exactas)
        response = HTMLResponse(content="<script>alert('¡Pase de 6 horas activado!'); window.location.href='/';</script>")
        response.set_cookie(key="uses", value="-1", max_age=21600)
        return response
    return HTMLResponse(content="<script>alert('Código inválido o vencido'); window.location.href='/';</script>")

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
    
    # Solo incrementamos el contador si NO está en modo "Pase de 6hs" (-1)
    if current_uses != -1:
        response.set_cookie(key="uses", value=str(current_uses + 1), max_age=86400)
    return response
