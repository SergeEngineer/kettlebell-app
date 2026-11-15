// Tiny shared UI state. `rev` is bumped whenever pages should reload their data
// (tab switch, player closed, popup saved).
export const ui = $state<{ rev: number; player: number | null; gif: { src: string; alt: string } | null }>({
  rev: 0, player: null, gif: null,
});
export const bump = () => { ui.rev++; };
export const openGif = (src: string, alt = '') => { ui.gif = { src, alt }; };
