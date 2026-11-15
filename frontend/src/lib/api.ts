import type { CalendarData, Category, Exercise, IgPreview, Program, ProgramDetail } from '../types';

async function req<T>(url: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(url, { credentials: 'same-origin', ...init });
  const text = await r.text();
  let data: any = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* non-JSON error page */ }
  if (!r.ok) throw new Error(data?.error || `Request failed (${r.status})`);
  return data as T;
}
const json = (method: string, body?: unknown): RequestInit => ({
  method, headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body),
});

export const fmt = (s: number) => Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
export const mins = (s: number) => (s > 0 ? Math.max(1, Math.floor((s + 30) / 60)) + ' min' : '');
export const media = (gif: string | null) => (gif ? '/media/' + gif.split('/').map(encodeURIComponent).join('/') : null);

export const api = {
  programs: () => req<Program[]>('/api/programs'),
  addProgram: (name: string) => req<Program>('/api/programs', json('POST', { name })),
  program: (id: number) => req<ProgramDetail>(`/api/programs/${id}`),
  renameProgram: (id: number, name: string) => req<{ ok: true }>(`/api/programs/${id}`, json('PATCH', { name })),
  deleteProgram: (id: number) => req<{ ok: true }>(`/api/programs/${id}`, json('DELETE')),
  addStep: (pid: number, exercise_id: number | null, seconds: number) =>
    req<ProgramDetail>(`/api/programs/${pid}/steps`, json('POST', { exercise_id, seconds })),
  setSeconds: (sid: number, seconds: number) => req<{ ok: true }>(`/api/steps/${sid}`, json('PATCH', { seconds })),
  deleteStep: (sid: number) => req<{ ok: true }>(`/api/steps/${sid}`, json('DELETE')),
  reorder: (pid: number, ids: number[]) => req<ProgramDetail>(`/api/programs/${pid}/order`, json('PUT', { ids })),
  complete: (pid: number, day: string) => req<{ ok: true }>(`/api/programs/${pid}/complete`, json('POST', { day })),

  exercises: () => req<{ exercises: Exercise[]; categories: Category[] }>('/api/exercises'),
  addExercise: (form: FormData) => req<Exercise>('/api/exercises', { method: 'POST', body: form }),
  editExercise: (id: number, body: { name: string; category: string; new_category?: string }) =>
    req<Exercise>(`/api/exercises/${id}`, json('PATCH', body)),
  deleteExercise: (id: number) => req<{ ok: true }>(`/api/exercises/${id}`, json('DELETE')),

  igPreview: (url: string) => req<IgPreview>('/api/instagram/preview', json('POST', { url })),
  igSave: (body: { token: string; start: number; end: number; name: string; category: string; new_category?: string }) =>
    req<Exercise>('/api/instagram/save', json('POST', body)),
  igRelease: (token: string) => navigator.sendBeacon('/api/instagram/release', new Blob([JSON.stringify({ token })], { type: 'application/json' })),

  calendar: () => req<CalendarData>('/api/calendar'),
};
