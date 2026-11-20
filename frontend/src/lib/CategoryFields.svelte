<script lang="ts">
  import type { Category } from '../types';
  // Category <select> with a "New category…" escape hatch, in Framework7 form-row markup.
  let { categories, category = $bindable(''), newCategory = $bindable(''), invalid = {} }:
    { categories: Category[]; category: string; newCategory: string; invalid?: { category?: boolean; newCategory?: boolean } } = $props();
</script>

<li class="item-content item-input" class:field-invalid={invalid.category}>
  <div class="item-inner">
    <div class="item-title item-label">Category</div>
    <div class="item-input-wrap input-dropdown-wrap">
      <select bind:value={category}>
        <option value="">No category</option>
        {#each categories as c (c.id)}<option value={String(c.id)}>{c.name}</option>{/each}
        <option value="new">＋ New category…</option>
      </select>
    </div>
  </div>
</li>
{#if category === 'new'}
  <li class="item-content item-input" class:field-invalid={invalid.newCategory}>
    <div class="item-inner">
      <div class="item-input-wrap">
        <input type="text" placeholder="New category name" autocapitalize="words" bind:value={newCategory}>
      </div>
    </div>
  </li>
{/if}
