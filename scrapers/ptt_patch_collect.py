"""
PTT targeted patch collector.

This script is intentionally separate from run.py.  It builds the todo list
from station_sites plus connector_status_snapshots, then reuses
EVStationPluZScraper's App navigation/parsing and db.save_station().

Todo rules:
  - station_sites.address is empty
  - or the station has no connector_status_snapshots rows
  - or any connector group is missing the current period price

The current period is evaluated at runtime:
  day   = 09:00 <= hour < 22:00
  night = 22:00 <= hour or hour < 09:00
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Allow direct execution: python scrapers/ptt_patch_collect.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
import db
from scrapers.ev_station_pluz import EVStationPluZScraper


DEFAULT_DEVICE_SERIAL = "7391e8d9"
RUN_MODE = "ptt_patch"


class _Tee:
    def __init__(self, console, file):
        self._console = console
        self._file = file

    def write(self, data):
        self._console.write(data)
        self._file.write(data)

    def flush(self):
        self._console.flush()
        self._file.flush()


def setup_stdout_log() -> tuple[Any, Any, Path]:
    """Mirror stdout to logs/ptt_patch_YYYYmmdd_HHMMSS.log."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"ptt_patch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_file = open(log_path, "w", encoding="utf-8")
    real_stdout = sys.stdout
    sys.stdout = _Tee(real_stdout, log_file)
    return real_stdout, log_file, log_path


def init_db() -> None:
    db.init(
        config.DB_HOST,
        config.DB_PORT,
        config.DB_USER,
        config.DB_PASSWORD,
        config.DB_NAME,
    )


def current_period() -> str:
    return EVStationPluZScraper.get_time_period(datetime.now())


def _int(value: Any) -> int:
    return int(value or 0)


def _text(value: Any) -> str:
    return (value or "").strip()


def _load_hours_fallback(hours_text: str | None) -> dict:
    if not hours_text:
        return {}
    try:
        data = json.loads(hours_text)
    except (TypeError, json.JSONDecodeError):
        return {"hours": str(hours_text)}
    return data if isinstance(data, dict) else {}


def query_snapshot_stats(platform_code: str) -> dict[int, dict]:
    """
    Return connector-group completeness by station_id.

    A connector group is station_id + platform_unit_id + connector_name.
    The group is complete for a period only when at least one historical
    snapshot in that group has a non-NULL period price.
    """
    conn = db._get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT g.station_id,
               COUNT(*) AS connector_groups,
               SUM(CASE WHEN g.has_day = 0 THEN 1 ELSE 0 END) AS missing_day_groups,
               SUM(CASE WHEN g.has_night = 0 THEN 1 ELSE 0 END) AS missing_night_groups,
               SUM(g.row_count) AS snapshot_rows
        FROM (
            SELECT css.station_id,
                   COALESCE(css.platform_unit_id, '') AS platform_unit_id,
                   COALESCE(css.connector_name, '') AS connector_name,
                   MAX(css.day_price_per_kwh IS NOT NULL) AS has_day,
                   MAX(css.night_price_per_kwh IS NOT NULL) AS has_night,
                   COUNT(*) AS row_count
            FROM connector_status_snapshots css
            INNER JOIN station_sites ss ON ss.id = css.station_id
            WHERE ss.platform_code = %s
            GROUP BY css.station_id,
                     COALESCE(css.platform_unit_id, ''),
                     COALESCE(css.connector_name, '')
        ) AS g
        GROUP BY g.station_id
        """,
        (platform_code,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return {row["station_id"]: row for row in rows}


def query_ptt_todo_stations(platform_code: str, time_period: str) -> list[dict]:
    """
    Build a station-level todo list for the current period.

    The list is deduped by station_sites.id, not by name/address, because the
    imported PTT rows often have empty address fields.
    """
    conn = db._get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, station_name,
               COALESCE(brief_address, '') AS brief_address,
               COALESCE(address, '') AS address,
               hours_text, latitude, longitude, google_url
        FROM station_sites
        WHERE platform_code = %s
        ORDER BY station_name
        """,
        (platform_code,),
    )
    stations = cursor.fetchall()
    cursor.close()

    stats_by_station = query_snapshot_stats(platform_code)
    missing_key = f"missing_{time_period}_groups"

    todo: list[dict] = []
    for row in stations:
        station_id = row["id"]
        stats = stats_by_station.get(station_id)
        missing_current_groups = _int(stats.get(missing_key)) if stats else 0
        no_snapshots = stats is None
        address_missing = not _text(row.get("address"))

        if not (address_missing or no_snapshots or missing_current_groups > 0):
            continue

        reasons = []
        if address_missing:
            reasons.append("address_missing")
        if no_snapshots:
            reasons.append("no_snapshots")
        elif missing_current_groups > 0:
            reasons.append(f"{time_period}_price_missing:{missing_current_groups}")

        row.update(
            {
                "reason": ",".join(reasons),
                "address_missing": address_missing,
                "no_snapshots": no_snapshots,
                "connector_groups": _int(stats.get("connector_groups")) if stats else 0,
                "missing_day_groups": _int(stats.get("missing_day_groups")) if stats else 0,
                "missing_night_groups": _int(stats.get("missing_night_groups")) if stats else 0,
                "snapshot_rows": _int(stats.get("snapshot_rows")) if stats else 0,
                "needs_snapshot_or_price": no_snapshots or missing_current_groups > 0,
            }
        )
        todo.append(row)

    return todo


def print_todo_summary(todo: list[dict], time_period: str, show: int) -> None:
    address_missing = sum(1 for row in todo if row["address_missing"])
    no_snapshots = sum(1 for row in todo if row["no_snapshots"])
    price_missing = sum(
        1
        for row in todo
        if (row["missing_day_groups"] if time_period == "day" else row["missing_night_groups"]) > 0
    )
    missing_groups = sum(
        row["missing_day_groups"] if time_period == "day" else row["missing_night_groups"]
        for row in todo
    )

    print(f"当前时段：{time_period}（白天 09:00-22:00，夜间 22:00-09:00）")
    print(f"待采站点：{len(todo)}")
    print(f"  - address 缺失：{address_missing}")
    print(f"  - 完全无快照：{no_snapshots}")
    print(f"  - 当前时段价格不完整站点：{price_missing}")
    print(f"  - 当前时段缺价枪口组：{missing_groups}")

    if not todo or show <= 0:
        return

    print(f"\n前 {min(show, len(todo))} 个待采站点：")
    for idx, row in enumerate(todo[:show], 1):
        print(
            f"  {idx:>3}. id={row['id']}  {row['station_name']}  "
            f"[{row['reason']}]"
        )


def start_app(d) -> None:
    current = d.app_current()
    if current.get("package") == EVStationPluZScraper.APP_PKG:
        print("App 已在前台，无需重启")
        return

    print(f"启动 App（当前：{current.get('package')}）...")
    d.app_start(EVStationPluZScraper.APP_PKG)
    time.sleep(5)


def return_to_map(scraper: EVStationPluZScraper) -> None:
    """Best-effort cleanup after each station."""
    try:
        scraper.d.press("back")
        time.sleep(1.5)
        scraper.ensure_app_running()
        scraper.dismiss_alert()
        scraper.close_preview_card()
        time.sleep(0.8)
    except Exception as exc:  # noqa: BLE001 - cleanup must not hide the save result
        print(f"  !! 返回 Map 页清理失败：{exc}")


def collect_station(
    scraper: EVStationPluZScraper,
    station: dict,
    run_id: int,
    label: str,
) -> tuple[bool, str]:
    """
    Search and collect one station.

    Returns (success, saved_period).  saved_period is the actual period at
    save time, which may differ if the clock crosses 09:00 or 22:00 mid-station.
    """
    name = station["station_name"]
    print(f"[{label}] 搜索：{name}  id={station['id']}  reason={station['reason']}")

    try:
        scraper.ensure_app_running()
        if not scraper.ensure_map_page():
            scraper.force_restart_app()
            if not scraper.ensure_map_page():
                print("  !! 无法回到 Map 页")
                return False, current_period()

        if not scraper._search_on_map(name):
            print("  !! Map 搜索框未找到")
            return False, current_period()

        scraper.ensure_app_running()
        scraper.dismiss_alert()

        if not scraper._click_map_search_result(name):
            print("  !! 搜索结果无匹配项")
            return False, current_period()

        time.sleep(2)
        scraper.ensure_app_running()
        scraper.dismiss_alert()

        if not scraper.preview_card_open():
            time.sleep(2)
            scraper.ensure_app_running()
            scraper.dismiss_alert()
            if not scraper.preview_card_open():
                print("  !! 预览卡未出现")
                return False, current_period()

        if not scraper.click_view_more():
            time.sleep(1)
            scraper.dismiss_alert()
            if not scraper.click_view_more():
                print("  !! View more 未找到")
                return False, current_period()

        time.sleep(3)
        scraper.ensure_app_running()
        scraper.dismiss_alert()

        station_start = time.time()
        charger_units = scraper._read_charger_units()
        charger_count = sum(len(unit.get("connectors", [])) for unit in charger_units)
        print(f"  -> {len(charger_units)} 个充电桩 / {charger_count} 个枪口")

        if charger_count == 0:
            print("  !! 未读到枪口数据，本次不写库，避免把缺价误判为完成")
            return False, current_period()

        detail = scraper.read_detail_info()
        more = scraper.read_more_information()

        scraped_full_address = _text(more.get("full_address"))
        existing_brief = _text(station.get("brief_address"))
        existing_address = _text(station.get("address"))
        full_address = scraped_full_address or existing_address or existing_brief
        brief_address = existing_brief or existing_address or scraped_full_address
        hours_by_day = more.get("hours_by_day") or _load_hours_fallback(station.get("hours_text"))

        target = {
            "name": name,
            "address": brief_address,
            "full_address": full_address,
            "hours_by_day": hours_by_day,
            "charger_units": charger_units,
            "charger_count": charger_count,
            "overall_status": detail.get("overall_status", ""),
            "last_update": detail.get("last_update", ""),
            "remarks": detail.get("remarks", ""),
            "lat": station.get("latitude"),
            "lng": station.get("longitude"),
            "google_url": station.get("google_url"),
            "elapsed_sec": round(time.time() - station_start, 1),
            "platform_code": EVStationPluZScraper.PLATFORM_CODE,
        }

        collected_at = datetime.now()
        saved_period = EVStationPluZScraper.get_time_period(collected_at)
        db.save_station(run_id, target, saved_period, collected_at)
        scraper._print_station(target, label, saved_period, target["elapsed_sec"])
        return True, saved_period

    except Exception as exc:  # noqa: BLE001 - keep the station retryable next run
        print(f"  !! 采集失败：{exc}")
        return False, current_period()

    finally:
        return_to_map(scraper)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PTT targeted patch collector for missing address/day/night prices.",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE_SERIAL,
        help=f"uiautomator2 device serial, default: {DEFAULT_DEVICE_SERIAL}",
    )
    parser.add_argument(
        "--max-stations",
        type=int,
        default=None,
        help="Maximum successful stations to collect in this run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print the current todo list. Do not connect to device or write DB.",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=30,
        help="How many todo rows to print in dry-run/summary output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    real_stdout = log_file = None
    log_path = None

    if not args.dry_run:
        real_stdout, log_file, log_path = setup_stdout_log()
    elif isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        print("连接数据库...")
        init_db()
        print("数据库连接成功\n")

        period = current_period()
        todo = query_ptt_todo_stations(EVStationPluZScraper.PLATFORM_CODE, period)
        print_todo_summary(todo, period, args.show)

        if args.dry_run:
            return 0

        if not todo:
            print("\n当前时段无待采站点")
            return 0

        run_id = db.find_or_create_run(EVStationPluZScraper.PLATFORM_CODE, RUN_MODE)
        target_desc = f"{args.max_stations} 个站点" if args.max_stations else "全部待采站点"
        print(f"\n开始 PTT 补采，目标：{target_desc}  批次：run_id={run_id}\n")

        import uiautomator2 as u2

        print(f"连接设备 {args.device}...")
        d = u2.connect(args.device)
        print("设备连接成功\n")
        start_app(d)

        scraper = EVStationPluZScraper(d)
        attempted_ids: set[int] = set()
        success_count = 0
        failure_count = 0
        active_period = period

        while True:
            now_period = current_period()
            if now_period != active_period:
                print(f"\n[时段切换] {active_period} -> {now_period}，重新加载待采队列")
                active_period = now_period
                attempted_ids.clear()

            todo = query_ptt_todo_stations(EVStationPluZScraper.PLATFORM_CODE, active_period)
            todo = [row for row in todo if row["id"] not in attempted_ids]

            if not todo:
                remaining = query_ptt_todo_stations(EVStationPluZScraper.PLATFORM_CODE, active_period)
                if remaining:
                    print(f"\n本轮可尝试站点已处理完，但仍有 {len(remaining)} 个站点未补齐")
                    return 1
                print("\n当前时段待采队列已清空")
                db.complete_run(run_id)
                return 0

            if args.max_stations is not None and success_count >= args.max_stations:
                print(f"\n已达到本次成功采集上限：{args.max_stations}")
                return 0

            station = todo[0]
            attempted_ids.add(station["id"])
            label = str(success_count + 1)
            if args.max_stations is not None:
                label = f"{success_count + 1}/{args.max_stations}"

            ok, saved_period = collect_station(scraper, station, run_id, label)
            if ok:
                success_count += 1
                if saved_period != active_period:
                    print(f"  -> 保存时段已变为 {saved_period}，下一轮重新加载队列")
                    active_period = saved_period
                    attempted_ids.clear()
            else:
                failure_count += 1

    except KeyboardInterrupt:
        print("\n[中断] Ctrl+C，已保存成功写入的数据；未完成站点下次会重新进入待采队列")
        return 130
    finally:
        if log_path:
            print(f"\n日志已保存至：{log_path}")
        if real_stdout is not None and log_file is not None:
            sys.stdout = real_stdout
            log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
