# -*- coding: utf-8 -*-
"""
run_demo_html.py -- Genera demo HTML portable del agente SGM en grid 2D.
Corre un trial del GridAgent (reusa run_grid_dolor.py), recolecta frames por tick,
y escribe demo_grid.html con TODOS los frames embebidos en JS (sin server, sin CORS).
El HTML tiene canvas + indicadores en tiempo real (tick#, pos, dist meta, valencia E,
dolor, masa PPR, huella) + controles play/pause/slider/velocidad.

Uso: python run_demo_html.py  ->  abrir phases/phase7_composicion/demo_grid.html
"""
import json, os, sys, random, math
sys.path.insert(0, os.path.dirname(__file__))
import run_grid_dolor as G   # reusa GridAgent, build_map, etc.
import run_grid_agent as G2  # reusa el agente de maze aleatorio (0032)

SEED_DEMO = 7
D, W, Ht = G.D, G.W, G.Ht

def snapshot(ag, meta, visitas):
    h = ag.history[-1] if ag.history else {"tick":0,"pos":ag.pos,"dist":G.manhattan(ag.pos,meta),
                                           "E":0.0,"dolor":0.0,"masa":0.0,"huella":0,"reached":False}
    r,c = h["pos"]
    visitas[(r,c)] = visitas.get((r,c),0)+1
    return {
        "tick": h["tick"], "pos": list(h["pos"]), "dist": h["dist"],
        "E": h["E"], "dolor": h["dolor"], "masa": h["masa"], "huella": h["huella"],
        "reached": h["reached"]
    }

def run_scenario_0033():
    """Grid abierto con zona de dolor (demo principal)."""
    rng = random.Random(SEED_DEMO)
    walls, body, meta, dolor_cells = G.build_map()
    ag = G.GridAgent(rng, walls, body, meta, dolor_cells, use_dolor=True, mode="afinidad")
    visitas = {}
    frames = [snapshot(ag, meta, visitas)]
    while ag.tick < G.MAX_TICKS:
        if ag.step(): pass
        frames.append(snapshot(ag, meta, visitas))
        if frames[-1]["reached"]: break
    layout = []
    for r in range(Ht):
        row = []
        for c in range(W):
            if (r,c) in walls: row.append("W")
            elif (r,c) in dolor_cells: row.append("D")
            elif (r,c) == meta: row.append("G")
            elif (r,c) == body: row.append("B")
            else: row.append(".")
        layout.append(row)
    return layout, frames, meta, body, sorted(dolor_cells), visitas

def run_scenario_0032():
    """Maze aleatorio 10x10 (demo laberinto)."""
    rng = random.Random(SEED_DEMO)
    walls, body, meta, dolor_cell = G2.make_scenario(rng)
    ag = G2.GridAgent(rng, walls, body, meta, dolor_cell, use_dolor=True, mode="afinidad")
    visitas = {}
    frames = [snapshot(ag, meta, visitas)]
    while ag.tick < G2.MAX_TICKS:
        ag.step()
        frames.append(snapshot(ag, meta, visitas))
        if frames[-1]["reached"]: break
    layout = []
    for r in range(G2.Ht):
        row = []
        for c in range(G2.W):
            if (r,c) in walls: row.append("W")
            elif dolor_cell and (r,c) == dolor_cell: row.append("D")
            elif (r,c) == meta: row.append("G")
            elif (r,c) == body: row.append("B")
            else: row.append(".")
        layout.append(row)
    return layout, frames, meta, body, ([dolor_cell] if dolor_cell else []), visitas

def write_html(layout, frames, meta, body, dolor, visitas, out_path, title):
    data = {
        "W": len(layout[0]), "Ht": len(layout), "layout": layout,
        "frames": frames, "meta": list(meta), "body": list(body),
        "dolor": [list(d) for d in dolor],
        "visitas": {f"{r},{c}": v for (r,c),v in visitas.items()},
        "seed": SEED_DEMO
    }
    html = HTML_TEMPLATE.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    html = html.replace("SGM Grid Agent (Camino A) - demo en vivo", title)
    open(out_path, "w", encoding="utf-8").write(html)
    print("HTML:", out_path, "| frames:", len(frames), "| llegada:", frames[-1]["reached"])

def main():
    d = os.path.dirname(__file__)
    l1,f1,m1,b1,dz1,v1 = run_scenario_0033()
    write_html(l1,f1,m1,b1,dz1,v1, os.path.join(d,"demo_grid.html"),
               "SGM Grid Agent (0033 - dolor) - demo en vivo")
    l2,f2,m2,b2,dz2,v2 = run_scenario_0032()
    write_html(l2,f2,m2,b2,dz2,v2, os.path.join(d,"demo_grid_maze.html"),
               "SGM Grid Agent (0032 - maze aleatorio) - demo en vivo")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SGM Grid Agent - Demo</title>
<style>
  body{background:#0d1117;color:#e6edf3;font-family:monospace;margin:0;padding:16px;}
  h2{margin:0 0 8px;font-size:18px;color:#58a6ff;}
  #wrap{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start;}
  canvas{background:#161b22;border:1px solid #30363d;border-radius:6px;}
  #panel{font-size:13px;line-height:1.7;min-width:240px;}
  #panel b{color:#58a6ff;}
  .ctrl{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
  button{background:#21262d;color:#e6edf3;border:1px solid #30363d;border-radius:5px;padding:6px 12px;cursor:pointer;font-family:monospace;}
  button:hover{background:#30363d;}
  input[type=range]{width:200px;}
  .k{display:inline-block;width:90px;color:#8b949e;}
  .v{display:inline-block;min-width:60px;font-weight:bold;}
</style>
</head>
<body>
<h2>SGM Grid Agent (Camino A) - demo en vivo</h2>
<div id="wrap">
  <div>
    <canvas id="cv" width="480" height="480"></canvas>
    <div class="ctrl">
      <button id="play">Play</button>
      <button id="pause">Pause</button>
      <span class="k">tick</span><input type="range" id="slider" min="0" max="0" value="0">
      <span class="k">vel</span><input type="range" id="speed" min="1" max="20" value="6">
    </div>
  </div>
  <div id="panel">
    <div><span class="k">tick</span><span class="v" id="i_tick">0</span></div>
    <div><span class="k">pos cuerpo</span><span class="v" id="i_pos">-</span></div>
    <div><span class="k">dist meta</span><span class="v" id="i_dist">-</span></div>
    <div><span class="k">valencia E</span><span class="v" id="i_E">-</span></div>
    <div><span class="k">dolor tick</span><span class="v" id="i_dolor">-</span></div>
    <div><span class="k">masa PPR</span><span class="v" id="i_masa">-</span></div>
    <div><span class="k">huella</span><span class="v" id="i_huella">-</span></div>
    <div><span class="k">llegada</span><span class="v" id="i_reached">-</span></div>
    <hr style="border-color:#30363d">
    <div style="color:#8b949e;font-size:11px;">
      B=inicio G=meta D=dolor W=pared<br>
      amarillo tenue = huella (veces pisada)<br>
      azul = cuerpo
    </div>
  </div>
</div>
<script>
const DATA = /*__DATA__*/;
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const cell = cv.width / DATA.W;
const slider = document.getElementById('slider');
slider.max = DATA.frames.length - 1;
let idx = 0, playing = false, timer = null;

function draw(i){
  const f = DATA.frames[i];
  const layout = DATA.layout;
  ctx.clearRect(0,0,cv.width,cv.height);
  for(let r=0;r<DATA.Ht;r++){
    for(let c=0;c<DATA.W;c++){
      const x=c*cell, y=r*cell;
      const ch = layout[r][c];
      if(ch==='W'){ ctx.fillStyle='#30363d'; }
      else if(ch==='D'){ ctx.fillStyle='#7d1f1f'; }
      else if(ch==='G'){ ctx.fillStyle='#1f5f2f'; }
      else if(ch==='B'){ ctx.fillStyle='#1f3a5f'; }
      else { ctx.fillStyle='#0d1117'; }
      ctx.fillRect(x,y,cell-1,cell-1);
      // huella
      const vk = r+','+c;
      if(DATA.visitas[vk]){
        const a = Math.min(0.5, DATA.visitas[vk]*0.08);
        ctx.fillStyle = 'rgba(240,200,60,'+a+')';
        ctx.fillRect(x,y,cell-1,cell-1);
      }
    }
  }
  // cuerpo
  const [pr,pc] = f.pos;
  ctx.fillStyle = '#58a6ff';
  ctx.beginPath();
  ctx.arc(pc*cell+cell/2, pr*cell+cell/2, cell*0.35, 0, 2*Math.PI);
  ctx.fill();
  // indicadores
  document.getElementById('i_tick').textContent = f.tick;
  document.getElementById('i_pos').textContent = '('+pr+','+pc+')';
  document.getElementById('i_dist').textContent = f.dist;
  document.getElementById('i_E').textContent = f.E;
  document.getElementById('i_dolor').textContent = f.dolor>0?'SI':'no';
  document.getElementById('i_masa').textContent = f.masa;
  document.getElementById('i_huella').textContent = f.huella;
  document.getElementById('i_reached').textContent = f.reached?'SI':'no';
  slider.value = i;
}

function tickStep(){
  if(idx >= DATA.frames.length-1){ playing=false; clearInterval(timer); return; }
  idx++; draw(idx);
}
document.getElementById('play').onclick = ()=>{
  if(playing) return; playing=true;
  const sp = parseInt(document.getElementById('speed').value);
  timer = setInterval(tickStep, 1000/sp);
};
document.getElementById('pause').onclick = ()=>{ playing=false; clearInterval(timer); };
slider.oninput = (e)=>{ idx=parseInt(e.target.value); draw(idx); };
draw(0);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
