<script lang="ts">
  import { App, Views, View, Toolbar, Link } from 'framework7-svelte';
  import routes from './routes';
  import Player from './pages/Player.svelte';
  import GifViewer from './lib/GifViewer.svelte';
  import { ui, bump } from './lib/state.svelte';

  const f7params = {
    name: 'Kettlebell', theme: 'ios', darkMode: 'auto', routes,
    touch: { tapHold: false },
    view: { iosDynamicNavbar: true, animate: true },
  };
</script>

<App {...f7params}>
  <Views tabs class="safe-areas">
    <Toolbar tabbar icons bottom>
      <Link tabLink="#view-workouts" tabLinkActive onClick={bump}>
        <i class="icon tabico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="13.5" r="7.5"/><path d="M12 9.5v4l2.5 1.5M9.5 3h5"/></svg></i>
        <span class="tabbar-label">Workouts</span>
      </Link>
      <Link tabLink="#view-exercises" onClick={bump}>
        <i class="icon tabico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="15" r="6.5"/><path d="M8.3 9.8C7 3.5 17 3.5 15.7 9.8"/></svg></i>
        <span class="tabbar-label">Exercises</span>
      </Link>
      <Link tabLink="#view-calendar" onClick={bump}>
        <i class="icon tabico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg></i>
        <span class="tabbar-label">Calendar</span>
      </Link>
    </Toolbar>
    <View id="view-workouts" main tab tabActive url="/" />
    <View id="view-exercises" tab url="/exercises/" />
    <View id="view-calendar" tab url="/calendar/" />
  </Views>

  {#if ui.player !== null}{#key ui.player}<Player id={ui.player} />{/key}{/if}
  <GifViewer />
</App>
