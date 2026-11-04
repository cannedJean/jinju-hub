import apiClient from './client'

export function fetchPosts(params = {}) {
  return apiClient.get('/posts', { params }).then((res) => res.data)
}

export function fetchPost(id) {
  return apiClient.get(`/posts/${id}`).then((res) => res.data)
}

export function createPost(payload) {
  return apiClient.post('/posts', payload).then((res) => res.data)
}

export function updatePost(id, payload) {
  return apiClient.put(`/posts/${id}`, payload).then((res) => res.data)
}

// Password is sent in the request body; wrong password returns 403.
export function deletePost(id, password) {
  return apiClient.delete(`/posts/${id}`, { data: { password } }).then((res) => res.data)
}
