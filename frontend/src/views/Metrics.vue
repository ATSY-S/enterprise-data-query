<template>
  <div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>业务指标口径</div>
      <div class="code-tip">这些定义来自后端的语义层。大模型生成 SQL 时会读到它们，
        所以「核销率」「客单价」这些词不会算错。这是企业 BI 里"语义层"的简化实现。</div>
      <el-table :data="metrics" size="small" stripe style="margin-top:14px">
        <el-table-column prop="name" label="指标" width="120" />
        <el-table-column prop="expr" label="计算方式" min-width="320" />
        <el-table-column prop="desc" label="说明" min-width="300" />
      </el-table>
    </div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>业务维度</div>
      <el-table :data="dimensions" size="small" stripe>
        <el-table-column prop="name" label="维度" width="120" />
        <el-table-column prop="desc" label="说明" min-width="500" />
      </el-table>
    </div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>业务术语</div>
      <el-table :data="terms" size="small" stripe>
        <el-table-column prop="name" label="术语" width="140" />
        <el-table-column prop="desc" label="含义" min-width="500" />
      </el-table>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { authHeader } from '../auth'
const metrics = ref([]), dimensions = ref([]), terms = ref([])
onMounted(async () => {
  try {
    const r = await axios.get('/api/semantics', { headers: authHeader() })
    const d = r.data?.data ?? r.data
    metrics.value = d.metrics || []
    dimensions.value = d.dimensions || []
    terms.value = d.terms || []
  } catch {}
})
</script>
