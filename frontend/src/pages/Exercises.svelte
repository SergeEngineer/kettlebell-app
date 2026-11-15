<script lang="ts">
  import { untrack } from 'svelte';
  import { Page, Navbar, NavRight, Link, List, ListItem, Block, SwipeoutActions, SwipeoutButton, Actions, ActionsGroup, ActionsLabel, ActionsButton, f7 } from 'framework7-svelte';
  import { api, media as mediaUrl } from '../lib/api';
  import { ui, bump, openGif } from '../lib/state.svelte';
  import ExerciseForm from './ExerciseForm.svelte';
  import InstagramStudio from './InstagramStudio.svelte';
  import type { Category, Exercise } from '../types';

  let exercises = $state<Exercise[] | null>(null), categories = $state<Category[]>([]);
  let menu = $state(false), uploading = $state(false), instagram = $state(false), editing = $state<Exercise | null>(null);

  async function load() {
    try { const r = await api.exercises(); exercises = r.exercises; categories = r.categories; }
    catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 2500 }); }
  }
  $effect(() => { void ui.rev; untrack(load); });

  async function remove(e: Exercise) {
    exercises = exercises?.filter(x => x.id !== e.id) ?? null;
    try { await api.deleteExercise(e.id); } catch { load(); }
  }
  const saved = async () => { await load(); bump(); };
</script>

<Page>
  <Navbar large title="Exercises">
    <NavRight><Link onClick={() => (menu = true)}>Add</Link></NavRight>
  </Navbar>

  {#if exercises && exercises.length}
    <List strong inset dividersIos>
      {#each exercises as e (e.id)}
        <ListItem swipeout title={e.name} footer={e.category ?? ''} link="#" onClick={() => (editing = e)} onSwipeoutDeleted={() => remove(e)}>
          {#snippet media()}
            {#if e.gif}
              <span class="thumbbtn" role="button" tabindex="0" aria-label={`View ${e.name} GIF full screen`}
                    onclick={(ev) => { ev.preventDefault(); ev.stopPropagation(); openGif(mediaUrl(e.gif)!, e.name); }}
                    onkeydown={(ev) => { if (ev.key === 'Enter') { ev.preventDefault(); ev.stopPropagation(); openGif(mediaUrl(e.gif)!, e.name); } }}>
                <img class="thumb" src={mediaUrl(e.gif)} alt="" draggable="false" />
              </span>
            {:else}
              <span class="thumb letter">{e.name.slice(0, 1).toUpperCase()}</span>
            {/if}
          {/snippet}
          <SwipeoutActions right>
            <SwipeoutButton delete>Delete</SwipeoutButton>
          </SwipeoutActions>
        </ListItem>
      {/each}
    </List>
  {:else if exercises}
    <Block class="empty">No exercises yet. Tap Add to upload a GIF or make one from an Instagram video.</Block>
  {/if}

  <Actions opened={menu} onActionsClosed={() => (menu = false)}>
    <ActionsGroup>
      <ActionsLabel>New exercise</ActionsLabel>
      <ActionsButton onClick={() => (uploading = true)}>Upload a GIF</ActionsButton>
      <ActionsButton onClick={() => (instagram = true)}>Create from an Instagram video</ActionsButton>
    </ActionsGroup>
    <ActionsGroup><ActionsButton strong close>Cancel</ActionsButton></ActionsGroup>
  </Actions>

  <ExerciseForm mode="create" bind:opened={uploading} {categories} onsaved={saved} />
  <ExerciseForm mode="edit" opened={!!editing} exercise={editing} {categories} onsaved={saved} onclosed={() => (editing = null)} />
  <InstagramStudio bind:opened={instagram} {categories} onsaved={saved} />
</Page>
