<script lang="ts">
  import { onDestroy, untrack } from 'svelte';
  import type { Crop } from '../types';

  let { src, kind, frameTime = 0, initial = null, busy = false, onapply, oncancel }: {
    src: string; kind: 'video' | 'image'; frameTime?: number; initial?: Crop | null;
    busy?: boolean; onapply: (crop: Crop) => void; oncancel: () => void;
  } = $props();

  type Mode = 'move' | 'nw' | 'ne' | 'sw' | 'se';

  const MIN = 0.08;
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

  const startCrop = untrack(() => initial);
  let crop = $state<Crop>(startCrop ? { ...startCrop } : { x: 0, y: 0, w: 1, h: 1 });
  let wrap: HTMLDivElement | undefined = $state();
  let drag: { mode: Mode; startX: number; startY: number; orig: Crop } | null = null;

  const wholeFrame = $derived(crop.x <= 0.001 && crop.y <= 0.001 && crop.w >= 0.999 && crop.h >= 0.999);
  const pct = (v: number) => `${Math.round(v * 100)}%`;

  function begin(event: PointerEvent, mode: Mode) {
    if (busy) return;
    event.preventDefault();
    event.stopPropagation();
    drag = { mode, startX: event.clientX, startY: event.clientY, orig: { ...crop } };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', stop, { once: true });
    window.addEventListener('pointercancel', stop, { once: true });
  }

  function onMove(event: PointerEvent) {
    if (!drag || !wrap) return;
    event.preventDefault();
    const rect = wrap.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dx = (event.clientX - drag.startX) / rect.width;
    const dy = (event.clientY - drag.startY) / rect.height;
    const o = drag.orig;
    let { x, y, w, h } = o;
    if (drag.mode === 'move') {
      x = clamp(o.x + dx, 0, 1 - o.w);
      y = clamp(o.y + dy, 0, 1 - o.h);
    } else {
      if (drag.mode.includes('w')) {
        const right = o.x + o.w;
        x = clamp(o.x + dx, 0, right - MIN);
        w = right - x;
      }
      if (drag.mode.includes('e')) w = clamp(o.w + dx, MIN, 1 - o.x);
      if (drag.mode.includes('n')) {
        const bottom = o.y + o.h;
        y = clamp(o.y + dy, 0, bottom - MIN);
        h = bottom - y;
      }
      if (drag.mode.includes('s')) h = clamp(o.h + dy, MIN, 1 - o.y);
    }
    crop = { x, y, w, h };
  }

  function stop() {
    drag = null;
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', stop);
    window.removeEventListener('pointercancel', stop);
  }
  onDestroy(stop);

  function reset() {
    crop = { x: 0, y: 0, w: 1, h: 1 };
  }
</script>

<div class="crop-stage">
  <div class="crop-wrap" bind:this={wrap} role="group" aria-label="Crop area"
       ontouchstart={(e) => e.stopPropagation()} ontouchmove={(e) => e.stopPropagation()}>
    {#if kind === 'video'}
      <video class="crop-media" {src} muted playsinline preload="auto" autoplay loop
             onloadedmetadata={(e) => {
               const v = e.currentTarget;
               try {
                 v.currentTime = Math.max(0, Math.min(frameTime, v.duration || frameTime));
                 void v.play().catch(() => { /* autoplay can be blocked, the frame still shows */ });
               } catch { /* ignore */ }
             }}></video>
    {:else}
      <img class="crop-media" {src} alt="Crop preview">
    {/if}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="crop-box" style={`left:${crop.x * 100}%;top:${crop.y * 100}%;width:${crop.w * 100}%;height:${crop.h * 100}%`}
         onpointerdown={(e) => begin(e, 'move')}>
      <button type="button" class="crop-handle nw" aria-label="Crop top left" onpointerdown={(e) => begin(e, 'nw')}></button>
      <button type="button" class="crop-handle ne" aria-label="Crop top right" onpointerdown={(e) => begin(e, 'ne')}></button>
      <button type="button" class="crop-handle sw" aria-label="Crop bottom left" onpointerdown={(e) => begin(e, 'sw')}></button>
      <button type="button" class="crop-handle se" aria-label="Crop bottom right" onpointerdown={(e) => begin(e, 'se')}></button>
    </div>
  </div>
</div>

<p class="help crop-hint">
  Drag the box or its corners to choose the part to keep. Keeping {pct(crop.w)} × {pct(crop.h)} of the frame.
</p>

<div class="crop-actions">
  <button type="button" class="button button-round" onclick={reset} disabled={busy}>Reset</button>
  <button type="button" class="button button-round" onclick={oncancel} disabled={busy}>Cancel</button>
  <button type="button" class="button button-fill button-round" onclick={() => onapply(crop)} disabled={busy || wholeFrame}>
    {busy ? 'Cropping…' : 'Use crop'}
  </button>
</div>
