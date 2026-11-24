<script lang="ts">
  import { Popup, View, Page, Navbar, NavLeft, NavRight, Link, f7 } from 'framework7-svelte';
  import { onDestroy } from 'svelte';
  import { api } from '../lib/api';
  import CategoryFields from '../lib/CategoryFields.svelte';
  import CropEditor from '../lib/CropEditor.svelte';
  import RangeSlider from '../lib/RangeSlider.svelte';
  import type { Category, Crop, IgPreview } from '../types';

  let { opened = $bindable(false), categories, onsaved }:
    { opened: boolean; categories: Category[]; onsaved: () => void } = $props();

  let url = $state(''), status = $state(''), loading = $state(false), saving = $state(false);
  let slowTimer: ReturnType<typeof setTimeout> | undefined;
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
  const MIN_CLIP = 0.5;   // at least six frames at 12 fps, so a save is never a single still
  const step = $derived(1 / Math.max(1, clip?.fps ?? 24));
  const minClip = $derived(Math.max(MIN_CLIP, 3 / Math.max(1, clip?.fps ?? 24)));
  const t = (x: number) => `${Math.floor(x / 60)}:${(x % 60).toFixed(2).padStart(5, '0')}`;

  // Moving either handle carries the other one along so a 15-second window can
  // be placed anywhere in a long video (otherwise the two handles deadlock).
  function rangeFor(which: 'start' | 'end', value: number): [number, number] {
    if (!clip) return [start, end];
    if (which === 'start') {
      const s = Math.max(0, Math.min(value, clip.duration - minClip));
      let e = Math.max(end, s + minClip);
      if (e > s + MAX) e = s + MAX;
      if (e > clip.duration) e = clip.duration;
      return [s, e];
    }
    const e = Math.max(0, Math.min(value, clip.duration));
    let s = Math.min(start, e - minClip);
    if (s < e - MAX) s = e - MAX;
    if (s < 0) s = 0;
    return [s, e];
  }

  // Focusing the save form must not let a still-in-flight video seek drift the
  // preview forward while the user is filling in the fields.
  function freezePreview(at = previewing === 'end' ? end : start) {
    if (!video || !clip || cropping || video.readyState < 1) return;
    video.pause();
    const target = Math.max(0, Math.min(clip.duration, at));
    if (Math.abs(video.currentTime - target) > 0.001) video.currentTime = target;
  }
  const lockPreview = () => freezePreview();

  function release() {
    if (clip) api.igRelease(clip.token);
    clip = null; video?.removeAttribute('src'); cropping = false; crop = null;
  }
  function reset() {
    release(); clearTimeout(slowTimer);
    url = ''; name = ''; category = ''; newCategory = '';
    status = ''; statusError = false; attempted = false;
  }
  $effect(() => { if (!opened) reset(); });
  onDestroy(() => { clearTimeout(slowTimer); release(); });

  async function load(e: Event) {
    e.preventDefault(); loading = true; statusError = false; attempted = false; status = 'Loading and preparing the video…'; release();
    // Long reels legitimately take a while to download and prepare; reassure the
    // user instead of leaving one static message on screen.
    clearTimeout(slowTimer);
    slowTimer = setTimeout(() => {
      if (loading) status = 'Still preparing the video — long clips can take up to a minute…';
    }, 8000);
    try {
      const p = await api.igPreview(url.trim());
      clip = p; start = 0; end = Math.min(5, p.duration, MAX); previewing = 'start';
      status = 'Drag the sliders to pick the first and last frame.';
    } catch (err) { status = (err as Error).message; }
    finally { clearTimeout(slowTimer); loading = false; }
  }
  function setRange(which: 'start' | 'end', value: number) {
    if (!clip) return;
    const [s, e] = rangeFor(which, value);
    start = s; end = e;
    previewing = which;
    freezePreview(which === 'start' ? s : e);
  }
  async function save(e: Event) {
    e.preventDefault(); if (!clip || saving) return;
    lockPreview();
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
      // Keep the name/category so a second clip only needs new frames + another click.
      status = `Saved “${label}”. Pick new frames and click Create GIF again to save another clip from this video.`;
    } catch (err) { status = (err as Error).message; }
    finally { saving = false; }
  }
</script>

<Popup class="ig-studio" {opened} swipeToClose={false} closeByBackdropClick={false} closeOnEscape={false}
       onPopupClosed={() => (opened = false)}>
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
          <div class="crop-row">
            <button type="button" class="button button-round" onclick={() => (cropping = true)}>{crop ? 'Adjust crop' : 'Crop video'}</button>
            {#if crop}<button type="button" class="button button-round" onclick={() => (crop = null)}>Reset crop</button>{/if}
          </div>
        {/if}
        <div class="list inset-strong form-list"><ul>
          <li class="item-content"><div class="item-inner">
            <RangeSlider id="ig-start" label="Start" text={t(start)} value={start} min={0} max={clip.duration} {step}
                         onValue={(v) => setRange('start', v)} />
          </div></li>
          <li class="item-content"><div class="item-inner">
            <RangeSlider id="ig-end" label="End" text={t(end)} value={end} min={0} max={clip.duration} {step}
                         onValue={(v) => setRange('end', v)} />
          </div></li>
        </ul></div>
        <p class="help">Selected length: {(end - start).toFixed(2)} s (up to 15 s)</p>

        <form onsubmit={save} novalidate onfocusin={lockPreview} onpointerdown={lockPreview}>
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
