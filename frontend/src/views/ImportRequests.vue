<template>
  <div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>提交导入申请</div>
      <p class="intro">选择 Excel/CSV 文件并说明用途，管理员审核通过后会将数据正式导入数据库。您无需接触数据库。</p>
      <el-form label-width="100px" style="max-width:640px">
        <el-form-item label="数据文件">
          <el-upload :auto-upload="false" :limit="1" accept=".csv,.xlsx,.xls"
                     :on-change="onFile" :on-exceed="()=>$message.warning('只能选一个文件')">
            <el-button size="small">{{ file?.name || '选择文件' }}</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="目标表">
          <el-select v-model="form.table" placeholder="选择要追加到的业务表" style="width:100%">
            <el-option v-for="t in tables" :key="t" :label="tableLabel[t] || t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="用途说明"><el-input v-model="form.reason" type="textarea" :rows="2" placeholder="简单说明这批数据的来源与用途" /></el-form-item>
        <el-form-item><el-button type="primary" :loading="busy" @click="submit">提交申请</el-button></el-form-item>
      </el-form>
      <div v-if="msg" class="msg" :class="msgOk?'ok':'bad'">{{ msg }}</div>
    </div>

    <div class="card">
      <div class="card-title"><span class="bar"></span>我的申请记录</div>
      <el-table :data="rows" size="small" stripe>
        <el-table-column prop="id" label="编号" width="70" />
        <el-table-column prop="ts" label="提交时间" width="170" />
        <el-table-column prop="filename" label="文件名" min-width="180" />
        <el-table-column prop="table" label="目标表" width="130" />
        <el-table-column label="状态" width="110"><template #default="{row}">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template></el-table-column>
        <el-table-column prop="imported_rows" label="导入行数" width="100" />
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
const tableLabel = { orders:'订单表', order_items:'订单明细', customers:'客户表', products:'商品表', stores:'门店表', activities:'活动表', coupons:'优惠券表' }
const form = ref({ table:'', reason:'' })
const file = ref(null)
const rows = ref([]), busy = ref(false), msg = ref(''), msgOk = ref(false)
const statusText = s => ({ pending:'待审批', approved:'已批准', rejected:'已驳回', imported:'已导入' }[s] || s)
const statusType = s => ({ pending:'warning', approved:'success', rejected:'danger', imported:'success' }[s] || 'info')
function onFile(f) { file.value = f.raw; form.value.table = '' }
async function load() {
  try { const r = await axios.get('/api/requests', { headers: authHeader() }); rows.value = r.data?.data ?? [] } catch {}
}
async function submit() {
  if (!file.value || !form.value.table) { msgOk.value=false; msg.value = '请选择文件并指定目标表'; return }
  busy.value = true; msg.value = ''
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('table', form.value.table)
  fd.append('reason', form.value.reason)
  try {
    const r = await axios.post('/api/requests', fd, { headers: authHeader() })
    const d = r.data?.data ?? r.data
    msgOk.value = !!d.success
    msg.value = d.success ? `${d.message}（共 ${d.rows} 行）` : (d.message || '提交失败')
    if (d.success) { file.value = null; form.value = { table:'', reason:'' }; load() }
  } catch (e) { msgOk.value=false; msg.value = '请求失败：' + e.message }
  finally { busy.value = false }
}
onMounted(load)
</script>

<style scoped>
.intro { font-size: 13px; color: #6b7280; line-height: 1.7; margin: 0 0 16px; }
.msg { margin-top: 10px; font-size: 12px; }
.msg.ok { color: #0f6e56; }
.msg.bad { color: #a32d2d; }
</style>
