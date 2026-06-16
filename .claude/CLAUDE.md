# charging_data_hub

多平台充电站数据采集框架。通过 uiautomator2 自动化操作 Android App，采集站点、充电桩、枪口数据并持久化到 MySQL。

## 项目结构

```
charging_data_hub/
├── run.py                   # 入口：DB 连接、批次管理、设备连接、驱动采集
├── db.py                    # MySQL 模块：连接管理、批次、事务写入
├── utils.py                 # 通用工具：设备操作原语、地理编码、保存
├── scrapers/
│   ├── __init__.py
│   └── ev_station_pluz.py   # EV Station PluZ 采集器
└── img/                     # 参考截图
```

## 环境要求

- Python 3.10+
- MySQL 5.7+
- Android 设备 USB 连接，开启 USB 调试
- 设备序列号：`7391e8d9`（`adb devices` 确认）
- 依赖：`uiautomator2`、`certifi`、`mysql-connector-python`

## 快速开始

```bash
adb devices
python run.py
```

## 关键配置（`run.py` 顶部）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_HOST` | `"127.0.0.1"` | MySQL 主机 |
| `DB_PORT` | `3307` | MySQL 端口 |
| `DB_USER` | `"root"` | 用户名 |
| `DB_PASSWORD` | `""` | 密码 |
| `DB_NAME` | `"charging_data_hub"` | 数据库名 |
| `DEVICE_SERIAL` | `"7391e8d9"` | ADB 设备序列号 |
| `MAX_STATIONS` | `None` | 采集总量上限；`None` = 全部 |
| `RUN_MODE` | `"full"` | `full` 全量；`refresh` 刷新快照 |

## 数据库结构（4 张表）

```
collection_runs              采集批次（跨多天的任务 = 一条记录）
  └─ station_sites           站点（platform_code + station_name 唯一）
       └─ station_charger_units     充电桩（Charger ID 唯一）
            └─ connector_status_snapshots  枪口状态快照（追加不覆盖）
```

`connector_status_snapshots` 含 `run_id`、`time_period`（day/night）、`collected_at`，支持跨时段价格分析。

## 断点续采机制

- 启动时查找 `status='running'` 的批次 → 从 DB 加载已完成站点 → 自动跳过
- 每站写入通过事务保证原子性：失败回滚，下次重试
- 安全中断（Ctrl+C）不丢失进度

## 采集流程（EV Station PluZ）

```
Map 页 → ≡ 全屏列表 → 找未处理站点
  → 点击 → 预览卡 → View more → 详情页
    ├→ _read_charger_units()    按充电桩分组读取枪口（含位置名）
    ├→ read_detail_info()       状态 / 更新时间 / 备注
    ├→ read_more_information()  完整地址 + 营业时间
    └→ get_location_coords()    坐标（Nominatim x2 → GMaps 兜底）
         └→ db.save_station()  事务写入 MySQL
```

## 时段划分（EV Station PluZ）

- 白天（`day`）：09:00 – 22:00
- 夜间（`night`）：22:00 – 09:00
- 按各快照的 `collected_at` 逐条计算，同一批次允许混合时段

## 采集数据层级

```
Platform → Station → Charger Unit（充电桩） → Connector（枪口）

charger_units[].connectors[]:
  position      枪口位置名，如 ซ้าย-A（左-A）、ขวา-B（右-B）
  connector_type  如 DC CCS COMBO 2 / AC Type 2
  power         如 Max 40 kW
  price         如 8.00 ฿/kWh
  status        Available / Occupied / Offline
```

## 坐标获取策略

1. Nominatim（站点名 + 简略地址）— 最快
2. Nominatim（站点名 + 完整地址）— 第二层
3. Google Maps 分享链接展开 — 最慢，兜底；成功时写入 `google_url`

## 添加新平台

1. `scrapers/<platform>.py` — 实现类，提供 `PLATFORM_CODE`、`get_time_period()`、`collect()`
2. 复用 `utils.py` 的 `dump()`、`click_node()`、`geocode_nominatim()`
3. `run.py` 替换导入和实例化语句

## 已知注意事项

- **断线重连**：`ensure_connected()` 最多重试 3 次，每次等待 4 秒
- **macOS SSL**：`certifi` 不可移除
- **跨天采集**：全量约 1352 站，UI 自动化耗时长，可能跨越多天，均属同一 `run_id`
- **滚动预算**：`max_scroll = len(processed) + 50`，动态计算
