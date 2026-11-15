// Keep the screen on during a workout: Wake Lock API (HTTPS only) plus a silent looping
// video fallback, both refreshed periodically and on every tap.
export function createAwake(video: HTMLVideoElement) {
  let on = false, wake: WakeLockSentinel | null = null, timer: number | undefined;
  video.muted = true;
  const lock = () => {
    if (!navigator.wakeLock || wake) return;
    navigator.wakeLock.request('screen').then(l => { wake = l; l.addEventListener('release', () => { wake = null; }); }).catch(() => {});
  };
  const refresh = () => { video.play().catch(() => {}); lock(); };
  const onTap = () => { if (on) refresh(); };
  const onVisible = () => { if (on && document.visibilityState === 'visible') refresh(); };
  return {
    secure: window.isSecureContext && !!navigator.wakeLock,
    start() {
      on = true; refresh();
      timer = window.setInterval(() => { if (on) { lock(); if (video.paused) video.play().catch(() => {}); } }, 4000);
      document.addEventListener('pointerdown', onTap); document.addEventListener('visibilitychange', onVisible);
    },
    stop() {
      on = false; clearInterval(timer);
      document.removeEventListener('pointerdown', onTap); document.removeEventListener('visibilitychange', onVisible);
      try { wake?.release(); } catch { /* ignore */ }
      wake = null; video.pause();
    },
  };
}
