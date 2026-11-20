<script lang="ts">
  import { untrack } from 'svelte';
  import { Page, Navbar, NavRight, Link, List, ListItem, Block, Button, SwipeoutActions, SwipeoutButton, f7 } from 'framework7-svelte';
  import { api, fmt, media as mediaUrl, thumb as thumbUrl } from '../lib/api';
  import { ui, bump, openGif } from '../lib/state.svelte';
  import { grip } from '../lib/reorder';
  import DurationPicker from '../lib/DurationPicker.svelte';
  import AddStep from './AddStep.svelte';
  import type { ProgramDetail, Step } from '../types';

  let { f7route }: { f7route: { params: Record<string, string> } } = $props();
  const pid = $derived(+f7route.params.id);

  let prog = $state<ProgramDetail | null>(null);
  let open = $state<number | null>(null);      // step whose time wheels are showing
  let adding = $state(false);
  const total = $derived(prog?.steps.reduce((n, s) => n + s.seconds, 0) ?? 0);
  const canStart = $derived(!!prog?.steps.some(s => s.kind === 'ex'));

  const toast = (e: unknown) => f7.toast.show({ text: (e as Error).message, closeTimeout: 2500 });
  async function load() { try { prog = await api.program(pid); } catch (e) { toast(e); } }
  $effect(() => { void ui.rev; untrack(load); });

  function rename() {
    f7.dialog.prompt('Workout name', 'Rename', async (name: string) => {
      const v = name.trim(); if (!v || !prog) return;
      try { await api.renameProgram(pid, v); prog.name = v; bump(); } catch (e) { toast(e); }
    }, undefined, prog?.name);
  }

  const saveTimers = new Map<number, number>();
  function setSeconds(s: Step, seconds: number) {
    if (seconds <= 0 || seconds === s.seconds) return;
    s.seconds = seconds;                        // update the row straight away, save once the wheels settle
    clearTimeout(saveTimers.get(s.id));
    saveTimers.set(s.id, window.setTimeout(() => api.setSeconds(s.id, seconds).then(bump).catch(toast), 500));
  }
  async function remove(s: Step) {
    if (!prog) return;
    prog.steps = prog.steps.filter(x => x.id !== s.id);
    if (open === s.id) open = null;
    try { await api.deleteStep(s.id); bump(); } catch (e) { toast(e); load(); }
  }
  async function commitOrder(ids: number[]) {
    if (!prog) return;
    const prev = prog.steps;
    prog.steps = ids.map(id => prev.find(s => s.id === id)!);
    try { prog = await api.reorder(pid, ids); } catch (e) { prog.steps = prev; toast(e); }
  }
  const toggle = (s: Step) => { open = open === s.id ? null : s.id; };
</script>

<Page>
  <Navbar large title={prog?.name ?? ''} backLink="Workouts">
    <NavRight>
      <Link onClick={rename}>Rename</Link>
      <Link onClick={() => (adding = true)}>Add</Link>
    </NavRight>
  </Navbar>

  <Block class="startblock">
    <Button large fill round disabled={!canStart} onClick={() => (ui.player = pid)}>
      Start{total ? ` · ${fmt(total)}` : ''}
    </Button>
  </Block>

  {#if prog && prog.steps.length}
    <List strong inset dividersIos class="steps">
      {#each prog.steps as s (s.id)}
        <ListItem swipeout title={s.name} onClick={() => toggle(s)} onSwipeoutDeleted={() => remove(s)}>
          {#snippet media()}
            {#if s.gif}
              <span class="thumbbtn" role="button" tabindex="0" aria-label={`View ${s.name} GIF full screen`}
                    onclick={(e) => { e.stopPropagation(); openGif(mediaUrl(s.gif)!, s.name); }}
                    onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); openGif(mediaUrl(s.gif)!, s.name); } }}>
                <img class="thumb" src={thumbUrl(s.gif)} alt="" draggable="false" loading="lazy" decoding="async" />
              </span>
            {:else}
              <span class="thumb letter">{s.kind === 'rest' ? 'Rest' : s.name.slice(0, 1).toUpperCase()}</span>
            {/if}
          {/snippet}
          {#snippet after()}
            <span class="tm">{fmt(s.seconds)}</span>
            <span class="grip" role="button" tabindex="0" aria-label={`Reorder ${s.name}. Use arrow keys to move.`}
                  data-grip={s.id} onclick={(e) => e.stopPropagation()} onkeydown={() => {}}
                  use:grip={{ onCommit: commitOrder, disabled: open !== null }}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h16M4 12h16M4 16h16" /></svg>
            </span>
          {/snippet}
          <SwipeoutActions right>
            <SwipeoutButton delete>Delete</SwipeoutButton>
          </SwipeoutActions>
        </ListItem>
        {#if open === s.id}
          <li class="steppick"><DurationPicker seconds={s.seconds} onchange={(v) => setSeconds(s, v)} /></li>
        {/if}
      {/each}
    </List>
    <p class="total">Total {fmt(total)}</p>
  {:else if prog}
    <Block class="empty">No steps yet. Tap Add to put an exercise or a rest in this workout.</Block>
  {/if}

  <AddStep bind:opened={adding} {pid} onadded={(d) => { prog = d; bump(); }} />
</Page>
