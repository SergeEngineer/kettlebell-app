import { DragGesture } from '@use-gesture/vanilla';
import { animate } from 'motion';

/**
 * Drag-to-reorder for rows in a list, driven by a grip handle.
 * - @use-gesture/vanilla tracks the finger (the handle has touch-action: none, so the page never scrolls).
 * - Motion springs animate the rows that get out of the way and the dragged row settling into place.
 * - Dragging near the top/bottom edge scrolls the page so rows beyond the viewport can be reached.
 * Rows are the <li> elements that contain a `[data-grip]` handle; the handle's data-grip holds the row id.
 */
const SPRING = { type: 'spring', stiffness: 520, damping: 42 } as const;
const EDGE_TOP = 150, EDGE_BOTTOM = 90, MAX_SPEED = 16;
interface Opts { onCommit: (ids: number[]) => void; disabled?: boolean }

export function grip(handle: HTMLElement, opts: Opts) {
  let o = opts;
  const state = new Map<HTMLElement, { y: number; stop?: () => void }>();
  let items: HTMLElement[] = [], rects: DOMRect[] = [], from = 0, to = 0, li: HTMLElement | null = null;
  let my = 0, pointerY = 0, scrollDelta = 0, scroller: HTMLElement | null = null, raf = 0;

  const rowsOf = (row: HTMLElement) =>
    [...(row.parentElement?.children ?? [])].filter((c): c is HTMLElement => c instanceof HTMLElement && !!c.querySelector('[data-grip]'));
  const idOf = (row: HTMLElement) => +(row.querySelector<HTMLElement>('[data-grip]')!.dataset.grip!);
  const paint = (el: HTMLElement, y: number) => { el.style.transform = y ? `translateY(${y}px)` : ''; };
  const place = (el: HTMLElement, y: number) => {          // jump, no animation
    const s = state.get(el) ?? { y: 0 }; s.stop?.(); s.y = y; state.set(el, s); paint(el, y);
  };
  const spring = (el: HTMLElement, target: number) => {     // animate from wherever the row currently is
    const s = state.get(el) ?? { y: 0 }; s.stop?.();
    const c = animate(s.y, target, { ...SPRING, onUpdate: (v: number) => { s.y = v; paint(el, v); } });
    s.stop = () => c.stop(); state.set(el, s);
    return c;
  };
  const reset = () => { items.forEach(el => { place(el, 0); el.style.zIndex = ''; el.classList.remove('lifting'); }); state.clear(); };

  const scrollParent = (row: HTMLElement) => {
    for (let el = row.parentElement; el; el = el.parentElement) {
      const style = getComputedStyle(el);
      if (/(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight) return el;
    }
    return null;
  };

  // Recompute the dragged row and the hovered slot from the finger position plus any edge scrolling.
  const apply = () => {
    if (!li) return;
    const h = rects[from].height;
    // The dragged row and the list shift together while scrolling, so travel limits stay constant.
    const top = rects[0].top - rects[from].top;
    const bottom = rects[rects.length - 1].bottom - rects[from].bottom;
    const y = Math.max(top, Math.min(my + scrollDelta, bottom));
    place(li, y);
    const centre = rects[from].top - scrollDelta + h / 2 + y;
    let t = items.length - 1;
    for (let i = 0; i < rects.length; i++) if (centre < rects[i].top - scrollDelta + rects[i].height) { t = i; break; }
    if (t !== to) {
      to = t;
      items.forEach((el, i) => {
        if (i === from) return;
        spring(el, from < to && i > from && i <= to ? -h : from > to && i >= to && i < from ? h : 0);
      });
    }
  };

  const autoScroll = () => {
    if (!li || !scroller) { raf = 0; return; }
    const box = scroller.getBoundingClientRect();
    let speed = 0;
    if (pointerY < box.top + EDGE_TOP) {
      const d = Math.max(0, pointerY - box.top);
      speed = -Math.max(1, Math.round(MAX_SPEED * (1 - d / EDGE_TOP)));
    } else if (pointerY > box.bottom - EDGE_BOTTOM) {
      const d = Math.max(0, box.bottom - pointerY);
      speed = Math.max(1, Math.round(MAX_SPEED * (1 - d / EDGE_BOTTOM)));
    }
    if (speed) {
      const before = scroller.scrollTop;
      scroller.scrollTop = before + speed;
      const moved = scroller.scrollTop - before;
      if (moved) { scrollDelta += moved; apply(); }
    }
    raf = requestAnimationFrame(autoScroll);
  };
  const stopAuto = () => { if (raf) cancelAnimationFrame(raf); raf = 0; };

  const drag = new DragGesture(handle, ({ first, last, movement, xy }) => {
    if (o.disabled) return;
    my = movement[1]; pointerY = xy[1];
    if (first) {
      li = handle.closest('li');
      if (!li) return;
      items = rowsOf(li); rects = items.map(e => e.getBoundingClientRect());
      from = to = items.indexOf(li); scrollDelta = 0;
      li.classList.add('lifting'); li.style.zIndex = '5';
      navigator.vibrate?.(8);
      scroller = scrollParent(li);
      raf = requestAnimationFrame(autoScroll);
    }
    if (!li) return;
    if (!last) { apply(); return; }
    stopAuto();
    const settle = to > from ? rects[to].bottom - rects[from].bottom : to < from ? rects[to].top - rects[from].top : 0;
    const row = li; li = null;
    spring(row, settle).finished
      .then(() => new Promise(r => setTimeout(r, 60)))
      .then(() => {
        const ids = items.map(idOf); const [moved] = ids.splice(from, 1); ids.splice(to, 0, moved);
        const changed = to !== from;
        reset();
        if (changed) o.onCommit(ids);
      });
  }, { filterTaps: true });

  const onKey = (e: KeyboardEvent) => {
    if (o.disabled || (e.key !== 'ArrowUp' && e.key !== 'ArrowDown')) return;
    const row = handle.closest('li'); if (!row) return;
    const list = rowsOf(row), i = list.indexOf(row), j = i + (e.key === 'ArrowUp' ? -1 : 1);
    if (j < 0 || j >= list.length) return;
    e.preventDefault();
    const ids = list.map(idOf); [ids[i], ids[j]] = [ids[j], ids[i]];
    o.onCommit(ids);
    requestAnimationFrame(() => document.querySelector<HTMLElement>(`[data-grip="${idOf(row)}"]`)?.focus());
  };
  handle.addEventListener('keydown', onKey);

  return {
    update(next: Opts) { o = next; },
    destroy() { stopAuto(); drag.destroy(); handle.removeEventListener('keydown', onKey); },
  };
}
