<script lang="ts">
  import { onDestroy, onMount, untrack } from 'svelte';
  import { api } from '../lib/api';
  import RangeSlider from './RangeSlider.svelte';
  import type { GifInfo } from '../types';

  // A GIF cannot be seeked in the browser. The server sends the exact frame at
  // each slider time, so the previews show precisely where the cut will land.
  let { id, src, info, busy = false, onapply, oncancel }: {
    id: number; src: string; info: GifInfo; busy?: boolean;
    onapply: (start: number, end: number) => void; oncancel: () => void;
  } = $props();

  type Handle = 'start' | 'end';

  const frame = $derived(1 / Math.max(1, info.fps || 12));
  const minLength = $derived(Math.max(0.25, frame));
  let start = $state(0);
  let end = $state(untrack(() => info.duration));
  let active = $state<Handle>('start');
  let frames = $state<Record<Handle, string>>({ start: '', end: '' });

  let urls: Record<Handle, string> = { start: '', end: '' };
  let timers: Partial<Record<Handle, ReturnType<typeof setTimeout>>> = {};
  let pending: Record<Handle, number | null> = { start: null, end: null };
  let seq: Record<Handle, number> = { start: 0, end: 0 };
  let alive = true;

  const t = (x: number) => `${Math.floor(x / 60)}:${(x % 60).toFixed(2).padStart(5, '0')}`;
  const pct = (x: number) => info.duration ? Math.max(0, Math.min(100, (x / info.duration) * 100)) : 0;
  const totalFrames = $derived(Math.max(1, Math.round(info.duration * (info.fps || 12))));
  const frameNo = (x: number) => Math.min(totalFrames, Math.floor(x * (info.fps || 12) + 0.0001) + 1);

  async function loadFrame(which: Handle, at: number) {
    const mine = ++seq[which];
    try {
      const url = await api.gifFrame(id, at);
      if (!alive || mine !== seq[which]) { URL.revokeObjectURL(url); return; }
      if (urls[which]) URL.revokeObjectURL(urls[which]);
      urls[which] = url;
      frames = { ...frames, [which]: url };
    } catch {
      // Keep the last good preview (or the animated GIF fallback).
    }
  }

  // Throttle scrubbing to ~11 previews/second, but always send the latest time.
  function scheduleFrame(which: Handle, at: number) {
    pending[which] = at;
    if (timers[which]) return;
    void loadFrame(which, at);
    timers[which] = setTimeout(() => {
      timers[which] = undefined;
      const next = pending[which];
      pending[which] = null;
      if (next !== null && Math.abs(next - at) > 0.0001) scheduleFrame(which, next);
    }, 90);
  }

  function setRange(which: Handle, value: number) {
    const at = which === 'start'
      ? (start = Math.max(0, Math.min(value, end - minLength)))
      : (end = Math.min(info.duration, Math.max(value, start + minLength)));
    active = which;
    scheduleFrame(which, at);
  }
  function reset() {
    start = 0; end = info.duration; active = 'start';
    scheduleFrame('start', start);
    scheduleFrame('end', end);
  }

  onMount(() => {
    scheduleFrame('start', start);
    scheduleFrame('end', end);
  });
  onDestroy(() => {
    alive = false;
    for (const which of ['start', 'end'] as Handle[]) {
      clearTimeout(timers[which]);
      if (urls[which]) URL.revokeObjectURL(urls[which]);
    }
  });
</script>

<div class="trim-stages">
  <figure class="trim-frame" class:active={active === 'start'}>
    <img src={frames.start || src} alt="Exact frame at the start cut" />
    <figcaption>
      <span>Start cut · {t(start)}</span>
      <small>frame {frameNo(start)}</small>
    </figcaption>
  </figure>
  <figure class="trim-frame" class:active={active === 'end'}>
    <img src={frames.end || src} alt="Exact frame at the end cut" />
    <figcaption>
      <span>End cut · {t(end)}</span>
      <small>frame {frameNo(end)}</small>
    </figcaption>
  </figure>
</div>

<div class="trim-timeline" aria-hidden="true">
  <span class="trim-kept" style={`left:${pct(start)}%;width:${Math.max(0, pct(end) - pct(start))}%`}></span>
</div>

<div class="list inset-strong form-list"><ul>
  <li class="item-content" class:trim-active={active === 'start'}><div class="item-inner">
    <RangeSlider id="trim-start" label="Start" text={t(start)} value={start} min={0} max={info.duration}
                 step={frame} onValue={(v) => setRange('start', v)} />
  </div></li>
  <li class="item-content" class:trim-active={active === 'end'}><div class="item-inner">
    <RangeSlider id="trim-end" label="End" text={t(end)} value={end} min={0} max={info.duration}
                 step={frame} onValue={(v) => setRange('end', v)} />
  </div></li>
</ul></div>
<p class="help">Cutting from <strong>{t(start)}</strong> to <strong>{t(end)}</strong> · keeping {(end - start).toFixed(2)} s of {info.duration.toFixed(2)} s ({totalFrames} frames).</p>

<div class="crop-actions">
  <button type="button" class="button button-round" onclick={reset} disabled={busy}>Reset</button>
  <button type="button" class="button button-round" onclick={oncancel} disabled={busy}>Cancel</button>
  <button type="button" class="button button-fill button-round" onclick={() => onapply(start, end)} disabled={busy}>
    {busy ? 'Trimming…' : 'Trim GIF'}
  </button>
</div>
