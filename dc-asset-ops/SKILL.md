---
name: dc-asset-ops
description: 数据中心服务器资产运营管理。用于查询服务器资产清单、统计摘要（按状态/型号/数据中心/用途）、机柜 U 位视图、质保到期预警、资产模糊搜索、单台设备生命周期追踪。当用户提到服务器资产、机柜、上下架、质保、CMDB、资产盘点、容量规划等场景时触发。
---

# 数据中心服务器资产运营

服务器资产全生命周期运营工具：清单查询、统计分析、机柜视图、质保预警、生命周期追踪。

## 数据源对接

脚本中的数据获取函数为接口占位（`raise NotImplementedError`），需对接实际系统后使用。

打开 `scripts/asset_query.py`，实现以下函数：

| 函数 | 用途 | 对接建议 |
|------|------|----------|
| `fetch_all_servers()` | 获取服务器列表 | CMDB API / 数据库 SELECT |
| `fetch_server_by_id()` | 按资产编号查单台 | CMDB API / 数据库 |
| `fetch_servers_by_rack()` | 按机柜查服务器 | 数据库 JOIN |
| `fetch_warranty_expiring()` | 质保到期查询 | 数据库 WHERE warranty_expire BETWEEN |
| `search_servers()` | 模糊搜索 | LIKE / 全文检索 |
| `fetch_lifecycle_events()` | 生命周期事件 | 事件表 / 工单系统 API |

返回格式参考 [references/asset_schema.md](references/asset_schema.md)。

## 功能

### 1. 资产清单查询

```bash
python scripts/asset_query.py inventory                          # 全量
python scripts/asset_query.py inventory --dc 北京一号 --status idle  # 按条件
python scripts/asset_query.py inventory --format json            # JSON 输出
python scripts/asset_query.py inventory --format csv             # CSV 导出
```

### 2. 资产统计摘要

按状态、用途、型号（Top 10）、数据中心分组统计。

```bash
python scripts/asset_query.py summary
python scripts/asset_query.py summary --dc 上海二号
```

### 3. 机柜 U 位视图

可视化展示机柜内设备分布与利用率。

```bash
python scripts/asset_query.py rack A01-R05
```

### 4. 质保到期预警

```bash
python scripts/asset_query.py warranty             # 默认 90 天
python scripts/asset_query.py warranty --days 30   # 30 天内到期
```

### 5. 资产搜索

模糊匹配 asset_id / SN / hostname / IP。

```bash
python scripts/asset_query.py search 10.0.1.55
python scripts/asset_query.py search web-prod
```

### 6. 设备生命周期

查看单台设备信息及全部生命周期事件（采购、上架、维修、搬迁、下架）。

```bash
python scripts/asset_query.py lifecycle SV-2024-001234
```

## 数据模型

完整字段定义见 [references/asset_schema.md](references/asset_schema.md)，涵盖：

- **Server** — 硬件配置、状态、用途
- **Location** — 数据中心、机房、机柜、U 位
- **Lifecycle** — 采购、质保、责任人、部门
- **Network** — 管理 IP、BMC、业务 IP、交换机端口
