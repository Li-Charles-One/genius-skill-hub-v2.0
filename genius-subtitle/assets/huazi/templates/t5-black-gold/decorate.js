// 模板 5 · 黑金质感：第一行身后的描边虚字、底部金色光线、光斑、尾点
window.HZ_DECORATE = function (el, it, api) {
  const back = el.querySelector('.hz-back'), front = el.querySelector('.hz-front');
  const l1 = el.querySelector('.hz-line'); if (!l1) return;
  const a = api.rel(l1), W = el.offsetWidth, H = el.offsetHeight;
  const right = it.align === 'right', center = it.align === 'center';
  const add = (host, html) => host.insertAdjacentHTML('beforeend', html);
  const f = it.fields || {};
  const ghost = (f.ghost || (f.lines || [])[0] || f.name || '').replace(/[{}]/g, '');
  if (ghost) {
    const pos = right ? `right:${W - a.x - a.w + 26}px` : center ? `left:${a.x - 30}px` : `left:${a.x + 26}px`;
    add(back, `<span class="t5-ghost" style="${pos};top:${a.y - 30}px">${ghost.replace(/</g, '&lt;')}</span>`);
  }
  const lw = Math.min(W * .8, 460), lx = center ? (W - lw) / 2 : right ? W - lw - 20 : 30;
  add(front, `<span class="t5-line" style="left:${lx}px;width:${lw}px;top:${H - 10}px"></span>`);
  add(front, `<span class="t5-flare" style="left:${lx + lw * (right ? .35 : .65)}px;top:${H - 9}px"></span>`);
  add(front, `<span class="t5-dots" style="left:${right ? lx - 10 : lx + lw - 24}px;top:${H - 2}px"></span>`);
};
