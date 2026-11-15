<script lang="ts">
  import { animate } from 'motion';
  import { ui } from './state.svelte';

  let box: HTMLDivElement | undefined = $state();
  $effect(() => {
    if (ui.gif && box) {
      animate(box, { opacity: [0, 1] }, { duration: 0.18 });
      animate(box.querySelector('img')!, { scale: [0.86, 1] }, { type: 'spring', stiffness: 380, damping: 28 });
    }
  });
  const close = () => { ui.gif = null; };
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && close()} />

{#if ui.gif}
  <div class="gif-viewer" bind:this={box} role="dialog" aria-modal="true" aria-label="Exercise GIF"
       onclick={(e) => e.target === e.currentTarget && close()} onkeydown={() => {}} tabindex="-1">
    <button class="gif-close" aria-label="Close" onclick={close}>×</button>
    <img src={ui.gif.src} alt={ui.gif.alt} />
  </div>
{/if}
