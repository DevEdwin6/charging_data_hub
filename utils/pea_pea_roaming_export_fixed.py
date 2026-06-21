#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PEA VOLTA / VOLTA CONNEXT / EV Roaming 站点采集脚本（修正版）

修正点：
1. PUPA 是枪口类型 AC Outlet，不是运营商；
2. 服务商只按 App 页面主开关分两类采集：
   - VOLTA_CONNECT：PEA VOLTA / VOLTA CONNEXT
   - EV_ROAMING_ALL：EV Roaming
3. 默认只请求 2 次地图接口，不再做 30 次重复请求；
4. 修复去重字段，兼容 stationId / stationID / id / locId / name+lat+lng；
5. 输出 raw markers，方便检查原始字段；
6. 名称优先取英文 textEN，没有英文再取 textTH；
7. 输出统一结构，并保留 operator / provider / source_groups。

采集链路：
1. POST /charger/ command=getMapStationStatus
2. POST /charger/ command=getStationInfo
3. GET  /v2/connector/{charger_number}/{connectorID}/info

依赖：
  pip install requests

运行：
  python pea_pea_roaming_export_fixed.py
"""

import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ==============================
# 认证信息：本地脚本硬编码
# 失效时替换这里
# ==============================

PEA_EVSESSIONKEY = "evc3kbeemfeckkq98s03i6i9c1"
PEA_USERKEY = "40712b898cf23a4ca273867159beffb0b1e27256b222a28d46a495b90d061461"

# ==============================
# 基础配置
# ==============================

BASE_URL = "https://volta-api.pea.co.th"

# 0 = 全部；调试可改 5 / 10。
MAX_STATIONS = 0

# 默认只请求 App 页面两个服务商开关，避免重复。
COLLECT_SERVICE_GROUPS = [
    "VOLTA_CONNECT",
    "EV_ROAMING_ALL",
]

# 如果你后面确认 EGAT / EVOLT / MEA / OR 细分筛选真正有效，再改为 True。
ENABLE_ROAMING_SUB_FILTERS = False

# 是否请求单枪详情接口，获取价格 / 实时 kW / iconUrl。
FETCH_CONNECTOR_INFO = True

# 某些 roaming 站点可能没有详情，是否输出 marker 兜底数据。
OUTPUT_MARKER_FALLBACK_WHEN_DETAIL_FAILED = True

# radius=999 从你的日志看已经返回固定大集合，默认不需要多中心点。
USE_MULTI_CENTERS = False

RADIUS = "999"

MAP_CENTERS = [
    ("13.7451863", "100.5458226", "Bangkok / Central"),
    ("18.7883", "98.9853", "Chiang Mai / North"),
    ("16.4322", "102.8236", "Khon Kaen / Northeast"),
    ("12.9236", "100.8825", "Pattaya / East"),
    ("7.0086", "100.4747", "Hat Yai / South"),
]

MAP_DELAY_RANGE = (1.0, 2.2)
REQUEST_DELAY_RANGE = (1.0, 2.5)
STATION_DELAY_RANGE = (0.6, 1.6)
CONNECTOR_DELAY_RANGE = (0.25, 0.8)
RETRY_BACKOFF_RANGE = (3.0, 8.0)

MAX_RETRIES = 3
TIMEOUT = 25
VERBOSE = True

# 是否打印每组返回第一条数据字段，便于确认字段名。
DEBUG_FIRST_ITEM = True

# ==============================
# 服务商分组
# ==============================

SERVICE_GROUP_CONFIG = {
    "VOLTA_CONNECT": {
        "label": "PEA VOLTA",
        "filters": {
            "filter[VOLTA_CONNECT]": "true",
            "filter[EV_ROAMING]": "false",
            "filter[EGAT]": "false",
            "filter[EVOLT]": "false",
            "filter[MEA]": "false",
            "filter[OR]": "false",
        },
    },
    "EV_ROAMING_ALL": {
        "label": "EV Roaming",
        "filters": {
            "filter[VOLTA_CONNECT]": "false",
            "filter[EV_ROAMING]": "true",

            # 从日志看，EGAT / EVOLT / MEA / OR 单独开关可能不生效或返回同一批。
            # 在 EV_ROAMING_ALL 中先全部打开，拿 Roaming 总集合。
            "filter[EGAT]": "true",
            "filter[EVOLT]": "true",
            "filter[MEA]": "true",
            "filter[OR]": "true",
        },
    },
    "EGAT": {
        "label": "EGAT",
        "filters": {
            "filter[VOLTA_CONNECT]": "false",
            "filter[EV_ROAMING]": "true",
            "filter[EGAT]": "true",
            "filter[EVOLT]": "false",
            "filter[MEA]": "false",
            "filter[OR]": "false",
        },
    },
    "EVOLT": {
        "label": "EVOLT",
        "filters": {
            "filter[VOLTA_CONNECT]": "false",
            "filter[EV_ROAMING]": "true",
            "filter[EGAT]": "false",
            "filter[EVOLT]": "true",
            "filter[MEA]": "false",
            "filter[OR]": "false",
        },
    },
    "MEA": {
        "label": "MEA",
        "filters": {
            "filter[VOLTA_CONNECT]": "false",
            "filter[EV_ROAMING]": "true",
            "filter[EGAT]": "false",
            "filter[EVOLT]": "false",
            "filter[MEA]": "true",
            "filter[OR]": "false",
        },
    },
    "OR": {
        "label": "OR",
        "filters": {
            "filter[VOLTA_CONNECT]": "false",
            "filter[EV_ROAMING]": "true",
            "filter[EGAT]": "false",
            "filter[EVOLT]": "false",
            "filter[MEA]": "false",
            "filter[OR]": "true",
        },
    },
}

PARTY_ID_OPERATOR_MAP = {
    "PEA": "PEA VOLTA",
    "VOLTA": "PEA VOLTA",
    "PEA VOLTA": "PEA VOLTA",
    "VOLTA CONNECT": "PEA VOLTA",
    "VOLTA CONNEXT": "PEA VOLTA",

    "EGAT": "EGAT",
    "EVOLT": "EVOLT",
    "MEA": "MEA",
    "OR": "OR",
    "PTTOR": "OR",
    "PTT": "OR",
}

NAME_OPERATOR_KEYWORDS = [
    ("PEA VOLTA", "PEA VOLTA"),
    ("VOLTA", "PEA VOLTA"),
    ("EGAT", "EGAT"),
    ("EVOLT", "EVOLT"),
    ("MEA", "MEA"),
    ("PTTOR", "OR"),
    ("PTT", "OR"),
    (" OR ", "OR"),
]


# ==============================
# 工具函数
# ==============================

def log(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def sleep_random(delay_range: Tuple[float, float], reason: str = "") -> None:
    seconds = round(random.uniform(delay_range[0], delay_range[1]), 2)
    if VERBOSE and reason:
        log(f"等待 {seconds}s：{reason}")
    time.sleep(seconds)


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def first_value(item: Dict[str, Any], keys: List[str]) -> str:
    for key in keys:
        value = clean_text(item.get(key))
        if value:
            return value
    return ""


def to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_number(value: Any) -> Optional[Any]:
    number = to_float(value)
    if number is None:
        return None
    return int(number) if number.is_integer() else number


def pick_text(value: Any, lang: str = "EN") -> str:
    """
    多语言字段英文优先：
    {"textTH": "...", "textEN": "..."}
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        if lang.upper() == "TH":
            return clean_text(value.get("textTH")) or clean_text(value.get("textEN"))
        return clean_text(value.get("textEN")) or clean_text(value.get("textTH"))

    return clean_text(value)


def get_marker_station_id(item: Dict[str, Any]) -> str:
    """
    当前 PEA marker 常见是 stationId；
    但 roaming 可能字段不同，所以做兼容。
    """
    return first_value(item, [
        "stationId",
        "stationID",
        "station_id",
        "stationCode",
        "station_code",
        "stationNo",
        "station_no",
        "id",
        "locId",
        "chargerId",
        "chargerID",
    ])


def get_marker_name(item: Dict[str, Any]) -> str:
    return first_value(item, [
        "stationName_Dev",
        "stationName",
        "station_name",
        "name",
        "locationName",
        "location_name",
        "title",
    ])


def get_marker_lat(item: Dict[str, Any]) -> Optional[float]:
    return to_float(
        item.get("lat")
        or item.get("latitude")
        or item.get("gpsLat")
        or item.get("gps_lat")
    )


def get_marker_lon(item: Dict[str, Any]) -> Optional[float]:
    return to_float(
        item.get("lng")
        or item.get("lon")
        or item.get("longitude")
        or item.get("gpsLng")
        or item.get("gps_lng")
    )


def get_marker_unique_id(item: Dict[str, Any]) -> str:
    """
    修复去重字段：
    1. 优先用 stationId / id / locId；
    2. 如果没有 ID，用 name + lat + lng 兜底；
    3. 如果仍然没有，返回空字符串。
    """
    station_id = get_marker_station_id(item)
    if station_id:
        return station_id

    name = get_marker_name(item)
    lat = get_marker_lat(item)
    lon = get_marker_lon(item)

    if name and lat is not None and lon is not None:
        return f"{name}|{lat}|{lon}"

    return ""


# ==============================
# 类型 / 状态规范化
# ==============================

def normalize_connector_type(code_org: Any) -> str:
    text = clean_text(code_org)
    lower = text.lower()

    if not text:
        return ""

    if "pupa" in lower or "outlet" in lower or "plug" in lower:
        return "AC Outlet"

    if "ac" in lower and "type" in lower:
        return "AC Type 2"

    if "type2" in lower or "type 2" in lower:
        return "AC Type 2"

    if "ccs" in lower:
        return "DC CCS2"

    if "chademo" in lower:
        return "DC CHAdeMO"

    return text


def connector_family(connector_type: str) -> str:
    upper = clean_text(connector_type).upper()

    if upper.startswith("AC"):
        return "AC"

    if upper.startswith("DC") or "CCS" in upper or "CHADEMO" in upper:
        return "DC"

    return ""


def normalize_charger_type(connectors: List[Dict[str, Any]]) -> str:
    families = set()

    for connector in connectors:
        family = connector_family(connector.get("type", ""))
        if family:
            families.add(family)

    if not families:
        return ""

    if len(families) == 1:
        return next(iter(families))

    return "MIXED"


def normalize_status(
        station_status: Any = None,
        icon_url: Any = None,
        info_status: Any = None,
) -> str:
    text = clean_text(station_status).lower()
    icon = clean_text(icon_url).lower()

    if "available" in text or "available" in icon:
        return "available"

    if "charging" in text or "occupied" in text or "occupied" in icon:
        return "occupied"

    if "reserved" in text or "reserved" in icon:
        return "reserved"

    if "fault" in text or "faulted" in text or "fault" in icon:
        return "faulted"

    if "maintenance" in text or "maintenance" in icon:
        return "maintenance"

    if "offline" in text or "offline" in icon:
        return "offline"

    if "outofservice" in text or "outofservice" in icon:
        return "unavailable"

    if "unavailable" in text or "disabled" in icon:
        return "unavailable"

    if info_status is True:
        return "available"

    if info_status is False:
        return "unknown"

    return "unknown"


# ==============================
# 运营商判断
# ==============================

def infer_operator_from_party_id(party_id: Any) -> str:
    value = clean_text(party_id).upper()
    if not value:
        return ""
    return PARTY_ID_OPERATOR_MAP.get(value, value)


def infer_operator_from_name(name: Any) -> str:
    text = f" {clean_text(name).upper()} "
    if not text.strip():
        return ""

    for keyword, operator in NAME_OPERATOR_KEYWORDS:
        if keyword.upper() in text:
            return operator

    return ""


def choose_operator(station_info: Optional[Dict[str, Any]], marker: Dict[str, Any]) -> str:
    if station_info:
        party_operator = infer_operator_from_party_id(station_info.get("partyId"))
        if party_operator:
            return party_operator

        detail_name = pick_text(station_info.get("stationName"))
        name_operator = infer_operator_from_name(detail_name)
        if name_operator:
            return name_operator

    marker_name = get_marker_name(marker)
    marker_name_operator = infer_operator_from_name(marker_name)
    if marker_name_operator:
        return marker_name_operator

    source_groups = marker.get("_source_groups") or []

    if "VOLTA_CONNECT" in source_groups:
        return "PEA VOLTA"

    for group in ["EGAT", "EVOLT", "MEA", "OR"]:
        if group in source_groups:
            return SERVICE_GROUP_CONFIG[group]["label"]

    if "EV_ROAMING_ALL" in source_groups:
        return "EV Roaming"

    return "Unknown"


def choose_provider(station_info: Optional[Dict[str, Any]], marker: Dict[str, Any]) -> str:
    if station_info:
        party_id = clean_text(station_info.get("partyId"))
        if party_id:
            return party_id

    source_groups = marker.get("_source_groups") or []
    return ",".join(source_groups)


# ==============================
# 请求体
# ==============================

def base_map_payload(lat: str, lng: str) -> Dict[str, str]:
    """
    App 搜索页对应：
    - 功率：slow / normal / fast / super_fast 全开
    - 枪口：TYPE2 / CHAdeMO / CCS2 / PUPA 全开
    - 服务商：默认全关，由 service group 打开
    """
    return {
        "version": "4",
        "command": "getMapStationStatus",
        "lat": lat,
        "lng": lng,
        "radius": RADIUS,

        # 状态
        "filter[ready]": "true",
        "filter[charging]": "true",
        "filter[reserved]": "true",
        "filter[maintenance]": "true",
        "filter[fault]": "true",
        "filter[offline]": "true",
        "filter[outOfService]": "true",
        "filter[underConstruction]": "true",

        # 枪口类型。PUPA 是 AC Outlet，不是运营商。
        "filter[TYPE2]": "true",
        "filter[CHAdeMO]": "true",
        "filter[CCS2]": "true",
        "filter[PUPA]": "true",

        # 功率档位
        "filter[slow]": "true",
        "filter[normal]": "true",
        "filter[fast]": "true",
        "filter[super_fast]": "true",

        # 营业
        "filter[opening]": "true",

        # 服务商默认关闭
        "filter[EV_ROAMING]": "false",
        "filter[VOLTA_CONNECT]": "false",

        # Roaming 细分默认关闭
        "filter[EGAT]": "false",
        "filter[EVOLT]": "false",
        "filter[MEA]": "false",
        "filter[OR]": "false",
    }


def build_service_payload(lat: str, lng: str, service_group: str) -> Dict[str, str]:
    payload = base_map_payload(lat, lng)

    config = SERVICE_GROUP_CONFIG.get(service_group)
    if not config:
        raise ValueError(f"未知 service_group：{service_group}")

    payload.update(config["filters"])

    return payload


# ==============================
# HTTP Client
# ==============================

class PEAVoltaClient:
    def __init__(self) -> None:
        evsessionkey = clean_text(PEA_EVSESSIONKEY)
        userkey = clean_text(PEA_USERKEY)

        if not evsessionkey:
            raise RuntimeError("PEA_EVSESSIONKEY 为空，请在脚本顶部填写")

        self.session = requests.Session()

        headers = {
            "User-Agent": "Dart/3.4 (dart:io)",
            "Accept-Encoding": "gzip",
            "evsessionkey": evsessionkey,
            "Cookie": f"evSessionKey={evsessionkey}",
        }

        if userkey:
            headers["userkey"] = userkey

        self.session.headers.update(headers)

    def request_json(
            self,
            method: str,
            url: str,
            *,
            data: Optional[Dict[str, Any]] = None,
            request_name: str = "",
            delay_range: Tuple[float, float] = REQUEST_DELAY_RANGE,
            allow_fail: bool = False,
    ) -> Optional[Dict[str, Any]]:
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            sleep_random(delay_range, reason=f"{request_name or url} 请求前限速")

            try:
                if method.upper() == "GET":
                    response = self.session.get(url, timeout=TIMEOUT)
                elif method.upper() == "POST":
                    response = self.session.post(url, data=data, timeout=TIMEOUT)
                else:
                    raise ValueError(f"不支持的请求方法：{method}")

                response.raise_for_status()
                payload = response.json()

                if payload.get("status") != "success":
                    if allow_fail:
                        return payload
                    raise RuntimeError(f"业务失败：{payload}")

                return payload

            except Exception as exc:
                last_error = exc
                log(f"请求失败 [{request_name}] 第 {attempt}/{MAX_RETRIES} 次：{exc}")

                if attempt < MAX_RETRIES:
                    sleep_random(RETRY_BACKOFF_RANGE, reason="失败退避")

        if allow_fail:
            log(f"请求最终失败但允许跳过 [{request_name}]：{last_error}")
            return None

        raise RuntimeError(f"请求最终失败 [{request_name}]：{last_error}")

    def get_map_station_status(self, lat: str, lng: str, service_group: str) -> List[Dict[str, Any]]:
        payload = build_service_payload(lat, lng, service_group)

        data = self.request_json(
            "POST",
            f"{BASE_URL}/charger/",
            data=payload,
            request_name=f"地图列表 service={service_group}, lat={lat}, lng={lng}",
            delay_range=MAP_DELAY_RANGE,
        )

        if not data:
            return []

        items = data.get("data") or []

        if not isinstance(items, list):
            return []

        if DEBUG_FIRST_ITEM:
            log(f"service={service_group} 第一条字段：{list(items[0].keys()) if items else []}")
            if items:
                log(f"service={service_group} 第一条数据预览：{json.dumps(items[0], ensure_ascii=False)[:500]}")

        return items

    def get_station_info(self, station_id: str) -> Optional[Dict[str, Any]]:
        payload = {
            "version": "4",
            "command": "getStationInfo",
            "stationId": station_id,
        }

        data = self.request_json(
            "POST",
            f"{BASE_URL}/charger/",
            data=payload,
            request_name=f"站点详情 stationId={station_id}",
            allow_fail=True,
        )

        if not data or data.get("status") != "success":
            return None

        info = data.get("data") or {}
        return info if isinstance(info, dict) else None

    def get_connector_info(self, charger_number: str, connector_id: str) -> Optional[Dict[str, Any]]:
        if not charger_number or not connector_id:
            return None

        url = f"{BASE_URL}/v2/connector/{charger_number}/{connector_id}/info"

        data = self.request_json(
            "GET",
            url,
            request_name=f"枪口详情 {charger_number}/{connector_id}",
            delay_range=CONNECTOR_DELAY_RANGE,
            allow_fail=True,
        )

        if not data or data.get("status") != "success":
            return None

        info = data.get("data") or {}
        return info if isinstance(info, dict) else None


# ==============================
# 数据转换
# ==============================

def parse_connector_price(connector_info: Optional[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    if not connector_info:
        return None, None

    info = connector_info.get("info") or {}
    price = to_float(info.get("price"))

    if price is None:
        return None, None

    return price, price


def parse_connector_kw(
        station_connector: Dict[str, Any],
        connector_info: Optional[Dict[str, Any]],
) -> Optional[Any]:
    if connector_info:
        info = connector_info.get("info") or {}
        kw = to_number(info.get("kW"))
        if kw is not None:
            return kw

    return to_number(station_connector.get("kW"))


def build_target_from_station_info(
        station_info: Dict[str, Any],
        marker: Dict[str, Any],
        client: PEAVoltaClient,
) -> Dict[str, Any]:
    chargers_output: List[Dict[str, Any]] = []

    for charger in station_info.get("arChargerInfo") or []:
        charger_name = (
                pick_text(charger.get("location"))
                or clean_text(charger.get("number"))
                or clean_text(charger.get("chargerID"))
        )

        charger_number = clean_text(charger.get("number"))
        connectors_output: List[Dict[str, Any]] = []

        for connector in charger.get("connector") or []:
            connector_id = clean_text(connector.get("connectorID"))
            connector_info: Optional[Dict[str, Any]] = None

            if FETCH_CONNECTOR_INFO and charger_number and connector_id:
                connector_info = client.get_connector_info(charger_number, connector_id)

            connector_type = normalize_connector_type(connector.get("codeOrg"))
            kw = parse_connector_kw(connector, connector_info)
            price_day, price_night = parse_connector_price(connector_info)

            info_block = (connector_info or {}).get("info") or {}

            connectors_output.append({
                "position": connector_id,
                "type": connector_type,
                "kw": kw,
                "price_day": price_day,
                "price_night": price_night,
                "status": normalize_status(
                    station_status=connector.get("connectorStatusCodeOrg"),
                    icon_url=info_block.get("iconUrl"),
                    info_status=info_block.get("status"),
                ),
            })

        kw_values = [
            to_float(item.get("kw"))
            for item in connectors_output
            if item.get("kw") is not None
        ]

        charger_kw = None
        if kw_values:
            max_kw = max(kw_values)
            charger_kw = int(max_kw) if float(max_kw).is_integer() else max_kw

        chargers_output.append({
            "name": charger_name,
            "type": normalize_charger_type(connectors_output),
            "heads": len(connectors_output),
            "kw": charger_kw,
            "connectors": connectors_output,
        })

    station_id = clean_text(station_info.get("stationId")) or get_marker_station_id(marker)

    return {
        "operator": choose_operator(station_info, marker),
        "station_id": station_id,
        "provider": choose_provider(station_info, marker),
        "source_groups": marker.get("_source_groups") or [],
        "source_labels": marker.get("_source_labels") or [],
        "name": pick_text(station_info.get("stationName")) or get_marker_name(marker),
        "lat": to_float(station_info.get("lat")) or get_marker_lat(marker),
        "lon": to_float(station_info.get("lng")) or get_marker_lon(marker),
        "chargers": chargers_output,
        "address": pick_text(station_info.get("description")),
    }


def build_fallback_from_marker(marker: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "operator": choose_operator(None, marker),
        "station_id": get_marker_station_id(marker),
        "provider": choose_provider(None, marker),
        "source_groups": marker.get("_source_groups") or [],
        "source_labels": marker.get("_source_labels") or [],
        "name": get_marker_name(marker),
        "lat": get_marker_lat(marker),
        "lon": get_marker_lon(marker),
        "chargers": [],
        "address": "",
    }


# ==============================
# 主流程
# ==============================

def build_effective_service_groups() -> List[str]:
    groups = list(COLLECT_SERVICE_GROUPS)

    if ENABLE_ROAMING_SUB_FILTERS:
        for group in ["EGAT", "EVOLT", "MEA", "OR"]:
            if group not in groups:
                groups.append(group)

    return groups


def collect_markers(client: PEAVoltaClient) -> List[Dict[str, Any]]:
    centers = MAP_CENTERS if USE_MULTI_CENTERS else [MAP_CENTERS[0]]
    service_groups = build_effective_service_groups()

    by_id: Dict[str, Dict[str, Any]] = {}
    no_id_count = 0
    request_index = 0

    for service_group in service_groups:
        config = SERVICE_GROUP_CONFIG[service_group]
        label = config["label"]

        for lat, lng, center_name in centers:
            request_index += 1

            log(
                f"地图请求 {request_index}: service={service_group}({label}), "
                f"center={center_name}, radius={RADIUS}"
            )

            items = client.get_map_station_status(lat, lng, service_group)
            log(f"返回站点数：{len(items)}")

            for item in items:
                unique_id = get_marker_unique_id(item)

                if not unique_id:
                    no_id_count += 1
                    continue

                if unique_id not in by_id:
                    item["_unique_id"] = unique_id
                    item["_source_groups"] = [service_group]
                    item["_source_labels"] = [label]
                    by_id[unique_id] = item
                else:
                    exist = by_id[unique_id]
                    groups = exist.setdefault("_source_groups", [])
                    labels = exist.setdefault("_source_labels", [])

                    if service_group not in groups:
                        groups.append(service_group)

                    if label not in labels:
                        labels.append(label)

    markers = list(by_id.values())
    markers.sort(key=lambda item: clean_text(item.get("_unique_id")))

    if no_id_count:
        log(f"警告：有 {no_id_count} 条 marker 没有可用 ID/name/lat/lng，已跳过")

    if MAX_STATIONS and MAX_STATIONS > 0:
        markers = markers[:MAX_STATIONS]

    return markers


def summarize_by_operator(results: List[Dict[str, Any]]) -> Dict[str, int]:
    summary: Dict[str, int] = {}

    for item in results:
        operator = item.get("operator") or "Unknown"
        summary[operator] = summary.get(operator, 0) + 1

    return dict(sorted(summary.items(), key=lambda kv: (-kv[1], kv[0])))


def collect_all() -> List[Dict[str, Any]]:
    client = PEAVoltaClient()

    log("开始采集 PEA App 地图可见站点")

    markers = collect_markers(client)

    log(f"去重后 marker 数量：{len(markers)}")

    results: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for index, marker in enumerate(markers, start=1):
        station_id = get_marker_station_id(marker)
        marker_name = get_marker_name(marker)
        groups = marker.get("_source_groups") or []

        log(f"处理站点 {index}/{len(markers)}：station_id={station_id}, name={marker_name}, groups={groups}")

        try:
            station_info = None

            if station_id:
                station_info = client.get_station_info(station_id)

            if station_info:
                target = build_target_from_station_info(station_info, marker, client)
                results.append(target)

                charger_count = len(target.get("chargers") or [])
                connector_count = sum(
                    len(charger.get("connectors") or [])
                    for charger in target.get("chargers") or []
                )

                log(
                    f"完成：operator={target.get('operator')}, "
                    f"name={target.get('name')}, 桩 {charger_count} 个，枪口 {connector_count} 个"
                )

            else:
                message = "getStationInfo 无有效详情或没有 station_id"
                log(f"{marker_name} {message}")

                if OUTPUT_MARKER_FALLBACK_WHEN_DETAIL_FAILED:
                    results.append(build_fallback_from_marker(marker))

                failed.append({
                    "unique_id": marker.get("_unique_id"),
                    "stationId": station_id,
                    "stationName": marker_name,
                    "source_groups": groups,
                    "error": message,
                })

        except Exception as exc:
            log(f"站点失败：station_id={station_id}, name={marker_name}，原因：{exc}")

            if OUTPUT_MARKER_FALLBACK_WHEN_DETAIL_FAILED:
                results.append(build_fallback_from_marker(marker))

            failed.append({
                "unique_id": marker.get("_unique_id"),
                "stationId": station_id,
                "stationName": marker_name,
                "source_groups": groups,
                "error": str(exc),
            })

        sleep_random(STATION_DELAY_RANGE, reason="站点处理间隔")

    script_dir = Path(__file__).resolve().parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_path = script_dir / f"pea_fixed_stations_{timestamp}.json"
    raw_marker_path = script_dir / f"pea_fixed_raw_markers_{timestamp}.json"
    summary_path = script_dir / f"pea_fixed_summary_{timestamp}.json"
    failed_path = script_dir / f"pea_fixed_failed_{timestamp}.json"

    summary = summarize_by_operator(results)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    with raw_marker_path.open("w", encoding="utf-8") as f:
        json.dump(markers, f, ensure_ascii=False, indent=2)

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log(f"最终 JSON 已输出：{output_path}")
    log(f"原始 marker 已输出：{raw_marker_path}")
    log(f"运营商统计已输出：{summary_path}")
    log(f"输出站点数：{len(results)}")
    log(f"运营商统计：{summary}")

    if failed:
        with failed_path.open("w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)
        log(f"失败站点数：{len(failed)}，失败记录已输出：{failed_path}")
    else:
        log("失败站点数：0")

    return results


def main() -> None:
    try:
        collect_all()
        log("采集完成")
    except KeyboardInterrupt:
        log("用户中断")
        sys.exit(130)
    except Exception as exc:
        log(f"程序异常退出：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
