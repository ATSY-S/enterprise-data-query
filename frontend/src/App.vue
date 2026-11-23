<template>
  <Login v-if="!user" @logged="onLogged" />
  <div v-else class="app">
    <aside class="sidebar">
      <div class="logo">
        <div class="logo-icon">D</div>
        <div><div class="logo-text">DataQuery</div><div class="logo-sub">企业数据智能查询系统</div></div>
      </div>
      <div class="nav">
        <div class="nav-group">工作台</div>
        <div v-for="item in visibleMenu" :key="item.key" class="nav-item"
             :class="{active: current===item.key}" @click="current=item.key">
          <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
          <span v-if="item.key==='approvals' && pending>0" class="nav-badge">{{ pending }}</span>
        </div>
      </div>
      <div class="sidebar-foot">v2.0 · 本地演示环境<br>数据均为模拟生成</div>
    </aside>
    <main class="main">
      <div class="topbar">
        <div><h1>{{ title }}</h1><div class="sub">{{ subtitle }}</div></div>
        <div class="top-right">
          <div class="badge"><span class="dot"></span>服务运行正常</div>
          <div class="user-chip">
            <span class="avatar-sm">{{ user.username[0].toUpperCase() }}</span>
            <span>{{ user.username }}</span>
            <el-tag size="small" :type="user.role==='admin'?'warning':'info'">{{ user.role==='admin'?'管理员':'用户' }}</el-tag>
          </div>
          <el-button size="small" text @click="doLogout">退出</el-button>
        </div>
      </div>
      <div class="content">
        <Dashboard v-if="current==='dashboard'" @go="current=$event" />
        <Chat v-else-if="current==='chat'" />
        <History v-else-if="current==='history'" />
        <DataImport v-else-if="current==='import'" />
        <ImportRequests v-else-if="current==='requests'" />
        <Approvals v-else-if="current==='approvals'" />
        <Metrics v-else-if="current==='metrics'" />
        <About v-else />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'
import { currentUser, setUser, setToken, authHeader } from './auth'
import Login from './views/Login.vue'
import Dashboard from './views/Dashboard.vue'
import Chat from './views/Chat.vue'
import History from './views/History.vue'
import DataImport from './views/DataImport.vue'
import ImportRequests from './views/ImportRequests.vue'
import Approvals from './views/Approvals.vue'
import Metrics from './views/Metrics.vue'
import About from './views/About.vue'

const user = ref(currentUser())
const current = ref('dashboard')
const pending = ref(0)
const isAdmin = computed(() => user.value?.role === 'admin')
const menu = [
  { key:'dashboard', label:'数据概览', icon:'DataAnalysis' },
  { key:'chat', label:'智能查询', icon:'ChatDotRound' },
  { key:'import', label:'数据导入', icon:'UploadFilled', adminOnly:true },
  { key:'requests', label:'我的申请', icon:'Tickets' },
  { key:'approvals', label:'导入审批', icon:'Checked', adminOnly:true },
  { key:'history', label:'查询历史', icon:'Clock' },
  { key:'metrics', label:'指标口径', icon:'Document' },
  { key:'about', label:'系统说明', icon:'InfoFilled' },
]
const visibleMenu = computed(() => menu.filter(m => !m.adminOnly || isAdmin.value))
const titles = {
  dashboard:['数据概览','了解系统当前的数据规模与运行状态'],
  chat:['智能查询','用中文提问，系统自动生成 SQL 并查询数据库'],
  import:['数据导入','上传表格即可追加数据，导入后立即可查'],
  requests:['我的导入申请','提交数据导入申请，跟踪审批进度'],
  approvals:['导入审批','审核普通用户提交的数据导入申请'],
  history:['查询历史','查询留痕，便于审计与复盘'],
  metrics:['指标口径管理','业务术语与计算公式，大模型据此生成 SQL'],
  about:['系统说明','技术架构、功能边界与使用须知'],
}
const title = computed(()=>titles[current.value]?.[0] || '')
const subtitle = computed(()=>titles[current.value]?.[1] || '')
function onLogged(d) { setUser({ username:d.username, role:d.role }); user.value = currentUser(); loadPending() }
async function loadPending() {
  if (!isAdmin.value) { pending.value = 0; return }
  try { const r = await axios.get('/api/requests/pending-count', { headers: authHeader() }); pending.value = r.data?.data?.count || 0 } catch {}
}
onMounted(loadPending)
watch(user, loadPending)
async function doLogout() {
  try { await axios.post('/api/logout', {}, { headers: authHeader() }) } catch {}
  setToken(''); setUser(null); user.value = null; current.value = 'dashboard'
}
</script>
