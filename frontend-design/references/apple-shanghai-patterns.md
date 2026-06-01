# Apple-Style / Shanghai Ad Agency Patterns

Proven patterns from building Charles' web resume (2026-05-04).
Aesthetic: pure black + blue accent, Apple-like restraint, Shanghai ad agency feel.

## Font Pairing (Proven)
- **All text**: Noto Sans SC (clean geometric sans-serif)
- Weight 700 for headings, 500 for nav/buttons, 300 for body
- Import: Google Fonts `@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@100;300;400;500;700&display=swap')`

## Color System (Proven)
```css
--bg: #000000;           /* pure black */
--bg-card: #0a0a0f;      /* near-black for card sections */
--text: #f5f5f7;          /* Apple-style off-white */
--text-muted: #6e6e73;    /* Apple gray */
--blue: #2997ff;          /* Apple blue accent */
--blue-dim: rgba(41, 151, 255, 0.08); /* subtle blue background */
```

## CSS Patterns

### 1. Frosted Glass Nav
```css
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  padding: 0 48px; height: 56px;
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(0,0,0,0.72);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
```

### 2. Spinner Loader (minimal)
```css
.loader-ring {
  width: 32px; height: 32px;
  border: 2px solid var(--text-muted);
  border-top-color: var(--blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

### 3. Card Hover Lift
```css
.phil-card {
  padding: 48px 36px; border-radius: 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  transition: all 0.4s var(--ease);
}
.phil-card:hover {
  background: var(--blue-dim);
  border-color: rgba(41,151,255,0.2);
  transform: translateY(-4px);
}
```

### 4. Pill Button
```css
.portfolio-btn {
  display: inline-block; font-size: 14px; font-weight: 500;
  color: var(--bg); background: var(--blue); text-decoration: none;
  padding: 14px 40px; border-radius: 980px;
  transition: all 0.3s var(--ease);
}
.portfolio-btn:hover {
  background: #1d8af0; transform: scale(1.02);
}
```

### 5. Contact Link Buttons
```css
.contact-links a {
  font-size: 13px; color: var(--blue); text-decoration: none;
  padding: 10px 28px;
  border: 1px solid rgba(41,151,255,0.3);
  border-radius: 980px;
  transition: all 0.3s; font-weight: 400;
}
.contact-links a:hover {
  background: var(--blue); color: var(--bg);
}
```

### 6. Accordion Expand
```css
.cap-desc {
  max-height: 0; overflow: hidden;
  transition: max-height 0.5s var(--ease), padding 0.3s;
  padding-left: 40px;
}
.cap-item.expanded .cap-desc {
  max-height: 300px; padding-top: 16px; padding-bottom: 8px;
}
```

### 7. Scroll Reveal (lighter than cinema version)
```css
.reveal {
  opacity: 0; transform: translateY(24px);
  transition: opacity 0.8s var(--ease), transform 0.8s var(--ease);
}
.reveal.visible { opacity: 1; transform: translateY(0); }
```

## Key Differences from Cinema-Grade Version
| Element | Cinema-Grade | Apple/Shanghai |
|---------|-------------|----------------|
| Background | #0a0a0a (warm black) | #000000 (pure black) |
| Accent | #c4a87c (warm gold) | #2997ff (Apple blue) |
| Typography | Serif (Cormorant) | Sans-serif (Noto Sans SC) |
| Cursor | Custom circle + dot | Default system cursor |
| Nav | mix-blend-mode | Frosted glass blur |
| Loader | Progress line | Spinner ring |
| Buttons | Border + fill animation | Solid pill, hover scale |
| Motion | Parallax + noise overlay | Restrained scroll reveal |
| Cards | Border on hover | Lift + blue tint |

## Responsive
- Desktop: max-width 1120px centered, multi-column
- Mobile (< 768px): single column, hide nav links, adjusted padding
