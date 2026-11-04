import { createRouter, createWebHistory } from 'vue-router'
import BoardListView from '../views/BoardListView.vue'
import PostFormView from '../views/PostFormView.vue'
import PostDetailView from '../views/PostDetailView.vue'
import NotFoundView from '../views/NotFoundView.vue'

// Temporary stub router; replaced in C2.
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/boards' },
    { path: '/boards', name: 'boards', component: BoardListView },
    { path: '/boards/new', name: 'post-new', component: PostFormView },
    { path: '/boards/:id/edit', name: 'post-edit', component: PostFormView },
    { path: '/boards/:id', name: 'post-detail', component: PostDetailView },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
