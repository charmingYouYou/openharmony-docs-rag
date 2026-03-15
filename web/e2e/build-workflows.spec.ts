/**
 * End-to-end verification for the build console workflows driven entirely through the deployed web UI.
 */
import { expect, test, type Locator, type Page } from '@playwright/test'

const BUILD_TIMEOUT_MS = 10 * 60 * 1000
const expectedDocPath =
  process.env.WEB_E2E_EXPECTED_DOC_PATH ??
  'zh-cn/application-dev/e2e/doc-001.md'
const expectedDocTitle = process.env.WEB_E2E_EXPECTED_DOC_TITLE ?? 'E2E Guide 001'

/**
 * Wait until the build status badge reflects one expected localized label.
 */
async function expectBuildStatus(page: Page, label: string) {
  await expect(page.getByTestId('build-status')).toContainText(label, {
    timeout: BUILD_TIMEOUT_MS,
  })
}

/**
 * Require the visible log panel to contain one expected message fragment.
 */
async function expectLogMessage(logPanel: Locator, message: string) {
  await expect(logPanel).toContainText(message, {
    timeout: BUILD_TIMEOUT_MS,
  })
}

/**
 * Read the numeric value from one summary stat tile rendered with a stable test id.
 */
async function readNumericStat(page: Page, testId: string) {
  const text = (await page.getByTestId(testId).textContent()) ?? ''
  const match = text.match(/(\d+)(?!.*\d)/)
  if (!match) {
    throw new Error(`Unable to read numeric stat from ${testId}: ${text}`)
  }
  return Number(match[1])
}

test.describe.configure({ mode: 'serial' })

test('通过页面点击覆盖构建工作流并验证模式化日志与只读索引详情', async ({
  page,
}) => {
  test.setTimeout(15 * 60 * 1000)

  await page.goto('/builds')
  const logPanel = page.getByTestId('build-log-panel')

  await test.step('同步并增量构建覆盖暂停与恢复', async () => {
    await page.getByTestId('build-start-sync').click()

    await expectLogMessage(logPanel, '构建任务已启动')
    await expectLogMessage(logPanel, '开始同步文档仓库')
    await expectLogMessage(logPanel, '仓库同步完成')
    await expectLogMessage(logPanel, '已发现')
    await expectLogMessage(logPanel, '正在处理')

    await page.getByTestId('build-pause-resume').click()
    await expectBuildStatus(page, '暂停中')
    await expectLogMessage(logPanel, '收到暂停请求，正在安全收尾')
    await expectBuildStatus(page, '已暂停')
    await expectLogMessage(logPanel, '已暂停，可继续增量恢复')

    await page.getByTestId('build-pause-resume').click()
    await expectLogMessage(logPanel, '已恢复任务，继续执行增量更新')
    await expectBuildStatus(page, '已完成')
    await expectLogMessage(logPanel, '构建任务已完成')
  })

  await test.step('仅增量构建跳过同步并复用现有索引', async () => {
    await page.getByTestId('build-start-incremental').click()

    await expectLogMessage(logPanel, '构建任务已启动')
    await expectLogMessage(logPanel, '进入增量构建，跳过仓库同步')
    await expectLogMessage(logPanel, '已发现')
    await expectBuildStatus(page, '已完成')
    await expectLogMessage(logPanel, '构建任务已完成')

    await expect
      .poll(async () => readNumericStat(page, 'build-stat-skipped'), {
        timeout: BUILD_TIMEOUT_MS,
      })
      .toBeGreaterThan(0)

    await expect(logPanel).not.toContainText('开始同步文档仓库')
  })

  await test.step('全量重建清空索引后重新建库', async () => {
    await page.getByTestId('build-full-rebuild').click()
    await page.getByTestId('build-full-rebuild-confirm').click()

    await expectLogMessage(logPanel, '构建任务已启动')
    await expectLogMessage(logPanel, '开始全量重建')
    await expectLogMessage(logPanel, '已清空 SQLite 和 Qdrant，开始重新建库')
    await expectLogMessage(logPanel, '已发现')
    await expectBuildStatus(page, '已完成')
    await expectLogMessage(logPanel, '构建任务已完成')

    await expect
      .poll(async () => readNumericStat(page, 'build-stat-skipped'), {
        timeout: BUILD_TIMEOUT_MS,
      })
      .toBe(0)
  })

  await test.step('索引浏览仅提供只读详情', async () => {
    await page.goto('/explorer')
    await expect(page.getByText(expectedDocPath)).toBeVisible({
      timeout: BUILD_TIMEOUT_MS,
    })

    const targetRow = page.getByRole('row', { name: new RegExp(expectedDocPath) })
    await targetRow.getByRole('button', { name: '查看详情' }).click()

    const dialog = page.getByRole('dialog')
    await expect(dialog).toContainText('文档只读详情')
    await expect(dialog).toContainText('只读')
    await expect(dialog).toContainText(expectedDocTitle)
    await expect(dialog).toContainText(expectedDocPath)
    await expect(dialog.getByRole('button', { name: /保存/i })).toHaveCount(0)
  })
})
