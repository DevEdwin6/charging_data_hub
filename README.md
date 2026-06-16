# Charging Data Hub

多平台充电站数据采集框架，基于 Android **uiautomator2** 自动化，支持从多个充电桩 App 中抓取站点、充电桩及枪口数据，持久化到 MySQL。

## 项目结构

```
charging_data_hub/
├── run.py                   # 入口：DB 连接、批次管理、设备连接、驱动采集
├── db.py                    # MySQL 模块：连接管理、批次管理、事务写入
├── utils.py                 # 通用工具：设备操作原语、地理编码
├── scrapers/
│   ├── __init__.py
│   └── ev_station_pluz.py   # EV Station PluZ 采集器（约 1352 个站点）
├── requirements.txt
└── img/                     # 参考截图
```

## 环境要求

- Python 3.10+
- MySQL 5.7+
- Android 设备，USB 连接并开启 USB 调试

```bash
pip install -r requirements.txt
```

## 快速开始

**1. 建库建表**

执行项目 SQL 建表脚本（包含 `collection_runs`、`station_sites`、`station_charger_units`、`connector_status_snapshots` 四张表）。

**2. 修改配置**（`run.py` 顶部）

```python
# 数据库
DB_HOST     = "127.0.0.1"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = "your_password"
DB_NAME     = "charging_data_hub"

# 设备
DEVICE_SERIAL = "7391e8d9"   # adb devices 确认
```

**3. 确认设备并运行**

```bash
adb devices
python run.py
```

## 配置项（`run.py`）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEVICE_SERIAL` | `"7391e8d9"` | ADB 设备序列号 |
| `MAX_STATIONS` | `None` | 采集总量上限；`None` = 全部 |
| `RUN_MODE` | `"full"` | `full` 初次全量；`refresh` 仅刷新枪口状态 |

## 数据库结构

```
collection_runs          采集批次（一次跨多天的任务 = 一条记录）
  └─ station_sites       站点（platform_code + station_name 唯一）
       └─ station_charger_units   充电桩（物理设备，Charger ID 唯一）
            └─ connector_status_snapshots   枪口状态快照（追加，保留历史）
```

`connector_status_snapshots` 每次采集追加，含 `time_period`（day/night）和 `run_id`，支持跨时段价格分析。

## 断点续采

启动时自动查找该平台 `status='running'` 的批次：
- **找到** → 从 DB 查询已完成站点，自动跳过，从中断处续跑
- **找不到** → 创建新批次，全量采集

安全中断（Ctrl+C）不丢失数据，下次运行自动续采。

## 采集流程（EV Station PluZ）

```
Map 页
  └→ 点 ≡ 进全屏站点列表
       └→ 滚动找第一个未处理站点
            └→ 点击 → 预览卡 → View more → 详情页
                 ├→ _read_charger_units()     按充电桩分组读取枪口
                 ├→ read_detail_info()        状态 / 更新时间 / 备注
                 ├→ read_more_information()   完整地址 + 营业时间
                 └→ get_location_coords()     坐标（三层策略）
                      └→ db.save_station()   事务写入 MySQL
```

### 坐标获取（三层降级）

| 层级 | 方式 | 触发条件 |
|------|------|---------|
| 1 | Nominatim（站点名 + 简略地址） | 优先，无需操作设备 |
| 2 | Nominatim（站点名 + 完整地址） | 层 1 未命中 |
| 3 | Google Maps 分享链接展开 | 层 2 未命中，最慢 |

### 时段划分（EV Station PluZ）

| 时段 | 时间范围 | `time_period` |
|------|---------|---------------|
| 白天 | 09:00 – 22:00 | `day` |
| 夜间 | 22:00 – 09:00 | `night` |

按实际采集时刻（`collected_at`）逐条计算，同一批次允许混合时段。

## 采集数据结构（内存 → DB 映射）

```
station_data {
  name, address, full_address, hours, hours_by_day,
  overall_status, last_update, remarks,
  lat, lng, google_url,
  charger_units: [
    {
      id: "240311",
      name: "TS (133A Max Current)",
      connectors: [
        { position: "ซ้าย-A", connector_type: "DC CCS COMBO 2",
          power: "Max 40 kW", price: "8.00 ฿/kWh", status: "Available" }
      ]
    }
  ]
}
```

## 添加新平台

1. 在 `scrapers/` 下新建 `<platform>.py`，实现类并提供：
   - `PLATFORM_CODE`、`APP_PKG` 类常量
   - `get_time_period(dt)` 静态方法（定义该平台的时段规则）
   - `collect(results, processed, max_stations, run_id)` 采集主循环
2. 复用 `utils.py` 中的 `dump()`、`click_node()`、`geocode_nominatim()` 等通用函数
3. 在 `run.py` 中替换导入和实例化语句

## 注意事项

- **断线重连**：ATX agent 断线时自动调用 `d.reset_uiautomator()` 重连，最多重试 3 次
- **macOS SSL**：依赖 `certifi` 提供根证书，不可移除
- **跨天采集**：UI 自动化每站耗时较长，全量采集（约 1352 站）可能跨越多天，均属同一 `run_id`
- **滚动预算**：`max_scroll = len(processed) + 50`，动态计算，支持全量采集
