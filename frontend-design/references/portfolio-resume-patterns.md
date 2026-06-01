# High-End Portfolio / Resume Page Patterns

Proven patterns from building Charles' Director & AIGCer web resume (2026-05-04).
Aesthetic: dark minimalist, cinema-grade, luxury/editorial feel.

## Font Pairing (Proven)
- **Display/Headings**: Cormorant Garamond (serif, italic for accents)
- **Body/Nav**: Space Grotesk (sans-serif, uppercase + wide tracking for nav)
- **Chinese**: Noto Serif SC (matches Cormorant'"'"'s elegance)
- Import: Google Fonts `@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@200;300;400;600;700&family=Space+Grotesk:wght@300;400;500;600;700&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&display=swap')`

## Color System (Proven)
```css
--bg: #0a0a0a;           /* near-black, not pure black */
--bg-warm: #0f0e0d;      /* slightly warm for section alternation */
--text: #e8e4df;          /* warm off-white, not pure white */
--text-muted: #8a8580;    /* muted for secondary text */
--accent: #c4a87c;        /* warm gold, used sparingly */
--accent-dim: rgba(196, 168, 124, 0.15); /* for subtle backgrounds */
```

## CSS Animation Patterns

### 1. Custom Cursor (mix-blend-mode difference)
```css
.cursor {
  position: fixed; width: 20px; height: 20px;
  border: 1px solid var(--accent); border-radius: 50%;
  pointer-events: none; z-index: 9999;
  transition: transform 0.15s var(--ease), opacity 0.3s;
  mix-blend-mode: difference;
}
.cursor.active { transform: scale(2.5); opacity: 0.5; }
.cursor-dot {
  position: fixed; width: 4px; height: 4px;
  background: var(--accent); border-radius: 50%;
  pointer-events: none; z-index: 9999;
}
/* JS: dot follows mouse instantly, cursor ring follows with lerp */
```

### 2. Scroll-Triggered Reveal (Intersection Observer)
```css
.reveal {
  opacity: 0; transform: translateY(40px);
  transition: all 0.9s var(--ease);
}
.reveal.visible { opacity: 1; transform: translateY(0); }
```
```js
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) entry.target.classList.add('visible');
  });
}, { threshold: 0.15, rootMargin: '0px 0px -60px 0px' });
document.querySelectorAll('.reveal, .stagger').forEach(el => observer.observe(el));
```

### 3. Staggered Children Reveal
```css
.stagger > * {
  opacity: 0; transform: translateY(30px);
  transition: all 0.7s var(--ease);
}
.stagger.visible > *:nth-child(1) { transition-delay: 0s; }
.stagger.visible > *:nth-child(2) { transition-delay: 0.1s; }
.stagger.visible > *:nth-child(3) { transition-delay: 0.2s; }
.stagger.visible > *:nth-child(4) { transition-delay: 0.3s; }
.stagger.visible > * { opacity: 1; transform: translateY(0); }
```

### 4. Loading Screen with Progress Line
```css
.loader { position: fixed; inset: 0; background: var(--bg); z-index: 10000;
  display: flex; align-items: center; justify-content: center; flex-direction: column; }
.loader-line { width: 120px; height: 1px; background: var(--text-muted);
  position: relative; overflow: hidden; }
.loader-line::after { content: ''; position: absolute; left: 0; top: 0;
  height: 100%; width: 0; background: var(--accent);
  animation: loadProgress 1.8s var(--ease) forwards; }
@keyframes loadProgress { to { width: 100%; } }
```

### 5. Button Fill Animation (scaleX from edge)
```css
.cta-btn { position: relative; overflow: hidden; /* ... */ }
.cta-btn::before { content: ''; position: absolute; inset: 0;
  background: var(--accent); transform: scaleX(0); transform-origin: right;
  transition: transform 0.5s var(--ease); z-index: -1; }
.cta-btn:hover { color: var(--bg); }
.cta-btn:hover::before { transform: scaleX(1); transform-origin: left; }
```

### 6. Parallax Hero (scroll-driven)
```js
window.addEventListener('scroll', () => {
  const scrolled = window.pageYOffset;
  hero.style.transform = `translateY(${scrolled * 0.15}px)`;
  hero.style.opacity = 1 - scrolled / 800;
});
```

### 7. Noise Texture Overlay (SVG-based)
```css
body::before {
  content: ''; position: fixed; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none; z-index: 1000;
}
```

### 8. Capabilities Accordion (click expand)
```css
.cap-desc { max-height: 0; overflow: hidden;
  transition: max-height 0.6s var(--ease), margin 0.4s; }
.cap-item.expanded .cap-desc { max-height: 200px; margin-top: 16px; }
```

## Easing
All animations use: `cubic-bezier(0.22, 1, 0.36, 1)` — fast start, slow finish, feels premium.

## Layout Patterns
- **Hero**: full viewport height, centered content, scroll indicator at bottom
- **About**: 2-column grid (portrait left, text right), asymmetric balance
- **Philosophy**: 3-column card grid with subtle borders
- **Capabilities**: vertical list with numbers, titles, arrows, expandable descriptions
- **Contact**: centered, minimal, with CTA button

## Pitfalls
- `mix-blend-mode: difference` on cursor won'"'"'t work on all backgrounds — test on both dark and light sections
- `IntersectionObserver` threshold 0.15 with rootMargin `-60px` bottom works well for most section heights
- Loading screen needs `pointer-events: none` after fade-out to not block interactions
- Mobile: hide custom cursor (`display: none`), set `body { cursor: auto }`
- Chinese font loading: Noto Serif SC is large, consider `font-display: swap` or preload

## Responsive Breakpoints
- Desktop: full layout, custom cursor, multi-column grids
- Mobile (< 768px): single column, hide cursor, simplified nav, adjusted padding
