// Genius Subtitle 花字运行时：把一条花字（window.HZ_SPEC）按模板排到 1280×720 的设计画布上，
// 再按视频尺寸缩放。huazi.py 用 window.hzReady 等待排版完成，用 window.hzSeek(t) 定到第 t 秒逐帧截图。
// 模板只提供 style.css 和可选的 decorate.js（定义 window.HZ_DECORATE(el, item, api)）。
(function () {
  const S = window.HZ_SPEC, it = S.item, f = it.fields || {};
  const BW = 1280, BH = 720;
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // 数字、英文自动套数字字体；中文不动
  // {重点} → <span class="hz-em">，粗细混排、强调色都靠它
  const rich = s => esc(s).replace(/([0-9][0-9.,%]*[A-Za-z%℃°]*|[A-Za-z][A-Za-z0-9.\-]*)/g, '<span class="hz-lat">$1</span>')
                          .replace(/\{([^}]*)\}/g, '<span class="hz-em">$1</span>');

  const root = document.documentElement;
  root.style.setProperty('--brand', S.brand);
  root.style.setProperty('--brand-light', S.brandLight);
  root.style.setProperty('--brand-deep', S.brandDeep);

  const stage = document.getElementById('stage');
  stage.style.transform = `scale(${S.W / BW})`;
  if (S.bg) stage.style.backgroundImage = `url("${S.bg}")`;

  const dur = Math.max(0.6, it.duration);
  const el = document.createElement('div');
  el.className = `hz type-${it.type} align-${it.align}`;
  el.style.setProperty('--dur', dur + 's');
  el.style.setProperty('--out', Math.max(0.5, dur - 0.4) + 's');

  let d = 0; const step = () => (d += 0.12).toFixed(2) + 's';
  const parts = [];
  parts.push('<div class="hz-deco hz-back"></div>');
  if (f.ghost) parts.push(`<div class="hz-ghost hz-a" style="--d:0s">${esc(f.ghost)}</div>`);
  if (f.kicker) parts.push(`<div class="hz-kicker hz-a" style="--d:0s"><span>${rich(f.kicker)}</span></div>`);
  if (it.type === 'name') {
    parts.push(`<div class="hz-line hz-l1 hz-a" style="--d:0s"><span class="hz-bar"></span><span class="hz-t hz-n">${esc(f.name)}</span></div>`);
    parts.push(`<div class="hz-sub hz-a" style="--d:${step()}"><i class="hz-bullet"></i><span>${rich(f.role)}</span></div>`);
  } else {
    const lines = f.lines || [];
    lines.forEach((ln, i) => {
      const last = i === lines.length - 1;
      const num = (it.type === 'number' && last && f.number)
        ? `<span class="hz-num"><span class="hz-v">${esc(f.number.value)}</span><span class="hz-u">${esc(f.number.unit || '')}</span></span>` : '';
      parts.push(`<div class="hz-line hz-l${i + 1}${last ? ' hz-last' : ''} hz-a" style="--d:${i ? step() : '0s'}"><span class="hz-bar"></span>` +
                 `<span class="hz-t">${rich(ln)}</span>${num}</div>`);
    });
    if (f.items && f.items.length)
      parts.push('<ul class="hz-items">' + f.items.map(x => `<li class="hz-a" style="--d:${step()}"><i class="hz-bullet"></i><span>${rich(x)}</span></li>`).join('') + '</ul>');
    if (f.sub) parts.push(`<div class="hz-sub hz-a" style="--d:${step()}"><i class="hz-bullet"></i><span>${rich(f.sub)}</span></div>`);
  }
  if (f.en) parts.push(`<div class="hz-en hz-a" style="--d:${step()}">${esc(f.en)}</div>`);
  parts.push('<div class="hz-deco hz-front"></div>');
  el.innerHTML = parts.join('');
  stage.appendChild(el);

  // 定位：左右按安全边距贴边，居中按宽度居中；y 是顶边占画面高度的比例，底边不进字幕区
  function place() {
    const sx = S.safe.x * BW, top = S.safe.top * BH, bottom = S.bottomLimit * BH;
    const w = el.offsetWidth, h = el.offsetHeight;
    if (it.align === 'right') { el.style.right = sx + 'px'; el.style.left = 'auto'; }
    else if (it.align === 'center') el.style.left = Math.round((BW - w) / 2) + 'px';
    else el.style.left = sx + 'px';
    let y = (it.y == null ? 0.42 : it.y) * BH;
    y = Math.max(top, Math.min(y, bottom - h));
    el.style.top = Math.round(y) + 'px';
  }

  // 节点相对花字容器的位置（设计单位，不受入场动画的 transform 影响）
  function rel(node) {
    let x = 0, y = 0, n = node;
    while (n && n !== el) { x += n.offsetLeft; y += n.offsetTop; n = n.offsetParent; }
    return { x, y, w: node.offsetWidth, h: node.offsetHeight };
  }
  const api = { place, rel, dur, BW, BH, brand: S.brand, svg: (w, h, inner) => `<svg width="1" height="1" style="position:absolute;left:0;top:0;overflow:visible">${inner}</svg>` };

  window.hzReady = document.fonts.ready.then(() => {
    place();
    if (window.HZ_DECORATE) window.HZ_DECORATE(el, it, api);
    place();
    const r = el.getBoundingClientRect();
    return { box: [r.left, r.top, r.width, r.height].map(v => Math.round(v * BW / S.W * 100) / 100) };
  });

  // 定到第 t 秒：暂停所有 CSS 动画和 SVG 动画，统一设时间
  window.hzSeek = function (t) {
    document.getAnimations().forEach(a => { a.pause(); a.currentTime = t * 1000; });
    document.querySelectorAll('svg').forEach(s => { if (s.pauseAnimations) { s.pauseAnimations(); s.setCurrentTime(t); } });
    return new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(true))));
  };
})();
