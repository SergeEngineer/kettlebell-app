<script lang="ts">
  import { Popup, View, Page, Navbar, NavLeft, NavRight, Link, f7 } from 'framework7-svelte';
  import { onDestroy } from 'svelte';
  import { api } from '../lib/api';
  import CategoryFields from '../lib/CategoryFields.svelte';
  import CropEditor from '../lib/CropEditor.svelte';
  import type { Category, Crop, IgPreview } from '../types';

  let { opened = $bindable(false), categories, onsaved }:
    { opened: boolean; categories: Category[]; onsaved: () => void } = $props();

  let url = $state(''), status = $state(''), loading = $state(false), saving = $state(false);
  let clip = $state<IgPreview | null>(null);
  let video: HTMLVideoElement | undefined = $state();
  let start = $state(0), end = $state(5), name = $state(''), category = $state(''), newCategory = $state('');
  let previewing = $state<'start' | 'end'>('start');
  let cropping = $state(false), crop = $state<Crop | null>(null);
  let attempted = $state(false), statusError = $state(false);

  // Validation is driven by an "attempted submit" flag, so a highlighted field
  // clears itself as soon as the user fills it in.
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

  const MAX = 15;
  const step = $derived(1 / Math.max(1, clip?.fps ?? 24));
  const t = (x: number) => `${Math.floor(x / 60)}:${(x % 60).toFixed(2).padStart(5, '0')}`;

  function release() {
    if (clip) api.igRelease(clip.token);
    clip = null; video?.removeAttribute('src'); cropping = false; crop = null;
    attempted = false; statusError = false;
  }
  $effect(() => { if (!opened) release(); });
  onDestroy(release);
  $effect(() => { const h = () => release(); window.addEventListener('pagehide', h); return () => window.removeEventListener('pagehide', h); });

  async function load(e: Event) {
    e.preventDefault(); loading = true; statusError = false; status = 'Loading and preparing the video…'; release();
    try {
      const p = await api.igPreview(url.trim());
      clip = p; start = 0; end = Math.min(5, p.duration, MAX); previewing = 'start';
      status = 'Drag the sliders to pick the first and last frame.';
    } catch (err) { status = (err as Error).message; }
    finally { loading = false; }
  }
  function seek(which: 'start' | 'end', event: Event) {
    if (!clip) return;
    const input = event.currentTarget as HTMLInputElement;
    const value = Number(input.value);
    const s = step;
    if (which === 'start') {
      start = Math.max(0, Math.max(Math.min(value, end - s), end - MAX));
      input.value = String(start);
    } else {
      end = Math.min(clip.duration, Math.min(Math.max(value, start + s), start + MAX));
      input.value = String(end);
    }
    previewing = which;
    if (video) { video.pause(); if (video.readyState >= 1) video.currentTime = which === 'start' ? start : end; }
  }
  async function save(e: Event) {
    e.preventDefault(); if (!clip || saving) return;
    if (missing.length) {
      attempted = true; statusError = true;
      status = `Missing: ${missing.join(', ')}.`;
      f7.toast.show({ text: status, closeTimeout: 3000 });
      return;
    }
    attempted = false; statusError = false;
    if (document.querySelector('.toast')) f7.toast.close('.toast');   // drop any stale "missing fields" hint
    const label = name.trim(); saving = true; status = 'Converting the selected frames into a GIF…';
    try {
      await api.igSave({ token: clip.token, start, end, name: label, category, new_category: newCategory.trim(), crop });
      onsaved();
      name = ''; if (category === 'new') { category = ''; newCategory = ''; }
      status = `Saved “${label}”. Adjust the sliders to cut another clip from this video.`;
    } catch (err) { status = (err as Error).message; }
    finally { saving = false; }
  }
</script>

<Popup {opened} swipeToClose onPopupClosed={() => (opened = false)}>
  <View>
    <Page>
      <Navbar title="From Instagram">
        <NavLeft><Link popupClose>Close</Link></NavLeft>
      </Navbar>
      <p class="help">Use a public post or Reel. Pick a start and end frame (up to 15 seconds), optionally crop the frame, then save. The video stays loaded so you can save several clips from the same post.</p>

      <form onsubmit={load}>
        <div class="list inset-strong form-list"><ul>
          <li class="item-content item-input"><div class="item-inner"><div class="item-input-wrap">
            <input type="url" placeholder="https://www.instagram.com/reel/…" required bind:value={url} aria-label="Instagram post or Reel URL">
          </div></div></li>
        </ul></div>
        <div class="block"><button class="button button-fill button-round" disabled={loading}>{loading ? 'Loading video…' : 'Load video'}</button></div>
      </form>
      {#if status}<p class={statusError ? 'help status-error' : 'help'} role="status" aria-live="polite">{status}</p>{/if}

      {#if clip}
        {#if cropping}
          <CropEditor src={clip.video_url} kind="video" frameTime={previewing === 'end' ? end : start}
                      initial={crop}
                      onapply={(c) => { crop = c; cropping = false; }}
                      oncancel={() => (cropping = false)} />
        {:else}
          <!-- svelte-ignore a11y_media_has_caption -->
          <video bind:this={video} src={clip.video_url} controls playsinline preload="metadata" class="igvideo"
                 onloadedmetadata={() => { if (video) video.currentTime = previewing === 'end' ? end : start; }}></video>
        {/if}
        <p class="help">Previewing the {previewing} frame</p>
        <div class="list inset-strong form-list"><ul>
          <li class="item-content"><div class="item-inner"><div class="sliderrow">
            <label for="ig-start">Start <output>{t(start)}</output></label>
            <input id="ig-start" type="range" min="0" max={clip.duration} {step} value={start} oninput={(e) => seek('start', e)}>
          </div></div></li>
          <li class="item-content"><div class="item-inner"><div class="sliderrow">
            <label for="ig-end">End <output>{t(end)}</output></label>
            <input id="ig-end" type="range" min="0" max={clip.duration} {step} value={end} oninput={(e) => seek('end', e)}>
          </div></div></li>
        </ul></div>
        <p class="help">Selected length: {(end - start).toFixed(2)} s (up to 15 s)</p>
        <div class="crop-row">
          <button type="button" class="button button-round" onclick={() => (cropping = true)}>{crop ? 'Adjust crop' : 'Crop video'}</button>
          {#if crop}<button type="button" class="button button-round" onclick={() => (crop = null)}>Reset crop</button>{/if}
        </div>
        {#if crop}<p class="help">Crop keeps {Math.round(crop.w * 100)}% × {Math.round(crop.h * 100)}% of each frame.</p>{/if}

        <form onsubmit={save} novalidate>
          <div class="list inset-strong form-list"><ul>
            <li class="item-content item-input" class:field-invalid={invalid.name}><div class="item-inner"><div class="item-input-wrap">
              <input type="text" placeholder="Exercise name" maxlength="120" autocapitalize="words" bind:value={name}>
            </div></div></li>
            <CategoryFields {categories} bind:category bind:newCategory {invalid} />
          </ul></div>
          <div class="block"><button class="button button-fill button-round" disabled={saving}>{saving ? 'Creating GIF…' : 'Create GIF and save exercise'}</button></div>
        </form>
      {/if}
    </Page>
  </View>
</Popup>
