<script lang="ts">
  import { App, Views, View, Toolbar, Link } from 'framework7-svelte';
  import routes from './routes';
  import Player from './pages/Player.svelte';
  import GifViewer from './lib/GifViewer.svelte';
  import { ui, bump } from './lib/state.svelte';
  import { effectiveDark } from './lib/settings.svelte';

  const f7params = {
    name: 'Kettlebell', theme: 'ios', darkMode: effectiveDark(), routes,
    touch: { tapHold: false },
    view: { iosDynamicNavbar: true, animate: true },
  };
</script>

<App {...f7params}>
  <Views tabs class="safe-areas">
    <Toolbar tabbar icons bottom>
      <Link tabLink="#view-workouts" tabLinkActive onClick={bump}>
        <i class="icon tabico"><svg viewBox="-0.5 -0.5 25 25" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="13.5" r="7.5"/><path d="M12 9.5v4l2.5 1.5M9.5 3h5"/></svg></i>
        <span class="tabbar-label">Workouts</span>
      </Link>
      <Link tabLink="#view-exercises" onClick={bump}>
        <i class="icon tabico"><svg viewBox="0.5 1.8 23 23" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="15" r="6.5"/><path d="M8.3 9.8C7 3.5 17 3.5 15.7 9.8"/></svg></i>
        <span class="tabbar-label">Exercises</span>
      </Link>
      <Link tabLink="#view-calendar" onClick={bump}>
        <i class="icon tabico"><svg viewBox="-0.2 -0.45 24.4 24.4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg></i>
        <span class="tabbar-label">Calendar</span>
      </Link>
      <Link tabLink="#view-settings" onClick={bump}>
        <i class="icon tabico"><svg viewBox="-3.03 -3.03 30.06 30.06" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.1-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.64 8.9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34H9.4a1.7 1.7 0 0 0 1-1.55V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.05a1.7 1.7 0 0 0 1.55 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51 1Z"/></svg></i>
        <span class="tabbar-label">Settings</span>
      </Link>
    </Toolbar>
    <View id="view-workouts" main tab tabActive url="/" />
    <View id="view-exercises" tab url="/exercises/" />
    <View id="view-calendar" tab url="/calendar/" />
    <View id="view-settings" tab url="/settings/" />
  </Views>

  {#if ui.player !== null}{#key ui.player}<Player id={ui.player} />{/key}{/if}
  <GifViewer />
</App>
