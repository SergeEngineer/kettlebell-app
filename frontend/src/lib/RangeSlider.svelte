<script lang="ts">
  // A small controlled range control.  Native range inputs behave differently
  // across mobile browsers (especially inside Framework7 popups) and could
  // shift their thumb when the surrounding form was touched.  This keeps the
  // value entirely in app state.
  let {
    id,
    label,
    text,
    value,
    min = 0,
    max = 1,
    step = 0.01,
    onValue
  }: {
    id: string;
    label: string;
    text: string;
    value: number;
    min?: number;
    max?: number;
    step?: number;
    onValue: (value: number) => void;
  } = $props();

  let track: HTMLDivElement | undefined = $state();
  let dragging = $state(false);

  const span = $derived(Math.max(0.000001, max - min));
  const pct = $derived(Math.max(0, Math.min(100, ((value - min) / span) * 100)));

  function setFromPointer(clientX: number) {
    if (!track) return;
    const rect = track.getBoundingClientRect();
    if (!rect.width) return;
    const fraction = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const raw = min + fraction * span;
    const snapped = Math.round(raw / step) * step;
    onValue(Math.max(min, Math.min(max, Number(snapped.toFixed(6)))));
  }

  function down(e: PointerEvent) {
    e.preventDefault();
    dragging = true;
    track?.setPointerCapture(e.pointerId);
    setFromPointer(e.clientX);
  }
  function move(e: PointerEvent) {
    if (dragging) setFromPointer(e.clientX);
  }
  function up(e: PointerEvent) {
    if (!dragging) return;
    dragging = false;
    if (track?.hasPointerCapture(e.pointerId)) track.releasePointerCapture(e.pointerId);
  }
  function keydown(e: KeyboardEvent) {
    const big = Math.max(step, 0.5);
    let next: number | null = null;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') next = value - step;
    else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') next = value + step;
    else if (e.key === 'PageDown') next = value - big;
    else if (e.key === 'PageUp') next = value + big;
    else if (e.key === 'Home') next = min;
    else if (e.key === 'End') next = max;
    if (next === null) return;
    e.preventDefault();
    onValue(Math.max(min, Math.min(max, Number(next.toFixed(6)))));
  }
</script>

<div class="sliderrow">
  <div class="slider-label"><span>{label}</span><output>{text}</output></div>
  <div id={id} bind:this={track} class="kb-range" class:dragging role="slider" tabindex="0"
       aria-label={label} aria-valuemin={min} aria-valuemax={max} aria-valuenow={value} aria-valuetext={text}
       onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up}
       onkeydown={keydown}>
    <div class="kb-range-track"></div>
    <div class="kb-range-fill" style:width="{pct}%"></div>
    <div class="kb-range-thumb" style:left="{pct}%"></div>
  </div>
</div>
