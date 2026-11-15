import type { Router } from 'framework7/types';
import Workouts from './pages/Workouts.svelte';
import Workout from './pages/Workout.svelte';
import Exercises from './pages/Exercises.svelte';
import Calendar from './pages/Calendar.svelte';

const routes: Router.RouteParameters[] = [
  { path: '/', component: Workouts },
  { path: '/workout/:id/', component: Workout },
  { path: '/exercises/', component: Exercises },
  { path: '/calendar/', component: Calendar },
];
export default routes;
