# MySQL 业务库丢失说明

> 2026-11-26。解决 DataGrip 报 `[42000][1049] Unknown database 'dorm_management'`。

## 一、这次是什么错（和上次密码错不是一回事）

| 报错 | 含义 | 状态 |
|---|---|---|
| `[28000][1045] Access denied ... using password: YES` | 密码不对 | 已解决（root 密码改成 123456） |
| `[42000][1049] Unknown database 'dorm_management'` | **密码对了，但这个库不存在** | 本次问题 |

所以现在连接是正常的，只是 DataGrip 那个查询窗口还指向一个不存在的库。

## 二、为什么库没了

11-24 修 MySQL 服务时发现：`C:\ProgramData\MySQL\MySQL Server 8.0` 整个目录是空的——**没有 my.ini、没有数据目录**。服务一直指向这个不存在的配置，所以启动即失败。

我重新初始化了数据目录（`mysqld --initialize-insecure`），生成的是**全新的空实例**，只有 4 个系统库。你原来那些业务库（dorm_management、sakila、sala 等）的数据文件，随着旧数据目录一起没了。

我全盘搜索过：
- `ibdata1`（InnoDB 核心数据文件）——除了新建的，没有别的
- `dorm_management` 目录——不存在
- `*.sql` 备份——只找到 `db_dorm.sql`（另一个项目，`t_admin`/`t_student` 那套表，不是 dorm_management）
- DataGrip 查询历史——只有数据库课的 Student 表练习语句，不是完整备份

**结论：dorm_management 的原始数据在本机找不到了。**

## 三、我已做的处理

创建了空的 `dorm_management` 库（utf8mb4），这样 DataGrip 再执行查询不会再报 1049。但库里**没有表、没有数据**。

DataGrip 左侧那些表名（bed_infos、students 等）是旧缓存，不是真实存在的。在 DataGrip 里：

1. 右键 `@localhost` 连接 → **刷新**（或按 F5）
2. 左侧树会更新成真实的库：`dorm_management`（空）、`mysql`、`information_schema`、`performance_schema`、`sys`
3. 关掉旧的 console_3 等查询窗口，重新打开，先 `USE dorm_management;` 再查

## 四、还能怎么恢复

按可能性排序：

1. **找备份**：如果有这个宿舍管理系统的源码包或数据库导出（`.sql`），直接导入：
   ```bash
   D:\123\bin\mysql.exe -h127.0.0.1 -uroot -p123456 dorm_management < 备份.sql
   ```
   我找到的 `D:\数据库\...\db_dorm.sql` 是另一个项目（t_admin/t_student），不是这个库——先确认别弄混。

2. **从 Git 仓库找**：如果这个项目源码提交过 `schema.sql` 或 migration 文件，可以重建表结构（数据还是得另找）。

3. **接受丢失**：如果这些只是课程练习数据，且你有源码能重新跑建表脚本，重建即可。

## 五、和毕业设计的关系

**这件事不影响你的论文。** 毕业设计用的是 SQLite 文件：

```
D:\web课程\企业数据智能查询系统\data\enterprise.db
```

里面 8 张表、2 万订单完好无损。DataGrip 想看论文数据，新建 **SQLite** 数据源指向这个 `.db` 文件即可，不用连 MySQL。

## 六、以后怎么避免

- 数据目录别放在会被清理的位置；定期 `mysqldump` 备份：
  ```bash
  mysqldump -h127.0.0.1 -uroot -p123456 --all-databases > backup.sql
  ```
- 服务修复脚本 `docs/fix-mysql-service.bat` 已更新，重新初始化时会自动把 root 密码设成 123456，不会再出现密码对不上的情况。
