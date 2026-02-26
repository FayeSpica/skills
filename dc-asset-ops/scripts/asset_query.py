#!/usr/bin/env python3
"""
数据中心服务器资产查询工具

提供资产查询、统计、报表生成等功能。
数据源部分为接口占位，需对接实际 CMDB / 数据库 / API 后使用。

Usage:
    python asset_query.py inventory [--dc <dc_name>] [--status <status>] [--format json|csv|table]
    python asset_query.py summary [--dc <dc_name>]
    python asset_query.py rack <rack_id>
    python asset_query.py warranty [--days <days>]
    python asset_query.py search <keyword>
    python asset_query.py lifecycle <asset_id>
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Optional


# ============================================================
# 数据源接口（留空 — 对接实际系统时实现以下函数）
# ============================================================

def fetch_all_servers(dc_name: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
    """
    获取服务器列表。

    对接建议：
    - CMDB API: GET /api/v1/servers?dc={dc_name}&status={status}
    - 数据库: SELECT * FROM servers WHERE dc_name = ? AND status = ?
    - Excel/CSV: pandas.read_csv('assets.csv') 后过滤

    Returns:
        list[dict]: 服务器记录列表，每条记录字段参考 references/asset_schema.md
    """
    # TODO: 对接实际数据源
    raise NotImplementedError(
        "请实现 fetch_all_servers()，对接 CMDB / 数据库 / API。\n"
        "返回格式: [{'asset_id': '...', 'sn': '...', 'hostname': '...', ...}, ...]"
    )


def fetch_server_by_id(asset_id: str) -> Optional[dict]:
    """
    根据资产编号获取单台服务器详情。

    对接建议：
    - CMDB API: GET /api/v1/servers/{asset_id}
    - 数据库: SELECT * FROM servers WHERE asset_id = ?

    Returns:
        dict | None: 服务器记录，或 None（未找到）
    """
    # TODO: 对接实际数据源
    raise NotImplementedError(
        "请实现 fetch_server_by_id()，对接 CMDB / 数据库 / API。"
    )


def fetch_servers_by_rack(rack_id: str) -> list[dict]:
    """
    获取指定机柜内所有服务器，按 U 位排序。

    对接建议：
    - CMDB API: GET /api/v1/racks/{rack_id}/servers
    - 数据库: SELECT * FROM servers WHERE rack_id = ? ORDER BY u_start

    Returns:
        list[dict]: 服务器列表，按 u_start 升序
    """
    # TODO: 对接实际数据源
    raise NotImplementedError(
        "请实现 fetch_servers_by_rack()，对接 CMDB / 数据库 / API。"
    )


def fetch_warranty_expiring(days: int = 90) -> list[dict]:
    """
    获取即将过保的服务器（未来 N 天内到期）。

    对接建议：
    - 数据库: SELECT * FROM servers
              WHERE warranty_expire BETWEEN NOW() AND NOW() + INTERVAL ? DAY
              ORDER BY warranty_expire

    Returns:
        list[dict]: 即将过保的服务器列表
    """
    # TODO: 对接实际数据源
    raise NotImplementedError(
        "请实现 fetch_warranty_expiring()，对接 CMDB / 数据库 / API。"
    )


def search_servers(keyword: str) -> list[dict]:
    """
    模糊搜索服务器（匹配 asset_id / sn / hostname / mgmt_ip）。

    对接建议：
    - CMDB API: GET /api/v1/servers/search?q={keyword}
    - 数据库: SELECT * FROM servers
              WHERE asset_id LIKE ? OR sn LIKE ? OR hostname LIKE ? OR mgmt_ip LIKE ?

    Returns:
        list[dict]: 匹配的服务器列表
    """
    # TODO: 对接实际数据源
    raise NotImplementedError(
        "请实现 search_servers()，对接 CMDB / 数据库 / API。"
    )


def fetch_lifecycle_events(asset_id: str) -> list[dict]:
    """
    获取单台服务器的生命周期事件记录。

    对接建议：
    - CMDB API: GET /api/v1/servers/{asset_id}/lifecycle
    - 数据库: SELECT * FROM lifecycle_events WHERE asset_id = ? ORDER BY event_time

    Returns:
        list[dict]: 事件列表 [{'event_time': '...', 'event_type': '...', 'detail': '...'}, ...]
        event_type: purchase / deploy / maintenance / relocate / decommission
    """
    # TODO: 对接实际数据源
    raise NotImplementedError(
        "请实现 fetch_lifecycle_events()，对接 CMDB / 数据库 / API。"
    )


# ============================================================
# 业务逻辑（基于数据源接口构建，无需修改）
# ============================================================

def cmd_inventory(dc_name=None, status=None, fmt="table"):
    """资产清单查询。"""
    servers = fetch_all_servers(dc_name=dc_name, status=status)
    if fmt == "json":
        print(json.dumps(servers, indent=2, ensure_ascii=False, default=str))
    elif fmt == "csv":
        if not servers:
            print("无记录")
            return
        keys = ["asset_id", "sn", "hostname", "model", "status", "dc_name", "rack_id", "u_start", "mgmt_ip"]
        print(",".join(keys))
        for s in servers:
            print(",".join(str(s.get(k, "")) for k in keys))
    else:
        _print_server_table(servers)
    print(f"\n共 {len(servers)} 台服务器", file=sys.stderr)


def cmd_summary(dc_name=None):
    """资产统计摘要。"""
    servers = fetch_all_servers(dc_name=dc_name)

    total = len(servers)
    by_status = {}
    by_model = {}
    by_dc = {}
    by_purpose = {}

    for s in servers:
        st = s.get("status", "unknown")
        by_status[st] = by_status.get(st, 0) + 1

        model = s.get("model", "unknown")
        by_model[model] = by_model.get(model, 0) + 1

        dc = s.get("dc_name", "unknown")
        by_dc[dc] = by_dc.get(dc, 0) + 1

        purpose = s.get("purpose", "unknown")
        by_purpose[purpose] = by_purpose.get(purpose, 0) + 1

    print(f"=== 资产统计摘要 ===")
    if dc_name:
        print(f"数据中心: {dc_name}")
    print(f"总计: {total} 台\n")

    print("--- 按状态 ---")
    for k, v in sorted(by_status.items()):
        pct = v / total * 100 if total else 0
        print(f"  {k:<20s} {v:>5d}  ({pct:.1f}%)")

    print("\n--- 按用途 ---")
    for k, v in sorted(by_purpose.items(), key=lambda x: -x[1]):
        print(f"  {k:<20s} {v:>5d}")

    print("\n--- 按型号 (Top 10) ---")
    for k, v in sorted(by_model.items(), key=lambda x: -x[1])[:10]:
        print(f"  {k:<30s} {v:>5d}")

    print("\n--- 按数据中心 ---")
    for k, v in sorted(by_dc.items(), key=lambda x: -x[1]):
        print(f"  {k:<20s} {v:>5d}")


def cmd_rack(rack_id):
    """机柜视图 — 显示机柜内服务器分布。"""
    servers = fetch_servers_by_rack(rack_id)

    print(f"=== 机柜 {rack_id} ===")
    if not servers:
        print("  (空)")
        return

    # 构建 U 位占用映射
    max_u = 42  # 标准 42U 机柜
    u_map = {}
    for s in servers:
        u_start = s.get("u_start", 0)
        u_height = s.get("u_height", 1)
        for u in range(u_start, u_start + u_height):
            u_map[u] = s

    print(f"{'U':>3s}  {'状态':<6s}  {'资产编号':<14s}  {'主机名':<20s}  {'型号'}")
    print("-" * 75)
    for u in range(max_u, 0, -1):
        if u in u_map:
            s = u_map[u]
            # 只在设备起始 U 位显示信息
            if u == s.get("u_start", 0):
                h = s.get("u_height", 1)
                label = f"{u}-{u + h - 1}U" if h > 1 else f"{u}U"
                print(f"{label:>5s}  {s.get('status', ''):<6s}  "
                      f"{s.get('asset_id', ''):<14s}  "
                      f"{s.get('hostname', ''):<20s}  "
                      f"{s.get('model', '')}")
        else:
            print(f"{u:>3d}U  {'--空--'}")

    used = len(set(u_map.keys()))
    print(f"\n利用率: {used}/{max_u} U ({used / max_u * 100:.1f}%)")


def cmd_warranty(days=90):
    """质保到期预警。"""
    servers = fetch_warranty_expiring(days=days)
    print(f"=== 未来 {days} 天内质保到期 ({len(servers)} 台) ===\n")
    if not servers:
        print("  无即将过保设备")
        return
    for s in servers:
        expire = s.get("warranty_expire", "?")
        print(f"  {s.get('asset_id', ''):<14s}  "
              f"{s.get('hostname', ''):<20s}  "
              f"过保: {expire}  "
              f"合同: {s.get('vendor_contract', 'N/A')}")


def cmd_search(keyword):
    """模糊搜索服务器。"""
    servers = search_servers(keyword)
    print(f"=== 搜索 '{keyword}' — {len(servers)} 条结果 ===\n")
    _print_server_table(servers)


def cmd_lifecycle(asset_id):
    """单台服务器生命周期查看。"""
    server = fetch_server_by_id(asset_id)
    if not server:
        print(f"未找到资产: {asset_id}", file=sys.stderr)
        sys.exit(1)

    print(f"=== 资产 {asset_id} 生命周期 ===\n")
    print(f"  主机名:   {server.get('hostname', '')}")
    print(f"  型号:     {server.get('model', '')}")
    print(f"  SN:       {server.get('sn', '')}")
    print(f"  状态:     {server.get('status', '')}")
    print(f"  位置:     {server.get('dc_name', '')} / {server.get('rack_id', '')} / U{server.get('u_start', '')}")
    print(f"  责任人:   {server.get('asset_owner', '')}")
    print(f"  部门:     {server.get('business_unit', '')}")
    print()

    events = fetch_lifecycle_events(asset_id)
    if events:
        print("--- 事件记录 ---")
        for e in events:
            print(f"  {e.get('event_time', '?'):<20s}  "
                  f"[{e.get('event_type', '?'):<15s}]  "
                  f"{e.get('detail', '')}")


def _print_server_table(servers):
    """打印服务器列表表格。"""
    if not servers:
        print("  无记录")
        return
    print(f"  {'资产编号':<14s}  {'主机名':<20s}  {'型号':<20s}  {'状态':<8s}  {'位置'}")
    print("  " + "-" * 80)
    for s in servers:
        loc = f"{s.get('dc_name', '')} {s.get('rack_id', '')} U{s.get('u_start', '')}"
        print(f"  {s.get('asset_id', ''):<14s}  "
              f"{s.get('hostname', ''):<20s}  "
              f"{s.get('model', ''):<20s}  "
              f"{s.get('status', ''):<8s}  "
              f"{loc}")


# ============================================================
# CLI
# ============================================================

USAGE = """\
数据中心服务器资产查询工具

Usage:
    python asset_query.py inventory [--dc DC] [--status STATUS] [--format json|csv|table]
    python asset_query.py summary   [--dc DC]
    python asset_query.py rack      <rack_id>
    python asset_query.py warranty  [--days N]
    python asset_query.py search    <keyword>
    python asset_query.py lifecycle <asset_id>

Commands:
    inventory   资产清单查询
    summary     资产统计摘要（按状态/型号/数据中心）
    rack        机柜视图（U 位分布）
    warranty    质保到期预警
    search      模糊搜索（asset_id / sn / hostname / IP）
    lifecycle   单台设备生命周期

注意: 数据源接口尚未实现，需对接实际 CMDB / 数据库 / API 后使用。
"""


def _parse_arg(args, flag, default=None):
    """Simple arg parser for --flag value."""
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    return default


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)

    cmd = args[0]

    try:
        if cmd == "inventory":
            dc = _parse_arg(args, "--dc")
            status = _parse_arg(args, "--status")
            fmt = _parse_arg(args, "--format", "table")
            cmd_inventory(dc_name=dc, status=status, fmt=fmt)
        elif cmd == "summary":
            dc = _parse_arg(args, "--dc")
            cmd_summary(dc_name=dc)
        elif cmd == "rack":
            if len(args) < 2:
                print("Error: rack_id required", file=sys.stderr)
                sys.exit(1)
            cmd_rack(args[1])
        elif cmd == "warranty":
            days = int(_parse_arg(args, "--days", "90"))
            cmd_warranty(days=days)
        elif cmd == "search":
            if len(args) < 2:
                print("Error: keyword required", file=sys.stderr)
                sys.exit(1)
            cmd_search(args[1])
        elif cmd == "lifecycle":
            if len(args) < 2:
                print("Error: asset_id required", file=sys.stderr)
                sys.exit(1)
            cmd_lifecycle(args[1])
        else:
            print(f"Unknown command: {cmd}\n", file=sys.stderr)
            print(USAGE)
            sys.exit(1)
    except NotImplementedError as e:
        print(f"[数据源未对接] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
