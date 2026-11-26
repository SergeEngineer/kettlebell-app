<script lang="ts">
  import { Popup, View, Page, Navbar, NavLeft, NavRight, Link, f7 } from 'framework7-svelte';
  import { api } from '../lib/api';
  import CategoryFields from '../lib/CategoryFields.svelte';
  import type { Category, Exercise } from '../types';

  // Popup for renaming / recategorising an existing exercise.
  let { opened = $bindable(false), categories, exercise = null, onsaved, onclosed, oncrop, ontrim }: {
    opened: boolean; categories: Category[]; exercise?: Exercise | null;
    onsaved: () => void; onclosed?: () => void; oncrop?: () => void; ontrim?: () => void;
  } = $props();

  let name = $state(''), category = $state(''), newCategory = $state(''), busy = $state(false);
  let attempted = $state(false);

  $effect(() => {
    if (!opened) return;
    name = exercise?.name ?? ''; category = exercise?.category_id ? String(exercise.category_id) : ''; newCategory = '';
    attempted = false;
  });
  const missing = $derived.by(() => {
    const out: string[] = [];
    if (!name.trim()) out.push('exercise name');
    if (!category) out.push('category');
    else if (category === 'new' && !newCategory.trim()) out.push('new category name');
    return out;
  });
  const invalid = $derived({
    name: attempted && !name.trim(),
    category: attempted && !category,
    newCategory: attempted && category === 'new' && !newCategory.trim(),
  });
  const ready = $derived(missing.length === 0);

  async function submit() {
    if (busy || !exercise) return;
    if (!ready) {
      attempted = true;
      f7.toast.show({ text: `Missing: ${missing.join(', ')}.`, closeTimeout: 3000 });
      return;
    }
    busy = true;
    try {
      await api.editExercise(exercise.id, { name: name.trim(), category, new_category: newCategory.trim() });
      opened = false; onsaved();
    } catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 3000 }); }
    finally { busy = false; }
  }
</script>

<Popup {opened} swipeToClose onPopupClosed={() => { opened = false; onclosed?.(); }}>
  <View>
    <Page>
      <Navbar title="Edit exercise">
        <NavLeft><Link popupClose>Cancel</Link></NavLeft>
        <NavRight><Link onClick={submit} class={busy ? 'disabled' : ''}>Save</Link></NavRight>
      </Navbar>
      <div class="list inset-strong form-list">
        <ul>
          <li class="item-content item-input" class:field-invalid={invalid.name}><div class="item-inner"><div class="item-input-wrap">
            <input type="text" placeholder="Exercise name" autocapitalize="words" bind:value={name}>
          </div></div></li>
          <CategoryFields {categories} bind:category bind:newCategory {invalid} />
        </ul>
      </div>
      {#if exercise?.gif}
        <div class="block block-strong inset-strong">
          <p class="help">You can also edit the GIF itself without changing the exercise name or category.</p>
          <div class="crop-row">
            <button type="button" class="button button-round" onclick={() => oncrop?.()}>Crop GIF</button>
            <button type="button" class="button button-round" onclick={() => ontrim?.()}>Trim GIF</button>
          </div>
        </div>
      {/if}
    </Page>
  </View>
</Popup>
