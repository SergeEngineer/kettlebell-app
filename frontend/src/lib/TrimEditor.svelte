<script lang="ts">
  import { untrack } from 'svelte';
  import RangeSlider from './RangeSlider.svelte';
  import type { GifInfo } from '../types';

  // A GIF cannot be seeked in the browser, so its timing comes from ffprobe and
  // the two sliders mark the frames to keep.  The server re-encodes the file.
  let { src, info, busy = false, onapply, oncancel }: {
    src: string; info: GifInfo; busy?: boolean;
    onapply: (start: number, end: number) => void; oncancel: () => void;
  } = $props();

  const frame = $derived(1 / Math.max(1, info.fps || 12));
  const minLength = $derived(Math.max(0.25, frame));
  let start = $state(0);
  let end = $state(untrack(() => info.duration));

  const t = (x: number) => `${Math.floor(x / 60)}:${(x % 60).toFixed(2).padStart(5, '0')}`;
  const pct = (x: number) => info.duration ? Math.max(0, Math.min(100, (x / info.duration) * 100)) : 0;

  function setRange(which: 'start' | 'end', value: number) {
    if (which === 'start') start = Math.max(0, Math.min(value, end - minLength));
    else end = Math.min(info.duration, Math.max(value, start + minLength));
  }
  function reset() { start = 0; end = info.duration; }
</script>

<div class="trim-stage"><img class="trim-media" {src} alt="GIF to trim"></div>

<div class="trim-timeline" aria-hidden="true">
  <span class="trim-kept" style={`left:${pct(start)}%;width:${Math.max(0, pct(end) - pct(start))}%`}></span>
</div>

<div class="list inset-strong form-list"><ul>
  <li class="item-content"><div class="item-inner">
    <RangeSlider id="trim-start" label="Start" text={t(start)} value={start} min={0} max={info.duration}
                 step={frame} onValue={(v) => setRange('start', v)} />
  </div></li>
  <li class="item-content"><div class="item-inner">
    <RangeSlider id="trim-end" label="End" text={t(end)} value={end} min={0} max={info.duration}
                 step={frame} onValue={(v) => setRange('end', v)} />
  </div></li>
</ul></div>
<p class="help">Keeping {(end - start).toFixed(2)} s of {info.duration.toFixed(2)} s.</p>

<div class="crop-actions">
  <button type="button" class="button button-round" onclick={reset} disabled={busy}>Reset</button>
  <button type="button" class="button button-round" onclick={oncancel} disabled={busy}>Cancel</button>
  <button type="button" class="button button-fill button-round" onclick={() => onapply(start, end)} disabled={busy}>
    {busy ? 'Trimming…' : 'Trim GIF'}
  </button>
</div>
