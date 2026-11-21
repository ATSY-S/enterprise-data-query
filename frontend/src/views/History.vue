<template>
  <div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>最近查询</div>
      <el-button size="small" style="float:right;margin-top:-30px" @click="load">刷新</el-button>
      <el-table :data="rows" size="small" stripe>
        <el-table-column prop="ts" label="时间" width="180" />
        <el-table-column prop="question" label="问题" min-width="240" />
        <el-table-column prop="sql" label="生成的 SQL" min-width="320" show-overflow-tooltip />
        <el-table-column label="状态" width="90"><template #default="{row}">
          <el-tag :type="row.success?'success':'danger'" size="small">{{ row.success?'成功':'失败' }}</el-tag>
        </template></el-table-column>
        <el-table-column prop="rows" label="行数" width="70" />
        <el-table-column prop="elapsed" label="耗时(s)" width="80" />
      </el-table>
      <div v-if="!rows.length" class="empty">暂无查询记录，先去「智能查询」问一句吧。</div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
const rows = ref([])
async function load(){ try { rows.value = (await axios.get('/api/history?limit=50')).data.data } catch(e){} }
onMounted(load)
</script>
