<template>
  <div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>导入新数据（Excel / CSV）</div>
      <p class="intro">上传结构化表格，确认字段后追加到业务表。导入完成即可用自然语言查询新数据。不会操作数据库也能完成。</p>
      <el-alert type="info" :closable="false" show-icon
        title="安全限制：只允许追加到已有业务表，不接受新建表结构或执行 SQL；仅管理员可导入。" style="margin-bottom:16px" />

      <div class="steps">
        <div :class="['step', step>=1&&'active']">① 选择文件</div>
        <div :class="['step', step>=2&&'active']">② 预览字段</div>
        <div :class="['step', step>=3&&'active']">③ 确认入库</div>
      </div>

      <el-upload drag :auto-upload="false" :limit="1" accept=".csv,.xlsx,.xls"
                 :on-change="onFile" :on-exceed="()=>$message.warning('只能上传一个文件')">
        <div style="padding:24px">
          <div style="font-size:28px;color:#1a4d73">↑</div>
          <div>将 .csv / .xlsx 文件拖到此处，或点击选择</div>
          <div style="font-size:12px;color:#9ca3af;margin-top:6px">首次上传后自动解析，不会写入数据库</div>
        </div>
      </el-upload>

      <template v-if="parsed?.success">
        <div class="summary">
          <span>文件：<b>{{ fileName }}</b></span>
          <span>{{ parsed.rows }} 行 × {{ parsed.columns.length }} 列</span>
          <el-button size="small" type="primary" @click="step=2">预览数据</el-button>
        </div>
      </template>
      <div v-else-if="parsed" class="error">{{ parsed.message }}</div>
    </div>

    <div class="card" v-if="step>=2 && parsed?.success">
      <div class="card-title"><span class="bar"></span>字段与目标表</div>
      <div class="form-row">
        <span>追加到表：</span>
        <el-select v-model="target" placeholder="选择业务表" style="width:220px">
          <el-option v-for="t in allowedTables" :key="t" :label="t" :value="t" />
        </el-select>
        <span class="muted">文件中的列：{{ parsed.columns.join('、') }}</span>
      </div>
      <table class="preview">
        <thead><tr><th v-for="c in parsed.columns" :key="c">{{ c }}</th></tr></thead>
        <tbody><tr v-for="(row,i) in parsed.preview" :key="i"><td v-for="c in parsed.columns" :key="c">{{ row[c] }}</td></tr></tbody>
      </table>
      <div style="margin-top:16px">
        <el-button type="primary" :loading="busy" @click="commit">确认导入 {{ target }}</el-button>
        <el-button @click="step=1">返回</el-button>
      </div>
      <div v-if="result" class="result" :class="result.success?'ok':'bad'">{{ result.message }}</div>
    </div>

    <div class="card" v-if="isAdmin">
      <div class="card-title"><span class="bar"></span>近期导入记录</div>
      <div v-if="!logs.length" class="muted">暂无记录</div>
      <div v-for="(l,i) in logs" :key="i" class="log">{{ l.ts }} · {{ l.table }} · 尝试 {{ l.attempted }} 行，成功 {{ l.inserted }} 行</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { authHeader, currentUser } from '../auth'
const allowedTables = ['orders','order_items','customers','products','stores','activities','coupons']
const isAdmin = currentUser()?.role === 'admin'
const step = ref(1), file = ref(null), fileName = ref(''), parsed = ref(null)
const target = ref(''), busy = ref(false), result = ref(null), logs = ref([])

async function onFile(f) {
  file.value = f.raw; fileName.value = f.name; step.value = 1; result.value = null
  const form = new FormData(); form.append('file', f.raw)
  try {
    const r = await axios.post('/api/import/preview', form)
    parsed.value = r.data?.data ?? r.data
    if (parsed.value?.success) step.value = 2
  } catch (e) { parsed.value = { success:false, message:e.message } }
}
async function commit() {
  if (!target.value) { window.$message?.warning?.('请选择目标表'); return }
  busy.value = true
  const form = new FormData(); form.append('file', file.value); form.append('table', target.value)
  try {
    const r = await axios.post('/api/import/commit', form, { headers: authHeader() })
    result.value = r.data?.data ?? r.data
    if (result.value.success) loadLogs()
  } catch (e) { result.value = { success:false, message:e.message } }
  finally { busy.value = false }
}
async function loadLogs() {
  if (!isAdmin) return
  try { const r = await axios.get('/api/import/history', { headers: authHeader() }); logs.value = r.data?.data ?? [] } catch {}
}
onMounted(loadLogs)
</script>

<style scoped>
.intro { font-size: 13px; color: #6b7280; line-height: 1.7; margin: 0 0 14px; }
.steps { display: flex; gap: 10px; margin-bottom: 16px; }
.step { padding: 6px 12px; border-radius: 6px; background: #f3f4f6; color: #9ca3af; font-size: 12px; }
.step.active { background: #e6f1fb; color: #1a4d73; }
.summary { display: flex; gap: 16px; align-items: center; margin-top: 14px; font-size: 13px; color: #374151; }
.error { color: #dc2626; font-size: 12px; margin-top: 10px; }
.form-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; font-size: 13px; margin-bottom: 12px; }
.muted { color: #9ca3af; font-size: 12px; }
table.preview { width: 100%; border-collapse: collapse; font-size: 12px; overflow-x: auto; display: block; }
.preview th, .preview td { border: 1px solid #e5e7eb; padding: 6px 10px; text-align: left; white-space: nowrap; }
.preview th { background: #f8fafc; color: #374151; }
.result { margin-top: 12px; padding: 10px; border-radius: 6px; font-size: 13px; }
.result.ok { background: #e1f5ee; color: #0f6e56; }
.result.bad { background: #fcebeb; color: #a32d2d; }
.log { font-size: 12px; color: #6b7280; padding: 6px 0; border-bottom: 1px dashed #f0f0f0; }
</style>
