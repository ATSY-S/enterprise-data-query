<template>
  <div class="login-page" ref="page">
    <canvas ref="canvas" class="particles"></canvas>
    <div class="glow glow-a"></div>
    <div class="glow glow-b"></div>
    <div class="glow glow-c"></div>
    <div class="grid-layer"></div>

    <div class="login-wrap">
      <div class="login-card">
        <div class="brand">
          <div class="brand-icon">D</div>
          <div>
            <div class="brand-name">DataQuery</div>
            <div class="brand-sub">企业数据智能查询系统</div>
          </div>
        </div>
        <h2>登录</h2>
        <p class="hint">使用公司账号访问数据查询服务</p>
        <el-form @submit.prevent="submit">
          <el-form-item><el-input v-model="username" placeholder="用户名" size="large" /></el-form-item>
          <el-form-item><el-input v-model="password" type="password" placeholder="密码" show-password size="large" @keyup.enter="submit" /></el-form-item>
          <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="submit">登录</el-button>
        </el-form>
        <div v-if="error" class="error">{{ error }}</div>
        <div class="demo">
          演示账号<br>
          <code>admin / admin123</code>（管理员，可导入数据、审批申请）<br>
          <code>user / user123</code>（普通用户，可查询、可申请导入）
        </div>
      </div>
      <div class="foot-note">移动鼠标试试 · 数据查询与可视化平台</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'
import { setToken, setUser } from '../auth'

const emit = defineEmits(['logged'])
const username = ref(''), password = ref(''), loading = ref(false), error = ref('')
const page = ref(null), canvas = ref(null)
let raf = null, points = [], mouse = { x: -1000, y: -1000 }, resizeHandler = null, moveHandler = null

async function submit() {
  if (!username.value || !password.value) { error.value = '请输入用户名和密码'; return }
  loading.value = true; error.value = ''
  try {
    const r = await axios.post('/api/login', { username: username.value, password: password.value })
    const d = r.data?.data ?? r.data
    if (d.success) { setToken(d.token); setUser({ username: d.username, role: d.role }); emit('logged', d) }
    else error.value = d.message || '登录失败'
  } catch (e) { error.value = '请求失败：' + e.message }
  finally { loading.value = false }
}

onMounted(() => {
  const cv = canvas.value
  const ctx = cv.getContext('2d')
  let w = 0, h = 0
  function size() {
    const r = page.value.getBoundingClientRect()
    w = cv.width = r.width
    h = cv.height = r.height
    cv.style.width = w + 'px'; cv.style.height = h + 'px'
    const count = Math.min(80, Math.floor(w * h / 18000))
    points = Array.from({ length: count }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25,
      r: Math.random() * 1.6 + 1,
    }))
  }
  size()
  resizeHandler = size
  window.addEventListener('resize', resizeHandler)
  moveHandler = e => {
    const r = page.value.getBoundingClientRect()
    mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top
  }
  window.addEventListener('mousemove', moveHandler)

  function frame() {
    ctx.clearRect(0, 0, w, h)
    for (const p of points) {
      p.x += p.vx; p.y += p.vy
      if (p.x < 0 || p.x > w) p.vx *= -1
      if (p.y < 0 || p.y > h) p.vy *= -1
      const dx = p.x - mouse.x, dy = p.y - mouse.y
      const dist = Math.hypot(dx, dy)
      if (dist < 110 && dist > 0) {
        const force = (110 - dist) / 110
        p.x += (dx / dist) * force * 1.6
        p.y += (dy / dist) * force * 1.6
      }
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fillStyle = dist < 110 ? 'rgba(37,99,235,.55)' : 'rgba(96,140,200,.28)'
      ctx.fill()
      for (const q of points) {
        if (q === p || q.x < p.x) continue
        const d = Math.hypot(p.x - q.x, p.y - q.y)
        if (d < 95) {
          ctx.beginPath()
          ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y)
          ctx.strokeStyle = `rgba(120,160,215,${(1 - d / 95) * 0.16})`
          ctx.lineWidth = 0.6
          ctx.stroke()
        }
      }
    }
    if (mouse.x > -100) {
      const g = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 100)
      g.addColorStop(0, 'rgba(120,170,240,.10)')
      g.addColorStop(1, 'rgba(120,170,240,0)')
      ctx.fillStyle = g
      ctx.fillRect(mouse.x - 100, mouse.y - 100, 200, 200)
    }
    raf = requestAnimationFrame(frame)
  }
  frame()
})
onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (moveHandler) window.removeEventListener('mousemove', moveHandler)
})
</script>

<style scoped>
.login-page { position: relative; min-height: 100vh; display: flex; align-items: center; justify-content: center; overflow: hidden; background: linear-gradient(135deg, #eef4fc 0%, #f7fafd 45%, #eaf1fb 100%); }
.particles { position: absolute; inset: 0; z-index: 2; pointer-events: none; }
.glow { position: absolute; border-radius: 50%; filter: blur(70px); opacity: .55; z-index: 0; }
.glow-a { width: 420px; height: 420px; background: #c9def8; top: -120px; left: 8%; animation: float1 18s ease-in-out infinite; }
.glow-b { width: 360px; height: 360px; background: #dbe7fb; bottom: -100px; right: 10%; animation: float2 22s ease-in-out infinite; }
.glow-c { width: 260px; height: 260px; background: #d4e4f7; top: 45%; left: 62%; animation: float3 26s ease-in-out infinite; }
@keyframes float1 { 0%,100% { transform: translate(0,0) } 50% { transform: translate(90px,60px) } }
@keyframes float2 { 0%,100% { transform: translate(0,0) } 50% { transform: translate(-70px,-50px) } }
@keyframes float3 { 0%,100% { transform: translate(0,0) } 50% { transform: translate(60px,-80px) } }
.grid-layer { position: absolute; inset: 0; z-index: 1; opacity: .35; background-image: linear-gradient(rgba(148,180,220,.12) 1px, transparent 1px), linear-gradient(90deg, rgba(148,180,220,.12) 1px, transparent 1px); background-size: 46px 46px; }
.login-wrap { position: relative; z-index: 3; display: flex; flex-direction: column; align-items: center; }
.login-card { width: 380px; max-width: 92vw; background: rgba(255,255,255,.94); border: 1px solid rgba(255,255,255,.9); border-radius: 14px; padding: 32px; box-shadow: 0 16px 48px rgba(30,64,110,.10); backdrop-filter: blur(6px); }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 28px; }
.brand-icon { width: 42px; height: 42px; border-radius: 10px; background: #1a4d73; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.brand-name { font-size: 17px; font-weight: 500; color: #1a4d73; }
.brand-sub { font-size: 12px; color: #6b7280; }
h2 { font-size: 20px; font-weight: 500; margin: 0 0 6px; color: #111827; }
.hint { font-size: 12px; color: #9ca3af; margin: 0 0 20px; }
.error { color: #dc2626; font-size: 12px; margin-top: 10px; }
.demo { margin-top: 20px; padding: 12px; background: #f8fafc; border-radius: 8px; font-size: 12px; color: #6b7280; line-height: 1.9; }
code { color: #1a4d73; }
.foot-note { margin-top: 18px; font-size: 11px; color: #93a7c4; letter-spacing: .5px; }
@media (prefers-reduced-motion: reduce) { .glow { animation: none } }
</style>
