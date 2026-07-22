from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.advisor.engine import advise
from app.repository import load_plants

app = FastAPI(title="PflanzenKI MVP", version="0.1.0")


class AskRequest(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang="de">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>PflanzenKI MVP</title>
<style>
body{font-family:system-ui;max-width:760px;margin:3rem auto;padding:0 1rem}
textarea{width:100%;min-height:90px;padding:.8rem}button{margin-top:.7rem;padding:.7rem 1rem}
pre{white-space:pre-wrap;background:#f4f4f4;padding:1rem}
</style></head>
<body>
<h1>PflanzenKI MVP v0.1</h1>
<p>Beispiel: Welche Tomaten eignen sich draußen ohne Dach?</p>
<textarea id="q">Welche Tomaten eignen sich draußen ohne Dach?</textarea><br>
<button onclick="ask()">Fragen</button>
<pre id="out"></pre>
<script>
async function ask(){
 const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({question:document.getElementById('q').value})});
 const d=await r.json();
 document.getElementById('out').textContent=d.answer+"\n\n"+JSON.stringify(d,null,2);
}
</script></body></html>"""


@app.post("/api/ask")
def ask(payload: AskRequest):
    return advise(load_plants(), payload.question)
