import { test, expect } from './support'

test('board: write -> detail -> wrong password rejected -> delete', async ({ page }, testInfo) => {
  const title = `e2e 시연 글 ${testInfo.project.name} ${Date.now()}`

  await page.goto('/boards')
  await page.getByRole('link', { name: /글쓰기/ }).click()
  await expect(page).toHaveURL(/\/boards\/new/)
  await page.getByLabel('카테고리').selectOption('free')
  await page.getByLabel('제목').fill(title)
  await page.getByLabel('내용').fill('유등축제 시연 리허설에서 작성한 글입니다.')
  await page.getByLabel('비밀번호').fill('1234')
  await page.getByRole('button', { name: '등록' }).click()

  await expect(page).toHaveURL(/\/boards\/\d+$/)
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()

  await page.getByRole('button', { name: '삭제' }).click()
  const dialog = page.getByRole('dialog', { name: '비밀번호 확인' })
  await expect(dialog).toBeVisible()
  await dialog.getByLabel('비밀번호').fill('9999')
  await dialog.getByRole('button', { name: '확인' }).click()
  await expect(dialog.getByText('비밀번호가 일치하지 않습니다.')).toBeVisible()
  await expect(page).toHaveURL(/\/boards\/\d+$/)

  await dialog.getByLabel('비밀번호').fill('1234')
  await dialog.getByRole('button', { name: '확인' }).click()
  await expect(page).toHaveURL(/\/boards$/)
  await expect(page.getByText(title)).toHaveCount(0)
})
