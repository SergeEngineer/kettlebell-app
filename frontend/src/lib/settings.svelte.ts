import { f7 } from 'framework7-svelte';

// Appearance preferences. Persisted in localStorage and applied to the root element
// (and to Framework7's dark-mode class) so every page picks them up immediately.
export type ThemeMode = 'light' | 'dark' | 'auto';

export interface Accent {
  id: string;
  name: string;
  hex: string;
  rgb: string;
  shade: string;
  tint: string;
  group: 'classic' | 'dark' | 'light';
}

export const ACCENTS: Accent[] = [
  // Pleasant on a black background (orange is the original accent).
  { id: 'orange', name: 'Orange', hex: '#ff6a13', rgb: '255, 106, 19', shade: '#e85a05', tint: '#ff8540', group: 'dark' },
  { id: 'gold', name: 'Gold', hex: '#ffb340', rgb: '255, 179, 64', shade: '#e89a24', tint: '#ffc25e', group: 'dark' },
  { id: 'mint', name: 'Mint', hex: '#34d399', rgb: '52, 211, 153', shade: '#1fae7d', tint: '#5ee0b0', group: 'dark' },
  { id: 'sky', name: 'Sky', hex: '#4fa8ff', rgb: '79, 168, 255', shade: '#2b8ae0', tint: '#71baff', group: 'dark' },
  { id: 'violet', name: 'Violet', hex: '#b794f6', rgb: '183, 148, 246', shade: '#9a72e0', tint: '#c8adf8', group: 'dark' },
  { id: 'rose', name: 'Rose', hex: '#ff6b8a', rgb: '255, 107, 138', shade: '#e34a6c', tint: '#ff88a2', group: 'dark' },
  { id: 'teal', name: 'Teal', hex: '#2dd4bf', rgb: '45, 212, 191', shade: '#17b3a0', tint: '#55ded0', group: 'dark' },
  { id: 'lime', name: 'Lime', hex: '#a3e635', rgb: '163, 230, 53', shade: '#84cc16', tint: '#bef264', group: 'dark' },
  { id: 'periwinkle', name: 'Periwinkle', hex: '#a5b4fc', rgb: '165, 180, 252', shade: '#818cf8', tint: '#c7d2fe', group: 'dark' },
  { id: 'sunshine', name: 'Sunshine', hex: '#fde047', rgb: '253, 224, 71', shade: '#eab308', tint: '#fef08a', group: 'dark' },
  // Deep enough to stay legible on white.
  { id: 'indigo', name: 'Indigo', hex: '#3f51b5', rgb: '63, 81, 181', shade: '#2f3f96', tint: '#5c6cc4', group: 'light' },
  { id: 'crimson', name: 'Crimson', hex: '#c62828', rgb: '198, 40, 40', shade: '#a51e1e', tint: '#d64848', group: 'light' },
  { id: 'forest', name: 'Forest', hex: '#1b7f4b', rgb: '27, 127, 75', shade: '#14663c', tint: '#3a9463', group: 'light' },
  { id: 'navy', name: 'Navy', hex: '#1e3a8a', rgb: '30, 58, 138', shade: '#172554', tint: '#3b5baf', group: 'light' },
  { id: 'plum', name: 'Plum', hex: '#6b21a8', rgb: '107, 33, 168', shade: '#581c87', tint: '#8b43c4', group: 'light' },
  { id: 'deep-teal', name: 'Deep Teal', hex: '#0f766e', rgb: '15, 118, 110', shade: '#115e59', tint: '#2c9388', group: 'light' },
  { id: 'burnt-orange', name: 'Burnt Orange', hex: '#c2410c', rgb: '194, 65, 12', shade: '#9a3412', tint: '#dc5c1e', group: 'light' },
  { id: 'olive', name: 'Olive', hex: '#3f6212', rgb: '63, 98, 18', shade: '#365314', tint: '#5a8225', group: 'light' },
  { id: 'slate', name: 'Slate', hex: '#334155', rgb: '51, 65, 85', shade: '#1e293b', tint: '#516079', group: 'light' },
  { id: 'fuchsia', name: 'Fuchsia', hex: '#a21caf', rgb: '162, 28, 175', shade: '#86198f', tint: '#bc31c9', group: 'light' },
];

export const THEMES: { id: ThemeMode; label: string; note: string }[] = [
  { id: 'light', label: 'White', note: 'Always light' },
  { id: 'dark', label: 'Black', note: 'Always dark' },
  { id: 'auto', label: 'Auto', note: 'White by day, black at night' },
];

// "Day" is 07:00–19:00 local time; everything else is night.
export const DAY_START = 7;
export const DAY_END = 19;

const KEY = 'kb.appearance.v1';
const DEFAULTS = { theme: 'auto' as ThemeMode, accent: 'orange' };

function load() {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '{}');
    return {
      theme: THEMES.some(t => t.id === raw.theme) ? raw.theme as ThemeMode : DEFAULTS.theme,
      accent: ACCENTS.some(a => a.id === raw.accent) ? raw.accent as string : DEFAULTS.accent,
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export const settings = $state(load());
/** Bumped once a minute so time-based "Auto" labels stay current. */
export const clock = $state({ tick: 0 });

export const isNight = (d = new Date()) => {
  const h = d.getHours();
  return h < DAY_START || h >= DAY_END;
};
export function effectiveDark() {
  void clock.tick;   // re-evaluate the label when the minute watcher ticks
  return settings.theme === 'dark' || (settings.theme === 'auto' && isNight());
}

function persist() {
  try { localStorage.setItem(KEY, JSON.stringify({ theme: settings.theme, accent: settings.accent })); }
  catch { /* private mode / storage disabled: settings still apply for this session */ }
}

export function applyAppearance() {
  const root = document.documentElement;
  const a = ACCENTS.find(x => x.id === settings.accent) ?? ACCENTS[0];
  root.style.setProperty('--f7-theme-color', a.hex);
  root.style.setProperty('--f7-theme-color-rgb', a.rgb);
  root.style.setProperty('--f7-theme-color-shade', a.shade);
  root.style.setProperty('--f7-theme-color-tint', a.tint);
  root.style.setProperty('--kb-work', a.hex);

  const dark = effectiveDark();
  if (f7 && typeof f7.setDarkMode === 'function') f7.setDarkMode(dark);
  else root.classList.toggle('dark', dark);
  document.querySelector('meta[name=theme-color]')?.setAttribute('content', dark ? '#000000' : '#ffffff');
}

export function setThemeMode(mode: ThemeMode) {
  settings.theme = mode;
  persist();
  applyAppearance();
}

export function setAccent(id: string) {
  if (!ACCENTS.some(a => a.id === id)) return;
  settings.accent = id;
  persist();
  applyAppearance();
}

let watching = false;
export function initAppearance() {
  applyAppearance();
  if (watching) return;
  watching = true;
  const refresh = () => { clock.tick++; applyAppearance(); };
  window.setInterval(refresh, 60_000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
}
