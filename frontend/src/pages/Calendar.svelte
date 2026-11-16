<script lang="ts">
  import { untrack, tick } from 'svelte';
  import { Page, Navbar, Block, List, ListItem, f7 } from 'framework7-svelte';
  import { api, duration } from '../lib/api';
  import { ui } from '../lib/state.svelte';
  import type { CalendarData, Completion } from '../types';

  const WEEKS = 53;
  const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const pad = (n: number) => String(n).padStart(2, '0');
  const key = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  let data = $state<CalendarData>({ done: {}, recent: [] });
  let picked = $state<string | null>(null);
  let scroller: HTMLDivElement | undefined = $state();

  const today = new Date(); today.setHours(0, 0, 0, 0);
  const first = new Date(today); first.setDate(today.getDate() - today.getDay() - (WEEKS - 1) * 7);

  // One entry per grid cell (column-major: Sunday→Saturday for each week). Future days are blank.
  const cells = $derived.by(() => {
    const out: { k: string; n: number; today: boolean; future: boolean }[] = [];
    for (let i = 0; i < WEEKS * 7; i++) {
      const d = new Date(first); d.setDate(first.getDate() + i);
      const k = key(d);
      out.push({ k, n: data.done[k]?.length ?? 0, today: d.getTime() === today.getTime(), future: d > today });
    }
    return out;
  });
  const months = $derived.by(() => {
    const out: { label: string; col: number }[] = [];
    for (let w = 0; w < WEEKS; w++) for (let dow = 0; dow < 7; dow++) {
      const d = new Date(first); d.setDate(first.getDate() + w * 7 + dow);
      if (d <= today && d.getDate() === 1) out.push({ label: MON[d.getMonth()], col: w + 1 });
    }
    return out;
  });
  const total = $derived(cells.reduce((n, c) => n + c.n, 0));
  const active = $derived(cells.filter(c => c.n).length);
  const streak = $derived.by(() => {
    let n = 0; const cur = new Date(today);
    if (!data.done[key(cur)]) cur.setDate(cur.getDate() - 1);
    while (data.done[key(cur)]) { n++; cur.setDate(cur.getDate() - 1); }
    return n;
  });
  const todayKey = key(today);
  const day = $derived.by(() => {
    const k = picked ?? todayKey;
    const items: Completion[] = data.done[k] ?? [];
    const secs = items.reduce((n, i) => n + i.seconds, 0);
    const label = new Date(k + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
    const summary = items.length
      ? `${items.length} ${items.length === 1 ? 'workout' : 'workouts'}${secs ? ' · ' + duration(secs) : ''}`
      : k === todayKey ? 'Nothing completed yet today' : 'No workout completed';
    return { label, summary, items };
  });

  async function load() {
    try { data = await api.calendar(); await tick(); if (scroller) scroller.scrollLeft = 1e6; }   // start at today (right edge)
    catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 2500 }); }
  }
  $effect(() => { void ui.rev; untrack(load); });
</script>

<Page>
  <Navbar large title="Calendar" />
  <Block class="stats">{total} completed · {active} active days · {streak} day streak</Block>

  <div class="heatscroll" bind:this={scroller}>
    <div class="heat">
      <div class="months">{#each months as m}<span style:grid-column={m.col}>{m.label}</span>{/each}</div>
      <div class="cells" role="grid" aria-label="Completed workouts, last 12 months">
        {#each cells as c (c.k)}
          {#if c.future}<div class="gap"></div>{:else}
            <button class="cell" class:on={c.n > 0} class:on2={c.n > 1} class:today={c.today} class:picked={picked === c.k}
                    aria-label={`${c.k}: ${c.n} ${c.n === 1 ? 'workout' : 'workouts'} completed`} onclick={() => (picked = c.k)}></button>
          {/if}
        {/each}
      </div>
    </div>
  </div>
  <div class="daycard" aria-live="polite">
    <div class="dayhead"><strong>{day.label}</strong><span>{day.summary}</span></div>
    {#each day.items as it}
      <div class="dayrow"><span>{it.name}</span>{#if it.seconds}<span class="dim">{duration(it.seconds)}</span>{/if}</div>
    {/each}
  </div>

  <div class="block-title">Recent</div>
  {#if data.recent.length}
    <List strong inset dividersIos>
      {#each data.recent as r}
        <ListItem title={r.name + (r.seconds ? ` (${duration(r.seconds)})` : '')} after={r.day} />
      {/each}
    </List>
  {:else}
    <Block class="empty">No completed workouts yet. Finish a workout from start to finish and its day turns green.</Block>
  {/if}
</Page>
