import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import PatternView from '../views/PatternView.vue'
import ProblemView from '../views/ProblemView.vue'
import AllProblemsView from '../views/AllProblemsView.vue'
import ReviewView from '../views/ReviewView.vue'
import PatternQuizView from '../views/PatternQuizView.vue'
import SettingsView from '../views/SettingsView.vue'
import MockInterviewView from '../views/MockInterviewView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: DashboardView,
    meta: { title: 'Dashboard' },
  },
  {
    path: '/pattern/:id',
    name: 'pattern',
    component: PatternView,
    meta: { title: 'Pattern' },
  },
  {
    path: '/problem/:slug',
    name: 'problem',
    component: ProblemView,
    meta: { title: 'Problem' },
  },
  {
    path: '/problems',
    name: 'all-problems',
    component: AllProblemsView,
    meta: { title: 'All Problems' },
  },
  {
    path: '/review',
    name: 'review',
    component: ReviewView,
    meta: { title: 'Review Queue' },
  },
  {
    path: '/quiz',
    name: 'quiz',
    component: PatternQuizView,
    meta: { title: 'Pattern Quiz' },
  },
  {
    path: '/mock-interview',
    name: 'mock-interview',
    component: MockInterviewView,
    meta: { title: 'Mock Interview' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: { title: 'Settings' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition ?? { top: 0 }
  },
})

router.afterEach((to) => {
  const base = 'DSA Pattern Lab'
  document.title = to.meta.title ? `${to.meta.title} · ${base}` : base
})

export default router
