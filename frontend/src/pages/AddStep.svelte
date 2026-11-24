<script lang="ts">
  import { Popup, View, Page, Navbar, NavLeft, NavRight, Link, f7 } from 'framework7-svelte';
  import { api, media, thumb } from '../lib/api';
  import { openGif } from '../lib/state.svelte';
  import DurationTabs from '../lib/DurationTabs.svelte';
  import type { Category, Exercise, ProgramDetail } from '../types';

  let { opened = $bindable(false), pid, onadded }:
    { opened: boolean; pid: number; onadded: (d: ProgramDetail) => void } = $props();

  let exercises = $state<Exercise[]>([]), categories = $state<Category[]>([]);
  let cat = $state<'all' | 'none' | number>('all');
  let selected = $state<number[]>([]);
  let addNew = $state(false);
  let newName = $state(''), file = $state<File | null>(null);
  let seconds = $state(60), rest = $state(30), busy = $state(false);

  const visible = $derived(exercises.filter(e => cat === 'all' || (cat === 'none' ? e.category_id === null : e.category_id === cat)));
  const hasUncat = $derived(exercises.some(e => e.category_id === null));
  const count = $derived(selected.length + (addNew ? 1 : 0));

  $effect(() => {
    if (!opened) return;
    selected = []; addNew = false; newName = ''; file = null; seconds = 60; rest = 30; cat = 'all';
    api.exercises().then(r => {
      exercises = r.exercises; categories = r.categories;
      if (!r.exercises.length) addNew = true;
    }).catch(e => f7.toast.show({ text: e.message, closeTimeout: 2500 }));
  });
  const toggle = (id: number) => {
    selected = selected.includes(id) ? selected.filter(x => x !== id) : [...selected, id];
  };
  const preview = (e: Exercise) => { if (e.gif) openGif(media(e.gif)!, e.name); };
  const ready = $derived(seconds > 0 && (selected.length > 0 || (addNew && !!newName.trim())));

  async function submit() {
    if (!ready || busy) return;
    busy = true;
    try {
      const ids = [...selected];
      if (addNew) {
        const fd = new FormData(); fd.set('name', newName.trim()); fd.set('category', '');
        if (file) fd.set('gif', file);
        ids.push((await api.addExercise(fd)).id);
      }
      let program: ProgramDetail | null = null;
      for (const id of ids) program = await api.addStep(pid, id, seconds, rest);
      if (program) onadded(program);
      opened = false;
    } catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 3000 }); }
    finally { busy = false; }
  }
</script>

<Popup {opened} swipeToClose onPopupClosed={() => (opened = false)}>
  <View>
    <Page>
      <Navbar title="Add exercises">
        <NavLeft><Link popupClose>Cancel</Link></NavLeft>
        <NavRight><Link onClick={submit} class={ready && !busy ? '' : 'disabled'}>Add{count > 1 ? ` (${count})` : ''}</Link></NavRight>
      </Navbar>

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
              <label class="item-checkbox item-content">
                <input type="checkbox" checked={selected.includes(e.id)} onchange={() => toggle(e.id)}>
                <i class="icon icon-checkbox"></i>
                <div class="item-media">
                  {#if e.gif}
                    <span class="thumbbtn" role="button" tabindex="0" aria-label={`View ${e.name} GIF full screen`}
                          onclick={(ev) => { ev.preventDefault(); ev.stopPropagation(); preview(e); }}
                          onkeydown={(ev) => { if (ev.key === 'Enter') { ev.preventDefault(); ev.stopPropagation(); preview(e); } }}>
                      <img class="thumb" src={thumb(e.gif)} alt="" draggable="false" loading="lazy" decoding="async" />
                    </span>
                  {:else}
                    <span class="thumb letter">{e.name.slice(0, 1).toUpperCase()}</span>
                  {/if}
                </div>
                <div class="item-inner">
                  <div class="item-title">{e.name}<div class="item-footer">{e.category ?? 'Uncategorized'}</div></div>
                </div>
              </label>
            </li>
          {/each}
          <li>
            <label class="item-checkbox item-content">
              <input type="checkbox" checked={addNew} onchange={(e) => (addNew = e.currentTarget.checked)}>
              <i class="icon icon-checkbox"></i>
              <div class="item-media"><span class="thumb letter">＋</span></div>
              <div class="item-inner"><div class="item-title">New exercise<div class="item-footer">Upload a GIF</div></div></div>
            </label>
          </li>
        </ul>
      </div>
      {#if !visible.length && exercises.length}<p class="empty-note">No exercises in this category.</p>{/if}

      {#if addNew}
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

      <div class="block-title">Duration</div>
      <div class="list inset-strong"><ul><li class="steppick">
        <DurationTabs {seconds} onseconds={(v) => (seconds = v)} {rest} onrest={(v) => (rest = v)} />
      </li></ul></div>
    </Page>
  </View>
</Popup>
