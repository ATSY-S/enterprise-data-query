<template>
  <div class="chat-wrap">
    <div class="quick">
      <el-button v-for="q in quickQuestions" :key="q" size="small" plain @click="send(q)">{{ q }}</el-button>
      <el-switch v-model="confirmMode" size="small" active-text="先确认 SQL" style="margin-left:auto" />
    </div>
    <div class="chat-box" ref="box">
      <div v-if="!messages.length" class="empty">
        <div style="font-size:32px;margin-bottom:8px">◈</div>
        向系统提问，例如「各品类的销售额是多少？」<br>
        系统会自动生成 SQL、查询数据库、给出图表与结果
      </div>
      <div v-for="(m,i) in messages" :key="i" class="msg" :class="m.role">
        <div class="avatar">{{ m.role==='user' ? 'U' : 'D' }}</div>
        <div class="body">
          <div>{{ m.content }}</div>
          <template v-if="m.role==='ai' && m.result">
            <div class="meta">
              <span>SQL {{ m.result.success ? '执行成功' : '执行失败' }}</span>
              <span>耗时 {{ m.result.elapsed }}s</span>
              <span>自动重试 {{ m.result.retries }} 次</span>
              <span>{{ m.result.row_count }} 行结果</span>
            </div>
            <div class="sql-block">{{ m.result.sql }}</div>
            <div v-if="m.result.pending" style="margin-top:8px">
              <el-button type="primary" size="small" :loading="m.executing" @click="confirmExecute(m)">确认执行这条 SQL</el-button>
              <el-button size="small" @click="m.result = null">取消</el-button>
            </div>
            <table v-if="m.result.data?.length" class="data">
              <thead><tr><th v-for="c in m.result.columns" :key="c">{{ m.result.column_labels?.[c] || c }}</th></tr></thead>
              <tbody><tr v-for="(row,ri) in m.result.data.slice(0,20)" :key="ri">
                <td v-for="c in m.result.columns" :key="c">{{ row[c] }}</td>
              </tr></tbody>
            </table>
            <div v-if="m.result.row_count>20" style="font-size:11px;color:#9ca3af;margin-top:6px">仅展示前 20 行</div>
            <ChartView v-if="m.result.chart?.available" :chart="m.result.chart" />
            <el-button v-if="m.result.export_path" size="small" style="margin-top:8px" @click="download(m.result.export_path)">下载 Excel</el-button>
          </template>
        </div>
      </div>
    </div>
    <div class="input-bar">
      <el-input v-model="input" type="textarea" :rows="2" placeholder="请输入您想查询的数据问题..." @keydown.enter.ctrl="send()" />
      <el-button type="primary" :loading="loading" style="height:56px;width:100px" @click="send()">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import axios from 'axios'
import ChartView from '../components/ChartView.vue'
import { authHeader } from '../auth'
const messages = ref([])
const input = ref('')
const loading = ref(false)
const box = ref(null)
const confirmMode = ref(false)
const quickQuestions = ['各品类的销售额分别是多少？','核销率最高的3个活动是哪几个？','2025年月度销售额趋势，画折线图']

async function send(preset) {
  const q = (preset || input.value).trim()
  if (!q || loading.value) return
  messages.value.push({ role:'user', content:q })
  input.value = ''
  loading.value = true
  try {
    if (confirmMode.value) {
      const r = await axios.post('/api/preview', { question:q }, { headers: authHeader() })
      const d = r.data?.data ?? r.data
      messages.value.push({ role:'ai', content:'已生成 SQL，请确认后执行：', result:{ ...d, pending:true } })
    } else {
      const r = await axios.post('/api/query', { question:q, want_chart:true }, { headers: authHeader() })
      const d = r.data?.data ?? r.data
      messages.value.push({ role:'ai', content: d.success ? '已查询完成，结果如下：' : (d.advice || '查询失败：'+d.message), result:d })
    }
  } catch (e) {
    messages.value.push({ role:'ai', content:'请求失败：'+e.message })
  } finally {
    loading.value = false
    await nextTick()
    box.value?.scrollTo({ top: box.value.scrollHeight, behavior:'smooth' })
  }
}

async function confirmExecute(msg) {
  msg.executing = true
  try {
    const r = await axios.post('/api/execute', { question:msg.result.question, sql:msg.result.sql, want_chart:true }, { headers: authHeader() })
    const d = r.data?.data ?? r.data
    msg.result = d
    msg.content = d.success ? '已按确认的 SQL 执行完成：' : ('执行失败：' + (d.advice || d.message))
  } catch (e) {
    msg.content = '执行请求失败：' + e.message
  } finally {
    msg.executing = false
  }
}
const fileUrl = p => '/api/file?path=' + encodeURIComponent(p)
function download(p) { window.open(fileUrl(p)) }
</script>
