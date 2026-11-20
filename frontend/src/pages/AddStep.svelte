<script lang="ts">
  import { Popup, View, Page, Navbar, NavLeft, NavRight, Link, Segmented, Button, f7 } from 'framework7-svelte';
  import { api, thumb } from '../lib/api';
  import DurationPicker from '../lib/DurationPicker.svelte';
  import type { Category, Exercise, ProgramDetail } from '../types';

  let { opened = $bindable(false), pid, onadded }:
    { opened: boolean; pid: number; onadded: (d: ProgramDetail) => void } = $props();

  let kind = $state<'ex' | 'rest'>('ex');
  let exercises = $state<Exercise[]>([]), categories = $state<Category[]>([]);
  let cat = $state<'all' | 'none' | number>('all');
  let sel = $state<number | 'new' | null>(null);
  let newName = $state(''), file = $state<File | null>(null);
  let seconds = $state(60), busy = $state(false);

  const visible = $derived(exercises.filter(e => cat === 'all' || (cat === 'none' ? e.category_id === null : e.category_id === cat)));
  const hasUncat = $derived(exercises.some(e => e.category_id === null));

  $effect(() => {
    if (!opened) return;
    kind = 'ex'; sel = null; newName = ''; file = null; seconds = 60; cat = 'all';
    api.exercises().then(r => { exercises = r.exercises; categories = r.categories; if (!r.exercises.length) sel = 'new'; })
      .catch(e => f7.toast.show({ text: e.message, closeTimeout: 2500 }));
  });
  const setKind = (k: 'ex' | 'rest') => { kind = k; seconds = k === 'rest' ? 30 : 60; };
  const ready = $derived(seconds > 0 && (kind === 'rest' || (sel === 'new' ? !!newName.trim() : sel !== null)));

  async function submit() {
    if (!ready || busy) return;
    busy = true;
    try {
      let exId: number | null = null;
      if (kind === 'ex') {
        if (sel === 'new') {
          const fd = new FormData(); fd.set('name', newName.trim()); fd.set('category', '');
          if (file) fd.set('gif', file);
          exId = (await api.addExercise(fd)).id;
        } else exId = sel as number;
      }
      onadded(await api.addStep(pid, exId, seconds));
      opened = false;
    } catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 3000 }); }
    finally { busy = false; }
  }
</script>

<Popup {opened} swipeToClose onPopupClosed={() => (opened = false)}>
  <View>
    <Page>
      <Navbar title="Add step">
        <NavLeft><Link popupClose>Cancel</Link></NavLeft>
        <NavRight><Link onClick={submit} class={ready && !busy ? '' : 'disabled'}>Add</Link></NavRight>
      </Navbar>

      <div class="block">
        <Segmented strong>
          <Button active={kind === 'ex'} onClick={() => setKind('ex')}>Exercise</Button>
          <Button active={kind === 'rest'} onClick={() => setKind('rest')}>Rest</Button>
        </Segmented>
      </div>

      {#if kind === 'ex'}
        {#if categories.length}
          <div class="chips" role="group" aria-label="Filter by category">
            <button class="chip" class:on={cat === 'all'} onclick={() => (cat = 'all')}>All</button>
            {#each categories as c (c.id)}<button class="chip" class:on={cat === c.id} onclick={() => (cat = c.id)}>{c.name}</button>{/each}
            {#if hasUncat}<button class="chip" class:on={cat === 'none'} onclick={() => (cat = 'none')}>Uncategorized</button>{/if}
          </div>
        {/if}
        <div class="list media-list inset-strong pick-list">
          <ul>
            {#each visible as e (e.id)}
              <li>
                <label class="item-radio item-content">
                  <input type="radio" name="exercise" checked={sel === e.id} onchange={() => (sel = e.id)}>
                  <i class="icon icon-radio"></i>
                  <div class="item-media">
                    {#if e.gif}<img class="thumb" src={thumb(e.gif)} alt="" draggable="false" loading="lazy" decoding="async">{:else}<span class="thumb letter">{e.name.slice(0, 1).toUpperCase()}</span>{/if}
                  </div>
                  <div class="item-inner">
                    <div class="item-title">{e.name}<div class="item-footer">{e.category ?? 'Uncategorized'}</div></div>
                  </div>
                </label>
              </li>
            {/each}
            <li>
              <label class="item-radio item-content">
                <input type="radio" name="exercise" checked={sel === 'new'} onchange={() => (sel = 'new')}>
                <i class="icon icon-radio"></i>
                <div class="item-media"><span class="thumb letter">＋</span></div>
                <div class="item-inner"><div class="item-title">New exercise<div class="item-footer">Upload a GIF</div></div></div>
              </label>
            </li>
          </ul>
        </div>
        {#if !visible.length && exercises.length}<p class="empty-note">No exercises in this category.</p>{/if}

        {#if sel === 'new'}
          <div class="list inset-strong form-list">
            <ul>
              <li class="item-content item-input"><div class="item-inner"><div class="item-input-wrap">
                <input type="text" placeholder="Exercise name" autocapitalize="words" bind:value={newName}>
              </div></div></li>
              <li class="item-content item-input"><div class="item-inner"><div class="item-input-wrap">
                <input type="file" accept="image/gif,image/webp,image/png,image/jpeg" onchange={(e) => (file = e.currentTarget.files?.[0] ?? null)}>
              </div></div></li>
            </ul>
          </div>
        {/if}
      {/if}

      <div class="block-title">{kind === 'rest' ? 'Rest for' : 'Duration'}</div>
      <div class="list inset-strong"><ul><li class="steppick"><DurationPicker {seconds} onchange={(v) => (seconds = v)} /></li></ul></div>
    </Page>
  </View>
</Popup>
