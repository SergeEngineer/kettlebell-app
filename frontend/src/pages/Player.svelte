<script lang="ts">
  import { onMount } from 'svelte';
  import { animate } from 'motion';
  import { DragGesture } from '@use-gesture/vanilla';
  import { api, fmt, media } from '../lib/api';
  import { ui, bump } from '../lib/state.svelte';
  import { createAwake } from '../lib/awake';

  let { id }: { id: number } = $props();

  interface Item { name: string; seconds: number; gif: string | null; kind: 'ready' | 'ex' | 'rest' }
  const R = 108, C = 2 * Math.PI * R;
  const READY: Item = { name: 'Get ready', seconds: 5, gif: null, kind: 'ready' };

  let title = $state(''), seq = $state<Item[]>([READY]), loadError = $state('');
  let began = $state(false), result = $state<null | 'complete' | 'ended'>(null), paused = $state(true);
  let i = $state(0), remain = $state(5000), total = $state(5000);
  let root: HTMLDivElement, stage: HTMLDivElement, nosleep: HTMLVideoElement, doneCard: HTMLDivElement | undefined = $state();

  let end = 0, lastSec = -1, ctx: AudioContext | null = null, logged = false;
  let awake: ReturnType<typeof createAwake>;

  const cur = $derived(seq[i]), next = $derived(seq[i + 1]);
  const stepCount = $derived(seq.length - 1);
  const pic = $derived(cur?.gif || (cur && cur.kind !== 'ex' && next?.gif) || null);
  const heading = $derived(cur?.kind === 'ready' && next ? next.name : cur?.name ?? title);
  const phase = $derived(cur?.kind === 'ex' ? 'Work' : cur?.kind === 'rest' ? 'Rest' : 'Get ready');
  const isIOSBrowser = /iPhone|iPad|iPod/.test(navigator.userAgent) && !(navigator as { standalone?: boolean }).standalone;

  function beep(f = 880, d = 0.12) {
    if (!ctx) return;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.value = f; g.gain.value = 0.25; o.connect(g); g.connect(ctx.destination);
    o.start(); o.stop(ctx.currentTime + d);
  }
  const enterFS = () => { const e = document.documentElement as any, f = e.requestFullscreen || e.webkitRequestFullscreen;
    try { f?.call(e)?.catch?.(() => {}); } catch { /* not supported */ } };
  const exitFS = () => { const d = document as any, f = d.exitFullscreen || d.webkitExitFullscreen;
    if (f && (d.fullscreenElement || d.webkitFullscreenElement)) try { f.call(d)?.catch?.(() => {}); } catch { /* ignore */ } };

  function load(k: number) {
    if (k >= seq.length) return finish(false);
    i = Math.max(0, k);
    total = remain = seq[i].seconds * 1000; end = Date.now() + remain; lastSec = -1;
    beep(seq[i].kind === 'ex' ? 1100 : 660, 0.3); navigator.vibrate?.(200);
  }
  function setPaused(p: boolean) { paused = p; if (!p) end = Date.now() + remain; }
  function logCompletion() {          // only a workout that ran all the way to the end counts for the calendar
    if (logged || !seq.some(s => s.kind === 'ex')) return; logged = true;
    const d = new Date();
    api.complete(id, `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`).catch(() => {});
  }
  function finish(natural: boolean) {
    paused = true; result = natural ? 'complete' : 'ended'; exitFS(); beep(1320, 0.5); awake.stop();
    if (natural) logCompletion();
  }
  function begin() {
    began = true; enterFS(); ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    awake.start(); load(0); setPaused(false);
  }
  function close() {
    exitFS(); awake.stop();
    animate(root, { y: [0, window.innerHeight], opacity: [1, 0.6] }, { type: 'spring', stiffness: 300, damping: 36 }).finished
      .then(() => { ui.player = null; bump(); });
  }
  const skip = () => { load(i + 1); };
  const prev = () => { load(i - 1); };

  $effect(() => { if (doneCard) animate(doneCard, { scale: [0.9, 1], opacity: [0, 1] }, { type: 'spring', stiffness: 420, damping: 26 }); });

  onMount(() => {
    awake = createAwake(nosleep);
    animate(root, { y: [window.innerHeight, 0] }, { type: 'spring', stiffness: 300, damping: 34 });
    api.program(id).then(p => {
      title = p.name;
      seq = [READY, ...p.steps.map(s => ({ name: s.name, seconds: s.seconds, gif: media(s.gif), kind: s.kind }))];
      total = remain = READY.seconds * 1000;
    }).catch(e => { loadError = (e as Error).message; });

    const timer = window.setInterval(() => {
      if (paused || result) return;
      remain = end - Date.now();
      if (remain <= 0) { if (i + 1 >= seq.length) finish(true); else load(i + 1); return; }
      const sec = Math.ceil(remain / 1000);
      if (sec <= 3 && sec !== lastSec) beep(880);
      lastSec = sec;
    }, 100);

    // Swipe left on the stage to skip, right to go back (the buttons do the same).
    const swipe = new DragGesture(stage, ({ swipe: [sx] }) => {
      if (!began || result || !sx) return;
      sx < 0 ? skip() : prev();
    }, { filterTaps: true, axis: 'x' });

    return () => { clearInterval(timer); swipe.destroy(); awake?.stop(); exitFS(); };
  });
</script>

<div class="player" bind:this={root} data-kind={cur?.kind ?? 'ready'}>
  <div class="stage" bind:this={stage}>
    <div class="top">
      <button class="circ" aria-label="Close player" onclick={close}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
      </button>
      <div><strong>{title}</strong><small>{i === 0 ? 'Get ready' : `Step ${i} of ${stepCount}`}</small></div>
    </div>

    <div class="ring">
      <svg viewBox="0 0 240 240" aria-hidden="true">
        <circle class="bg" cx="120" cy="120" r={R} />
        <circle class="fg" cx="120" cy="120" r={R} stroke-dasharray={C} stroke-dashoffset={C * (1 - remain / total)} />
      </svg>
      <div class="ringtxt"><div class="time" aria-live="off">{fmt(Math.ceil(remain / 1000))}</div><div class="phase">{phase}</div></div>
    </div>

    <div class="name"><h2>{heading}</h2><small>{next ? `Next: ${next.name} · ${fmt(next.seconds)}` : cur?.kind === 'ready' ? '' : 'Last one'}</small></div>
    <div class="media">{#if pic}<img src={pic} alt="" />{/if}</div>
    <div class="spacer"></div>

    <div class="ctrl">
      <button aria-label="Previous step" onclick={prev}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M11 6l-6 6 6 6" /></svg></button>
      <button class="big" aria-label={paused ? 'Resume' : 'Pause'} onclick={() => setPaused(!paused)}>
        {#if paused}<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
        {:else}<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>{/if}
      </button>
      <button aria-label="Skip step" onclick={skip}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg></button>
    </div>
  </div>

  <video bind:this={nosleep} src="/static/nosleep.mp4" loop muted playsinline class="nosleep"></video>

  {#if !began && !result}
    <div class="overlay">
      {#if loadError}<p class="hint">{loadError}</p><button class="startbtn" onclick={close}>Back</button>
      {:else}
        <button class="startbtn" onclick={begin} disabled={seq.length < 2}>Tap to begin</button>
        {#if !window.isSecureContext || !navigator.wakeLock}
          <p class="hint">Keeping the screen awake needs HTTPS. Without it your iPhone can still dim and lock: set Settings → Display &amp; Brightness → Auto-Lock → Never (and turn off Low Power Mode).</p>
        {/if}
        {#if isIOSBrowser}<p class="hint">For true full screen on iPhone: tap Share → Add to Home Screen, then open Kettlebell from your Home Screen.</p>{/if}
      {/if}
    </div>
  {/if}
  {#if result}
    <div class="overlay">
      <div bind:this={doneCard} class="donecard">
        <h1>{result === 'complete' ? 'Workout complete' : 'Workout ended'}</h1>
        <button class="startbtn" onclick={close}>Done</button>
      </div>
    </div>
  {/if}
</div>
