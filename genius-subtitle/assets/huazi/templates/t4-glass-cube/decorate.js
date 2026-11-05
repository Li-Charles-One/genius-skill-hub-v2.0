// 模板 4 · 玻璃方块：身后平行四边形、玻璃方块、方形粒子、弧线
window.HZ_DECORATE = function (el, it, api) {
  const back = el.querySelector('.hz-back'), front = el.querySelector('.hz-front');
  const lines = el.querySelectorAll('.hz-line');
  if (!lines.length) return;
  const a = api.rel(lines[0]), z = api.rel(lines[lines.length - 1]);
  const W = el.offsetWidth, H = el.offsetHeight, right = it.align === 'right';
  const add = (host, html) => host.insertAdjacentHTML('beforeend', html);
  // 平行四边形：一块压在第一行后，一块错位
  const px = right ? W - a.x - a.w : a.x;
  const side = (x, w) => right ? `right:${x}px` : `left:${x}px`;
  add(back, `<span class="t4-panel a" style="${side(px + a.w * .45, a.w * .5)};width:${Math.max(120, a.w * .5)}px;top:${a.y - 14}px;height:${H - a.y - 6}px"></span>`);
  add(back, `<span class="t4-panel b" style="${side(px - 34, 0)};width:${Math.max(90, a.w * .35)}px;top:${a.y + 4}px;height:${H - a.y - 18}px"></span>`);
  // 玻璃方块
  const cube = (x, y, s, d) => `<span class="t4-glow" style="left:${x + s / 2}px;top:${y + s / 2 + 30}px"></span>` +
    `<span class="t4-cube" style="--s:${s}px;left:${x}px;top:${y}px;animation-delay:${d}s"><span class="c" style="animation-delay:${-d * 3}s">${'<i></i>'.repeat(6)}</span></span>`;
  const ex = right ? z.x - 70 : z.x + z.w + 26;
  add(front, cube(ex, z.y + z.h * .15, 40, .35));
  add(front, cube(right ? a.x + a.w + 10 : a.x - 64, a.y + a.h * .45, 30, .5));
  if (lines.length > 1 || it.type === 'number') add(front, cube(right ? a.x - 50 : a.x + a.w + 8, a.y - 26, 26, .65));
  // 方形粒子
  const pts = [[.08, -.12], [.92, .05], [.6, -.18], [1.04, .7], [-.05, .85], [.35, 1.06]];
  pts.forEach(([u, v], i) => add(front, `<span class="t4-p" style="left:${u * W}px;top:${v * H}px;animation-delay:${-i * .37}s"></span>`));
  // 弧线（标题 / 人名）
  if (it.type === 'title' || it.type === 'name') {
    const r = 46, cx = right ? a.x - 20 : a.x + a.w + 30, cy = a.y + a.h / 2;
    add(back, `<span class="t4-arc" style="left:${cx}px;top:${cy}px">${api.svg(0, 0,
      `<path d="M ${-r} 0 A ${r} ${r} 0 1 1 ${r * .5} ${r * .87}" fill="none" stroke-width="5" stroke-linecap="round" style="stroke:rgba(var(--brand-light),.85);filter:drop-shadow(0 0 4px rgba(var(--brand),1))"/>`)}</span>`);
  }
};
