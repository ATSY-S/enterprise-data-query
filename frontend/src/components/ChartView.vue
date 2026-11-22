<template>
  <div class="chart-card" v-if="chart && chart.available">
    <div class="chart-head">
      <div class="chart-title">{{ chart.title || '查询结果图表' }}</div>
      <div class="chart-actions">
        <el-radio-group v-model="localType" size="small" @change="render">
          <el-radio-button value="bar">柱状</el-radio-button>
          <el-radio-button value="line">折线</el-radio-button>
          <el-radio-button value="pie">饼图</el-radio-button>
        </el-radio-group>
        <el-button size="small" @click="zoom = true">放大</el-button>
        <el-button size="small" @click="download">下载 PNG</el-button>
      </div>
    </div>
    <div ref="smallEl" class="chart-small"></div>
    <div class="chart-tip">悬停查看数值 · 点击图例可隐藏系列 · 放大后可滚轮缩放</div>

    <el-dialog v-model="zoom" width="92%" top="4vh" :title="chart.title || '查询结果图表'"
               class="chart-dialog" destroy-on-close>
      <div ref="bigEl" class="chart-big"></div>
      <template #footer>
        <el-button @click="download">下载 PNG</el-button>
        <el-button type="primary" @click="zoom = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({ chart: { type: Object, default: null } })
const smallEl = ref(null)
const bigEl = ref(null)
const zoom = ref(false)
const localType = ref(props.chart?.type || 'bar')
let smallChart = null
let bigChart = null

const PALETTE = ['#2563eb', '#0891b2', '#7c3aed', '#059669', '#d97706']

function option(big = false) {
  const c = props.chart
  const type = localType.value
  const base = {
    color: PALETTE,
    animationDuration: 500,
    backgroundColor: 'transparent',
    tooltip: {
      trigger: type === 'pie' ? 'item' : 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#ffffff', borderColor: '#d1d5db', borderWidth: 1,
      textStyle: { color: '#1f2937', fontSize: 12 },
      extraCssText: 'box-shadow:0 4px 12px rgba(0,0,0,.08);border-radius:6px;',
    },
    legend: { bottom: 0, textStyle: { color: '#6b7280', fontSize: 11 }, type: 'scroll' },
    grid: { left: 16, right: 24, top: 36, bottom: 56, containLabel: true },
  }
  if (type === 'pie') {
    return {
      ...base,
      series: [{
        name: c.series[0]?.name || '数值', type: 'pie', radius: big ? ['32%', '62%'] : ['28%', '58%'],
        center: ['50%', '46%'],
        itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
        label: { formatter: '{b}: {d}%', fontSize: 11, color: '#374151' },
        data: c.labels.map((l, i) => ({ name: l, value: c.series[0].data[i] })),
      }],
    }
  }
  return {
    ...base,
    xAxis: {
      type: 'category', data: c.labels, name: c.x_name || '', nameLocation: 'middle', nameGap: 34,
      axisLabel: { color: '#6b7280', fontSize: 11, interval: 'auto', hideOverlap: true },
      axisLine: { lineStyle: { color: '#d1d5db' } },
    },
    yAxis: {
      type: 'value', name: c.y_name || '', nameTextStyle: { color: '#9ca3af', fontSize: 11 },
      axisLabel: { color: '#9ca3af', fontSize: 11, formatter: v => Math.abs(v) >= 10000 ? (v / 10000).toFixed(0) + '万' : v },
      splitLine: { lineStyle: { color: '#eef2f7' } },
    },
    dataZoom: c.labels.length > 14 ? [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', height: 16, bottom: 34, borderColor: '#e5e7eb', fillerColor: 'rgba(37,99,235,.12)',
        handleStyle: { color: '#2563eb' }, textStyle: { color: '#9ca3af', fontSize: 10 } },
    ] : [],
    series: c.series.map(s => ({
      name: s.name, type, data: s.data,
      barMaxWidth: 44, smooth: type === 'line', showSymbol: c.labels.length < 20,
      symbolSize: 6, lineStyle: { width: 2 },
      itemStyle: { borderRadius: type === 'bar' ? [5, 5, 0, 0] : 0 },
      areaStyle: type === 'line' ? { opacity: 0.08 } : undefined,
    })),
  }
}

function render() {
  if (!props.chart?.available) return
  if (smallChart) smallChart.setOption(option(false), true)
  if (zoom.value && bigChart) bigChart.setOption(option(true), true)
}

function download() {
  const inst = zoom.value && bigChart ? bigChart : smallChart
  if (!inst) return
  const url = inst.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' })
  const a = document.createElement('a')
  a.href = url
  a.download = (props.chart.title || 'chart').replace(/[\\/:*?"<>|]/g, '_') + '.png'
  a.click()
}

onMounted(async () => {
  await nextTick()
  if (smallEl.value) smallChart = echarts.init(smallEl.value)
  render()
  window.addEventListener('resize', resize)
})
function resize() { smallChart?.resize(); bigChart?.resize() }
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  smallChart?.dispose(); bigChart?.dispose()
})
watch(() => props.chart, async () => {
  localType.value = props.chart?.type || 'bar'
  await nextTick()
  render()
})
watch(zoom, async v => {
  if (v) {
    await nextTick()
    if (bigEl.value) {
      bigChart?.dispose()
      bigChart = echarts.init(bigEl.value)
      bigChart.setOption(option(true), true)
    }
  }
})
</script>

<style scoped>
.chart-card { margin-top: 12px; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; background: #fff; }
.chart-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
.chart-title { font-size: 13px; font-weight: 500; color: #1a4d73; }
.chart-actions { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.chart-small { width: 100%; height: 300px; }
.chart-big { width: 100%; height: 68vh; }
.chart-tip { font-size: 11px; color: #9ca3af; text-align: center; margin-top: 2px; }
</style>
