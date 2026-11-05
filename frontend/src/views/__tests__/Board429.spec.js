import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('../../api/posts', () => ({
  fetchPosts: vi.fn(),
  fetchPost: vi.fn(),
  createPost: vi.fn(),
  updatePost: vi.fn(),
  deletePost: vi.fn(),
}))

import BoardListView from '../BoardListView.vue'
import PostDetailView from '../PostDetailView.vue'
import PostFormView from '../PostFormView.vue'
import { fetchPosts, fetchPost, createPost, updatePost, deletePost } from '../../api/posts'

const MSG = '잠시 후 다시 시도해 주세요'
const err429 = () => ({ response: { status: 429, data: { detail: 'rate_limited' } } })

async function mountAt(comp, path, routePath) {
  const Stub = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/boards', name: 'boards', component: Stub },
      { path: routePath, name: path.endsWith('edit') ? 'post-edit' : path.endsWith('new') ? 'post-new' : 'post', component: comp },
      { path: '/boards/:id', name: 'post-d', component: Stub },
    ],
  })
  router.push(path)
  await router.isReady()
  const w = mount(comp, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return w
}

describe('429 rate_limited handling', () => {
  beforeEach(() => vi.clearAllMocks())

  test('list load', async () => {
    fetchPosts.mockRejectedValue(err429())
    const w = await mountAt(BoardListView, '/boards', '/boards')
    expect(w.text()).toContain(MSG)
  })

  test('detail load', async () => {
    fetchPost.mockRejectedValue(err429())
    const w = await mountAt(PostDetailView, '/boards/1', '/boards/:id')
    expect(w.text()).toContain(MSG)
  })

  test('detail delete', async () => {
    fetchPost.mockResolvedValue({ id: 1, title: 't', content: 'c', category: 'free', created_at: '2026-01-01T00:00:00' })
    deletePost.mockRejectedValue(err429())
    const w = await mountAt(PostDetailView, '/boards/1', '/boards/:id')
    await w.findAll('button').find((b) => b.text() === '삭제').trigger('click')
    await flushPromises()
    const input = w.find('#modal-pwd')
    await input.setValue('1234')
    await w.findAll('button').find((b) => b.text() === '확인').trigger('click')
    await flushPromises()
    expect(w.text()).toContain(MSG)
  })

  test('edit form load', async () => {
    fetchPost.mockRejectedValue(err429())
    const w = await mountAt(PostFormView, '/boards/1/edit', '/boards/:id/edit')
    expect(w.text()).toContain(MSG)
    expect(fetchPost).toHaveBeenCalledWith('1', { countView: false })
  })

  test('create submit', async () => {
    createPost.mockRejectedValue(err429())
    const w = await mountAt(PostFormView, '/boards/new', '/boards/new')
    await w.find('select').setValue(w.find('select').findAll('option')[1].element.value)
    await w.find('input[type="text"]').setValue('제목')
    await w.find('textarea').setValue('내용')
    await w.find('input[type="password"]').setValue('123456')
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(createPost).toHaveBeenCalled()
    expect(w.text()).toContain(MSG)
  })

  test('update submit', async () => {
    fetchPost.mockResolvedValue({ category: 'free', title: 't', content: 'c' })
    updatePost.mockRejectedValue(err429())
    const w = await mountAt(PostFormView, '/boards/1/edit', '/boards/:id/edit')
    await w.find('input[type="password"]').setValue('1234')
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(updatePost).toHaveBeenCalled()
    expect(w.text()).toContain(MSG)
  })
})

describe('board password length', () => {
  beforeEach(() => vi.clearAllMocks())

  test('a new post needs at least 6 characters (the server rejects shorter ones)', async () => {
    createPost.mockResolvedValue({ id: 9 })
    const w = await mountAt(PostFormView, '/boards/new', '/boards/new')
    await w.find('select').setValue(w.find('select').findAll('option')[1].element.value)
    await w.find('input[type="text"]').setValue('제목')
    await w.find('textarea').setValue('내용')
    await w.find('input[type="password"]').setValue('12345')
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(createPost).not.toHaveBeenCalled()
    expect(w.text()).toContain('6자 이상')
  })

  test('editing an existing post still accepts its 4-character password', async () => {
    fetchPost.mockResolvedValue({ category: 'free', title: 't', content: 'c' })
    updatePost.mockResolvedValue({ id: 1 })
    const w = await mountAt(PostFormView, '/boards/1/edit', '/boards/:id/edit')
    await w.find('input[type="password"]').setValue('1234')
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(updatePost).toHaveBeenCalled()
  })
})
