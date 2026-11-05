import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('../../api/posts', () => ({ fetchPost: vi.fn(), deletePost: vi.fn() }))

import PostDetailView from '../PostDetailView.vue'
import { fetchPost } from '../../api/posts'

describe('PostDetailView route param change', () => {
  beforeEach(() => vi.clearAllMocks())

  test('navigating from /boards/1 to /boards/2 reloads and shows the new post', async () => {
    fetchPost.mockImplementation(async (id) => ({
      id: Number(id),
      title: `post ${id}`,
      content: `body ${id}`,
      category: 'free',
      author: 'a',
      created_at: '2026-11-01T00:00:00',
    }))
    const Stub = { template: '<div />' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/boards', name: 'boards', component: Stub },
        { path: '/boards/:id', name: 'post', component: PostDetailView },
      ],
    })
    router.push('/boards/1')
    await router.isReady()
    const w = mount(PostDetailView, { global: { plugins: [router] }, attachTo: document.body })
    await flushPromises()
    expect(w.text()).toContain('post 1')

    await router.push('/boards/2')
    await flushPromises()
    expect(fetchPost.mock.calls.map((c) => String(c[0]))).toEqual(['1', '2'])
    expect(w.text()).toContain('post 2')
    expect(w.text()).not.toContain('post 1')
    w.unmount()
  })

  test('a late response for an older id never overwrites the current post', async () => {
    const resolvers = {}
    fetchPost.mockImplementation((id) => new Promise((r) => (resolvers[id] = r)))
    const mk = (id) => ({ id, title: `post ${id}`, content: 'c', category: 'free', author: 'a', created_at: '2026-11-01T00:00:00' })
    const Stub = { template: '<div />' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/boards', name: 'boards', component: Stub },
        { path: '/boards/:id', name: 'post', component: PostDetailView },
      ],
    })
    router.push('/boards/1')
    await router.isReady()
    const w = mount(PostDetailView, { global: { plugins: [router] }, attachTo: document.body })
    await router.push('/boards/2')
    resolvers['2'](mk(2))
    await flushPromises()
    resolvers['1'](mk(1))
    await flushPromises()
    expect(w.text()).toContain('post 2')
    expect(w.text()).not.toContain('post 1')
    w.unmount()
  })
})
