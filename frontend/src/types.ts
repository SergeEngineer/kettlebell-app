export interface Category { id: number; name: string }
export interface Exercise { id: number; name: string; gif: string | null; version: number; category_id: number | null; category: string | null }
export interface Program { id: number; name: string; steps: number; total: number }
export interface Step { id: number; seconds: number; rest: number; exercise_id: number | null; name: string; gif: string | null; version: number; kind: 'ex' | 'rest' }
export interface ProgramDetail { id: number; name: string; steps: Step[] }
export interface Recent { day: string; name: string; seconds: number }
export interface Completion { name: string; seconds: number }
export interface CalendarData { done: Record<string, Completion[]>; recent: Recent[] }
export interface VideoPreview { token: string; duration: number; fps: number; video_url: string }
export interface Crop { x: number; y: number; w: number; h: number }
export interface GifInfo { duration: number; fps: number }
