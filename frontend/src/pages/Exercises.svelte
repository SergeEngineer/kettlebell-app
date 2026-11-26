<script lang="ts">
  import { untrack } from 'svelte';
  import { Page, Navbar, NavRight, NavLeft, Link, List, ListItem, Block, SwipeoutActions, SwipeoutButton, Actions, ActionsGroup, ActionsLabel, ActionsButton, Popup, View, f7 } from 'framework7-svelte';
  import { api, media as mediaUrl, thumb } from '../lib/api';
  import { ui, bump, openGif } from '../lib/state.svelte';
  import CropEditor from '../lib/CropEditor.svelte';
  import TrimEditor from '../lib/TrimEditor.svelte';
  import ExerciseForm from './ExerciseForm.svelte';
  import VideoStudio from './VideoStudio.svelte';
  import type { Category, Crop, Exercise, GifInfo } from '../types';

  let exercises = $state<Exercise[] | null>(null), categories = $state<Category[]>([]);
  let menu = $state(false), videoUpload = $state(false), instagram = $state(false), editing = $state<Exercise | null>(null);
  let cropping = $state<Exercise | null>(null), cropBusy = $state(false), pendingCrop = $state<Exercise | null>(null);
  let trimming = $state<{ exercise: Exercise; info: GifInfo } | null>(null), trimBusy = $state(false);
  let pendingTrim = $state<Exercise | null>(null);
  let versions = $state<Record<number, number>>({});
  let cat = $state<'all' | 'none' | number>('all');

  const visible = $derived((exercises ?? []).filter(e =>
    cat === 'all' || (cat === 'none' ? e.category_id === null : e.category_id === cat)));
  const hasUncat = $derived((exercises ?? []).some(e => e.category_id === null));

  const gifSrc = (e: Exercise) => {
    const url = mediaUrl(e.gif);
    return url && versions[e.id] ? `${url}?v=${versions[e.id]}` : url;
  };
  const thumbSrc = (e: Exercise) => {
    const url = thumb(e.gif);
    return url && versions[e.id] ? `${url}&v=${versions[e.id]}` : url;
  };

  async function load() {
    try {
      const r = await api.exercises();
      exercises = r.exercises; categories = r.categories;
      if (cat !== 'all' && cat !== 'none' && !categories.some(c => c.id === cat)) cat = 'all';
    }
    catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 2500 }); }
  }
  $effect(() => { void ui.rev; untrack(load); });

  async function remove(e: Exercise) {
    exercises = exercises?.filter(x => x.id !== e.id) ?? null;
    try { await api.deleteExercise(e.id); } catch { load(); }
  }

  async function applyCrop(c: Crop) {
    if (!cropping) return;
    const target = cropping;
    cropBusy = true;
    try {
      const updated = await api.cropExercise(target.id, c);
      exercises = exercises?.map(x => x.id === updated.id ? updated : x) ?? null;
      versions = { ...versions, [target.id]: Date.now() };   // force the cropped file to reload
      bump();
      f7.toast.show({ text: 'GIF cropped.', closeTimeout: 2000 });
      cropping = null;
    } catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 3000 }); }
    finally { cropBusy = false; }
  }
  function cropFromEdit() {
    pendingCrop = editing; pendingTrim = null;
    editing = null;
  }
  async function openTrim(e: Exercise) {
    try { trimming = { exercise: e, info: await api.gifInfo(e.id) }; }
    catch (err) { f7.toast.show({ text: (err as Error).message, closeTimeout: 3000 }); }
  }
  async function applyTrim(start: number, end: number) {
    if (!trimming) return;
    const target = trimming.exercise;
    trimBusy = true;
    try {
      const updated = await api.trimExercise(target.id, start, end);
      exercises = exercises?.map(x => x.id === updated.id ? updated : x) ?? null;
      versions = { ...versions, [target.id]: Date.now() };   // reload the shortened GIF
      bump();
      f7.toast.show({ text: 'GIF trimmed.', closeTimeout: 2000 });
      trimming = null;
    } catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 3000 }); }
    finally { trimBusy = false; }
  }
  function trimFromEdit() {
    pendingTrim = editing; pendingCrop = null;
    editing = null;
  }
  function editClosed() {
    editing = null;
    if (pendingCrop) { cropping = pendingCrop; pendingCrop = null; pendingTrim = null; }   // open after the edit popup has fully closed
    else if (pendingTrim) { const e = pendingTrim; pendingTrim = null; void openTrim(e); }
  }
  const saved = async () => { await load(); bump(); };
</script>

<Page>
  <Navbar large title="Exercises">
    <NavRight><Link onClick={() => (menu = true)}>Add</Link></NavRight>
  </Navbar>

  {#if exercises && exercises.length}
    {#if categories.length || hasUncat}
      <div class="chips" role="group" aria-label="Filter by category">
        <button class="chip" class:on={cat === 'all'} onclick={() => (cat = 'all')}>All</button>
        {#each categories as c (c.id)}<button class="chip" class:on={cat === c.id} onclick={() => (cat = c.id)}>{c.name}</button>{/each}
        {#if hasUncat}<button class="chip" class:on={cat === 'none'} onclick={() => (cat = 'none')}>Uncategorized</button>{/if}
      </div>
    {/if}
    {#if visible.length}
      <List strong inset dividersIos>
        {#each visible as e (e.id)}
          <ListItem swipeout title={e.name} footer={e.category ?? ''} link="#"
                    onClick={(ev) => {
                      // Swipeout actions bubble to the row; ignore them so Crop/Trim don't also open the edit popup.
                      if ((ev.target as HTMLElement | null)?.closest('.swipeout-actions-right')) return;
                      editing = e;
                    }}
                    onSwipeoutDeleted={() => remove(e)}>
            {#snippet media()}
              {#if e.gif}
                <span class="thumbbtn" role="button" tabindex="0" aria-label={`View ${e.name} GIF full screen`}
                      onclick={(ev) => { ev.preventDefault(); ev.stopPropagation(); openGif(gifSrc(e)!, e.name); }}
                      onkeydown={(ev) => { if (ev.key === 'Enter') { ev.preventDefault(); ev.stopPropagation(); openGif(gifSrc(e)!, e.name); } }}>
                  <img class="thumb" src={thumbSrc(e)} alt="" draggable="false" loading="lazy" decoding="async" />
                </span>
              {:else}
                <span class="thumb letter">{e.name.slice(0, 1).toUpperCase()}</span>
              {/if}
            {/snippet}
            <SwipeoutActions right>
              {#if e.gif}<SwipeoutButton close onclick={() => (cropping = e)}>Crop</SwipeoutButton>
                <SwipeoutButton close onclick={() => openTrim(e)}>Trim</SwipeoutButton>{/if}
              <SwipeoutButton delete>Delete</SwipeoutButton>
            </SwipeoutActions>
          </ListItem>
        {/each}
      </List>
    {:else}
      <Block class="empty">No exercises in this category.</Block>
    {/if}
  {:else if exercises}
    <Block class="empty">No exercises yet. Tap Add to upload a video or make one from an Instagram video.</Block>
  {/if}

  <Actions opened={menu} onActionsClosed={() => (menu = false)}>
    <ActionsGroup>
      <ActionsLabel>New exercise</ActionsLabel>
      <!-- F7's ActionsButton only calls a lowercase `onclick` (and that replaces its auto-close), so close the menu here -->
      <ActionsButton onclick={() => { menu = false; videoUpload = true; }}>Upload a Video</ActionsButton>
      <ActionsButton onclick={() => { menu = false; instagram = true; }}>Create from an Instagram video</ActionsButton>
    </ActionsGroup>
    <ActionsGroup><ActionsButton strong close>Cancel</ActionsButton></ActionsGroup>
  </Actions>

  <ExerciseForm opened={!!editing} exercise={editing} {categories} onsaved={saved} onclosed={editClosed} oncrop={cropFromEdit} ontrim={trimFromEdit} />
  <VideoStudio source="video" bind:opened={videoUpload} {categories} onsaved={saved} />
  <VideoStudio source="instagram" bind:opened={instagram} {categories} onsaved={saved} />

  <Popup opened={!!cropping} onPopupClosed={() => (cropping = null)}>
    <View>
      <Page>
        <Navbar title="Crop GIF">
          <NavLeft><Link popupClose>Cancel</Link></NavLeft>
        </Navbar>
        {#if cropping && cropping.gif}
          <CropEditor src={gifSrc(cropping)!} kind="image" busy={cropBusy}
                      onapply={applyCrop} oncancel={() => (cropping = null)} />
        {/if}
      </Page>
    </View>
  </Popup>

  <Popup opened={!!trimming} onPopupClosed={() => (trimming = null)}>
    <View>
      <Page>
        <Navbar title="Trim GIF">
          <NavLeft><Link popupClose>Cancel</Link></NavLeft>
        </Navbar>
        {#if trimming}
          <TrimEditor id={trimming.exercise.id} src={gifSrc(trimming.exercise)!} info={trimming.info} busy={trimBusy}
                      onapply={applyTrim} oncancel={() => (trimming = null)} />
        {/if}
      </Page>
    </View>
  </Popup>
</Page>
