#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iGreen+ 全量站点采集脚本

功能：
1. 分页获取全部站点；
2. 根据 staPkId 获取充电桩 / 枪口明细；
3. 根据 staPkId 获取价格规则；
4. 输出最终目标 JSON 文件到脚本同目录。

输出结构：
[
  {
    "name": "...",
    "lat": 13.000000,
    "lon": 100.000000,
    "chargers": [
      {
        "name": "...",
        "type": "AC",
        "heads": 1,
        "kw": 7.4,
        "connectors": [
          {
            "position": "A",
            "type": "AC Type 2",
            "kw": 7.4,
            "price_day": 9.0,
            "price_night": 9.0,
            "status": "available"
          }
        ]
      }
    ],
    "address": "..."
  }
]
"""

import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ==============================
# 基础配置
# ==============================

BASE_URL = "https://user.csenergytech.com/api/oms-operation-service/v1"

OPR_PK_ID = "0001"

# 坐标会影响列表排序和 currentDistance，不影响站点真实经纬度。
USER_LAT = 13.747679932548326
USER_LNG = 100.54582240059972

PAGE_SIZE = 20

# 低频采集：每次请求前随机等待，避免请求过密。
REQUEST_DELAY_RANGE = (1.5, 4.0)

# 每处理完一个站点，再额外随机等待。
STATION_DELAY_RANGE = (0.8, 2.5)

# 请求失败后的退避等待。
RETRY_BACKOFF_RANGE = (5.0, 12.0)

MAX_RETRIES = 3
TIMEOUT = 20

# 调试用：0 表示采集全部；设置为 5 表示只采集前 5 个站点。
MAX_STATIONS = 0

# 是否输出更详细日志。
VERBOSE = True

HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip",
    "Content-Type": "application/json",
    "accept-language": "zh-CN",
    "version": "11001301",
    "ostype": "android",
    "x-device-id": "android-560c2f971b3122af",
}


# ==============================
# 工具函数
# ==============================

def log(message: str) -> None:
    """控制台日志输出。"""
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def sleep_random(delay_range: Tuple[float, float], reason: str = "") -> None:
    """随机等待，降低请求频率。"""
    seconds = round(random.uniform(delay_range[0], delay_range[1]), 2)
    if VERBOSE and reason:
        log(f"等待 {seconds}s：{reason}")
    time.sleep(seconds)


def to_float(value: Any) -> Optional[float]:
    """安全转 float。"""
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_kw(value: Any) -> Optional[float]:
    """
    把 '7.4kW' / '22kW' / 7.4 转成 float。
    """
    if value is None or value == "":
        return None

    text = str(value)
    match = re.search(r"[\d.]+", text)
    if not match:
        return None

    return to_float(match.group())


def normalize_charger_type(device_type_desc: Any, device_type: Any = None) -> Optional[str]:
    """
    充电桩类型标准化。
    """
    desc = str(device_type_desc or "")

    if "交流" in desc:
        return "AC"

    if "直流" in desc:
        return "DC"

    # 兜底：从已观察数据看，2=交流桩，3=直流桩。
    if device_type == 2:
        return "AC"

    if device_type == 3:
        return "DC"

    return None


def normalize_connector_type(charger_type: Optional[str], interface_desc: Any) -> Optional[str]:
    """
    枪口类型标准化。
    """
    if interface_desc is None or interface_desc == "":
        return None

    text = str(interface_desc).strip()

    # Type2 -> Type 2
    if text.lower() == "type2":
        text = "Type 2"

    # CCS2 -> CCS2
    if charger_type == "AC":
        return f"AC {text}"

    if charger_type == "DC":
        return f"DC {text}"

    return text


def normalize_status(gun_status_desc: Any, device_status_desc: Any = None) -> str:
    """
    枪口状态标准化成目标结构需要的英文状态。
    """
    device_text = str(device_status_desc or "")
    if "离线" in device_text or "下线" in device_text:
        return "offline"

    text = str(gun_status_desc or "")

    status_map = {
        "空闲": "available",
        "充电中": "occupied",
        "占用": "occupied",
        "预约中": "reserved",
        "故障": "faulted",
        "离线": "offline",
        "下线": "offline",
        "维护中": "maintenance",
        "不可用": "unavailable",
    }

    return status_map.get(text, "unknown")


def covers_time(begin: Any, end: Any, target: int) -> bool:
    """
    判断一个价格时间段是否覆盖 target。

    时间格式：
    0    = 00:00
    1200 = 12:00
    2200 = 22:00
    2400 = 24:00
    """
    if begin is None or end is None:
        return False

    try:
        begin_int = int(begin)
        end_int = int(end)
    except (TypeError, ValueError):
        return False

    # 正常时间段：0-2400、600-2000
    if begin_int <= end_int:
        return begin_int <= target < end_int

    # 跨天时间段：2200-600
    return target >= begin_int or target < end_int


def pick_price_by_time(price_parts: List[Dict[str, Any]], target: int) -> Optional[float]:
    """
    从分时价格里取覆盖指定时间点的价格。
    """
    if not price_parts:
        return None

    # 优先取覆盖目标时间的价格
    for part in price_parts:
        if covers_time(part.get("beginTime"), part.get("endTime"), target):
            price = part.get("slotCampaignElecPrice")
            if price is None:
                price = part.get("slotElecPrice")
            return to_float(price)

    # 如果没有命中，取第一条作为兜底
    first = price_parts[0]
    price = first.get("slotCampaignElecPrice")
    if price is None:
        price = first.get("slotElecPrice")
    return to_float(price)


def build_price_map(station: Dict[str, Any], fee_data: Optional[Dict[str, Any]]) -> Dict[
    str, Dict[str, Optional[float]]]:
    """
    生成 AC / DC 的 day/night 价格。

    优先使用 detail/fee 接口：
    - day：取覆盖 12:00 的价格
    - night：取覆盖 22:00 的价格

    如果 detail/fee 失败，则回退到 page.currentPriceList。
    """
    result = {
        "AC": {"price_day": None, "price_night": None},
        "DC": {"price_day": None, "price_night": None},
    }

    if fee_data:
        ac_parts = fee_data.get("acElecpricePartDescPos") or []
        dc_parts = fee_data.get("dcElecpricePartDescPos") or []

        result["AC"]["price_day"] = pick_price_by_time(ac_parts, 1200)
        result["AC"]["price_night"] = pick_price_by_time(ac_parts, 2200)

        result["DC"]["price_day"] = pick_price_by_time(dc_parts, 1200)
        result["DC"]["price_night"] = pick_price_by_time(dc_parts, 2200)

    # fallback：使用列表接口 currentPriceList 的第一条当前价
    current_price_list = station.get("currentPriceList") or []
    if current_price_list:
        current = current_price_list[0]

        if result["AC"]["price_day"] is None:
            result["AC"]["price_day"] = to_float(current.get("acElecFee"))
        if result["AC"]["price_night"] is None:
            result["AC"]["price_night"] = to_float(current.get("acElecFee"))

        if result["DC"]["price_day"] is None:
            result["DC"]["price_day"] = to_float(current.get("dcElecFee"))
        if result["DC"]["price_night"] is None:
            result["DC"]["price_night"] = to_float(current.get("dcElecFee"))

    return result


# ==============================
# HTTP 请求函数
# ==============================

class IGreenClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def request_json(
            self,
            method: str,
            url: str,
            *,
            params: Optional[Dict[str, Any]] = None,
            json_body: Optional[Dict[str, Any]] = None,
            request_name: str = "",
    ) -> Dict[str, Any]:
        """
        带低频等待、失败重试的 JSON 请求。
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            sleep_random(REQUEST_DELAY_RANGE, reason=f"{request_name or url} 请求前限速")

            try:
                if method.upper() == "GET":
                    response = self.session.get(
                        url,
                        params=params,
                        timeout=TIMEOUT,
                    )
                elif method.upper() == "POST":
                    response = self.session.post(
                        url,
                        json=json_body,
                        timeout=TIMEOUT,
                    )
                else:
                    raise ValueError(f"不支持的请求方法：{method}")

                response.raise_for_status()
                data = response.json()

                if data.get("status") != 0:
                    raise RuntimeError(f"接口业务失败：{data.get('msg')}")

                return data

            except Exception as exc:
                last_error = exc
                log(f"请求失败 [{request_name}] 第 {attempt}/{MAX_RETRIES} 次：{exc}")

                if attempt < MAX_RETRIES:
                    sleep_random(RETRY_BACKOFF_RANGE, reason="失败退避")

        raise RuntimeError(f"请求最终失败 [{request_name}]：{last_error}")

    def fetch_station_page(self, page_index: int) -> Dict[str, Any]:
        url = f"{BASE_URL}/opr/sta/wx/page"

        payload = {
            "userPkId": "",
            "chargeUserPkId": "",
            "oprPkId": OPR_PK_ID,
            "globalPageIndex": page_index,
            "globalPageSize": PAGE_SIZE,
            "userLat": USER_LAT,
            "userLng": USER_LNG,
            "distance": "",
            "speedTypes": [],
            "pileStatusList": [],
            "featureList": [],
            "operator": [],
            "gunInterfaceTypeList": [],
            "discountTypeList": [],
        }

        return self.request_json(
            "POST",
            url,
            json_body=payload,
            request_name=f"站点分页 page={page_index}",
        )

    def fetch_pile_list(self, sta_pk_id: str, opr_pk_id: str = OPR_PK_ID) -> List[Dict[str, Any]]:
        url = f"{BASE_URL}/opr/sta/wx/detail_more/pile/list"

        params = {
            "oprPkId": opr_pk_id,
            "staPkId": sta_pk_id,
        }

        data = self.request_json(
            "GET",
            url,
            params=params,
            request_name=f"桩枪列表 staPkId={sta_pk_id}",
        )

        return data.get("data") or []

    def fetch_fee_info(self, sta_pk_id: str, opr_pk_id: str = OPR_PK_ID) -> Optional[Dict[str, Any]]:
        url = f"{BASE_URL}/opr/sta/wx/detail/fee"

        params = {
            "oprPkId": opr_pk_id,
            "staPkId": sta_pk_id,
        }

        data = self.request_json(
            "GET",
            url,
            params=params,
            request_name=f"价格规则 staPkId={sta_pk_id}",
        )

        items = data.get("data") or []
        return items[0] if items else None


# ==============================
# 数据转换函数
# ==============================

def build_target_station(
        station: Dict[str, Any],
        pile_items: List[Dict[str, Any]],
        fee_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    合并 page + pile/list + detail/fee，生成最终目标结构。
    """
    price_map = build_price_map(station, fee_data)

    chargers_map: Dict[str, Dict[str, Any]] = {}

    for item in pile_items:
        pile_pk_id = str(item.get("pilePkId") or item.get("serialNumber") or item.get("pileName") or "")

        if not pile_pk_id:
            continue

        charger_type = normalize_charger_type(
            item.get("deviceTypeDesc"),
            item.get("deviceType"),
        )
        kw = parse_kw(item.get("pilePower"))

        if pile_pk_id not in chargers_map:
            chargers_map[pile_pk_id] = {
                "name": item.get("pileName") or item.get("serialNumber") or "",
                "type": charger_type,
                "heads": 0,
                "kw": kw,
                "connectors": [],
            }

        connector_price = price_map.get(charger_type or "", {
            "price_day": None,
            "price_night": None,
        })

        connector = {
            "position": item.get("gunName") or item.get("gunNumber") or "",
            "type": normalize_connector_type(
                charger_type,
                item.get("gunInterfaceTypeDesc"),
            ),
            "kw": kw,
            "price_day": connector_price.get("price_day"),
            "price_night": connector_price.get("price_night"),
            "status": normalize_status(
                item.get("gunStatusDesc"),
                item.get("deviceStatusDesc"),
            ),
        }

        chargers_map[pile_pk_id]["connectors"].append(connector)
        chargers_map[pile_pk_id]["heads"] = len(chargers_map[pile_pk_id]["connectors"])

    return {
        "name": station.get("staName") or "",
        "lat": to_float(station.get("staLat")),
        "lon": to_float(station.get("staLng")),
        "chargers": list(chargers_map.values()),
        "address": station.get("staAddress") or "",
    }


# ==============================
# 主流程
# ==============================

def collect_all_stations() -> List[Dict[str, Any]]:
    client = IGreenClient()

    log("开始采集 iGreen+ 站点数据")

    first_page = client.fetch_station_page(1)
    total_page = int(first_page.get("totalPage") or 1)
    total = int(first_page.get("total") or 0)

    log(f"站点总数：{total}，总页数：{total_page}，每页：{PAGE_SIZE}")

    all_station_rows: List[Dict[str, Any]] = []

    # 第一页已经请求过，避免重复请求。
    for page_index in range(1, total_page + 1):
        if page_index == 1:
            page_data = first_page
        else:
            page_data = client.fetch_station_page(page_index)

        stations = page_data.get("data") or []
        log(f"分页进度：{page_index}/{total_page}，当前页站点数：{len(stations)}")

        for station in stations:
            all_station_rows.append(station)

            if MAX_STATIONS and len(all_station_rows) >= MAX_STATIONS:
                break

        if MAX_STATIONS and len(all_station_rows) >= MAX_STATIONS:
            break

    log(f"已获取站点列表数量：{len(all_station_rows)}")

    results: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for index, station in enumerate(all_station_rows, start=1):
        sta_pk_id = station.get("staPkId")
        sta_name = station.get("staName") or ""
        opr_pk_id = station.get("oprPkId") or OPR_PK_ID

        log(f"处理站点 {index}/{len(all_station_rows)}：{sta_name} ({sta_pk_id})")

        if not sta_pk_id:
            log("跳过：staPkId 为空")
            continue

        try:
            pile_items = client.fetch_pile_list(
                sta_pk_id=sta_pk_id,
                opr_pk_id=opr_pk_id,
            )

            fee_data = client.fetch_fee_info(
                sta_pk_id=sta_pk_id,
                opr_pk_id=opr_pk_id,
            )

            target = build_target_station(
                station=station,
                pile_items=pile_items,
                fee_data=fee_data,
            )

            results.append(target)

            charger_count = len(target["chargers"])
            connector_count = sum(len(charger.get("connectors") or []) for charger in target["chargers"])

            log(f"完成：{sta_name}，桩 {charger_count} 个，枪口 {connector_count} 个")

        except Exception as exc:
            log(f"站点处理失败：{sta_name} ({sta_pk_id})，原因：{exc}")
            failed.append({
                "staPkId": sta_pk_id,
                "staName": sta_name,
                "error": str(exc),
            })

        sleep_random(STATION_DELAY_RANGE, reason="站点处理间隔")

    script_dir = Path(__file__).resolve().parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_path = script_dir / f"igreen_plus_stations_{timestamp}.json"
    failed_path = script_dir / f"igreen_plus_failed_{timestamp}.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log(f"最终 JSON 已输出：{output_path}")
    log(f"成功站点数：{len(results)}")

    if failed:
        with failed_path.open("w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)

        log(f"失败站点数：{len(failed)}，失败记录已输出：{failed_path}")
    else:
        log("失败站点数：0")

    return results


def main() -> None:
    try:
        collect_all_stations()
        log("采集完成")
    except KeyboardInterrupt:
        log("用户中断")
        sys.exit(130)
    except Exception as exc:
        log(f"程序异常退出：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
