<template>
  <div class="app">
    <aside class="sidebar">
      <div class="logo">
        <div class="logo-icon">D</div>
        <div><div class="logo-text">DataQuery</div><div class="logo-sub">企业数据智能查询系统</div></div>
      </div>
      <div class="nav">
        <div class="nav-group">工作台</div>
        <div v-for="item in menu" :key="item.key" class="nav-item"
             :class="{active: current===item.key}" @click="current=item.key">
          <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
        </div>
      </div>
      <div class="sidebar-foot">v1.0 · 本地演示环境<br>数据均为模拟生成</div>
    </aside>
    <main class="main">
      <div class="topbar">
        <div><h1>{{ title }}</h1><div class="sub">{{ subtitle }}</div></div>
        <div class="badge"><span class="dot"></span>服务运行正常</div>
      </div>
      <div class="content">
        <Dashboard v-if="current==='dashboard'" @go="current=$event" />
        <Chat v-else-if="current==='chat'" />
        <History v-else-if="current==='history'" />
        <Metrics v-else-if="current==='metrics'" />
        <About v-else />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Dashboard from './views/Dashboard.vue'
import Chat from './views/Chat.vue'
import History from './views/History.vue'
import Metrics from './views/Metrics.vue'
import About from './views/About.vue'

const current = ref('dashboard')
const menu = [
  { key:'dashboard', label:'数据概览', icon:'DataAnalysis' },
  { key:'chat', label:'智能查询', icon:'ChatDotRound' },
  { key:'history', label:'查询历史', icon:'Clock' },
  { key:'metrics', label:'指标口径', icon:'Document' },
  { key:'about', label:'系统说明', icon:'InfoFilled' },
]
const titles = {
  dashboard:['数据概览','了解系统当前的数据规模与运行状态'],
  chat:['智能查询','用中文提问，系统自动生成 SQL 并查询数据库'],
  history:['查询历史','所有查询留痕，便于审计与复盘'],
  metrics:['指标口径管理','业务术语与计算公式，大模型据此生成 SQL'],
  about:['系统说明','技术架构、功能边界与使用须知'],
}
const title = computed(()=>titles[current.value][0])
const subtitle = computed(()=>titles[current.value][1])
</script>
