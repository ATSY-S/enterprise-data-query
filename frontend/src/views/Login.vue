<template>
  <div class="login-page">
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
        <code>admin / admin123</code>（管理员，可导入数据）<br>
        <code>user / user123</code>（普通用户，仅查询）
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { setToken, setUser } from '../auth'
const emit = defineEmits(['logged'])
const username = ref(''), password = ref(''), loading = ref(false), error = ref('')
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
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f3f6fa; }
.login-card { width: 380px; max-width: 92vw; background: #fff; border-radius: 14px; padding: 32px; box-shadow: 0 8px 30px rgba(15,42,70,.08); }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 28px; }
.brand-icon { width: 42px; height: 42px; border-radius: 10px; background: #1a4d73; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.brand-name { font-size: 17px; font-weight: 500; color: #1a4d73; }
.brand-sub { font-size: 12px; color: #6b7280; }
h2 { font-size: 20px; font-weight: 500; margin: 0 0 6px; color: #111827; }
.hint { font-size: 12px; color: #9ca3af; margin: 0 0 20px; }
.error { color: #dc2626; font-size: 12px; margin-top: 10px; }
.demo { margin-top: 20px; padding: 12px; background: #f8fafc; border-radius: 8px; font-size: 12px; color: #6b7280; line-height: 1.9; }
code { color: #1a4d73; }
</style>
