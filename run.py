"""
run.py — 采集入口

配置设备、数据库连接和采集参数，
管理采集批次（collection_runs），驱动 scraper 完成数据采集。

新增 App 支持：
  1. 在 scrapers/ 下新建模块
  2. 在此文件中替换导入和实例化语句
"""

import sys
import io
import time
import uiautomator2 as u2

import config
import db
from scrapers.ev_station_pluz import EVStationPluZScraper

# Windows 终端默认 cp936，强制 UTF-8 以正确显示泰文和中文
assert isinstance(sys.stdout, io.TextIOWrapper)
sys.stdout.reconfigure(encoding="utf-8")

# ══════════════════════════════════════════════════════════════
# 采集参数
#
# MAX_STATIONS = None  → 采集全部站点
# MAX_STATIONS = 5     → 最终总量目标（含历史记录，非本次增量）
# RUN_MODE     = 'full'    → 初次全量采集（跳过已处理站点）
# RUN_MODE     = 'refresh' → 状态刷新（重新采集所有站点快照）
# ══════════════════════════════════════════════════════════════
DEVICE_SERIAL = "7391e8d9"
MAX_STATIONS = None
RUN_MODE = "full"

# ── 初始化数据库连接 ──────────────────────────────────────────
print("连接数据库...")
db.init(
    config.DB_HOST,
    config.DB_PORT,
    config.DB_USER,
    config.DB_PASSWORD,
    config.DB_NAME,
)
print("数据库连接成功\n")

# ── 查找或创建采集批次 ────────────────────────────────────────
run_id = db.find_or_create_run(EVStationPluZScraper.PLATFORM_CODE, RUN_MODE)

# ── 从 DB 加载当前批次已处理站点（断点续采）──────────────────
processed = db.get_processed_stations(EVStationPluZScraper.PLATFORM_CODE, run_id)

target_desc = f"{MAX_STATIONS} 个站点" if MAX_STATIONS is not None else "全部站点"
print(f"开始采集，目标：{target_desc}  批次：run_id={run_id}\n")

# ── 连接设备 ──────────────────────────────────────────────────
print(f"连接设备 {DEVICE_SERIAL}...")
d = u2.connect(DEVICE_SERIAL)
print("设备连接成功\n")

# ── 启动 App（若已在前台则跳过）─────────────────────────────
current = d.app_current()
if current.get("package") == EVStationPluZScraper.APP_PKG:
    print("App 已在前台，无需重启")
else:
    print(f"启动 App（当前：{current.get('package')}）...")
    d.app_start(EVStationPluZScraper.APP_PKG)
    time.sleep(5)

# ── 采集（results 仅用于本次会话的汇总打印）─────────────────
results = []
scraper = EVStationPluZScraper(d)

try:
    scraper.collect(results, processed, MAX_STATIONS, run_id)
    db.complete_run(run_id)
except KeyboardInterrupt:
    print("\n[中断] Ctrl+C，已保存进度，下次运行自动续采")

print(f"\n{'=' * 60}")
print(f"本次会话共采集 {len(results)} 个站点，详情见上方实时输出")
print(f"{'=' * 60}")
