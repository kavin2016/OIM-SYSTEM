import { api } from '../../../api/request.js'
import { token } from '../../../composables/useAuth.js'
import { formatDate } from '../resourcePageUtils.js'

function parseCsvLine(line) {
  const values = []
  let current = ''
  let quoted = false
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]
    const next = line[index + 1]
    if (char === '"' && quoted && next === '"') {
      current += '"'
      index += 1
    } else if (char === '"') {
      quoted = !quoted
    } else if (char === ',' && !quoted) {
      values.push(current)
      current = ''
    } else {
      current += char
    }
  }
  values.push(current)
  return values.map((value) => value.trim())
}

function csvEscape(value) {
  const text = String(value ?? '')
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function createUserImportExportActions(ctx, deps) {
  const { canOperate, importFileInput, message, rows, saving } = ctx
  const { loadRows } = deps

  function triggerImport() {
    if (!canOperate('import')) {
      message.value = '当前用户无权导入用户。'
      return
    }
    if (importFileInput.value) {
      importFileInput.value.value = ''
      importFileInput.value.click()
    }
  }

  async function importUsers(event) {
    const file = event.target.files?.[0]
    if (!file) return
    if (!token.value || !canOperate('import')) {
      message.value = '当前用户无权导入用户。'
      return
    }
    saving.value = true
    message.value = ''
    try {
      const content = await file.text()
      const lines = content.split(/\r?\n/).filter((line) => line.trim())
      if (lines.length <= 1) {
        message.value = '导入文件没有用户数据。'
        return
      }
      const headers = parseCsvLine(lines[0])
      let successCount = 0
      for (const line of lines.slice(1)) {
        const values = parseCsvLine(line)
        const row = Object.fromEntries(headers.map((header, index) => [header, values[index] || '']))
        await api.admin.users.create(token.value, {
          username: row.username,
          nickname: row.nickname || null,
          gender: row.gender || null,
          email: row.email || null,
          contacts: row.contacts ? row.contacts.split('|').map((item) => item.trim()).filter(Boolean) : [],
          password: row.password || '123456',
          is_admin: row.is_admin === 'true' || row.is_admin === '是',
          is_active: row.is_active !== 'false' && row.is_active !== '否',
        })
        successCount += 1
      }
      message.value = `已导入 ${successCount} 个用户`
      await loadRows()
    } catch (err) {
      message.value = err.message || '导入失败'
    } finally {
      saving.value = false
    }
  }

  function exportUsers() {
    if (!canOperate('export')) {
      message.value = '当前用户无权导出用户。'
      return
    }
    const headers = [
      'id',
      'username',
      'nickname',
      'gender',
      'email',
      'contacts',
      'is_admin',
      'is_active',
      'is_deleted',
      'created_at',
      'updated_at',
    ]
    const lines = rows.value.map((row) =>
      headers
        .map((header) => {
          if (header === 'contacts') return csvEscape(Array.isArray(row.contacts) ? row.contacts.join('|') : '')
          if (header === 'created_at') return csvEscape(formatDate(row.created_at))
          if (header === 'updated_at') return csvEscape(formatDate(row.updated_at))
          return csvEscape(row[header])
        })
        .join(','),
    )
    const blob = new Blob([[headers.join(','), ...lines].join('\n')], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `users-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return {
    exportUsers,
    importUsers,
    triggerImport,
  }
}
