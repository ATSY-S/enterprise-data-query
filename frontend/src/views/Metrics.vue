<template>
  <div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>业务指标口径</div>
      <div class="code-tip">这些定义来自后端的 semantic.py。大模型生成 SQL 时会读到它们，
        所以「核销率」「客单价」这些词不会算错。这是企业 BI 里"语义层"的简化实现。</div>
      <el-table :data="metrics" size="small" stripe style="margin-top:14px">
        <el-table-column prop="name" label="指标" width="120" />
        <el-table-column prop="expr" label="计算方式" min-width="300" />
        <el-table-column prop="desc" label="说明" min-width="280" />
      </el-table>
    </div>
    <div class="card">
      <div class="card-title"><span class="bar"></span>数据表结构</div>
      <el-table :data="tables" size="small" stripe>
        <el-table-column prop="name" label="表名" width="130" />
        <el-table-column prop="cols" label="字段" min-width="420" />
        <el-table-column prop="desc" label="用途" min-width="200" />
      </el-table>
    </div>
  </div>
</template>
<script setup>
const metrics = [
  {name:'销售额',expr:'SUM(orders.sales_amount)',desc:'订单实付金额之和，单位元'},
  {name:'订单量',expr:'COUNT(orders.id)',desc:'订单笔数'},
  {name:'客单价',expr:'AVG(orders.sales_amount)',desc:'平均每笔订单金额'},
  {name:'销量',expr:'SUM(orders.quantity)',desc:'售出商品件数'},
  {name:'核销率',expr:"COUNT(status='已核销') / COUNT(id)",desc:'已核销券数 / 已领取券数'},
  {name:'预算',expr:'SUM(activities.budget)',desc:'活动预算总和'},
]
const tables = [
  {name:'orders',cols:'id, order_date, store_id, category, product_name, region, sales_amount, quantity',desc:'销售订单（2400 行）'},
  {name:'activities',cols:'id, activity_name, channel, start_date, end_date, budget',desc:'营销活动（12 行）'},
  {name:'coupons',cols:'id, activity_id, store_id, receive_date, verify_date, status',desc:'优惠券（514 行）'},
  {name:'stores',cols:'id, store_name, region, city',desc:'门店维表（16 行）'},
]
</script>
