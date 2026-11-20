<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import { f7 } from 'framework7-svelte';

  // iOS wheel picker (Framework7's inline Picker) for minutes and seconds.
  // The unit labels sit above fixed-width, centred columns so the numbers always line up.
  let { seconds, onchange }: { seconds: number; onchange: (seconds: number) => void } = $props();

  let el: HTMLDivElement;
  let picker: ReturnType<typeof f7.picker.create> | undefined;
  const pad = (n: number) => String(n).padStart(2, '0');
  const mm = (s: number) => Math.floor(s / 60);
  const ss = (s: number) => s % 60;

  onMount(() => {
    const start = untrack(() => seconds);
    const secs = [0, 15, 30, 45];
    if (!secs.includes(ss(start))) secs.push(ss(start)), secs.sort((a, b) => a - b);   // keep odd legacy values selectable
    picker = f7.picker.create({
      containerEl: el, toolbar: false, rotateEffect: true, value: [String(mm(start)), String(ss(start))],
      cols: [
        { values: Array.from({ length: 100 }, (_, i) => String(i)), cssClass: 'dur-col', textAlign: 'center' },
        { values: secs.map(String), displayValues: secs.map(pad), cssClass: 'dur-col', textAlign: 'center' },
      ],
      on: { change: (_p: unknown, v: unknown) => { const [m, s] = (v as string[]).map(Number); onchange(m * 60 + s); } },
    });

    // Framework7 measures the wheel when it is first mounted. Inside a closed popup that is
    // 0×0, which leaves the scroll padding at 0 and puts the selected value off the highlight.
    // Re-measure as soon as the picker actually has a size.
    const recenter = () => {
      if (!picker) return;
      const s = seconds;
      (picker as unknown as { resizeCols: () => void }).resizeCols();
      picker.setValue([String(mm(s)), String(ss(s))]);
    };
    const ro = new ResizeObserver(entries => {
      if (entries[0]?.contentRect.height) recenter();
    });
    ro.observe(el);

    return () => { ro.disconnect(); picker?.destroy(); };
  });

  // Follow external changes (e.g. switching Workout → Rest resets the time).
  $effect(() => {
    const s = seconds;
    const cur = (picker?.value as string[] | undefined)?.map(Number);
    if (picker && cur && cur[0] * 60 + cur[1] !== s) picker.setValue([String(mm(s)), String(ss(s))]);
  });
</script>

<div class="dur">
  <div class="dur-labels" aria-hidden="true"><span>min</span><span>sec</span></div>
  <div class="duration-picker" bind:this={el}></div>
</div>
