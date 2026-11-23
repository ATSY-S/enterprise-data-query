<template>
  <div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>待审批申请 <el-tag v-if="pending.length" type="danger" size="small">{{ pending.length }}</el-tag></div>
      <div v-if="!pending.length" class="empty">暂无待审批申请。</div>
      <div v-for="r in pending" :key="r.id" class="req">
        <div class="req-head">
          <b>#{{ r.id }} · {{ r.filename }}</b>
          <span class="muted">{{ r.applicant }} 提交于 {{ r.ts }} → 追加到 {{ r.table }}</span>
        </div>
        <div class="reason" v-if="r.reason">用途：{{ r.reason }}</div>
        <div class="req-actions">
          <el-input v-model="notes[r.id]" size="small" placeholder="审批意见（可选）" style="width:220px" />
          <el-button type="success" size="small" @click="review(r.id, true)">批准</el-button>
          <el-button type="danger" size="small" @click="review(r.id, false)">驳回</el-button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title"><span class="bar"></span>已处理记录</div>
      <el-table :data="processed" size="small" stripe>
        <el-table-column prop="id" label="编号" width="70" />
        <el-table-column prop="applicant" label="申请人" width="100" />
        <el-table-column prop="filename" label="文件名" min-width="170" />
        <el-table-column label="结果" width="100"><template #default="{row}">
          <el-tag :type="row.status==='approved'?'success':'danger'" size="small">{{ row.status==='approved'?'已批准':'已驳回' }}</el-tag>
        </template></el-table-column>
        <el-table-column prop="reviewer" label="审批人" width="100" />
        <el-table-column prop="review_ts" label="审批时间" width="170" />
        <el-table-column prop="review_note" label="意见" min-width="140" show-overflow-tooltip />
      </el-table>
      <div v-if="!processed.length" class="empty">暂无已处理记录。</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { authHeader } from '../auth'
const rows = ref([]), notes = ref({})
const pending = computed(() => rows.value.filter(r => r.status === 'pending'))
const processed = computed(() => rows.value.filter(r => r.status !== 'pending'))
async function load() {
  try { const r = await axios.get('/api/requests', { headers: authHeader() }); rows.value = r.data?.data ?? [] } catch {}
}
async function review(id, approve) {
  try {
    const r = await axios.post(`/api/requests/${id}/review`, { approve, note: notes.value[id] || '' }, { headers: authHeader() })
    const d = r.data?.data ?? r.data
    ElMessage({ message: d.message || (approve ? '已批准' : '已驳回'), type: d.success ? 'success' : 'error' })
    if (d.success) { delete notes.value[id]; load() }
  } catch (e) { ElMessage.error('请求失败：' + e.message) }
}
onMounted(load)
</script>

<style scoped>
.req { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; background: #fcfdff; }
.req-head { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; font-size: 13px; color: #1f2937; }
.muted { font-size: 12px; color: #9ca3af; }
.reason { font-size: 12px; color: #6b7280; margin: 8px 0; }
.req-actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
</style>
