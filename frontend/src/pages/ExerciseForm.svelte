<script lang="ts">
  import { Popup, View, Page, Navbar, NavLeft, NavRight, Link, f7 } from 'framework7-svelte';
  import { api } from '../lib/api';
  import CategoryFields from '../lib/CategoryFields.svelte';
  import type { Category, Exercise } from '../types';

  // One popup for both uploading a new exercise and renaming / recategorising an existing one.
  let { mode, opened = $bindable(false), categories, exercise = null, onsaved, onclosed }: {
    mode: 'create' | 'edit'; opened: boolean; categories: Category[]; exercise?: Exercise | null;
    onsaved: () => void; onclosed?: () => void;
  } = $props();

  let name = $state(''), category = $state(''), newCategory = $state(''), file = $state<File | null>(null), busy = $state(false);

  $effect(() => {
    if (!opened) return;
    name = exercise?.name ?? ''; category = exercise?.category_id ? String(exercise.category_id) : ''; newCategory = ''; file = null;
  });
  const ready = $derived(!!name.trim() && (category !== 'new' || !!newCategory.trim()));

  async function submit() {
    if (!ready || busy) return;
    busy = true;
    try {
      if (mode === 'edit' && exercise) {
        await api.editExercise(exercise.id, { name: name.trim(), category, new_category: newCategory.trim() });
      } else {
        const fd = new FormData();
        fd.set('name', name.trim()); fd.set('category', category); fd.set('new_category', newCategory.trim());
        if (file) fd.set('gif', file);
        await api.addExercise(fd);
      }
      opened = false; onsaved();
    } catch (e) { f7.toast.show({ text: (e as Error).message, closeTimeout: 3000 }); }
    finally { busy = false; }
  }
</script>

<Popup {opened} swipeToClose onPopupClosed={() => { opened = false; onclosed?.(); }}>
  <View>
    <Page>
      <Navbar title={mode === 'edit' ? 'Edit exercise' : 'New exercise'}>
        <NavLeft><Link popupClose>Cancel</Link></NavLeft>
        <NavRight><Link onClick={submit} class={ready && !busy ? '' : 'disabled'}>Save</Link></NavRight>
      </Navbar>
      <div class="list inset-strong form-list">
        <ul>
          <li class="item-content item-input"><div class="item-inner"><div class="item-input-wrap">
            <input type="text" placeholder="Exercise name" autocapitalize="words" bind:value={name}>
          </div></div></li>
          <CategoryFields {categories} bind:category bind:newCategory />
          {#if mode === 'create'}
            <li class="item-content item-input"><div class="item-inner"><div class="item-input-wrap">
              <input type="file" accept="image/gif,image/webp,image/png,image/jpeg" onchange={(e) => (file = e.currentTarget.files?.[0] ?? null)}>
            </div></div></li>
          {/if}
        </ul>
      </div>
      {#if mode === 'create'}<p class="empty-note">GIF, WebP, PNG or JPEG, up to 30 MB. Renaming the exercise later renames its file too.</p>{/if}
    </Page>
  </View>
</Popup>
