import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import PlaceDetailView from '../views/PlaceDetailView.vue'
import LanternsView from '../views/LanternsView.vue'
import FestivalsView from '../views/FestivalsView.vue'
import DataSourcesView from '../views/DataSourcesView.vue'
import BoardListView from '../views/BoardListView.vue'
import PostFormView from '../views/PostFormView.vue'
import PostDetailView from '../views/PostDetailView.vue'
import NotFoundView from '../views/NotFoundView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    // Lazy: keeps Leaflet + markercluster out of the main bundle. Full-height map, no footer.
    { path: '/explore', name: 'explore', component: () => import('../views/ExploreView.vue'), meta: { fullscreen: true } },
    { path: '/places/:id', name: 'place', component: PlaceDetailView },
    { path: '/lanterns', name: 'lanterns', component: LanternsView },
    { path: '/festivals', name: 'festivals', component: FestivalsView },
    { path: '/boards', name: 'boards', component: BoardListView },
    { path: '/boards/new', name: 'post-new', component: PostFormView },
    { path: '/boards/:id/edit', name: 'post-edit', component: PostFormView },
    { path: '/boards/:id', name: 'post', component: PostDetailView },
    { path: '/about/data', name: 'data', component: DataSourcesView },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView },
  ],
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    // Explore keeps scroll when only the query changes (filters, search).
    if (to.name === 'explore' && from.name === 'explore') return false
    return { top: 0 }
  },
})

export default router
