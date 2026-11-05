// 模板 6 · 露营风：按 fields.variant 加样式类，再补每种样式的装饰
window.HZ_DECORATE = function (el, it, api) {
  const f = it.fields || {}, v = f.variant || 'tag';
  el.classList.add('v-' + v);
  const stage = document.getElementById('stage');
  const back = el.querySelector('.hz-back'), front = el.querySelector('.hz-front');
  const add = (host, html) => host.insertAdjacentHTML('beforeend', html);
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const out = el.style.getPropertyValue('--out');

  // pinyin：{词|拼音} → 词 + 下方注音
  if (v === 'pinyin') el.querySelectorAll('.hz-em').forEach(em => {
    const [w, py] = em.textContent.split('|');
    em.innerHTML = esc(w) + (py ? `<span class="sg-py">${esc(py.trim())}</span>` : '');
  });
  api.place();

  // 整屏卡底与水印挂在 stage 上（不进倒影，不受花字位置影响）
  if (f.card && v !== 'tag' && v !== 'pinyin') {
    const c = document.createElement('div'); c.className = 'sg-card c-' + (v === 'box' ? 'box' : 'green'); c.style.setProperty('--out', out);
    if (v === 'box' && f.en) {
      const t = esc((f.en + '   ').repeat(4));
      c.innerHTML = `<div class="sg-wm l">${t}</div><div class="sg-wm r">${t}</div>`;
    }
    // part：kicker 挪到画面左上角
    if (v === 'part') {
      const k = el.querySelector('.hz-kicker');
      if (k) { k.classList.add('sg-k-abs'); k.style.left = (60 - el.offsetLeft) + 'px'; k.style.top = (72 - el.offsetTop) + 'px'; }
    }
    stage.insertBefore(c, el);
  }
  if (v === 'quote') {
    // 大号引号压在左上、右下
    const W = el.offsetWidth, H = el.offsetHeight;
    add(back, `<span class="sg-q o">“</span><span class="sg-q c" style="left:${W - 260}px;top:${H - 50}px">”</span>`);
  }

  if (v === 'box') {
    // 盒子顶面：细线框，向右上退
    const W = el.offsetWidth, sw = 58, dx = 24, dy = 18, k = W * .08;
    const pts = `0,0 ${dx},${-dy} ${W + sw},${-dy - 18} ${W},0`;
    add(back, `<svg class="sg-top" width="1" height="1" style="overflow:visible"><polygon points="${pts}" style="fill:rgba(255,255,255,.35);stroke:rgb(var(--brand));stroke-width:1.5"/>` +
      `<line x1="${k}" y1="0" x2="${k + dx}" y2="${-dy}" style="stroke:rgb(var(--brand));stroke-width:1.5"/></svg>`);
  }
  if (v === 'pinyin') add(back, '<span class="sg-shaft"></span>');
  if (v === 'brush') {
    // 毛边笔刷块：矩形 + 固定种子的湍流位移，压在文字下半部、向右多出一截
    const t = api.rel(el.querySelector('.hz-t')), x = t.x - 70, y = t.y + t.h * .38, w = t.w + 130, h = t.h * .9;
    add(back, `<svg width="1" height="1" style="position:absolute;left:0;top:0;overflow:visible"><defs>` +
      `<filter id="sg-rough" x="-10%" y="-30%" width="120%" height="160%"><feTurbulence type="fractalNoise" baseFrequency="0.09 0.5" numOctaves="3" seed="7"/>` +
      `<feDisplacementMap in="SourceGraphic" scale="14"/></filter></defs>` +
      `<rect x="${x}" y="${y}" width="${w}" height="${h}" filter="url(#sg-rough)" style="fill:color-mix(in srgb, rgb(var(--brand-light)) 70%, #e9f1a8)"/>` +
      `<rect x="${x + 20}" y="${y + h * .62}" width="${w - 30}" height="${h * .22}" filter="url(#sg-rough)" style="fill:rgba(255,255,255,.18)"/></svg>`);
  }
};
