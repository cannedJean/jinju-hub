import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import ImageGallery from '../ImageGallery.vue'

describe('ImageGallery', () => {
  test('Type3 caption says 변경 금지 and images are never cropped', () => {
    const w = mount(ImageGallery, {
      props: { images: [{ url: 'https://x/a.jpg', license: 'Type3', source: '한국관광공사' }] },
    })
    expect(w.text()).toContain('출처: 한국관광공사')
    expect(w.text()).toContain('변경 금지')
    const img = w.find('img')
    expect(img.attributes('src')).toBe('https://x/a.jpg')
    expect(img.attributes('style') || '').toContain('object-fit: contain')
  })

  test('license labels', async () => {
    const w = mount(ImageGallery, {
      props: {
        images: [
          { url: 'a', license: 'Type1', source: 'A' },
          { url: 'b', license: 'jinju_city_unverified', source: 'B' },
        ],
      },
    })
    expect(w.text()).toContain('공공누리 제1유형')
    await w.findAll('button')[1].trigger('click')
    expect(w.text()).toContain('진주시 제공')
  })

  test('placeholder when no images', () => {
    const w = mount(ImageGallery, { props: { images: [] } })
    expect(w.find('img').exists()).toBe(false)
    expect(w.findComponent({ name: 'ImagePlaceholder' }).exists()).toBe(true)
  })

  test('missing license falls back', () => {
    const w = mount(ImageGallery, { props: { images: [{ url: 'a', source: 'A' }] } })
    expect(w.text()).toContain('라이선스 정보 없음')
  })
})
