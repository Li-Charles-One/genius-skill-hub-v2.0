// 模板 7 · 拼贴纸张风：按 fields.variant 加样式类，按文字位置铺撕纸、贴贴纸。
// 撕边用 item id 做种子的伪随机（每条花字毛边不同，逐帧渲染结果固定）。
window.HZ_DECORATE = function (el, it, api) {
  const f = it.fields || {}, v = f.variant || 'tape';
  el.classList.add('v-' + v);
  const back = el.querySelector('.hz-back'), front = el.querySelector('.hz-front');
  const q = s => el.querySelector(s), R = n => api.rel(n);
  if (v === 'card' && f.button) {
    const b = document.createElement('div');
    b.className = 'tp-btn hz-a'; b.style.setProperty('--d', '.55s'); b.textContent = f.button;
    el.insertBefore(b, front);
  }
  const esc = x => String(x).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  if (v === 'board' && f.cols) {
    const c = document.createElement('div'); c.className = 'tp-cols';
    c.innerHTML = f.cols.map((col, i) => `<div class="tp-col hz-a" style="--d:${(.3 + i * .15).toFixed(2)}s"><div class="tp-h">${esc(col.h)}</div>` +
      `<div class="tp-p">${(col.p || []).map(esc).join('<br>')}</div></div>`).join('');
    el.insertBefore(c, front);
  }
  api.place();

  let seed = 2166136261;
  for (const c of String(it.id) + v) seed = Math.imul(seed ^ c.charCodeAt(0), 16777619) >>> 0;
  const rnd = () => (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296;
  const pad = (b, l, t, r, bt) => ({ x: b.x - l, y: b.y - t, w: b.w + l + r, h: b.h + t + bt });
  const union = (...bs) => {
    const x = Math.min(...bs.map(b => b.x)), y = Math.min(...bs.map(b => b.y));
    return { x, y, w: Math.max(...bs.map(b => b.x + b.w)) - x, h: Math.max(...bs.map(b => b.y + b.h)) - y };
  };
  const px = p => p.map(([x, y]) => `${x.toFixed(1)}px ${y.toFixed(1)}px`).join(',');

  // 撕边矩形：sides 里列出的边撕开，其余整齐；a 是毛边深度
  function tornRect(w, h, a = 6, sides = 'tlbr') {
    const pts = [];
    const edge = (x0, y0, x1, y1, nx, ny, torn) => {
      const n = Math.max(1, Math.round(Math.hypot(x1 - x0, y1 - y0) / (5 + rnd() * 4)));
      for (let i = 0; i < n; i++) {
        const t = (i + (torn && i ? rnd() * .5 - .25 : 0)) / n, j = torn ? rnd() * a * (rnd() < .15 ? 1.8 : 1) : 0;
        pts.push([x0 + (x1 - x0) * t + nx * j, y0 + (y1 - y0) * t + ny * j]);
      }
    };
    edge(0, 0, w, 0, 0, 1, sides.includes('t')); edge(w, 0, w, h, -1, 0, sides.includes('r'));
    edge(w, h, 0, h, 0, -1, sides.includes('b')); edge(0, h, 0, 0, 1, 0, sides.includes('l'));
    return `polygon(${px(pts)})`;
  }
  // 撕边椭圆：低频起伏 + 细碎毛边
  function tornEllipse(w, h, a = 6) {
    const rx = w / 2, ry = h / 2, ph = rnd() * 6, pts = [];
    for (let i = 0; i < 150; i++) {
      const t = i / 150 * Math.PI * 2, k = 1 + .035 * Math.sin(3 * t + ph) - rnd() * a / Math.min(rx, ry);
      pts.push([rx + Math.cos(t) * rx * k, ry + Math.sin(t) * ry * k]);
    }
    return `polygon(${px(pts)})`;
  }
  function paper(cls, b, o = {}) {
    const clip = o.ellipse ? tornEllipse(b.w, b.h, o.a) : tornRect(b.w, b.h, o.a, o.sides);
    (o.front ? front : back).insertAdjacentHTML('beforeend', `<div class="tp ${cls}" style="left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px;` +
      `--r:${o.r || 0}deg;--d:${o.d || 0}s;clip-path:${clip}"></div>`);
  }
  function sticker(x, y, w, h, inner, o = {}) {
    (o.back ? back : front).insertAdjacentHTML('beforeend', `<div class="st" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px;--d:${o.d ?? .3}s;` +
      `transform-origin:50% 50%;rotate:${o.r || 0}deg">${api.svg(w, h, inner)}</div>`);
  }
  const eyes = (x, y, o) => sticker(x, y, 64, 42, `<g class="blink">
      <ellipse cx="17" cy="21" rx="14" ry="18" fill="#fff" stroke="#111" stroke-width="3.2"/>
      <ellipse cx="46" cy="21" rx="14" ry="18" fill="#fff" stroke="#111" stroke-width="3.2"/>
      <circle cx="22" cy="25" r="6.5" fill="#111"/><circle cx="51" cy="25" r="6.5" fill="#111"/>
      <circle cx="24" cy="22" r="2" fill="#fff"/><circle cx="53" cy="22" r="2" fill="#fff"/></g>`, o);
  const clip = (x, y, o) => sticker(x, y, 24, 62, `<path d="M8 50 V12 a6 6 0 0 1 12 0 V46 a9 9 0 0 1 -18 0 V6" fill="none" stroke="#2c2c30" stroke-width="3.4" stroke-linecap="round"/>
      <path d="M8 50 V12 a6 6 0 0 1 12 0 V46" fill="none" stroke="#c9c9cf" stroke-width="1.1" stroke-linecap="round"/>`, o);
  const barcode = (x, y, o) => {
    let bars = '', bx = 5;
    while (bx < 54) { const bw = 1 + Math.round(rnd() * 2.4); bars += `<rect x="${bx}" y="4" width="${bw}" height="13" fill="#111"/>`; bx += bw + 1 + Math.round(rnd() * 2); }
    sticker(x, y, 60, 22, `<rect width="60" height="22" fill="#f4f3ee"/>${bars}`, o);
  };
  const acc = 'stroke:rgb(var(--acc))';

  if (v === 'tape') {
    const a = R(q('.hz-l1 .hz-t')), b = R(q('.hz-l2 .hz-t') || q('.hz-l1 .hz-t'));
    const p1 = pad(a, 22, 14, 26, 10), p2 = pad(b, 30, 10, 34, 14);
    paper('white', { x: p2.x + 8, y: p2.y + 6, w: p2.w, h: p2.h }, { r: 1.2, a: 7 });
    paper('yellow', p1, { r: -2, a: 6, sides: 'lr' });
    paper('yellow', p2, { r: .8, a: 7, d: .08 });
    clip(p1.x + 4, p1.y - 22, { r: -8, d: .45 });
    sticker(p2.x + p2.w - 46, p1.y - 34, 96, 60, `<path class="draw" pathLength="1" d="M4 52 C14 10 44 0 50 26 C56 50 20 52 26 26 C32 2 70 -4 86 18 C94 30 84 44 74 34"
      fill="none" style="${acc}" stroke-width="3.6" stroke-linecap="round"/>`, { d: .35 });
    barcode(p2.x + p2.w - 76, p2.y + p2.h - 20, { r: -10, d: .5 });
  }

  if (v === 'blob') {
    const all = union(...[...el.querySelectorAll('.hz-t, .hz-sub')].map(R));
    const p = pad(all, 70, 46, 70, 40);
    paper('white', pad(p, 7, 7, 7, 7), { ellipse: true, a: 5, r: -3 });
    paper('blue', p, { ellipse: true, a: 4, r: -3, d: .05 });
    const cx = p.x + p.w / 2, cy = p.y + p.h / 2, rx = p.w / 2 + 16, ry = p.h / 2 + 10;
    const P = t => [cx + rx * Math.cos(t * Math.PI / 180), cy + ry * Math.sin(t * Math.PI / 180)].map(n => n.toFixed(1));
    const [sx, sy] = P(150), [ex, ey] = P(18).map(Number);
    const d = `M${sx} ${sy} A${rx} ${ry} 0 1 1 ${ex} ${ey} C${ex + 30} ${ey + 26} ${ex + 84} ${ey + 4} ${ex + 72} ${ey - 26} ` +
              `C${ex + 62} ${ey - 50} ${ex + 34} ${ey - 20} ${ex + 64} ${ey - 4} C${ex + 90} ${ey + 8} ${ex + 120} ${ey - 10} ${ex + 140} ${ey - 30}`;
    front.insertAdjacentHTML('beforeend', `<div style="position:absolute;left:0;top:0;transform-origin:${cx}px ${cy}px;rotate:-5deg">${api.svg(0, 0,
      `<path class="draw" pathLength="1" d="${d}" fill="none" style="${acc};--d:.4s" stroke-width="3.4" stroke-linecap="round"/>
       <path class="draw" pathLength="1" d="M${ex + 124} ${ey - 32} L${ex + 141} ${ey - 31} L${ex + 137} ${ey - 15}" fill="none" style="${acc};--d:1s" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>`)}</div>`);
    eyes(p.x + 40, p.y + p.h - 50, { d: .5, r: -6 });
  }

  if (v === 'card') {
    const W = el.offsetWidth, btn = q('.tp-btn'), bb = btn ? R(btn) : null, H = (bb ? bb.y + bb.h / 2 : el.offsetHeight);
    const card = { x: 0, y: 0, w: W, h: H + 4 };
    paper('blue', { x: 10, y: 10, w: W, h: H + 2 }, { a: 6, r: .6 });
    paper('grid', card, { a: 5, r: -.4, d: .04 });
    const l1 = R(q('.hz-l1'));
    paper('yellow', { x: -12, y: l1.y - 10, w: W + 20, h: l1.h + 18 }, { a: 6, r: -.8, d: .12 });
    sticker(l1.x + 2, l1.y + l1.h / 2 - 10, 20, 20, `<circle cx="10" cy="10" r="7" style="fill:rgb(var(--brand))" stroke="#fff" stroke-width="2.4"/>`, { d: .3 });
    if (bb) sticker(bb.x - 112, bb.y + bb.h / 2 - 16, 104, 32, `<path class="draw" pathLength="1" d="M4 22 L18 8 L26 26 L38 6 L46 24 Q60 30 98 14 M86 8 L99 14 L90 25"
      fill="none" style="${acc}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>`, { d: .6 });
  }

  if (v === 'badge') {
    const W = el.offsetWidth, H = el.offsetHeight;
    paper('yellow', { x: W - 210, y: -12, w: 222, h: 70 }, { a: 7, r: 2.5 });
    paper('yellow', { x: -14, y: H - 52, w: 170, h: 64 }, { a: 7, r: -2 });
    paper('dots', { x: 0, y: 0, w: W, h: H }, { a: 6, d: .05 });
    const k = q('.hz-kicker');
    if (k) paper('yellow', pad(R(k), 4, 2, 4, 2), { a: 4, r: -2, d: .25 });
    const x0 = 18, y0 = 16, x1 = W - 20, y1 = H - 20, r = 10;
    const d = `M${x0 + r} ${y0} H${x1 - r} Q${x1} ${y0} ${x1} ${y0 + r} V${y1 - r} Q${x1} ${y1} ${x1 - r} ${y1} H${x0 + 74} L${x0 + 30} ${y1 + 30} L${x0 + 40} ${y1} ` +
              `H${x0 + r} Q${x0} ${y1} ${x0} ${y1 - r} V${y0 + r} Q${x0} ${y0} ${x0 + r} ${y0} Z`;
    back.insertAdjacentHTML('beforeend', `<div style="position:absolute;left:0;top:0">${api.svg(0, 0,
      `<path class="draw" pathLength="1" d="${d}" fill="none" style="stroke:rgb(var(--brand));--d:.3s" stroke-width="3.6" stroke-linejoin="round"/>`)}</div>`);
  }

  if (v === 'strip') {
    const k = q('.hz-kicker'), t = q('.hz-l1 .hz-t'), s = q('.hz-sub');
    if (t) { const b = R(t); paper('white', pad(b, 6, 6, 6, 6), { a: 5, r: -1 }); paper('blue', b, { a: 4, r: -1, d: .05 }); }
    if (s) { const b = R(s); paper('white', pad(b, 5, 5, 5, 5), { a: 4, r: .6, d: .1 }); paper('blue', b, { a: 3, r: .6, d: .14 }); }
    if (k) { const b = R(k); paper('yellow', b, { a: 5, r: -1.5, d: .02, sides: 'lr' }); eyes(b.x - 58, b.y - 14, { d: .45, r: -8 }); }
  }

  const sparkle = (x, y, s, o) => sticker(x, y, s, s, `<path class="twinkle" d="M${s/2} 2 Q${s*.56} ${s*.44} ${s-2} ${s/2} Q${s*.56} ${s*.56} ${s/2} ${s-2} Q${s*.44} ${s*.56} 2 ${s/2} Q${s*.44} ${s*.44} ${s/2} 2Z"
      fill="none" style="${acc}" stroke-width="2.6" stroke-linejoin="round"/>`, o);
  const bigClip = (x, y, o) => sticker(x, y, 56, 120, `<g transform="scale(2.1)">
      <path d="M8 50 V12 a6 6 0 0 1 12 0 V46 a9 9 0 0 1 -18 0 V6" fill="none" stroke="#1b1b1f" stroke-width="5.2" stroke-linecap="round"/>
      <path d="M8 50 V12 a6 6 0 0 1 12 0 V46 a9 9 0 0 1 -18 0 V6" fill="none" style="${acc}" stroke-width="3" stroke-linecap="round"/></g>`, o);
  const binder = (x, y, o) => sticker(x, y, 76, 76, `<g transform="scale(1.35) rotate(-28 28 28)" stroke="#173a26" stroke-width="2.6" stroke-linejoin="round">
      <path d="M18 14 C12 -2 30 -4 27 12 M38 14 C44 -2 26 -4 29 12" fill="none" stroke-width="3.2"/>
      <path d="M12 16 H44 L39 46 H17 Z" fill="#74DE92"/><path d="M15 22 H41" stroke="#bff3cd" stroke-width="2"/></g>`, o);

  if (v === 'board') {
    const W = el.offsetWidth, H = el.offsetHeight;
    paper('bluegrid', { x: -24, y: -20, w: W + 44, h: H + 34 }, { a: 9, r: -.6 });
    paper('grid', { x: 0, y: 0, w: W, h: H }, { a: 0, sides: '', d: .05 });
    const t = q('.hz-l1 .hz-t');
    if (t) { const b = R(t); paper('yellow', pad(b, 26, 8, 26, 10), { a: 4, r: -1, d: .15 }); sparkle(b.x + b.w + 30, b.y - 20, 54, { d: .5 }); sparkle(b.x + b.w + 80, b.y + 34, 22, { d: .6 }); }
    el.querySelectorAll('.tp-h').forEach((h, i) => paper('yellow', pad(R(h), 18, 4, 22, 6), { a: 4, r: i % 2 ? 1 : -1.2, d: .35 + i * .15 }));
    const cs = [...el.querySelectorAll('.tp-col')].map(R);
    if (cs.length > 2) {
      const x0 = cs[1].x, y0 = cs[1].y - 24, w = cs[2].x - x0 + 10;
      sticker(x0, y0 - 80, w, 90, `<path class="draw" pathLength="1" d="M4 84 L${w*.28} 34 L${w*.26} 74 L${w*.58} 24 L${w*.56} 60 L${w-8} 8 M${w-34} 8 L${w-6} 7 L${w-16} 32"
        fill="none" style="stroke:rgb(var(--brand))" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>`, { d: .5, back: false });
    }
    bigClip(46, -54, { r: -38, d: .45 });
    sticker(W - 84, H - 84, 84, 84, `<defs><linearGradient id="curl-${it.id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#c9c9cf"/></linearGradient></defs>
      <path d="M84 0 V84 H0 Z" style="fill:rgb(var(--brand))"/>
      <path d="M84 0 Q40 10 22 22 Q10 40 0 84 Q46 46 84 0Z" fill="url(#curl-${it.id})" stroke="rgba(0,0,0,.15)"/>`, { d: .6 });
  }

  if (v === 'note') {
    const W = el.offsetWidth, H = el.offsetHeight, k = q('.hz-l1');
    const kb = k ? R(k) : { x: 0, y: 0, w: 0, h: 0 }, top = kb.y + kb.h * .62;
    paper('blue', { x: -7, y: top + 4, w: W + 14, h: H - top - 6 }, { a: 6, r: -.4 });
    paper('crumple', { x: 0, y: top, w: W, h: H - top }, { a: 8, r: -.4, d: .05 });
    if (k) paper('yellow', kb, { a: 4, r: -3, d: .15 });
    paper('tape', { x: W - 150, y: top - 26, w: 150, h: 42 }, { a: 4, sides: 'lr', r: 16, d: .5, front: true });
    barcode(W - 60, H - 74, { r: 90, d: .55 });
    sticker(-22, H - 56, 64, 46, `<path class="draw" pathLength="1" d="M4 20 L46 4 M8 32 L54 14 M12 44 L40 32" fill="none" style="${acc}" stroke-width="3.4" stroke-linecap="round"/>`, { d: .55 });
  }

  if (v === 'tile') {
    const t = q('.hz-l1 .hz-t');
    if (t) {
      const p = pad(R(t), 30, 16, 62, 20);
      paper('white', pad(p, 7, 7, 7, 7), { a: 6, r: -.5 });
      paper('tiles', p, { a: 5, r: -.5, d: .05 });
      paper('tape', { x: p.x - 34, y: p.y + p.h - 22, w: 74, h: 20 }, { a: 3, sides: 'lr', r: 28, d: .5, front: true });
      paper('tape', { x: p.x - 34, y: p.y + p.h - 22, w: 74, h: 20 }, { a: 3, sides: 'lr', r: -24, d: .55, front: true });
      binder(p.x + p.w - 30, p.y - 40, { d: .45 });
      barcode(p.x + p.w - 70, p.y + p.h - 14, { r: -12, d: .55 });
    }
  }

  if (v === 'label') {
    const em = q('.hz-em'), line = q('.hz-l1 .hz-t');
    if (em) {
      const b = R(em);
      paper('white', pad(b, 6, 2, 6, 4), { a: 6, r: -1.5 });
      paper('blue-dots', pad(b, 0, -4, 0, -2), { a: 5, r: -1.5, d: .05 });
      barcode(b.x - 8, b.y - 10, { r: -8, d: .5 });
      if (line) {
        const l = R(line), x0 = b.x + b.w + 30, y0 = l.y + l.h + 6, w = l.x + l.w - x0 + 10;
        sticker(x0, y0 - 14, w, 30, `<path class="draw" pathLength="1" d="M4 22 C${w*.25} 8 ${w*.5} 4 ${w*.62} 12 C${w*.7} 18 ${w*.62} 24 ${w*.72} 18 C${w*.82} 12 ${w*.92} 10 ${w-4} 12"
          fill="none" style="${acc}" stroke-width="3.6" stroke-linecap="round"/>`, { d: .5 });
      }
    }
  }
};
