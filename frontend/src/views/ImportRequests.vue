<template>
  <div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>提交导入申请</div>
      <p class="intro">需要导入新数据？填写下方信息提交申请，管理员审批通过后即可由管理员协助导入。普通用户不能直接操作数据库。</p>
      <el-form label-width="100px" style="max-width:620px">
        <el-form-item label="文件名"><el-input v-model="form.filename" placeholder="例如：2026年3月销售数据.xlsx" /></el-form-item>
        <el-form-item label="目标表">
          <el-select v-model="form.table" placeholder="选择要追加到的业务表" style="width:100%">
            <el-option v-for="t in tables" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="用途说明"><el-input v-model="form.reason" type="textarea" :rows="2" placeholder="简单说明这批数据的来源与用途" /></el-form-item>
        <el-form-item><el-button type="primary" :loading="busy" @click="submit">提交申请</el-button></el-form-item>
      </el-form>
      <div v-if="msg" class="msg">{{ msg }}</div>
    </div>

    <div class="card">
      <div class="card-title"><span class="bar"></span>我的申请记录</div>
      <el-table :data="rows" size="small" stripe>
        <el-table-column prop="id" label="编号" width="70" />
        <el-table-column prop="ts" label="提交时间" width="170" />
        <el-table-column prop="filename" label="文件名" min-width="180" />
        <el-table-column prop="table" label="目标表" width="130" />
        <el-table-column label="状态" width="100"><template #default="{row}">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template></el-table-column>
        <el-table-column prop="reviewer" label="审批人" width="100" />
        <el-table-column prop="review_note" label="审批意见" min-width="140" show-overflow-tooltip />
      </el-table>
      <div v-if="!rows.length" class="empty">还没有提交过申请。</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { authHeader } from '../auth'
const tables = ['orders','order_items','customers','products','stores','activities','coupons']
const form = ref({ filename:'', table:'', reason:'' })
const rows = ref([]), busy = ref(false), msg = ref('')
const statusText = s => ({ pending:'待审批', approved:'已批准', rejected:'已驳回' }[s] || s)
const statusType = s => ({ pending:'warning', approved:'success', rejected:'danger' }[s] || 'info')
async function load() {
  try { const r = await axios.get('/api/requests', { headers: authHeader() }); rows.value = r.data?.data ?? [] } catch {}
}
async function submit() {
  if (!form.value.filename || !form.value.table) { msg.value = '请填写文件名并选择目标表'; return }
  busy.value = true; msg.value = ''
  try {
    const r = await axios.post('/api/requests', form.value, { headers: authHeader() })
    const d = r.data?.data ?? r.data
    msg.value = d.success ? d.message : (d.message || '提交失败')
    if (d.success) { form.value = { filename:'', table:'', reason:'' }; load() }
  } catch (e) { msg.value = '请求失败：' + e.message }
  finally { busy.value = false }
}
onMounted(load)
</script>

<style scoped>
.intro { font-size: 13px; color: #6b7280; line-height: 1.7; margin: 0 0 16px; }
.msg { margin-top: 10px; font-size: 12px; color: #0f6e56; }
</style>
