#!/usr/bin/env python3
"""PMI Test Dashboard — живая визуализация хода испытаний.
Обновляется скриптами runbook через JSON-файл статуса."""

import http.server
import json
import os
import time
from pathlib import Path

STATUS_FILE = "/opt/aiops-aither/pmi/test-status.json"
PORT = 8085

HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="5">
<title>ПМИ — Ход испытаний</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #c9d1d9; font: 14px/1.6 "Segoe UI", sans-serif; padding: 20px; }
h1 { color: #58a6ff; margin-bottom: 10px; }
.status-bar { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
.stat { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 18px; text-align: center; min-width: 100px; }
.stat .val { font-size: 28px; font-weight: bold; }
.stat .lbl { font-size: 11px; color: #8b949e; margin-top: 4px; }
.stat.ok .val { color: #3fb950; }
.stat.fail .val { color: #f85149; }
.stat.run .val { color: #d29922; }
.cat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; margin-bottom: 20px; }
.cat { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; }
.cat h3 { font-size: 13px; margin-bottom: 8px; }
.cat .bar { height: 6px; background: #21262d; border-radius: 3px; margin-bottom: 4px; }
.cat .bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.cat .bar-fill.ok { background: #3fb950; }
.cat .bar-fill.fail { background: #f85149; }
.cat .bar-fill.run { background: #d29922; }
.cat .info { font-size: 11px; color: #8b949e; }
.current { background: #161b22; border: 1px solid #d29922; border-radius: 8px; padding: 14px; margin-bottom: 20px; }
.current h2 { font-size: 14px; color: #d29922; margin-bottom: 6px; }
.current pre { font-size: 12px; color: #8b949e; margin: 0; }
.phase { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px; }
.phase.inject { background: #f8514933; color: #f85149; }
.phase.detect { background: #d2992233; color: #d29922; }
.phase.recover { background: #3fb95033; color: #3fb950; }
.phase.idle { background: #30363d; color: #8b949e; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #21262d; font-size: 12px; }
th { color: #8b949e; }
td.ok { color: #3fb950; }
td.fail { color: #f85149; }
td.run { color: #d29922; }
</style>
</head>
<body>
<h1>🧪 ПМИ: Программа и методика испытаний</h1>
<div class="status-bar">
    <div class="stat ok"><div class="val" id="total-ok">0</div><div class="lbl">✅ Пройдено</div></div>
    <div class="stat fail"><div class="val" id="total-fail">0</div><div class="lbl">❌ Провалено</div></div>
    <div class="stat run"><div class="val" id="total-run">0</div><div class="lbl">🔄 В процессе</div></div>
    <div class="stat"><div class="val" id="total-left">0</div><div class="lbl">⏳ Осталось</div></div>
    <div class="stat"><div class="val" id="total-ml">0/7</div><div class="lbl">📊 ML-методов</div></div>
</div>
<div id="current"></div>
<div class="cat-grid" id="categories"></div>
<h3 style="margin:15px 0 10px">📋 Последние события</h3>
<table id="events"><tr><th>Время</th><th>Категория</th><th>Тест</th><th>Результат</th><th>ML</th><th>Время</th></tr></table>
<script>
const OK={ok:1,fail:1,run:1};
async function load(){try{const r=await fetch('/status.json');const d=await r.json();update(d)}catch(e){console.error(e)}}
function update(d){
    let ok=0,fail=0,run=0,total=0;
    let cats={};
    (d.categories||[]).forEach(c=>{
        ok+=c.ok||0;fail+=c.fail||0;run+=c.run||0;total+=c.total||0;
        cats[c.id]=c;
    });
    document.getElementById('total-ok').textContent=ok;
    document.getElementById('total-fail').textContent=fail;
    document.getElementById('total-run').textContent=run;
    document.getElementById('total-left').textContent=total-ok-fail-run;
    document.getElementById('total-ml').textContent=(d.ml_methods||[]).filter(m=>m.covered).length+'/7';

    let cur=d.current_test;
    let curHTML=cur?`<div class="current"><h2>⚡ Текущий тест: ${cur.id} — ${cur.name}<span class="phase ${cur.phase}">${cur.phase||'idle'}</span></h2><pre>${cur.step||'Ожидание...'}</pre></div>`:'';
    document.getElementById('current').innerHTML=curHTML;

    let catHTML='';
    Object.values(cats).forEach(c=>{
        let pct=Math.round((c.ok+0.5*c.run)/Math.max(1,c.total)*100);
        let cls=pct===100?'ok':c.run>0?'run':c.fail>0?'fail':'';
        catHTML+=`<div class="cat"><h3>${c.name}</h3><div class="bar"><div class="bar-fill ${cls}" style="width:${pct}%"></div></div><div class="info">${c.ok+c.run}/${c.total} • ${pct}%</div></div>`;
    });
    document.getElementById('categories').innerHTML=catHTML;

    let evHTML='';
    (d.recent_events||[]).slice(-20).reverse().forEach(e=>{
        let cls=e.status==='ok'?'ok':e.status==='fail'?'fail':'run';
        evHTML+=`<tr><td>${e.time}</td><td>${e.category}</td><td>${e.test_id}</td><td class="${cls}">${e.status}</td><td>${(e.ml||[]).join(', ')||'-'}</td><td>${e.duration||'-'}</td></tr>`;
    });
    document.getElementById('events').innerHTML=evHTML+(evHTML?'':'<tr><td colspan="6">Нет событий</td></tr>');
}
load();setInterval(load,5000);
</script>
</body>
</html>"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status.json':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            try:
                with open(STATUS_FILE) as f:
                    self.wfile.write(f.read().encode())
            except FileNotFoundError:
                self.wfile.write(json.dumps({"categories":[],"recent_events":[],"ml_methods":[]}).encode())
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML.encode())

if __name__ == '__main__':
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    print(f"PMI Dashboard → :{PORT}")
    http.server.HTTPServer(('0.0.0.0', PORT), DashboardHandler).serve_forever()
