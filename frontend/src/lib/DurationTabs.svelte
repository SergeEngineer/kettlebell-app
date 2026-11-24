<script lang="ts">
  import DurationPicker from './DurationPicker.svelte';

  // One wheel at a time, chosen with a small segmented control.  Stacking two
  // full-height pickers made the workout rows and the Add popup very tall.
  let {
    seconds,
    onseconds,
    rest = null,
    onrest = null,
    timeLabel = 'Exercise time',
    restLabel = 'Rest after'
  }: {
    seconds: number;
    onseconds: (seconds: number) => void;
    rest?: number | null;
    onrest?: ((seconds: number) => void) | null;
    timeLabel?: string;
    restLabel?: string;
  } = $props();

  let tab = $state<'time' | 'rest'>('time');
  const hasRest = $derived(rest !== null && onrest !== null);

  // A step with no rest phase (e.g. a legacy Rest row) only has a time wheel.
  $effect(() => { if (!hasRest) tab = 'time'; });
</script>

<div class="dur-tabs" role="tablist" aria-label="Duration to edit">
  <button type="button" role="tab" class="dur-tab" class:on={tab === 'time'}
          aria-selected={tab === 'time'} onclick={() => (tab = 'time')}>{timeLabel}</button>
  {#if hasRest}
    <button type="button" role="tab" class="dur-tab" class:on={tab === 'rest'}
            aria-selected={tab === 'rest'} onclick={() => (tab = 'rest')}>{restLabel}</button>
  {/if}
</div>

<div role="tabpanel">
  {#if tab === 'rest' && rest !== null && onrest}
    <DurationPicker seconds={rest} onchange={(v) => onrest(v)} />
    {#if rest === 0}<p class="help">No rest after this exercise.</p>{/if}
  {:else}
    <DurationPicker {seconds} onchange={onseconds} />
  {/if}
</div>
