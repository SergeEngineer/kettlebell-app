export interface Category { id: number; name: string }
export interface Exercise { id: number; name: string; gif: string | null; category_id: number | null; category: string | null }
export interface Program { id: number; name: string; steps: number; total: number }
export interface Step { id: number; seconds: number; exercise_id: number | null; name: string; gif: string | null; kind: 'ex' | 'rest' }
export interface ProgramDetail { id: number; name: string; steps: Step[] }
export interface Recent { day: string; name: string; seconds: number }
export interface CalendarData { done: Record<string, string[]>; recent: Recent[] }
export interface IgPreview { token: string; duration: number; fps: number; video_url: string }
