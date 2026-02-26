# 数据中心服务器资产数据模型

## 核心实体

### Server（服务器）

| 字段 | 类型 | 说明 |
|------|------|------|
| asset_id | string | 资产编号（唯一标识） |
| sn | string | 序列号 |
| hostname | string | 主机名 |
| model | string | 型号（如 Dell R750, Huawei 2288H V6） |
| manufacturer | string | 厂商 |
| cpu_model | string | CPU 型号 |
| cpu_count | int | CPU 数量 |
| memory_gb | int | 内存容量（GB） |
| disk_info | string | 磁盘配置（如 8×960G SSD） |
| gpu_model | string | GPU 型号（可空） |
| gpu_count | int | GPU 数量 |
| os | string | 操作系统 |
| status | enum | 状态：in_use / idle / maintenance / decommissioned / in_stock |
| purpose | string | 用途标签（计算/存储/网络/GPU） |

### Location（位置）

| 字段 | 类型 | 说明 |
|------|------|------|
| dc_name | string | 数据中心名称 |
| room | string | 机房 |
| rack_id | string | 机柜编号 |
| u_start | int | 起始 U 位 |
| u_height | int | 占用 U 数 |

### Lifecycle（生命周期）

| 字段 | 类型 | 说明 |
|------|------|------|
| purchase_date | date | 采购日期 |
| deploy_date | date | 上架日期 |
| warranty_expire | date | 质保到期 |
| decommission_date | date | 下架日期（可空） |
| vendor_contract | string | 维保合同编号 |
| asset_owner | string | 资产责任人 |
| business_unit | string | 归属业务部门 |

### Network（网络）

| 字段 | 类型 | 说明 |
|------|------|------|
| mgmt_ip | string | 管理 IP |
| bmc_ip | string | BMC/IPMI IP |
| business_ips | list[string] | 业务 IP 列表 |
| vlan | string | VLAN |
| switch_port | string | 接入交换机端口 |

## 状态流转

```
in_stock → in_use → maintenance → in_use
                  → decommissioned
         → idle  → in_use
                 → decommissioned
```

## 常用聚合维度

- 按数据中心 / 机房 / 机柜
- 按状态（在用 / 空闲 / 维修 / 已下架）
- 按厂商 / 型号
- 按业务部门
- 按质保到期时间范围
- 按用途标签（计算 / 存储 / GPU）
