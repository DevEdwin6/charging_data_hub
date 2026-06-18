"""
ptt_rebuild.py — 从数据库重建补全 ptt.js

数据来源：
  station_sites              → 站点名、地址、营业时间、经纬度
  connector_status_snapshots → 充电桩、枪口、功率、价格（日/夜）、状态

处理规则：
  - 站点有快照数据  → 用快照完整重建 chargers（保留 position_cn）
  - 站点无快照数据  → 保留 ptt.js 原有 chargers 不动
  - DB 有但 ptt.js 没有的站点 → 追加到末尾
  - ptt.js 有但 DB 没有的站点  → 原样保留

用法：
    python utils/ptt_rebuild.py                         # 写 web/data/ptt_new.js
    python utils/ptt_rebuild.py --output /path/out.js   # 指定输出路径
    python utils/ptt_rebuild.py --platform ev_station_pluz
"""

import re
import json
import logging
import argparse
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config
import db
from utils.ptt_sync import load_ptt_stations

PLATFORM_CODE = "ev_station_pluz"
DEFAULT_INPUT  = Path(__file__).parent.parent / "web" / "data" / "ptt.js"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "web" / "data" / "ptt_new.js"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── 工具函数 ───────────────────────────────────────────────────────────────

def _f(val) -> float | None:
    """Decimal / int / float → Python float，None 原样返回。"""
    return float(val) if val is not None else None


def extract_connector_type(raw: str) -> str:
    """
    从复合 connector_type 字符串中提取纯类型名。
    "DC CCS COMBO 2 Max 40 kW | 9.00 ฿/kWh"  →  "DC CCS COMBO 2"
    "AC Type 2 Max 22 kW | 9.00 ฿/kWh"        →  "AC Type 2"
    """
    if not raw:
        return ""
    m = re.match(r'^(.*?)\s+(?:Max\s+\d|\|)', raw.strip())
    return m.group(1).strip() if m else raw.strip()


def charger_ac_dc(connector_type: str) -> str:
    """从枪口类型推断充电桩 AC/DC。"""
    upper = connector_type.upper()
    if upper.startswith("DC"):
        return "DC"
    if upper.startswith("AC"):
        return "AC"
    return "AC"


def parse_hours_text(hours_text: str | None) -> str | None:
    """
    将 hours_text JSON 转为人读字符串。
    {"hours": "24小时"}                       →  "24小时"
    {"Monday": "24 hours", ...}（全天相同）    →  "24 hours"
    {"Monday": "08:00-22:00", ...}（不同）     →  "Mon: 08:00-22:00; ..."
    """
    if not hours_text:
        return None
    try:
        data = json.loads(hours_text)
    except (json.JSONDecodeError, TypeError):
        return str(hours_text) or None

    if not data:
        return None

    # 我们导入时写的格式
    if "hours" in data:
        return data["hours"] or None

    # scraper 写的 hours_by_day 格式
    vals = list(set(v for v in data.values() if v))
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    return "; ".join(f"{k[:3]}: {v}" for k, v in sorted(data.items()) if v)


# ── 数据库查询 ─────────────────────────────────────────────────────────────

def query_station_sites(platform_code: str) -> dict[int, dict]:
    """返回 {station_id: row_dict}。"""
    conn = db._get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, station_name, brief_address, address,
               hours_text, latitude, longitude
        FROM station_sites
        WHERE platform_code = %s
        """,
        (platform_code,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return {r["id"]: r for r in rows}


def query_all_snapshots(platform_code: str) -> dict[int, list[dict]]:
    """
    返回 {station_id: [snap_dict, ...]}，每个站点的快照按 collected_at 降序。
    一次性加载全部，避免 N+1 查询。
    """
    conn = db._get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT css.station_id, css.platform_unit_id, css.unit_name,
               css.connector_name, css.connector_type,
               css.power_kw, css.status,
               css.day_price_per_kwh, css.night_price_per_kwh,
               css.collected_at
        FROM connector_status_snapshots css
        INNER JOIN station_sites ss ON ss.id = css.station_id
        WHERE ss.platform_code = %s
        ORDER BY css.station_id, css.platform_unit_id, css.connector_name, css.collected_at DESC
        """,
        (platform_code,),
    )
    rows = cursor.fetchall()
    cursor.close()

    result: dict[int, list] = defaultdict(list)
    for row in rows:
        result[row["station_id"]].append(row)
    return dict(result)


# ── chargers 重建 ──────────────────────────────────────────────────────────

def _build_pos_cn_lookup(orig_chargers: list) -> dict[tuple, str]:
    """
    从 ptt.js 原有 chargers 建立 (charger_name_suffix, position) → position_cn 映射。
    DB 中 platform_unit_id 只存数字后缀（如 "240356"），
    而 ptt.js charger name 是完整编号（如 "THPORE240356"），用后缀匹配。
    """
    lookup: dict[tuple, str] = {}
    for ch in (orig_chargers or []):
        ch_name = ch.get("name", "")
        for conn in ch.get("connectors", []):
            pos_cn = conn.get("position_cn")
            if pos_cn:
                lookup[(ch_name, conn.get("position", ""))] = pos_cn
    return lookup


def _find_pos_cn(lookup: dict, uid: str, position: str) -> str | None:
    """通过后缀匹配在 lookup 中找 position_cn。"""
    # 精确匹配
    if (uid, position) in lookup:
        return lookup[(uid, position)]
    # 后缀匹配：ptt.js 的 charger name 末尾含 uid
    for (ch_name, pos), cn in lookup.items():
        if pos == position and (ch_name.endswith(uid) or uid.endswith(ch_name)):
            return cn
    return None


def build_chargers_from_snaps(snaps: list[dict], orig_chargers: list) -> list[dict]:
    """
    从 connector_status_snapshots 行重建 chargers 列表。

    - 按 platform_unit_id 分组为充电桩
    - 按 connector_name 分组为枪口
    - 价格取最新非 NULL 的 day/night 各一条
    - 状态/功率/类型取最新行
    - position_cn 从 orig_chargers 后缀匹配保留
    """
    pos_cn_lookup = _build_pos_cn_lookup(orig_chargers)

    # 按 (platform_unit_id, connector_name) 分组
    unit_conn: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for snap in snaps:
        uid   = snap["platform_unit_id"] or ""
        cname = snap["connector_name"]   or ""
        unit_conn[uid][cname].append(snap)

    chargers = []
    for uid, conn_map in sorted(unit_conn.items()):
        connectors    = []
        unit_type     = None
        unit_max_kw   = None

        for cname, csnaps in sorted(conn_map.items()):
            # 已按 collected_at DESC 排序
            latest    = csnaps[0]
            day_price   = next((_f(s["day_price_per_kwh"])   for s in csnaps if s["day_price_per_kwh"]   is not None), None)
            night_price = next((_f(s["night_price_per_kwh"]) for s in csnaps if s["night_price_per_kwh"] is not None), None)

            raw_type   = latest.get("connector_type") or ""
            conn_type  = extract_connector_type(raw_type)
            power_kw   = _f(latest.get("power_kw"))
            status     = (latest.get("status") or "").lower()

            if power_kw and (unit_max_kw is None or power_kw > unit_max_kw):
                unit_max_kw = power_kw

            ac_dc = charger_ac_dc(conn_type)
            if ac_dc == "DC":
                unit_type = "DC"
            elif unit_type is None:
                unit_type = "AC"

            conn_dict: dict = {"position": cname}
            pos_cn = _find_pos_cn(pos_cn_lookup, uid, cname)
            if pos_cn:
                conn_dict["position_cn"] = pos_cn
            if conn_type:
                conn_dict["type"] = conn_type
            if power_kw is not None:
                conn_dict["kw"] = power_kw
            if day_price is not None:
                conn_dict["price_day"] = day_price
            if night_price is not None:
                conn_dict["price_night"] = night_price
            if status:
                conn_dict["status"] = status
            connectors.append(conn_dict)

        charger: dict = {
            "name":  uid,
            "type":  unit_type or "AC",
            "heads": len(connectors),
        }
        if unit_max_kw:
            charger["kw"] = unit_max_kw
        if connectors:
            charger["connectors"] = connectors
        chargers.append(charger)

    return chargers


# ── 站点合并 ───────────────────────────────────────────────────────────────

def merge_station(ptt_entry: dict, db_row: dict, snaps: list[dict]) -> dict:
    """
    将 DB 数据合并进 ptt.js 站点 dict，返回更新后的 dict。
    chargers：有快照则重建；无快照则保留原样。
    """
    result = dict(ptt_entry)

    # 地址
    addr = db_row.get("brief_address") or db_row.get("address")
    if addr:
        result["address"] = addr

    # 营业时间
    hours = parse_hours_text(db_row.get("hours_text"))
    if hours:
        result["hours"] = hours

    # 经纬度（DB 有则更新，保证精度）
    if db_row.get("latitude") is not None:
        result["lat"] = float(db_row["latitude"])
    if db_row.get("longitude") is not None:
        result["lon"] = float(db_row["longitude"])

    # chargers
    if snaps:
        result["chargers"] = build_chargers_from_snaps(snaps, ptt_entry.get("chargers", []))
    # else: 保留 ptt_entry 原有 chargers 不动

    return result


def build_new_station(db_row: dict, snaps: list[dict]) -> dict:
    """为 DB 有但 ptt.js 无的站点构建新条目。"""
    entry: dict = {"name": db_row["station_name"]}
    if db_row.get("latitude") is not None:
        entry["lat"] = float(db_row["latitude"])
    if db_row.get("longitude") is not None:
        entry["lon"] = float(db_row["longitude"])
    addr = db_row.get("brief_address") or db_row.get("address")
    if addr:
        entry["address"] = addr
    hours = parse_hours_text(db_row.get("hours_text"))
    if hours:
        entry["hours"] = hours
    if snaps:
        entry["chargers"] = build_chargers_from_snaps(snaps, [])
    return entry


# ── 输出 ───────────────────────────────────────────────────────────────────

def write_ptt_js(stations: list[dict], output_path: Path):
    """将站点列表写成 window.PTT_DATA = [...]; 格式。"""
    content = (
        "window.PTT_DATA = "
        + json.dumps(stations, ensure_ascii=False, indent=2, default=str)
        + ";\n"
    )
    output_path.write_text(content, encoding="utf-8")
    log.info(f"已写入: {output_path}  ({len(content):,} 字节，{len(stations)} 个站点)")


# ── 主流程 ─────────────────────────────────────────────────────────────────

def rebuild(input_path: Path, output_path: Path, platform_code: str):
    log.info(f"加载 ptt.js: {input_path}")
    ptt_stations = load_ptt_stations(input_path)
    ptt_by_name  = {s["name"].strip().lower(): s for s in ptt_stations}
    log.info(f"ptt.js 站点数: {len(ptt_stations)}")

    log.info("查询 station_sites ...")
    db_stations  = query_station_sites(platform_code)
    db_by_name   = {r["station_name"].strip().lower(): r for r in db_stations.values()}
    log.info(f"DB 站点数: {len(db_stations)}")

    log.info("查询 connector_status_snapshots ...")
    snaps_by_sid = query_all_snapshots(platform_code)
    stations_with_snaps = len(snaps_by_sid)
    log.info(f"有快照数据的站点: {stations_with_snaps} 个")

    # 建立 station_name(lower) → station_id 的映射
    name_to_sid = {
        r["station_name"].strip().lower(): sid
        for sid, r in db_stations.items()
    }

    result        = []
    updated       = 0
    kept_original = 0
    appended      = 0

    # ① 处理 ptt.js 中的每个站点
    for ptt_entry in ptt_stations:
        name_key = ptt_entry["name"].strip().lower()
        db_row   = db_by_name.get(name_key)

        if db_row is None:
            # DB 中没有 → 原样保留
            result.append(ptt_entry)
            kept_original += 1
            continue

        sid   = name_to_sid.get(name_key)
        snaps = snaps_by_sid.get(sid, [])
        merged = merge_station(ptt_entry, db_row, snaps)
        result.append(merged)
        updated += 1

    # ② 追加 DB 有但 ptt.js 没有的站点
    for name_key, db_row in db_by_name.items():
        if name_key not in ptt_by_name:
            sid   = name_to_sid[name_key]
            snaps = snaps_by_sid.get(sid, [])
            result.append(build_new_station(db_row, snaps))
            appended += 1

    log.info(
        f"处理完成：更新 {updated} 条，原样保留 {kept_original} 条，"
        f"新追加 {appended} 条，共 {len(result)} 条"
    )
    write_ptt_js(result, output_path)


# ── 入口 ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="从数据库重建补全 ptt.js")
    parser.add_argument("--input",    default=str(DEFAULT_INPUT),  help="源 ptt.js 路径")
    parser.add_argument("--output",   default=str(DEFAULT_OUTPUT), help="输出路径（默认 ptt_new.js）")
    parser.add_argument("--platform", default=PLATFORM_CODE,       help="平台编码")
    args = parser.parse_args()

    db.init(
        host=config.DB_HOST, port=config.DB_PORT,
        user=config.DB_USER, password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )
    rebuild(Path(args.input), Path(args.output), args.platform)


if __name__ == "__main__":
    main()
