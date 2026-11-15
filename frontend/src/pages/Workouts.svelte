<script lang="ts">
  import { untrack } from 'svelte';
  import { Page, Navbar, NavRight, Link, List, ListItem, Block, SwipeoutActions, SwipeoutButton, f7 } from 'framework7-svelte';
  import { api, fmt } from '../lib/api';
  import { ui, bump } from '../lib/state.svelte';
  import type { Program } from '../types';

  let programs = $state<Program[] | null>(null);

  async function load() {
    try { programs = await api.programs(); } catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 2500 }); }
  }
  $effect(() => { void ui.rev; untrack(load); });

  function add() {
    f7.dialog.prompt('Give your workout a name.', 'New workout', async (name: string) => {
      if (!name.trim()) return;
      try { await api.addProgram(name.trim()); await load(); } catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 2500 }); }
    });
  }
  async function remove(p: Program) {
    programs = programs?.filter(x => x.id !== p.id) ?? null;
    try { await api.deleteProgram(p.id); bump(); } catch { load(); }
  }
</script>

<Page>
  <Navbar large title="Workouts">
    <NavRight><Link onClick={add}>Add</Link></NavRight>
  </Navbar>

  {#if programs && programs.length}
    <List strong inset dividersIos>
      {#each programs as p (p.id)}
        <ListItem swipeout link={`/workout/${p.id}/`} title={p.name}
                  after={fmt(p.total)} footer={`${p.steps} ${p.steps === 1 ? 'step' : 'steps'}`}
                  onSwipeoutDeleted={() => remove(p)}>
          <SwipeoutActions right>
            <SwipeoutButton delete>Delete</SwipeoutButton>
          </SwipeoutActions>
        </ListItem>
      {/each}
    </List>
  {:else if programs}
    <Block class="empty">No workouts yet. Tap Add to build your first one.</Block>
  {/if}
</Page>
