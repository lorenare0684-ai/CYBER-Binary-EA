const canvas = document.getElementById('chart');
const ctx = canvas.getContext('2d');
let candles = [];
let price = 1.08542;

function seedCandles() {
  let value = 1.08455;
  candles = Array.from({ length: 42 }, (_, i) => {
    const open = value;
    const move = (Math.random() - 0.45) * 0.00034;
    const close = open + move;
    const high = Math.max(open, close) + Math.random() * 0.00016;
    const low = Math.min(open, close) - Math.random() * 0.00016;
    value = close;
    return { open, close, high, low };
  });
}
function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * ratio;
  canvas.height = rect.height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  drawChart(rect.width, rect.height);
}
function drawChart(width, height) {
  ctx.clearRect(0, 0, width, height);
  const pad = { top: 10, right: 2, bottom: 5, left: 2 };
  const values = candles.flatMap(c => [c.high, c.low]);
  const max = Math.max(...values) + .0001;
  const min = Math.min(...values) - .0001;
  const scaleY = v => pad.top + (max - v) / (max - min) * (height - pad.top - pad.bottom);
  const step = (width - 8) / candles.length;
  const candleWidth = Math.max(3, step * .54);
  // subtle horizontal chart guides
  ctx.strokeStyle = '#172741'; ctx.lineWidth = 1;
  for (let n = 0; n < 4; n++) { const y = pad.top + n * (height - 22) / 3; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }
  candles.forEach((c, i) => {
    const x = 4 + i * step + step / 2;
    const up = c.close >= c.open;
    ctx.strokeStyle = up ? '#54d8c6' : '#7259a4';
    ctx.fillStyle = up ? '#42beaF' : '#644d91';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, scaleY(c.high)); ctx.lineTo(x, scaleY(c.low)); ctx.stroke();
    const y = scaleY(Math.max(c.open, c.close));
    const h = Math.max(2, Math.abs(scaleY(c.open) - scaleY(c.close)));
    ctx.fillRect(x - candleWidth / 2, y, candleWidth, h);
  });
  const latest = candles[candles.length - 1].close;
  const lineY = scaleY(latest);
  ctx.setLineDash([4, 4]); ctx.strokeStyle = '#45cfc7'; ctx.globalAlpha = .65;
  ctx.beginPath(); ctx.moveTo(0, lineY); ctx.lineTo(width, lineY); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
}
function tick() {
  const last = candles[candles.length - 1];
  const open = last.close;
  const close = open + (Math.random() - .47) * .00011;
  candles.push({ open, close, high: Math.max(open, close) + Math.random() * .00007, low: Math.min(open, close) - Math.random() * .00007 });
  if (candles.length > 44) candles.shift();
  price = close;
  document.getElementById('price').textContent = close.toFixed(5);
  const rect = canvas.getBoundingClientRect(); drawChart(rect.width, rect.height);
}
seedCandles();
window.addEventListener('resize', resizeCanvas);
requestAnimationFrame(resizeCanvas);
setInterval(tick, 5000);

document.querySelectorAll('.timeframes button').forEach(btn => btn.addEventListener('click', () => {
  document.querySelector('.timeframes .selected').classList.remove('selected'); btn.classList.add('selected');
}));
document.querySelector('.switch').addEventListener('click', e => e.currentTarget.classList.toggle('on'));
document.querySelector('.refresh').addEventListener('click', e => {
  e.currentTarget.style.transform = 'rotate(360deg)';
  setTimeout(() => e.currentTarget.style.transform = '', 500);
});

// Asset intelligence and guarded paper-trading controls.
const assets = document.querySelectorAll('.asset-row');
const assetName = document.getElementById('assetName');
const rescan = document.getElementById('rescanBtn');
const priceEl = document.getElementById('price');
assets.forEach(row => row.addEventListener('click', () => {
  assets.forEach(item => item.classList.remove('selected'));
  row.classList.add('selected');
  assetName.innerHTML = `${row.dataset.asset} <small>OTC</small>`;
  price = Number(row.dataset.price);
  priceEl.textContent = price.toFixed(5);
}));
rescan.addEventListener('click', () => {
  rescan.textContent = '⌁ Scanning...';
  rescan.disabled = true;
  setTimeout(() => { rescan.textContent = '✓ Best match'; rescan.disabled = false; }, 850);
});
const autoToggle = document.getElementById('automationToggle');
const automationState = document.getElementById('automationState');
let automationEnabled = false;
autoToggle.addEventListener('click', () => {
  automationEnabled = !automationEnabled;
  autoToggle.classList.toggle('active', automationEnabled);
  autoToggle.textContent = automationEnabled ? 'Pause automation' : 'Enable automation';
  automationState.textContent = automationEnabled ? 'Automation armed' : 'Automation paused';
  document.querySelector('.automation-icon').textContent = automationEnabled ? '✓' : '⏱';
});
document.getElementById('autoScanBtn').addEventListener('click', e => {
  e.currentTarget.querySelector('.switch').classList.toggle('on');
});
document.getElementById('editRisk').addEventListener('click', () => alert('Risk rules are locked to paper mode in this demo. Configure risk per trade, daily loss limit, open-trade cap, and cooldown here.'));

// Historic validation chart: deterministic sample output for the selected window.
const historyCanvas = document.getElementById('historyCanvas');
const historyCtx = historyCanvas.getContext('2d');
function drawHistory() {
  const rect = historyCanvas.getBoundingClientRect(), ratio = devicePixelRatio || 1;
  historyCanvas.width = rect.width * ratio; historyCanvas.height = rect.height * ratio;
  historyCtx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const w = rect.width, h = rect.height, points = 31;
  historyCtx.clearRect(0,0,w,h);
  for(let i=0;i<4;i++){const y=i*(h-2)/3+1;historyCtx.strokeStyle='#172741';historyCtx.beginPath();historyCtx.moveTo(0,y);historyCtx.lineTo(w,y);historyCtx.stroke()}
  let y=h*.83; historyCtx.beginPath();
  for(let i=0;i<points;i++){y-= (i%5===0?7:3)+Math.sin(i*1.7)*2; const x=i*w/(points-1); if(i===0)historyCtx.moveTo(x,y);else historyCtx.lineTo(x,y)}
  historyCtx.strokeStyle='#54d8c6';historyCtx.lineWidth=2;historyCtx.shadowColor='#36cfc0';historyCtx.shadowBlur=8;historyCtx.stroke();historyCtx.shadowBlur=0;
  const grad=historyCtx.createLinearGradient(0,0,0,h);grad.addColorStop(0,'#31bca522');grad.addColorStop(1,'#31bca500');historyCtx.lineTo(w,h);historyCtx.lineTo(0,h);historyCtx.fillStyle=grad;historyCtx.fill();
}
window.addEventListener('resize', drawHistory); requestAnimationFrame(drawHistory);
document.getElementById('runBacktest').addEventListener('click', e => {
  const days=Number(document.getElementById('historyRange').value); e.currentTarget.disabled=true; e.currentTarget.textContent='Running...';
  setTimeout(()=>{ document.getElementById('historyAccuracy').textContent=days===7?'71.2%':days===90?'66.9%':'68.4%'; document.getElementById('profitableDays').textContent=days===7?'5 / 7':days===90?'61 / 90':'21 / 30'; document.getElementById('candleCount').textContent=(days*96).toLocaleString(); e.currentTarget.disabled=false;e.currentTarget.textContent='Run backtest'; },650);
});
