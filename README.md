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

执行项目 SQL 建表脚本（包含 `collection_runs`、`station_sites`、`connector_status_snapshots` 三张表）。

**2. 修改配置**（`config.py`）

```python
# 数据库
DB_HOST     = "127.0.0.1"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = "your_password"
DB_NAME     = "charging_data_hub"
```

**3. 确认设备并运行**

```bash
adb devices
python run.py
```

## 配置项（`config.py`）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | 见 `config.py` | MySQL 连接信息 |

采集数量、运行模式和设备序列号仍在 `run.py` 顶部调整，不放入 `config.py`。

## 数据库结构

```
collection_runs          采集批次（一次跨多天的任务 = 一条记录）
  └─ station_sites       站点（platform_code + station_name 唯一）
       └─ connector_status_snapshots   枪口状态快照（追加，保留历史；含充电桩信息）
```

`connector_status_snapshots` 每次采集追加，含 `platform_unit_id`、`unit_name`、`time_period`（day/night）和 `run_id`，支持按充电桩、枪口、时段做价格和状态分析。

旧库从 `station_charger_units + connector_status_snapshots` 合并到单表时，先执行：

```sql
source migrations/001_merge_charger_units_into_connector_status_snapshots.sql;
```

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
                 └→ get_location_coords()     Google Maps 坐标
                      └→ db.save_station()   事务写入 MySQL
```

### 坐标获取

直接打开 Google Maps，读取分享链接并从链接中解析坐标；不再调用 Nominatim 或 Google Geocoding API。

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
2. 复用 `utils.py` 中的 `dump()`、`click_node()` 等通用函数
3. 在 `run.py` 中替换导入和实例化语句

## 注意事项

- **断线重连**：ATX agent 断线时自动调用 `d.reset_uiautomator()` 重连，最多重试 3 次
- **macOS SSL**：依赖 `certifi` 提供根证书，不可移除
- **跨天采集**：UI 自动化每站耗时较长，全量采集（约 1352 站）可能跨越多天，均属同一 `run_id`
- **滚动预算**：`max_scroll = len(processed) + 50`，动态计算，支持全量采集
