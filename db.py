"""
db.py — MySQL 数据库模块

负责连接管理和所有写入操作。
核心方法 save_station() 在单个事务内完成：
  UPSERT station_sites
  → INSERT connector_status_snapshots（每个枪口，含充电桩信息）
  → UPDATE collection_runs.collected_count + 1
"""

import re
import json
import mysql.connector
from datetime import datetime

# ── 模块级连接状态 ─────────────────────────────────────────────
_conn = None
_config = {}


# ── 连接管理 ───────────────────────────────────────────────────

def init(host, port, user, password, database):
    """
    初始化数据库连接配置，建立首次连接。
    后续所有操作通过 _get_conn() 获取连接，断线自动重连。

    :param host:     MySQL 主机地址
    :param port:     端口，通常为 3306
    :param user:     用户名
    :param password: 密码
    :param database: 数据库名
    """
    global _config
    _config = dict(
        host=host, port=port,
        user=user, password=password,
        database=database,
        charset="utf8mb4",
        autocommit=False,
        connection_timeout=10,
    )
    _get_conn()  # 立即验证连接是否可用


def _get_conn():
    """
    获取当前数据库连接。
    若连接不存在或已断开，自动重新建立。
    """
    global _conn
    if _conn is None or not _conn.is_connected():
        _conn = mysql.connector.connect(**_config)
    return _conn


# ── 采集批次管理 ───────────────────────────────────────────────

def find_or_create_run(platform_code, mode="full"):
    """
    查找该平台 status='running' 的批次用于续跑；
    若不存在则创建新批次。

    run_label 由系统自动生成，格式：{platform}_{YYYYMMDD_HHMM}_{mode}

    :param platform_code: 平台编码，如 'ev_station_pluz'
    :param mode:          'full'=全量采集；'refresh'=状态刷新
    :return: run_id (int)
    """
    conn = _get_conn()
    cursor = conn.cursor(dictionary=True)

    # 优先续跑已有的进行中批次
    cursor.execute("""
                   SELECT id, run_label
                   FROM collection_runs
                   WHERE platform_code = %s
                     AND status = 'running'
                   ORDER BY started_at DESC LIMIT 1
                   """, (platform_code,))
    row = cursor.fetchone()
    cursor.close()

    if row:
        print(f"[续跑] 发现进行中的批次  run_id={row['id']}  label={row['run_label']}")
        return row["id"]

    # 创建新批次
    now = datetime.now()
    run_label = f"{platform_code}_{now.strftime('%Y%m%d_%H%M')}_{mode}"
    cursor = conn.cursor()
    cursor.execute("""
                   INSERT INTO collection_runs
                       (platform_code, run_label, mode, status, started_at)
                   VALUES (%s, %s, %s, 'running', %s)
                   """, (platform_code, run_label, mode, now))
    conn.commit()
    run_id = cursor.lastrowid
    cursor.close()

    print(f"[新批次] run_id={run_id}  label={run_label}")
    return run_id


def update_total_stations(run_id, total):
    """
    更新批次的目标站点总数（首次从 App 列表页读取到总数后调用）。

    :param run_id: 批次 ID
    :param total:  站点总数
    """
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE collection_runs SET total_stations = %s WHERE id = %s",
        (total, run_id),
    )
    conn.commit()
    cursor.close()


def get_processed_stations(platform_code, run_id, time_period):
    """
    查询当前批次中、当前时段价格已全部填充的站点，返回 key 集合。
    key 格式与 scraper 内保持一致：station_name + brief_address。

    判断逻辑：该站在本批次内所有枪口快照的当前时段价格列均不为 NULL，
    才算"已完成"；任意枪口价格仍为空则需要重新采集以补全。

    :param platform_code: 平台编码
    :param run_id:        当前批次 ID
    :param time_period:   'day' 或 'night'
    :return: set of str，每个元素为 name+brief_address
    """
    price_col = "day_price_per_kwh" if time_period == "day" else "night_price_per_kwh"
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
                   SELECT ss.station_name, ss.brief_address
                   FROM station_sites ss
                            INNER JOIN connector_status_snapshots css
                                       ON css.station_id = ss.id AND css.run_id = %s
                   WHERE ss.platform_code = %s
                   GROUP BY ss.id, ss.station_name, ss.brief_address
                   HAVING SUM(css.{price_col} IS NULL) = 0
                   """, (run_id, platform_code))
    rows = cursor.fetchall()
    cursor.close()

    processed = {name + (addr or "") for name, addr in rows}
    if processed:
        print(f"[断点续采] 当前批次已完成 {len(processed)} 个站点（{time_period} 时段价格已全），自动跳过\n")
    return processed


def get_stations_missing_price(platform_code, time_period):
    """
    查询指定平台、指定时段价格完全缺失的站点。
    "缺失"定义：站点在 connector_status_snapshots 中存在快照，
    但所有快照的该时段价格列均为 NULL（即没有任何一条非空价格）。

    用于补齐模式确定待处理列表；已补齐的站点（任意快照中有非空价格）自动排除。

    :param platform_code: 平台编码
    :param time_period:   'day' 或 'night'
    :return: list of dict {id, station_name, brief_address}
    """
    price_col = "day_price_per_kwh" if time_period == "day" else "night_price_per_kwh"
    conn = _get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
                   SELECT ss.id,
                          ss.station_name,
                          COALESCE(ss.brief_address, '') AS brief_address
                   FROM station_sites ss
                   WHERE ss.platform_code = %s
                     AND EXISTS (SELECT 1
                                 FROM connector_status_snapshots
                                 WHERE station_id = ss.id)
                     AND NOT EXISTS (SELECT 1
                                     FROM connector_status_snapshots
                                     WHERE station_id = ss.id
                                       AND {price_col} IS NOT NULL)
                   ORDER BY ss.station_name
                   """, (platform_code,))
    rows = cursor.fetchall()
    cursor.close()
    if rows:
        print(f"[补齐模式] 发现 {len(rows)} 个站点的 {time_period} 时段价格缺失")
    return rows


def get_stations_incomplete(platform_code, time_period):
    """
    查询地址或当前时段价格任一缺失的站点，用于 fill 补全模式。

    触发条件（OR 关系）：
      - station_sites.brief_address 为 NULL 或空字符串（列表简短地址缺失）
      - station_sites.address 为 NULL 或空字符串（详情完整地址缺失）
      - connector_status_snapshots 中该时段无任何非空价格（含从未有过快照）

    :param platform_code: 平台编码
    :param time_period:   'day' 或 'night'
    :return: list of dict {id, station_name, brief_address}
    """
    price_col = "day_price_per_kwh" if time_period == "day" else "night_price_per_kwh"
    conn = _get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"""
                   SELECT ss.id,
                          ss.station_name,
                          COALESCE(ss.brief_address, '') AS brief_address
                   FROM station_sites ss
                   WHERE ss.platform_code = %s
                     AND (
                         ss.brief_address IS NULL OR ss.brief_address = ''
                         OR ss.address    IS NULL OR ss.address    = ''
                         OR NOT EXISTS (
                             SELECT 1 FROM connector_status_snapshots
                             WHERE station_id = ss.id
                               AND {price_col} IS NOT NULL
                         )
                     )
                   ORDER BY ss.station_name
                   """, (platform_code,))
    rows = cursor.fetchall()
    cursor.close()
    if rows:
        print(f"[补全模式] 发现 {len(rows)} 个站点数据不完整（地址或 {time_period} 价格缺失）")
    return rows


def complete_run(run_id):
    """
    将批次状态标记为 completed，记录结束时间。
    采集循环正常退出时调用。

    :param run_id: 批次 ID
    """
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("""
                   UPDATE collection_runs
                   SET status       = 'completed',
                       completed_at = NOW()
                   WHERE id = %s
                   """, (run_id,))
    conn.commit()
    cursor.close()
    print(f"[批次完成] run_id={run_id}")


# ── 数据解析工具 ───────────────────────────────────────────────

def _parse_power_kw(text):
    """
    从功率文本中提取 kW 数值。
    支持 'Max 40 kW'、'7.4 kW'、'40kW' 等格式。

    :param text: 功率原始文本
    :return: float 或 None
    """
    if not text:
        return None
    m = re.search(r"([\d.]+)\s*kW", text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _parse_price_per_kwh(text):
    """
    从价格文本中提取每度电价格（泰铢）。
    支持 '8.00 ฿/kWh'、'8.00฿/kWh'、'8 ฿' 等格式。

    :param text: 价格原始文本
    :return: float 或 None
    """
    if not text:
        return None
    m = re.search(r"([\d.]+)\s*฿", text)
    return float(m.group(1)) if m else None


# ── 核心写入 ───────────────────────────────────────────────────

def save_station(run_id, station_data, time_period, collected_at):
    """
    在单个事务内保存一个站点的完整采集数据。

    写入顺序：
      1. UPSERT station_sites（以 platform_code+station_name 去重）
      2. 逐枪口：若本批次已有快照且当前时段价格为空 → UPDATE 补价格；
                 否则 INSERT 新行，仅填充当前时段的价格列
      3. UPDATE collection_runs.collected_count + 1

    任意步骤异常则整体回滚，站点不计入 processed，下次重试。

    :param run_id:        采集批次 ID
    :param station_data:  站点完整数据 dict（scraper 采集结果）
    :param time_period:   'day' 或 'night'，由平台规则从采集时刻计算
    :param collected_at:  datetime，实际采集完成时刻
    :return: station_id (int)
    """
    conn = _get_conn()
    cursor = conn.cursor()

    try:
        # ── 1. UPSERT 站点 ────────────────────────────────────
        # ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id) 确保
        # INSERT 和 UPDATE 后 lastrowid 均返回正确的 station_id
        cursor.execute("""
                       INSERT INTO station_sites
                       (platform_code, station_name, brief_address, address,
                        overall_status, remarks, hours_text,
                        latitude, longitude, google_url,
                        collection_status, raw_data, last_collected_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'completed', %s, %s) ON DUPLICATE KEY
                       UPDATE
                           brief_address =
                       VALUES (brief_address), address =
                       VALUES (address), overall_status =
                       VALUES (overall_status), remarks =
                       VALUES (remarks), hours_text =
                       VALUES (hours_text), latitude =
                       VALUES (latitude), longitude =
                       VALUES (longitude), google_url = COALESCE (VALUES (google_url), google_url), collection_status = 'completed', raw_data =
                       VALUES (raw_data), last_collected_at =
                       VALUES (last_collected_at), id = LAST_INSERT_ID(id)
                       """, (
                           station_data["platform_code"],
                           station_data["name"],
                           station_data.get("address"),
                           station_data.get("full_address"),
                           station_data.get("overall_status"),
                           station_data.get("remarks"),
                           json.dumps(station_data.get("hours_by_day", {}), ensure_ascii=False),
                           station_data.get("lat"),
                           station_data.get("lng"),
                           station_data.get("google_url"),
                           json.dumps(station_data, ensure_ascii=False, default=str),
                           collected_at,
                       ))
        station_id = cursor.lastrowid

        # ── 2. 逐枪口：UPDATE 补价格 或 INSERT 新快照 ────────────
        for unit in station_data.get("charger_units", []):
            for connector in unit.get("connectors", []):
                raw_data = {
                    "unit": {
                        "id": unit.get("id"),
                        "name": unit.get("name"),
                    },
                    "connector": connector,
                }
                raw_json   = json.dumps(raw_data, ensure_ascii=False)
                price_text = connector.get("price", "")
                price_kwh  = _parse_price_per_kwh(connector.get("price"))

                # 查找本批次内同一枪口的已有快照
                cursor.execute("""
                               SELECT id, day_price_per_kwh, night_price_per_kwh
                               FROM connector_status_snapshots
                               WHERE run_id = %s
                                 AND station_id = %s
                                 AND COALESCE(platform_unit_id, '') = COALESCE(%s, '')
                                 AND connector_name = %s
                               ORDER BY id DESC LIMIT 1
                               """, (
                                   run_id, station_id,
                                   unit.get("id"),
                                   connector.get("position", ""),
                               ))
                existing = cursor.fetchone()

                if existing:
                    snap_id, day_kwh, night_kwh = existing
                    if time_period == "day" and day_kwh is None:
                        cursor.execute("""
                                       UPDATE connector_status_snapshots
                                       SET day_price_text = %s, day_price_per_kwh = %s
                                       WHERE id = %s
                                       """, (price_text, price_kwh, snap_id))
                    elif time_period == "night" and night_kwh is None:
                        cursor.execute("""
                                       UPDATE connector_status_snapshots
                                       SET night_price_text = %s, night_price_per_kwh = %s
                                       WHERE id = %s
                                       """, (price_text, price_kwh, snap_id))
                    # 当前时段价格已存在，无需操作
                else:
                    day_pt   = price_text if time_period == "day"   else None
                    day_pkwh = price_kwh  if time_period == "day"   else None
                    ngt_pt   = price_text if time_period == "night" else None
                    ngt_pkwh = price_kwh  if time_period == "night" else None

                    cursor.execute("""
                                   INSERT INTO connector_status_snapshots
                                   (run_id, station_id,
                                    platform_unit_id, unit_name,
                                    connector_name, connector_type,
                                    power_text, power_kw,
                                    day_price_text, day_price_per_kwh,
                                    night_price_text, night_price_per_kwh,
                                    status, time_period,
                                    raw_data, collected_at)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                   """, (
                                       run_id, station_id,
                                       unit.get("id"), unit.get("name"),
                                       connector.get("position", ""),
                                       connector.get("connector_type", ""),
                                       connector.get("power", ""),
                                       _parse_power_kw(connector.get("power")),
                                       day_pt, day_pkwh,
                                       ngt_pt, ngt_pkwh,
                                       connector.get("status", ""),
                                       time_period,
                                       raw_json, collected_at,
                                   ))

        # ── 3. 批次进度 +1 ────────────────────────────────────
        cursor.execute("""
                       UPDATE collection_runs
                       SET collected_count = collected_count + 1
                       WHERE id = %s
                       """, (run_id,))

        conn.commit()
        return station_id

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
