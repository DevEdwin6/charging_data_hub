"""
ptt_sync.py — PTT 数据同步工具

功能一（check）：
    从 station_sites 读取所有站点名，检查每个站点名是否存在于 ptt.js。
    将不存在的站点名输出到日志（WARNING 级别）。

功能二（import）：
    将 ptt.js 中的站点批量写入 station_sites，以 station_name 去重（已存在则跳过）。

功能三（dedup）：
    对 station_sites 中同平台的站点做模糊去重。
    规则：若 A 是 B 的前缀（忽略大小写），视为同一站点的重复录入；
    保留名字更完整（较长）的那条，删除较短的重复项并将其快照数据迁移过去。
    默认 dry-run，加 --execute 才真正写库。

用法：
    python utils/ptt_sync.py check            # 只执行功能一
    python utils/ptt_sync.py import           # 只执行功能二
    python utils/ptt_sync.py all              # 顺序执行两个功能
    python utils/ptt_sync.py dedup            # 功能三 dry-run，预览重复对
    python utils/ptt_sync.py dedup --execute  # 功能三 实际合并+删除
    python utils/ptt_sync.py dedup --min-len 12   # 调高前缀最短长度（默认 8）
    python utils/ptt_sync.py check --platform ev_station_pluz
    python utils/ptt_sync.py check --ptt-js /path/to/ptt.js
"""

import re
import json
import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime

# 将项目根目录加入模块搜索路径，以便直接运行脚本时能 import config/db
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
import db

PLATFORM_CODE = "ev_station_pluz"
DEFAULT_PTT_JS = Path(__file__).parent.parent / "web" / "data" / "ptt.js"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── JS 解析 ────────────────────────────────────────────────────────────────

def _quote_unquoted_js_keys(raw: str) -> str:
    """
    只在字符串外部将 JS 对象的未加引号 key 转为 JSON key。

    不能用简单正则全局替换 `xxx:`，因为营业时间字符串里会出现
    `Mon:`、`Sat:`，全局替换会破坏字符串内容。
    """
    out = []
    i = 0
    in_string = False
    escape = False

    while i < len(raw):
        ch = raw[i]

        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch.isalpha() or ch == "_":
            prev = raw[i - 1] if i > 0 else ""
            if i == 0 or prev in "{[,\r\n\t ":
                j = i + 1
                while j < len(raw) and (raw[j].isalnum() or raw[j] == "_"):
                    j += 1
                k = j
                while k < len(raw) and raw[k].isspace():
                    k += 1
                if k < len(raw) and raw[k] == ":":
                    out.append(f'"{raw[i:j]}"')
                    out.append(raw[j:k + 1])
                    i = k + 1
                    continue

        out.append(ch)
        i += 1

    return "".join(out)

def load_ptt_stations(filepath=DEFAULT_PTT_JS):
    """
    解析 ptt.js，返回站点列表（list[dict]）。

    ptt.js 是 JS 格式（window.PTT_DATA = [...]），非标准 JSON。
    处理步骤：
      1. 去掉 window.XXX = 前缀和末尾分号
      2. 将未加引号的 JS 对象键名转换为 JSON 合法的双引号形式
      3. 用标准 json.loads 解析
    """
    raw = Path(filepath).read_text(encoding="utf-8")

    # 去掉 window.PTT_DATA = 前缀
    raw = re.sub(r"^\s*window\.\w+\s*=\s*", "", raw, flags=re.MULTILINE)
    raw = raw.strip().rstrip(";").strip()

    # 去掉 JS 尾随逗号（JSON 不允许 ,} 或 ,]）
    raw = re.sub(r',(\s*[}\]])', r'\1', raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raw = _quote_unquoted_js_keys(raw)
        return json.loads(raw)


# ── 功能一 ──────────────────────────────────────────────────────────────────

def check_db_vs_ptt(ptt_names: set, platform_code: str | None = None):
    """
    从 station_sites 读取站点名，检查每条记录是否存在于 ptt.js 中。
    不存在的站点以 WARNING 写入日志。

    :param ptt_names:      ptt.js 中所有站点名构成的集合
    :param platform_code:  若指定，则只检查该平台的站点；否则检查全部
    """
    conn = db._get_conn()
    cursor = conn.cursor()

    if platform_code:
        cursor.execute(
            "SELECT station_name FROM station_sites WHERE platform_code = %s ORDER BY station_name",
            (platform_code,),
        )
        scope_desc = f"平台 [{platform_code}]"
    else:
        cursor.execute("SELECT station_name FROM station_sites ORDER BY station_name")
        scope_desc = "全部平台"

    db_names = [row[0] for row in cursor.fetchall()]
    cursor.close()

    missing = [n for n in db_names if n not in ptt_names]
    found_count = len(db_names) - len(missing)

    log.info(
        f"[功能一] {scope_desc} 共 {len(db_names)} 条站点，"
        f"在 ptt.js 中匹配 {found_count} 条，不存在 {len(missing)} 条"
    )

    for name in missing:
        log.warning(f"[不在ptt.js] {name}")

    return missing


# ── 功能二 ──────────────────────────────────────────────────────────────────

def import_ptt_to_db(stations: list[dict]):
    """
    将 ptt.js 站点批量写入 station_sites。
    以 (platform_code, station_name) 为唯一键去重：已存在则跳过，不存在则新增。

    :param stations: load_ptt_stations() 返回的站点列表
    :return: (inserted, skipped) 新增数量和跳过数量
    """
    conn = db._get_conn()
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    errors = 0
    now = datetime.now()

    for station in stations:
        name = (station.get("name") or "").strip()
        if not name:
            continue

        address = station.get("address") or ""
        hours_raw = station.get("hours") or ""
        hours_text = json.dumps({"hours": hours_raw}, ensure_ascii=False) if hours_raw else None
        raw_data = json.dumps(station, ensure_ascii=False)

        try:
            cursor.execute(
                """
                INSERT IGNORE INTO station_sites
                    (platform_code, station_name, brief_address, address,
                     hours_text, latitude, longitude,
                     collection_status, raw_data, last_collected_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'completed', %s, %s)
                """,
                (
                    PLATFORM_CODE,
                    name,
                    address,
                    address,
                    hours_text,
                    station.get("lat"),
                    station.get("lon"),
                    raw_data,
                    now,
                ),
            )
            if cursor.rowcount > 0:
                inserted += 1
                log.debug(f"[新增] {name}")
            else:
                skipped += 1
                log.debug(f"[跳过] {name}（已存在）")

        except Exception as exc:
            errors += 1
            log.error(f"[写入失败] {name}: {exc}")
            conn.rollback()
            continue

    conn.commit()
    cursor.close()

    log.info(
        f"[功能二] 导入完成：新增 {inserted} 条，跳过 {skipped} 条"
        + (f"，失败 {errors} 条" if errors else "")
    )
    return inserted, skipped


# ── 功能三 ──────────────────────────────────────────────────────────────────

def dedup_station_names(platform_code: str = PLATFORM_CODE, dry_run: bool = True, min_len: int = 8):
    """
    查找 station_sites 中名字存在前缀关系的重复站点对。

    匹配规则（忽略大小写）：
      - 站点 A 的名字是站点 B 名字的前缀（A 较短）
      - A 的名字长度 >= min_len（防止过短的名字误匹配）

    结果：
      - dry_run=True  ：只输出匹配对，不修改数据库
      - dry_run=False ：将较短站点的快照数据迁移到较长站点，然后删除较短站点

    保留策略：始终保留名字更长（更完整）的那条记录。

    :param platform_code: 要检查的平台编码
    :param dry_run:       True=预览；False=实际执行合并+删除
    :param min_len:       前缀最短字符数，默认 8
    :return: list of (shorter_id, longer_id, shorter_name, longer_name)
    """
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, station_name FROM station_sites WHERE platform_code = %s ORDER BY LENGTH(station_name)",
        (platform_code,),
    )
    rows = cursor.fetchall()
    cursor.close()

    # 按名字长度升序，方便前缀查找
    stations = [(id_, name, name.lower().strip()) for id_, name in rows]

    # 找出所有前缀对（A 是 B 的前缀，A 更短）
    pairs: list[tuple] = []
    for i, (id_a, name_a, norm_a) in enumerate(stations):
        if len(norm_a) < min_len:
            continue
        for id_b, name_b, norm_b in stations[i + 1:]:
            if norm_b.startswith(norm_a):
                pairs.append((id_a, id_b, name_a, name_b))

    log.info(
        f"[功能三] 平台 [{platform_code}] 共 {len(rows)} 条站点，"
        f"发现 {len(pairs)} 对前缀重复（min_len={min_len}）"
    )

    for shorter_id, longer_id, shorter_name, longer_name in pairs:
        diff = len(longer_name) - len(shorter_name)
        log.warning(
            f"[重复] id={shorter_id} \"{shorter_name}\"  →  id={longer_id} \"{longer_name}\"  (差 {diff} 字符)"
        )

    if not pairs:
        log.info("[功能三] 未发现重复，无需处理")
        return pairs

    if dry_run:
        log.info(f"[功能三] dry-run 模式，未修改数据库。加 --execute 执行实际合并")
        return pairs

    # ── 实际执行：迁移快照 → 删除较短站点 ──────────────────────────────────
    cursor = conn.cursor()
    merged = 0
    deleted = 0

    for shorter_id, longer_id, shorter_name, longer_name in pairs:
        try:
            # 将较短站点的快照迁移到较长站点
            cursor.execute(
                "UPDATE connector_status_snapshots SET station_id = %s WHERE station_id = %s",
                (longer_id, shorter_id),
            )
            migrated = cursor.rowcount

            # 删除较短站点
            cursor.execute("DELETE FROM station_sites WHERE id = %s", (shorter_id,))
            conn.commit()

            merged += migrated
            deleted += 1
            log.info(
                f"[合并] \"{shorter_name}\" → \"{longer_name}\"，迁移快照 {migrated} 条，已删除原记录"
            )
        except Exception as exc:
            conn.rollback()
            log.error(f"[合并失败] id={shorter_id} \"{shorter_name}\": {exc}")

    cursor.close()
    log.info(f"[功能三] 完成：删除 {deleted} 条重复站点，迁移快照 {merged} 条")
    return pairs


# ── 功能四 ──────────────────────────────────────────────────────────────────

def _coord_dist(lat1, lon1, lat2, lon2) -> float:
    """经纬度欧氏距离（度），适用于同一城市范围内的近似判断。"""
    return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5


def dedup_by_name_and_coords(
    platform_code: str = PLATFORM_CODE,
    dry_run: bool = True,
    threshold: float = 0.005,
):
    """
    按「名字相同（忽略大小写）+ 坐标相近」去重 station_sites。

    threshold=0.005° ≈ 550m，足以区分同一物理站点的两条重复记录。
    两条记录只要满足以下任一条件即视为重复：
      - 名字完全相同（忽略大小写、首尾空格），且经纬度距离 < threshold
      - 名字完全相同，且其中一条坐标为 NULL（无法验证坐标，按名字去重）

    保留策略：优先保留 connector_status_snapshots 更多的那条；
               快照数相同时保留 id 较小（更早录入）的那条。

    :param platform_code: 要检查的平台编码
    :param dry_run:       True=只输出预览日志；False=实际执行合并+删除
    :param threshold:     坐标距离阈值（度），默认 0.005
    :return: list of (keep_id, drop_id, name, reason)
    """
    conn = db._get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT s.id, s.station_name, s.latitude, s.longitude,
               COUNT(c.id) AS snap_count
        FROM station_sites s
        LEFT JOIN connector_status_snapshots c ON c.station_id = s.id
        WHERE s.platform_code = %s
        GROUP BY s.id, s.station_name, s.latitude, s.longitude
        ORDER BY s.station_name, s.id
        """,
        (platform_code,),
    )
    rows = cursor.fetchall()
    cursor.close()

    # 按归一化名字分组
    groups: dict[str, list[dict]] = {}
    for row in rows:
        key = row["station_name"].strip().lower()
        groups.setdefault(key, []).append(row)

    to_merge: list[tuple] = []  # (keep_id, drop_id, name, reason)

    for norm_name, members in groups.items():
        if len(members) < 2:
            continue

        # 在同名组内，找坐标相近或含 NULL 坐标的重复对
        # 用 union-find 思路：已标记为"要删除"的不再作为 keep 候选
        drop_ids: set[int] = set()

        for i, a in enumerate(members):
            if a["id"] in drop_ids:
                continue
            for b in members[i + 1:]:
                if b["id"] in drop_ids:
                    continue

                # 判断是否为同一站点
                lat_a, lon_a = a["latitude"], a["longitude"]
                lat_b, lon_b = b["latitude"], b["longitude"]

                if lat_a is None or lat_b is None:
                    reason = "坐标缺失，按名字去重"
                    is_dup = True
                else:
                    dist = _coord_dist(float(lat_a), float(lon_a), float(lat_b), float(lon_b))
                    is_dup = dist < threshold
                    reason = f"坐标距离 {dist:.5f}°"

                if not is_dup:
                    continue

                # 决定保留哪条：快照多的优先；相同则 id 小的优先
                if a["snap_count"] >= b["snap_count"]:
                    keep, drop = a, b
                else:
                    keep, drop = b, a

                drop_ids.add(drop["id"])
                to_merge.append((keep["id"], drop["id"], a["station_name"], reason))

    total = len(rows)
    log.info(
        f"[功能四] 平台 [{platform_code}] 共 {total} 条站点，"
        f"发现 {len(to_merge)} 对重复（threshold={threshold}°）"
    )

    for keep_id, drop_id, name, reason in to_merge:
        log.warning(f"[重复] 保留 id={keep_id}  删除 id={drop_id}  \"{name}\"  ({reason})")

    if not to_merge:
        log.info("[功能四] 未发现重复，无需处理")
        return to_merge

    if dry_run:
        log.info(f"[功能四] dry-run 模式，未修改数据库。加 --execute 执行实际合并")
        return to_merge

    # ── 实际执行：迁移快照 → 删除重复站点 ─────────────────────────────────
    cursor = conn.cursor()
    merged_snaps = 0
    deleted = 0

    for keep_id, drop_id, name, reason in to_merge:
        try:
            cursor.execute(
                "UPDATE connector_status_snapshots SET station_id = %s WHERE station_id = %s",
                (keep_id, drop_id),
            )
            migrated = cursor.rowcount
            cursor.execute("DELETE FROM station_sites WHERE id = %s", (drop_id,))
            conn.commit()
            merged_snaps += migrated
            deleted += 1
            log.info(f"[合并] \"{name}\"  id={drop_id} → id={keep_id}，迁移快照 {migrated} 条")
        except Exception as exc:
            conn.rollback()
            log.error(f"[合并失败] \"{name}\" id={drop_id}: {exc}")

    cursor.close()
    log.info(
        f"[功能四] 完成：删除 {deleted} 条重复站点，迁移快照 {merged_snaps} 条，"
        f"剩余 {total - deleted} 条"
    )
    return to_merge


# ── 功能五 ──────────────────────────────────────────────────────────────────

def fill_missing_coords(filepath=DEFAULT_PTT_JS, platform_code: str = PLATFORM_CODE):
    """
    从 ptt.js 按 station_name 查找坐标，补全 station_sites 中缺失的经纬度。

    匹配规则：station_name 忽略大小写、首尾空格完全匹配。
    只更新 latitude IS NULL 或 longitude IS NULL 的记录。

    :param filepath:      ptt.js 文件路径
    :param platform_code: 只处理该平台的站点
    :return: (updated, not_found) 更新数量和未找到数量
    """
    # 构建 ptt.js 名字 → 坐标映射（只含有坐标的条目）
    stations = load_ptt_stations(filepath)
    ptt_map = {
        s["name"].strip().lower(): (s["lat"], s["lon"])
        for s in stations
        if s.get("lat") is not None and s.get("lon") is not None
    }
    log.info(f"ptt.js 中含坐标的站点: {len(ptt_map)} 条")

    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, station_name FROM station_sites WHERE platform_code = %s AND (latitude IS NULL OR longitude IS NULL)",
        (platform_code,),
    )
    missing = cursor.fetchall()
    cursor.close()
    log.info(f"[功能五] 需要补坐标的站点: {len(missing)} 条")

    updated = 0
    not_found = []

    cursor = conn.cursor()
    for station_id, station_name in missing:
        key = station_name.strip().lower()
        coords = ptt_map.get(key)
        if coords is None:
            not_found.append(station_name)
            log.warning(f"[未找到] \"{station_name}\"")
            continue

        lat, lon = coords
        cursor.execute(
            "UPDATE station_sites SET latitude = %s, longitude = %s WHERE id = %s",
            (lat, lon, station_id),
        )
        updated += 1

    conn.commit()
    cursor.close()

    log.info(
        f"[功能五] 完成：补全 {updated} 条，未找到 {len(not_found)} 条"
    )
    return updated, not_found


# ── 入口 ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PTT 数据同步工具：校验 DB 站点与 ptt.js 的差异，或将 ptt.js 导入数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "action",
        choices=["check", "import", "all", "dedup", "dedup-geo", "fill-coords"],
        help="check=功能一  import=功能二  all=功能一+二  dedup=功能三  dedup-geo=功能四  fill-coords=功能五",
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="功能一/三：指定平台（功能三默认用 PLATFORM_CODE，功能一默认全部平台）",
    )
    parser.add_argument(
        "--ptt-js",
        default=str(DEFAULT_PTT_JS),
        metavar="PATH",
        help=f"ptt.js 文件路径（默认：{DEFAULT_PTT_JS}）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="功能三：实际执行合并+删除（默认 dry-run 仅预览）",
    )
    parser.add_argument(
        "--min-len",
        type=int,
        default=8,
        metavar="N",
        help="功能三：前缀最短字符数，默认 8",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.005,
        metavar="DEG",
        help="功能四：坐标距离阈值（度），默认 0.005°≈550m",
    )
    args = parser.parse_args()

    # 初始化数据库连接
    db.init(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )

    # 功能三：前缀模糊去重
    if args.action == "dedup":
        platform = args.platform or PLATFORM_CODE
        dedup_station_names(platform_code=platform, dry_run=not args.execute, min_len=args.min_len)
        return

    # 功能四：同名+坐标去重
    if args.action == "dedup-geo":
        platform = args.platform or PLATFORM_CODE
        dedup_by_name_and_coords(platform_code=platform, dry_run=not args.execute, threshold=args.threshold)
        return

    # 功能五：补全缺失坐标
    if args.action == "fill-coords":
        platform = args.platform or PLATFORM_CODE
        fill_missing_coords(filepath=args.ptt_js, platform_code=platform)
        return

    # 解析 ptt.js（功能一/二）
    log.info(f"加载 ptt.js: {args.ptt_js}")
    stations = load_ptt_stations(args.ptt_js)
    log.info(f"共解析到 {len(stations)} 个站点")
    ptt_names = {s["name"] for s in stations if s.get("name")}

    if args.action in ("check", "all"):
        log.info("─" * 50)
        check_db_vs_ptt(ptt_names, platform_code=args.platform)

    if args.action in ("import", "all"):
        log.info("─" * 50)
        import_ptt_to_db(stations)


if __name__ == "__main__":
    main()

