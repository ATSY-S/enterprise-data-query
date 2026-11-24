<template>
  <div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>待审批申请 <el-tag v-if="pending.length" type="danger" size="small">{{ pending.length }}</el-tag></div>
      <div v-if="!pending.length" class="empty">暂无待审批申请。</div>
      <div v-for="r in pending" :key="r.id" class="req">
        <div class="req-head">
          <b>#{{ r.id }} · {{ r.filename }}</b>
          <span class="muted">{{ r.applicant }} 提交于 {{ r.ts }} → 追加到 {{ tableLabel[r.table] || r.table }}</span>
        </div>
        <div v-if="r.reason" class="reason">用途：{{ r.reason }}</div>
        <div class="req-actions">
          <el-button size="small" @click="preview(r.id)">预览文件内容</el-button>
          <el-input v-model="notes[r.id]" size="small" placeholder="审批意见（可选）" style="width:200px" />
          <el-button type="success" size="small" @click="review(r.id, true)">批准</el-button>
          <el-button type="danger" size="small" @click="review(r.id, false)">驳回</el-button>
        </div>
        <div v-if="previewData[r.id]?.success" class="preview-box">
          <div class="preview-title">{{ previewData[r.id].filename }} · {{ previewData[r.id].rows }} 行 · {{ previewData[r.id].columns.length }} 列</div>
          <div class="preview-cols">字段：{{ previewData[r.id].columns.join('、') }}</div>
          <table class="pt">
            <thead><tr><th v-for="c in previewData[r.id].columns" :key="c">{{ c }}</th></tr></thead>
            <tbody><tr v-for="(row,i) in previewData[r.id].preview" :key="i"><td v-for="c in previewData[r.id].columns" :key="c">{{ row[c] }}</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title"><span class="bar"></span>已处理记录</div>
      <el-table :data="processed" size="small" stripe>
        <el-table-column prop="id" label="编号" width="70" />
        <el-table-column prop="applicant" label="申请人" width="100" />
        <el-table-column prop="filename" label="文件名" min-width="160" />
        <el-table-column label="状态" width="100"><template #default="{row}">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template></el-table-column>
        <el-table-column prop="imported_rows" label="导入行数" width="100" />
        <el-table-column prop="reviewer" label="审批人" width="100" />
        <el-table-column prop="review_ts" label="审批时间" width="165" />
        <el-table-column label="操作" width="120"><template #default="{row}">
          <el-button v-if="row.status==='approved'" size="small" type="primary" :loading="importing===row.id" @click="doImport(row.id)">执行导入</el-button>
        </template></el-table-column>
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
const tableLabel = { orders:'订单表', order_items:'订单明细', customers:'客户表', products:'商品表', stores:'门店表', activities:'活动表', coupons:'优惠券表' }
const rows = ref([]), notes = ref({}), previewData = ref({}), importing = ref(null)
const pending = computed(() => rows.value.filter(r => r.status === 'pending'))
const processed = computed(() => rows.value.filter(r => r.status !== 'pending'))
const statusText = s => ({ pending:'待审批', approved:'已批准', rejected:'已驳回', imported:'已导入' }[s] || s)
const statusType = s => ({ pending:'warning', approved:'success', rejected:'danger', imported:'primary' }[s] || 'info')
async function load() {
  try { const r = await axios.get('/api/requests', { headers: authHeader() }); rows.value = r.data?.data ?? [] } catch {}
}
async function preview(id) {
  try {
    const r = await axios.get(`/api/requests/${id}/preview`, { headers: authHeader() })
    const d = r.data?.data ?? r.data
    if (!d.success) ElMessage.error(d.message || '预览失败')
    else previewData.value = { ...previewData.value, [id]: d }
  } catch (e) { ElMessage.error('预览失败：' + e.message) }
}
async function review(id, approve) {
  try {
    const r = await axios.post(`/api/requests/${id}/review`, { approve, note: notes.value[id] || '' }, { headers: authHeader() })
    const d = r.data?.data ?? r.data
    ElMessage({ message: d.message || (approve ? '已批准' : '已驳回'), type: d.success ? 'success' : 'error' })
    if (d.success) { delete notes.value[id]; load() }
  } catch (e) { ElMessage.error('请求失败：' + e.message) }
}
async function doImport(id) {
  importing.value = id
  try {
    const r = await axios.post(`/api/requests/${id}/import`, {}, { headers: authHeader() })
    const d = r.data?.data ?? r.data
    ElMessage({ message: d.success ? `导入成功：${d.message}` : (d.message || '导入失败'), type: d.success ? 'success' : 'error' })
    if (d.success) load()
  } catch (e) { ElMessage.error('导入失败：' + e.message) }
  finally { importing.value = null }
}
onMounted(load)
</script>

<style scoped>
.req { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; background: #fcfdff; }
.req-head { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; font-size: 13px; color: #1f2937; }
.muted { font-size: 12px; color: #9ca3af; }
.reason { font-size: 12px; color: #6b7280; margin: 8px 0; }
.req-actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.preview-box { margin-top: 12px; border: 1px solid #dbeafe; background: #f8fbff; border-radius: 6px; padding: 10px; }
.preview-title { font-size: 12px; color: #1a4d73; font-weight: 500; }
.preview-cols { font-size: 11px; color: #9ca3af; margin: 6px 0; }
.pt { width: 100%; border-collapse: collapse; font-size: 11px; overflow-x: auto; display: block; }
.pt th, .pt td { border: 1px solid #e5e7eb; padding: 4px 8px; text-align: left; white-space: nowrap; }
.pt th { background: #eef4fc; color: #374151; }
</style>
