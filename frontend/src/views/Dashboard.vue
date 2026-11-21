<template>
  <div>
    <div class="stats">
      <div class="stat"><div class="label">订单数据</div><div class="value">20,000</div><div class="hint">orders + 37,508 条明细</div></div>
      <div class="stat"><div class="label">客户 / 商品</div><div class="value">600 / 20</div><div class="hint">customers / products</div></div>
      <div class="stat"><div class="label">优惠券 / 活动</div><div class="value">3,682 / 36</div><div class="hint">coupons / activities</div></div>
      <div class="stat"><div class="label">覆盖时间</div><div class="value">2024–2025</div><div class="hint">两年，含旺季与淡季</div></div>
    </div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>系统能做什么</div>
      <div class="feature-grid">
        <div><b>自然语言查询</b><br>输入中文问题，自动生成 SQL，查真实数据库。</div>
        <div><b>结果可视化</b><br>自动画柱状图/折线图/饼图，可导出 Excel。</div>
        <div><b>SQL 可查看</b><br>每条结果都显示生成的 SQL，看得见、可追溯。</div>
        <div><b>口径管理</b><br>核销率、客单价等指标口径集中定义，减少歧义。</div>
        <div><b>自动纠错</b><br>SQL 执行失败时，把错误回灌模型自动重试。</div>
        <div><b>查询留痕</b><br>所有问题与 SQL 存入本地历史，便于审计复盘。</div>
      </div>
    </div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>开始使用</div>
      <div class="code-tip">在左侧点击「智能查询」，试试这些问题：<br>
        · 各品类的销售额分别是多少？<br>
        · 核销率最高的 3 个活动是哪几个？<br>
        · 2025 年月度销售额趋势，画折线图</div>
      <el-button type="primary" style="margin-top:14px" @click="$emit('go','chat')">进入智能查询</el-button>
    </div>
  </div>
</template>
