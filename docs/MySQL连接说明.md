# MySQL 连接说明

> 2026-11-26 更新。解决 DataGrip 报 `[28000][1045] Access denied for user 'root'@'localhost'`。

## 一、为什么之前连不上

服务能启动但密码不对，根因是**初始化方式**：

昨天修复 MySQL80 服务时，数据目录是空的，我用了 `mysqld --initialize-insecure` 初始化——这个参数会把 root 建成**空密码**账号。所以你用 `123456` 连接必然被拒，报 1045。

## 二、已修复

已执行：

```sql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';
FLUSH PRIVILEGES;
```

验证结果：
- `root / 123456` → 连接成功，版本 8.0.41
- 空密码 → 被拒绝（说明密码确实生效）

## 三、DataGrip 连接参数

| 项 | 值 |
|---|---|
| 主机 | `localhost` 或 `127.0.0.1` |
| 端口 | `3306` |
| 用户 | `root` |
| 密码 | `123456` |
| 认证方式 | 用户密码（mysql_native_password） |

命令行验证：

```bash
D:\123\bin\mysql.exe -h127.0.0.1 -uroot -p123456 -e "SELECT VERSION();"
```

## 四、重要提醒：原来的业务库不在了

当前实例只有 4 个系统库：`information_schema`、`mysql`、`performance_schema`、`sys`。

你截图里看到的 `dorm_management`（学生宿舍管理）、`sakila`、`sala` 等业务库，**本机已经找不到对应的数据文件**——大概率是原来那个 MySQL 安装的数据目录被清空时一起丢了。我全盘搜过 `ibdata1` 和 `dorm_management` 目录，都没有。

如果那些库对你重要，只能从备份恢复（如果有）。但要注意：**毕业设计项目完全不依赖 MySQL**，它用的是 SQLite 文件：

```
D:\web课程\企业数据智能查询系统\data\enterprise.db   （8 张业务表、2 万订单）
```

DataGrip 想看论文项目的数据，应该新建 **SQLite** 数据源，指向上面这个 `.db` 文件，而不是连 MySQL。

## 五、修复脚本已更新

`docs/fix-mysql-service.bat` 和 `docs/启动MYSQL80服务.bat` 已更新：如果将来重新初始化数据目录，脚本会自动把 root 密码设成 `123456`，不会再出现空密码的情况。
