<script lang="ts">
  import { Page, Navbar, Block, List, ListItem } from 'framework7-svelte';
  import {
    ACCENTS, THEMES, DAY_START, DAY_END, settings,
    setThemeMode, setAccent, effectiveDark,
  } from '../lib/settings.svelte';

  const groups = [
    { id: 'dark', label: 'Pleasant on black' },
    { id: 'light', label: 'Contrast on white' },
  ] as const;

  const accentName = $derived(ACCENTS.find(a => a.id === settings.accent)?.name ?? 'Orange');
</script>

<Page>
  <Navbar large title="Settings" />

  <div class="block-title">Appearance</div>
  <List strong inset dividersIos>
    {#each THEMES as t}
      <ListItem title={t.label} subtitle={t.note} radio name="theme" value={t.id}
                checked={settings.theme === t.id} onChange={() => setThemeMode(t.id)} />
    {/each}
  </List>
  <Block class="help">
    Auto is white from {DAY_START}:00 to {DAY_END}:00 and black overnight. It is
    {effectiveDark() ? 'black' : 'white'} right now.
  </Block>

  <div class="block-title">Accent color · {accentName}</div>
  {#each groups as g}
    <div class="swatch-group">
      <div class="swatch-title">{g.label}</div>
      <div class="swatches">
        {#each ACCENTS.filter(a => a.group === g.id) as a}
          <button class="swatch" class:on={settings.accent === a.id}
                  style:--swatch={a.hex} title={a.name} aria-label={`${a.name} accent`}
                  aria-pressed={settings.accent === a.id} onclick={() => setAccent(a.id)}></button>
        {/each}
      </div>
    </div>
  {/each}
  <Block class="help">The accent is used for selections, links, buttons and the START button.</Block>
</Page>
