import Framework7 from 'framework7/lite-bundle';
import Framework7Svelte from 'framework7-svelte';
import 'framework7/css/bundle';
import { mount } from 'svelte';
import './app.css';
import App from './App.svelte';
import { initAppearance } from './lib/settings.svelte';

Framework7.use(Framework7Svelte);
initAppearance();   // apply saved theme/accent before the UI is mounted
mount(App, { target: document.getElementById('app')! });
