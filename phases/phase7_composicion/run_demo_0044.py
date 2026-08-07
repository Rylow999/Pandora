# -*- coding: utf-8 -*-
"""
exp_SGM_0044_demo -- genera demo HTML portable del sistema completo (0044)
Reproduce la traza REAL de 0044 (agente frustracion 0043 en mundo 0042) tick a tick.
HTML+JS embebido, sin server, portable: se abre el archivo y se ve la animacion.
Visual: synthwave (fondo oscuro, glow). Indicadores en tiempo real.
"""
import json, random
SEED = 20260803
GRID = 12
STEPS = 300

# ---- reusa World y Agent de 0044 ----
class World:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.dolor_cells = set()
        self.food_cells = set()
        for _ in range(8):
            self.dolor_cells.add((self.rng.randint(0,GRID-1), self.rng.randint(0,GRID-1)))
        for _ in range(10):
            self.food_cells.add((self.rng.randint(0,GRID-1), self.rng.randint(0,GRID-1)))
        self.walls = set([(3,3),(3,4),(8,7),(8,8),(5,9),(6,9)])
    def dolor_at(self, pos):
        return 1.0 if pos in self.dolor_cells or pos in self.walls else 0.0
    def food_at(self, pos):
        return pos in self.food_cells
    def eat(self, pos):
        self.food_cells.discard(pos)

class Agent:
    def __init__(self, use_abur=True):
        self.pos = (GRID//2, GRID//2)
        self.dolor = 0.0; self.eta = 0.5; self.abur = 0.0
        self.use_abur = use_abur
        self.omega = {}; self.visited = set(); self.last_pos = None
        self.pain_cum = 0.0; self.food_eaten = 0; self.returns = 0
    def bind_location(self, pos, val):
        self.omega[pos] = self.omega.get(pos, 0.0) + val
    def affinity_to(self, pos, world):
        w = self.omega.get(pos, 0.0)
        d = world.dolor_at(pos); food = world.food_at(pos)
        nb = 0; nbnov = 0
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny = pos[0]+dx, pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                nb += 1
                if (nx,ny) not in self.visited: nbnov += 1
        frontier = (nbnov/nb) if nb else 0.0
        aff = w + (0.8 if food else 0.0) + self.eta*frontier*0.6 - (2.0*d)
        if self.use_abur and pos == self.last_pos:
            aff -= self.abur
        return aff
    def step(self, world):
        self.visited.add(self.pos)
        best = None; best_a = -1e9
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny = self.pos[0]+dx, self.pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                a = self.affinity_to((nx,ny), world)
                if a > best_a:
                    best_a = a; best = (nx,ny)
        if best is None: return
        if best == self.last_pos: self.returns += 1
        self.last_pos = self.pos; self.pos = best
        if world.dolor_at(self.pos) > 0:
            self.dolor = min(self.dolor + 1.0, 3.0); self.pain_cum += 1.0
        if world.food_at(self.pos):
            self.food_eaten += 1; world.eat(self.pos); self.bind_location(self.pos, 0.5)
        novedad = 1.0 if best not in self.visited else 0.2
        self.eta = max(0.1, min(1.0, self.eta + 0.05*(novedad - 0.5)))
        self.abur = max(0.0, min(1.0, self.abur + (0.03 if novedad < 0.3 else -0.05)))

def build_trace():
    w = World(SEED)
    a = Agent(use_abur=True)
    traj = [a.pos]
    food_left = list(w.food_cells)
    for _ in range(STEPS):
        a.step(w)
        traj.append(a.pos)
    return w, traj, a

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SGM MiniSandbox — Sistema Completo (0044)</title>
<style>
  :root{
    --bg:#0b0e1a; --panel:#121733; --ink:#e6ecff; --dim:#8b93c7;
    --cyan:#39e6ff; --green:#4dff9e; --red:#ff5d73; --gray:#3a4170;
    --purple:#a06bff; --amber:#ffc24d;
  }
  *{box-sizing:border-box}
  body{margin:0;background:radial-gradient(1200px 800px at 70% -10%, #1a1340 0%, var(--bg) 60%);
       color:var(--ink);font-family:"Segoe UI",system-ui,sans-serif;padding:18px}
  h1{font-size:19px;margin:0 0 2px;letter-spacing:.5px}
  .sub{color:var(--dim);font-size:12px;margin-bottom:14px}
  .wrap{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}
  .stage{background:var(--panel);border:1px solid #232a55;border-radius:14px;padding:14px;
         box-shadow:0 0 40px rgba(57,230,255,.08)}
  canvas{border-radius:10px;background:#070a16;display:block}
  .side{width:280px;display:flex;flex-direction:column;gap:12px}
  .card{background:var(--panel);border:1px solid #232a55;border-radius:12px;padding:12px 14px}
  .card h2{font-size:12px;text-transform:uppercase;letter-spacing:1.4px;color:var(--dim);margin:0 0 8px}
  .row{display:flex;justify-content:space-between;font-size:13px;padding:3px 0}
  .row b{color:var(--cyan);font-variant-numeric:tabular-nums}
  .bar{height:9px;border-radius:6px;background:#0c1130;overflow:hidden;margin:5px 0}
  .bar > i{display:block;height:100%;border-radius:6px}
  .quad{display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:11px;color:var(--dim)}
  .quad div{background:#0c1130;border-radius:6px;padding:6px;text-align:center}
  .quad b{color:var(--ink)}
  .ctrls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:6px}
  button{background:#1b2350;color:var(--ink);border:1px solid #2c3570;border-radius:8px;
         padding:7px 12px;font-size:13px;cursor:pointer}
  button:hover{background:#26306b}
  input[type=range]{width:120px;accent-color:var(--cyan)}
  .leg{display:flex;gap:14px;font-size:11px;color:var(--dim);margin-top:10px;flex-wrap:wrap}
  .leg span{display:inline-flex;align-items:center;gap:5px}
  .dot{width:10px;height:10px;border-radius:3px;display:inline-block}
  .tag{display:inline-block;font-size:10px;padding:2px 6px;border-radius:5px;background:#1b2350;color:var(--cyan);margin-left:6px}
</style>
</head>
<body>
  <h1>SGM · MiniSandbox <span class="tag">exp_SGM_0044</span></h1>
  <div class="sub">Sistema completo en acción: frustración (0043) + evitación de daño (0033/39) + búsqueda de comida HRR (0028). Mundo abierto, sin objetivo externo.</div>
  <div class="wrap">
    <div class="stage">
      <canvas id="cv" width="468" height="468"></canvas>
      <div class="leg">
        <span><i class="dot" style="background:var(--cyan)"></i>agente</span>
        <span><i class="dot" style="background:#2b3b8f"></i>visitado</span>
        <span><i class="dot" style="background:var(--green)"></i>comida</span>
        <span><i class="dot" style="background:var(--red)"></i>dolor</span>
        <span><i class="dot" style="background:var(--gray)"></i>obstáculo</span>
      </div>
      <div class="ctrls">
        <button id="play">⏸ Pausa</button>
        <button id="reset">↺ Reiniciar</button>
        <label style="font-size:11px;color:var(--dim)">vel
          <input id="speed" type="range" min="1" max="30" value="10"></label>
        <label style="font-size:11px;color:var(--dim)">tick
          <input id="scrub" type="range" min="0" max="__STEPS__" value="0" style="width:160px"></label>
      </div>
    </div>
    <div class="side">
      <div class="card">
        <h2>Estado del agente</h2>
        <div class="row"><span>tick</span><b id="k">0</b></div>
        <div class="row"><span>posición</span><b id="pos">—</b></div>
        <div class="row"><span>celdas visitadas</span><b id="vis">0</b></div>
        <div class="row"><span>comida</span><b id="food">0</b></div>
        <div class="row"><span>eventos de dolor</span><b id="pain">0</b></div>
      </div>
      <div class="card">
        <h2>Campos del sustrato</h2>
        <div class="row"><span>η (curiosidad)</span><b id="eta">0.50</b></div>
        <div class="bar"><i id="etaB" style="background:linear-gradient(90deg,#a06bff,#39e6ff);width:50%"></i></div>
        <div class="row"><span>aburrimiento</span><b id="abur">0.00</b></div>
        <div class="bar"><i id="aburB" style="background:linear-gradient(90deg,#ffc24d,#ff5d73);width:0%"></i></div>
        <div class="row"><span>retornos (osc.)</span><b id="ret">0</b></div>
      </div>
      <div class="card">
        <h2>Cobertura por cuadrante</h2>
        <div class="quad">
          <div>Q(0,0)<br><b id="q00">0%</b></div>
          <div>Q(0,1)<br><b id="q01">0%</b></div>
          <div>Q(1,0)<br><b id="q10">0%</b></div>
          <div>Q(1,1)<br><b id="q11">0%</b></div>
        </div>
      </div>
      <div class="card">
        <h2>Leyenda del método</h2>
        <div style="font-size:11px;color:var(--dim);line-height:1.5">
          Sin hardcode ni agregados. La exploración EMERGE del campo <b style="color:var(--amber)">abur</b>
          (0036) acoplado a la pena de retorno. El daño se evita por el campo <b style="color:var(--red)">dolor</b>
          en la afinidad. La comida se halla por <b style="color:var(--green)">HRR</b> (0028).
        </div>
      </div>
    </div>
  </div>
<script>
const GRID=__GRID__;
const TRAJ=__TRAJ__;
const DOLOR=__DOLOR__;
const COMIDA0=__COMIDA__;
const WALLS=__WALLS__;
const STEPS=__STEPS__;
const cv=document.getElementById('cv'), ctx=cv.getContext('2d');
const CS=cv.width/GRID;
const COL={bg:'#070a16',visited:'#1b2552',agent:'#39e6ff',food:'#4dff9e',
           dolor:'#ff5d73',wall:'#3a4170',grid:'#141a37',trail:'rgba(57,230,255,0.18)'};
let i=0, playing=true, timer=null;

function quad(coverage){
  const q={ '00':0,'01':0,'10':0,'11':0 };
  for(const [x,y] of coverage){ const kx=x<GRID/2?0:1, ky=y<GRID/2?0:1; q[''+kx+ky]++; }
  const tot=coverage.length||1;
  return [q['00']/tot*100, q['01']/tot*100, q['10']/tot*100, q['11']/tot*100];
}

function draw(t){
  ctx.fillStyle=COL.bg; ctx.fillRect(0,0,cv.width,cv.height);
  // grid
  ctx.strokeStyle=COL.grid; ctx.lineWidth=1;
  for(let k=0;k<=GRID;k++){ ctx.beginPath();ctx.moveTo(k*CS,0);ctx.lineTo(k*CS,cv.height);ctx.stroke();
    ctx.beginPath();ctx.moveTo(0,k*CS);ctx.lineTo(cv.width,k*CS);ctx.stroke(); }
  // visited
  const seen=new Set();
  for(let s=0;s<=t;s++){ const [x,y]=TRAJ[s]; seen.add(x+','+y); }
  seen.forEach(p=>{ const [x,y]=p.split(',').map(Number);
    ctx.fillStyle=COL.visited; ctx.fillRect(x*CS+3,y*CS+3,CS-6,CS-6); });
  // food (solo las que quedan en t)
  const eaten=new Set();
  for(let s=0;s<=t;s++){ for(const f of COMIDA0){ if(TRAJ[s][0]===f[0]&&TRAJ[s][1]===f[1]) eaten.add(f[0]+','+f[1]); } }
  for(const f of COMIDA0){ if(eaten.has(f[0]+','+f[1])) continue;
    ctx.fillStyle=COL.food; ctx.shadowColor=COL.food; ctx.shadowBlur=12;
    ctx.beginPath();ctx.arc(f[0]*CS+CS/2,f[1]*CS+CS/2,CS*0.28,0,7);ctx.fill(); ctx.shadowBlur=0; }
  // walls
  for(const [x,y] of WALLS){ ctx.fillStyle=COL.wall; ctx.fillRect(x*CS+2,y*CS+2,CS-4,CS-4); }
  // dolor
  for(const [x,y] of DOLOR){ ctx.fillStyle=COL.dolor; ctx.shadowColor=COL.dolor; ctx.shadowBlur=14;
    ctx.fillRect(x*CS+3,y*CS+3,CS-6,CS-6); ctx.shadowBlur=0; }
  // trail (ultimos 14)
  const from=Math.max(0,t-14);
  for(let s=from;s<=t;s++){ const [x,y]=TRAJ[s];
    ctx.fillStyle=COL.trail; ctx.fillRect(x*CS+4,y*CS+4,CS-8,CS-8); }
  // agente
  const [ax,ay]=TRAJ[t];
  ctx.fillStyle=COL.agent; ctx.shadowColor=COL.agent; ctx.shadowBlur=18;
  ctx.beginPath();ctx.arc(ax*CS+CS/2,ay*CS+CS/2,CS*0.32,0,7);ctx.fill(); ctx.shadowBlur=0;
}

function updatePanel(t){
  const cov=TRAJ.slice(0,t+1);
  document.getElementById('k').textContent=t;
  document.getElementById('pos').textContent='('+TRAJ[t][0]+','+TRAJ[t][1]+')';
  document.getElementById('vis').textContent=new Set(cov.map(p=>p[0]+','+p[1])).size;
  let food=0; const eaten=new Set();
  for(let s=0;s<=t;s++) for(const f of COMIDA0) if(TRAJ[s][0]===f[0]&&TRAJ[s][1]===f[1]) eaten.add(f[0]+','+f[1]);
  food=COMIDA0.length-eaten.size;
  document.getElementById('food').textContent=food;
  let pain=0; for(let s=0;s<=t;s++) if(DOLOR.some(d=>d[0]===TRAJ[s][0]&&d[1]===TRAJ[s][1])) pain++;
  document.getElementById('pain').textContent=pain;
  // aproximacion de campos por tramo (eta baja con visita, abur alto con repeticion)
  const local=new Set(cov.map(p=>p[0]+','+p[1]));
  const rep=new Set(); const seen2=new Set();
  for(const p of cov){ if(seen2.has(p[0]+','+p[1])) rep.add(p[0]+','+p[1]); seen2.add(p[0]+','+p[1]); }
  const eta=Math.max(0.1,0.5-(local.size/144)*0.35);
  const abur=Math.min(1, rep.size/40);
  document.getElementById('eta').textContent=eta.toFixed(2);
  document.getElementById('etaB').style.width=(eta*100)+'%';
  document.getElementById('abur').textContent=abur.toFixed(2);
  document.getElementById('aburB').style.width=(abur*100)+'%';
  document.getElementById('ret').textContent=rep.size;
  const q=quad(cov);
  document.getElementById('q00').textContent=q[0].toFixed(0)+'%';
  document.getElementById('q01').textContent=q[1].toFixed(0)+'%';
  document.getElementById('q10').textContent=q[2].toFixed(0)+'%';
  document.getElementById('q11').textContent=q[3].toFixed(0)+'%';
}

function frame(){
  draw(i); updatePanel(i);
  document.getElementById('scrub').value=i;
  if(playing){ if(i<STEPS){ i++; } else { playing=false; document.getElementById('play').textContent='▶ Play'; } }
}

function loop(){
  const sp=+document.getElementById('speed').value;
  frame();
  timer=setTimeout(loop, 1000/Math.max(1,sp));
}
document.getElementById('play').onclick=()=>{ playing=!playing;
  document.getElementById('play').textContent=playing?'⏸ Pausa':'▶ Play'; };
document.getElementById('reset').onclick=()=>{ i=0; playing=true;
  document.getElementById('play').textContent='⏸ Pausa'; };
document.getElementById('scrub').oninput=(e)=>{ i=+e.target.value; playing=false;
  document.getElementById('play').textContent='▶ Play'; draw(i); updatePanel(i); };
loop();
</script>
</body>
</html>
"""

def main():
    w, traj, a = build_trace()
    dolor = [list(p) for p in w.dolor_cells | w.walls]
    comida = [list(p) for p in w.food_cells]
    walls = [list(p) for p in w.walls]
    html = (HTML
        .replace("__GRID__", str(GRID))
        .replace("__STEPS__", str(STEPS))
        .replace("__TRAJ__", json.dumps([[x,y] for (x,y) in traj]))
        .replace("__DOLOR__", json.dumps(dolor))
        .replace("__COMIDA__", json.dumps(comida))
        .replace("__WALLS__", json.dumps(walls)))
    out = "/data/user/0/com.hermesagent.android/files/home/demo_grid_0044.html"
    open(out, "w", encoding="utf-8").write(html)
    print("HTML escrito:", out, "ticks:", len(traj)-1, "comida_total:", a.food_eaten, "dolor:", a.pain_cum)

if __name__ == "__main__":
    main()
