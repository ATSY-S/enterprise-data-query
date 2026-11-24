<template>
  <div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>技术架构</div>
      <div class="code-tip">
        提问 → 提示词（表结构 + 指标口径）→ DeepSeek 生成 SQL → 只读执行 → 报错自动回灌修正 → 表格 / 图表 / 导出<br>
        前端 Vue 3 + Element Plus；后端 FastAPI；模型 DeepSeek；数据库 SQLite；图表 ECharts。
      </div>
    </div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>安全与边界</div>
      <div style="font-size:13px;line-height:2;color:#4b5563">
        · 只允许 SELECT / WITH，拒绝任何写操作与多语句注入（代码层守卫）。<br>
        · 所有查询写入本地历史记录，可追溯。<br>
        · 当前仅支持单表与简单两表关联，多层嵌套子查询不在支持范围。<br>
        · 数据为本地模拟生成，不含任何真实业务数据。
      </div>
    </div>
  </div>
</template>
