<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import { f7 } from 'framework7-svelte';

  // iOS wheel picker (Framework7's inline Picker) for minutes and seconds.
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
        { values: Array.from({ length: 100 }, (_, i) => String(i)), textAlign: 'right' },
        { divider: true, content: 'min' },
        { values: secs.map(String), displayValues: secs.map(pad), textAlign: 'left' },
        { divider: true, content: 'sec' },
      ],
      on: { change: (_p: unknown, v: unknown) => { const [m, s] = (v as string[]).map(Number); onchange(m * 60 + s); } },
    });
    return () => picker?.destroy();
  });

  // Follow external changes (e.g. switching Workout → Rest resets the time).
  $effect(() => {
    const s = seconds;
    const cur = (picker?.value as string[] | undefined)?.map(Number);
    if (picker && cur && cur[0] * 60 + cur[1] !== s) picker.setValue([String(mm(s)), String(ss(s))]);
  });
</script>

<div class="duration-picker" bind:this={el}></div>
