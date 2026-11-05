// 模板 1 · 光带科技：按主行的位置摆装饰（× 标记、条码短线、小晶块、端头光斑、椭圆轨道光点 / HUD 圆环）
window.HZ_DECORATE = function (el, it, api) {
  const front = el.querySelector('.hz-front'), back = el.querySelector('.hz-back');
  const l1 = el.querySelector('.hz-l1'), lines = el.querySelectorAll('.hz-line');
  const last = lines[lines.length - 1], sub = el.querySelector('.hz-sub') || el.querySelector('.hz-items');
  if (!l1) return;
  const right = it.align === 'right', center = it.align === 'center';
  const a = api.rel(l1), z = api.rel(last);
  const add = (host, html) => host.insertAdjacentHTML('beforeend', html);

  // × 标记：主行上方外侧
  add(front, `<span class="t1-x" style="left:${right ? a.x - 6 : a.x + a.w - 4}px;top:${a.y - 16}px">×</span>`);
  // 小晶块：方块外侧
  add(front, `<span class="t1-gem" style="left:${right ? a.x - 74 : a.x + a.w + 52}px;top:${a.y + 6}px"></span>`);
  // 端头光斑：最后一行光带的外端
  const fx = center ? z.x + z.w + 40 : right ? z.x - 20 : z.x + z.w + 30;
  add(front, `<span class="t1-flare" style="left:${fx}px;top:${z.y + z.h - 2}px"></span>`);
  if (center) add(front, `<span class="t1-flare" style="left:${a.x - 40}px;top:${a.y + a.h - 2}px;animation-delay:-1.2s"></span>`);
  // 条码短线：副标题（或最后一行）下方外侧
  if (sub) {
    const s = api.rel(sub);
    add(front, `<span class="t1-code" style="left:${right ? s.x : s.x + s.w - 64}px;top:${s.y + s.h + 8}px"></span>`);
  }

  // 标题型：一圈斜椭圆轨道 + 跑动光点；两行 / 数字型：外侧 HUD 圆环
  if (it.type === 'title' || it.type === 'name') {
    const w = Math.min(320, a.w * .7), h = 120, cx = right ? a.x + a.w - w / 2 - 20 : a.x + w / 2 + 20, cy = a.y + a.h / 2;
    const rx = w / 2, ry = h / 2;
    const path = `M${-rx},0 a${rx},${ry} 0 1,0 ${2 * rx},0 a${rx},${ry} 0 1,0 ${-2 * rx},0`;
    add(back, `<div style="position:absolute;left:${cx}px;top:${cy}px;transform:rotate(-24deg)">${api.svg(0, 0,
      `<path d="${path}" fill="none" stroke="rgba(255,255,255,.5)" stroke-width="1"/>
       <circle r="3.2" fill="#fff" style="filter:drop-shadow(0 0 4px #fff)"><animateMotion dur="5s" repeatCount="indefinite" path="${path}"/></circle>`)}</div>`);
  } else if (it.type === 'stack' || it.type === 'number' || it.type === 'list') {
    const r = 64, cx = center ? a.x - 70 : right ? a.x + a.w + 40 : a.x - 30, cy = a.y + a.h + 6;
    const ticks = Array.from({ length: 48 }, (_, i) => {
      const t = i / 48 * Math.PI * 2, r1 = r - 6, r2 = i % 4 ? r - 2 : r + 2;
      return `<line x1="${Math.cos(t) * r1}" y1="${Math.sin(t) * r1}" x2="${Math.cos(t) * r2}" y2="${Math.sin(t) * r2}"/>`;
    }).join('');
    add(back, `<div style="position:absolute;left:${cx}px;top:${cy}px">${api.svg(0, 0,
      `<g stroke="rgba(255,255,255,.55)" stroke-width="1" fill="none">
         <g class="t1-spin">${ticks}</g>
         <g class="t1-spin rev"><circle r="${r + 12}" stroke-dasharray="60 18 8 18" stroke="rgba(255,255,255,.4)"/></g>
         <circle r="${r - 18}" style="stroke:rgba(var(--brand-light),.6)"/>
         <line x1="${-r - 40}" y1="0" x2="${r + 40}" y2="0" stroke="rgba(255,255,255,.3)"/>
         <line x1="0" y1="${-r - 40}" x2="0" y2="${r + 40}" stroke="rgba(255,255,255,.3)"/>
       </g>`)}</div>`);
  }
};
