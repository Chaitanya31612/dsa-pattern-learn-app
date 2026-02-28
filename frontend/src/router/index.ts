import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import PatternView from '../views/PatternView.vue'
import ProblemView from '../views/ProblemView.vue'
import AllProblemsView from '../views/AllProblemsView.vue'

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
