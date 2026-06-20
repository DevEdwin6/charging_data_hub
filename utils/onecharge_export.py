#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OneCharge 全量站点导出脚本

采集路径：
1. GET /api/v1/partner-station/stations
2. GET /api/v1/partner-station/stations/{id}
3. 输出统一 JSON 到脚本同目录

运行前设置环境变量：
Windows PowerShell:
  $env:ONECHARGE_AUTHORIZATION="Bearer 你的token"
  python onecharge_export.py

macOS / Linux:
  export ONECHARGE_AUTHORIZATION="Bearer 你的token"
  python3 onecharge_export.py
"""

import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


BASE_URL = "https://api-be-core.onecharge.co.th/api/v1"

# 地图筛选参数：
# max_kwh=4：筛选页最低功率在最左侧，基本等于不限制功率。
# false：不启用公共站点、RFID、Autocharge 筛选。
STATION_LIST_PARAMS = {
    "max_kwh": "4",
    "is_public_station_available": "false",
    "is_rfid": "false",
    "is_autocharge": "false",
}

REQUEST_DELAY_RANGE = (1.2, 3.2)
STATION_DELAY_RANGE = (0.5, 1.8)
RETRY_BACKOFF_RANGE = (4.0, 10.0)
MAX_RETRIES = 3
TIMEOUT = 25

# 0 表示全部。测试时可以改成 5 / 10。
MAX_STATIONS = 0
VERBOSE = True


def log(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def sleep_random(delay_range: Tuple[float, float], reason: str = "") -> None:
    seconds = round(random.uniform(delay_range[0], delay_range[1]), 2)
    if VERBOSE and reason:
        log(f"等待 {seconds}s：{reason}")
    time.sleep(seconds)


def to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_number(value: Any) -> Optional[Any]:
    number = to_float(value)
    if number is None:
        return None
    if number.is_integer():
        return int(number)
    return number


def normalize_auth(auth: str) -> str:
    auth = (auth or "").strip()
    if not auth:
        raise RuntimeError(
            "缺少 ONECHARGE_AUTHORIZATION 环境变量。请设置为：Bearer 你的token"
        )
    lower = auth.lower()
    if lower.startswith("bearer ") or lower.startswith("basic "):
        return auth
    return f"Bearer {auth}"


def normalize_connector_type(connector_type: Any, plug_type: Any) -> Optional[str]:
    c_type = str(connector_type or "").strip().upper()
    p_type = str(plug_type or "").strip()
    if not c_type and not p_type:
        return None
    if p_type.lower() == "type2":
        p_type = "Type 2"
    if c_type and p_type:
        return f"{c_type} {p_type}"
    return c_type or p_type


def normalize_charger_type(connectors: List[Dict[str, Any]]) -> Optional[str]:
    types = set()
    for connector in connectors:
        c_type = str(connector.get("type") or "").strip().upper()
        if c_type:
            types.add(c_type)
    if not types:
        return None
    if len(types) == 1:
        return next(iter(types))
    return "MIXED"


def normalize_status(status: Any) -> str:
    text = str(status or "").strip().lower()
    status_map = {
        "available": "available",
        "charging": "occupied",
        "preparing": "occupied",
        "occupied": "occupied",
        "finishing": "occupied",
        "suspendedev": "occupied",
        "suspendedevse": "occupied",
        "reserved": "reserved",
        "unavailable": "unavailable",
        "faulted": "faulted",
        "offline": "offline",
    }
    return status_map.get(text, "unknown")


def pick_connector_price(connector: Dict[str, Any], charger: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    输出 price_day / price_night。

    优先级：
    1. team_group_price_set.price_on_peak / price_off_peak
    2. team_group_price_set.price_per_kwh，如果 > 0
    3. charger.cost_rate_kwh
    4. 最后才接受 connector 里的 0
    """
    price_sets = connector.get("team_group_price_set") or []
    selected = None

    for item in price_sets:
        if str(item.get("status_type") or "").upper() == "GENERAL":
            selected = item
            break
    if selected is None and price_sets:
        selected = price_sets[0]

    cost_rate = to_float(charger.get("cost_rate_kwh"))

    if selected:
        price_on_peak = to_float(selected.get("price_on_peak"))
        price_off_peak = to_float(selected.get("price_off_peak"))
        price_per_kwh = to_float(selected.get("price_per_kwh"))

        if price_on_peak is not None or price_off_peak is not None:
            day = price_on_peak if price_on_peak is not None else price_off_peak
            night = price_off_peak if price_off_peak is not None else price_on_peak
            if day is None:
                day = cost_rate
            if night is None:
                night = cost_rate
            return day, night

        # 很多站点 price_per_kwh=0，但 App 展示 charger.cost_rate_kwh，例如 7.5。
        # 所以 0 不优先作为真实价格。
        if price_per_kwh is not None and price_per_kwh > 0:
            return price_per_kwh, price_per_kwh

    if cost_rate is not None:
        return cost_rate, cost_rate

    if selected:
        price_per_kwh = to_float(selected.get("price_per_kwh"))
        if price_per_kwh is not None:
            return price_per_kwh, price_per_kwh

    return None, None


def get_charger_kw(connectors: List[Dict[str, Any]]) -> Optional[Any]:
    powers = []
    for connector in connectors:
        power = to_float(connector.get("power"))
        if power is not None:
            powers.append(power)
    if not powers:
        return None
    return clean_number(max(powers))


class OneChargeClient:
    def __init__(self) -> None:
        authorization = normalize_auth(os.getenv("ONECHARGE_AUTHORIZATION", ""))
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Dart/2.19 (dart:io)",
            "Accept-Encoding": "gzip",
            "authorization": authorization,
            "content-type": "application/json",
            "lang-id": "2",
        })

    def request_json(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        request_name: str = "",
    ) -> Dict[str, Any]:
        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            sleep_random(REQUEST_DELAY_RANGE, reason=f"{request_name or url} 请求前限速")
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, params=params, timeout=TIMEOUT)
                elif method.upper() == "POST":
                    response = self.session.post(url, json=json_body, timeout=TIMEOUT)
                else:
                    raise ValueError(f"不支持的请求方法：{method}")

                response.raise_for_status()
                data = response.json()
                status_code = data.get("statusCode")
                if status_code not in (200, 201):
                    raise RuntimeError(f"接口业务失败：statusCode={status_code}, message={data.get('message')}")
                return data
            except Exception as exc:
                last_error = exc
                log(f"请求失败 [{request_name}] 第 {attempt}/{MAX_RETRIES} 次：{exc}")
                if attempt < MAX_RETRIES:
                    sleep_random(RETRY_BACKOFF_RANGE, reason="失败退避")
        raise RuntimeError(f"请求最终失败 [{request_name}]：{last_error}")

    def fetch_station_markers(self) -> List[Dict[str, Any]]:
        url = f"{BASE_URL}/partner-station/stations"
        data = self.request_json(
            "GET",
            url,
            params=STATION_LIST_PARAMS,
            request_name="站点地图列表",
        )
        items = data.get("data") or []
        if not isinstance(items, list):
            raise RuntimeError("站点地图列表 data 不是数组")
        return items

    def fetch_station_detail(self, station_id: Any) -> Dict[str, Any]:
        url = f"{BASE_URL}/partner-station/stations/{station_id}"
        data = self.request_json(
            "GET",
            url,
            request_name=f"站点详情 id={station_id}",
        )
        detail = data.get("data") or {}
        if not isinstance(detail, dict):
            raise RuntimeError(f"站点详情格式异常：station_id={station_id}")
        return detail


def build_target_station(detail: Dict[str, Any]) -> Dict[str, Any]:
    output_chargers: List[Dict[str, Any]] = []
    chargers = detail.get("chargers") or []

    for charger in chargers:
        plug_powers = charger.get("charger_plug_powers") or []
        output_connectors: List[Dict[str, Any]] = []

        for connector in plug_powers:
            kw = clean_number(connector.get("power"))
            price_day, price_night = pick_connector_price(connector, charger)

            output_connectors.append({
                "position": str(connector.get("name") or connector.get("connection_id") or ""),
                "type": normalize_connector_type(
                    connector.get("type"),
                    connector.get("plug_type"),
                ),
                "kw": kw,
                "price_day": price_day,
                "price_night": price_night,
                "status": normalize_status(connector.get("connector_status")),
            })

        output_chargers.append({
            "name": str(charger.get("name") or ""),
            "type": normalize_charger_type(plug_powers),
            "heads": len(output_connectors),
            "kw": get_charger_kw(plug_powers),
            "connectors": output_connectors,
        })

    return {
        "name": detail.get("station_name") or "",
        "lat": to_float(detail.get("latitude")),
        "lon": to_float(detail.get("longitude")),
        "chargers": output_chargers,
        "address": detail.get("address") or "",
    }


def collect_all_stations() -> List[Dict[str, Any]]:
    client = OneChargeClient()
    log("开始采集 OneCharge 站点数据")

    markers = client.fetch_station_markers()
    if MAX_STATIONS and MAX_STATIONS > 0:
        markers = markers[:MAX_STATIONS]

    log(f"地图站点数量：{len(markers)}")

    results: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for index, marker in enumerate(markers, start=1):
        station_id = marker.get("id")
        station_name = marker.get("station_name") or ""
        log(f"处理站点 {index}/{len(markers)}：{station_name} (id={station_id})")

        if station_id is None:
            log("跳过：station_id 为空")
            continue

        try:
            detail = client.fetch_station_detail(station_id)
            target = build_target_station(detail)
            results.append(target)

            charger_count = len(target.get("chargers") or [])
            connector_count = sum(
                len(charger.get("connectors") or [])
                for charger in target.get("chargers") or []
            )
            log(f"完成：{target.get('name')}，桩 {charger_count} 个，枪口 {connector_count} 个")
        except Exception as exc:
            log(f"站点处理失败：{station_name} (id={station_id})，原因：{exc}")
            failed.append({
                "id": station_id,
                "station_name": station_name,
                "error": str(exc),
            })

        sleep_random(STATION_DELAY_RANGE, reason="站点处理间隔")

    script_dir = Path(__file__).resolve().parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = script_dir / f"onecharge_stations_{timestamp}.json"
    failed_path = script_dir / f"onecharge_failed_{timestamp}.json"

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
