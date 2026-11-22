// 前端轻量认证状态：Token 存 localStorage，刷新页面不掉登录
const KEY = 'dq_token'

export function getToken() { return localStorage.getItem(KEY) || '' }
export function setToken(t) { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY) }
export function authHeader() {
  const t = getToken()
  return t ? { Authorization: 'Bearer ' + t } : {}
}
export function currentUser() {
  try { return JSON.parse(localStorage.getItem('dq_user') || 'null') } catch { return null }
}
export function setUser(u) { u ? localStorage.setItem('dq_user', JSON.stringify(u)) : localStorage.removeItem('dq_user') }
export function logout() { setToken(''); setUser(null) }
