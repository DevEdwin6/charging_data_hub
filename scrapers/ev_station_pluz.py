"""
scrapers/ev_station_pluz.py — EV Station PluZ 采集器

目标 App：EV Station PluZ（com.pttor.evstationpluz）
泰国 PTT 旗下充电站 App，共约 1352 个站点。

采集流程：
  Map 页 → 点 ≡ 进全屏站点列表 → 找未处理站点
  → 点击站点 → 预览卡 → View more → 详情页
  → _read_charger_units()     按充电桩分组读取枪口数据
  → read_detail_info()        状态 / 更新时间 / 备注
  → read_more_information()   完整地址 + 营业时间
  → get_location_coords()     Google Maps 坐标
  → db.save_station()         事务写入 MySQL
"""

import re
import time
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from http.client import RemoteDisconnected

import db
from utils import (
    dump, click_node, center,
    _ssl_context,
    ensure_connected,
)


class EVStationPluZScraper:
    """
    EV Station PluZ 充电站数据采集器。

    外部调用方式：
        scraper = EVStationPluZScraper(d)
        scraper.collect(results, processed, max_stations, run_id)
    """

    PLATFORM_CODE = "ev_station_pluz"
    APP_PKG       = "com.pttor.evstationpluz"

    # 站点状态词，用于过滤非站点节点和识别详情页状态角标
    STATUS_WORDS = {"Available", "Occupied", "Closed", "Unavailable", "Full"}

    # 白天时段：09:00（含）~ 22:00（不含），其余为夜间
    DAY_HOURS = (9, 22)

    def __init__(self, d):
        """
        :param d: uiautomator2 设备对象，由 run.py 创建并传入
        """
        self.d = d
        self._last_google_url = None  # _get_coords_via_google_maps() 成功时写入

    @staticmethod
    def get_time_period(dt):
        """
        根据平台规则判断采集时段。
        EV Station PluZ：09:00-22:00 为白天，其余为夜间。

        :param dt: datetime 对象
        :return: 'day' 或 'night'
        """
        return "day" if EVStationPluZScraper.DAY_HOURS[0] <= dt.hour < EVStationPluZScraper.DAY_HOURS[1] else "night"

    # ══════════════════════════════════════════════════════════
    # App 节点过滤
    # ══════════════════════════════════════════════════════════

    def _app_nodes(self, root):
        """
        从 UI 树中筛选出属于本 App 的节点。
        通过 package 属性过滤，防止误操作系统弹窗或其他 App 的节点。

        :param root: dump() 返回的 ElementTree 根节点
        :return: 属于 APP_PKG 的节点列表
        """
        return [n for n in root.iter("node")
                if n.attrib.get("package") == self.APP_PKG]

    # ══════════════════════════════════════════════════════════
    # App 存活检测 & 恢复
    # ══════════════════════════════════════════════════════════

    def ensure_app_running(self):
        """
        检测 App 是否仍在前台，若已被系统回收则重新启动。
        采集过程中 App 可能因内存压力被杀后台，
        在每轮循环开始和关键步骤后调用。
        """
        current = self.d.app_current()
        if current.get("package") == self.APP_PKG:
            return
        print(f"  !! App 已关闭（当前：{current.get('package')}），正在重启...")
        self.d.app_start(self.APP_PKG)
        time.sleep(5)
        self.ensure_map_page()

    def force_restart_app(self):
        """
        强制停止并重启 App，用于 App 卡死或白屏等无法正常导航的情况。
        """
        print("  !! 强制重启 App...")
        self.d.app_stop(self.APP_PKG)
        time.sleep(2)
        self.d.app_start(self.APP_PKG)
        time.sleep(6)
        self.ensure_map_page()

    # ══════════════════════════════════════════════════════════
    # 弹窗 & 预览卡
    # ══════════════════════════════════════════════════════════

    def dismiss_alert(self):
        """
        关闭网络错误、无法继续等系统/App 提示框。
        识别常见确认按钮文本（Confirm / OK / Close / Got it）并点击。

        :return: True = 成功关闭；False = 未发现弹窗
        """
        root = dump(self.d)
        for node in root.iter("node"):
            if node.attrib.get("text", "").strip() in (
                    "Confirm", "OK", "Close", "Got it"):
                if click_node(self.d, node):
                    time.sleep(1)
                    return True
        return False

    def close_preview_card(self):
        """
        点击地图预览卡右上角的关闭按钮（字体图标 \\uea37）。
        每轮循环结束时调用，确保回到纯 Map 页面。

        :return: True = 成功关闭；False = 预览卡不存在或点击失败
        """
        root = dump(self.d)
        for node in root.iter("node"):
            if (node.attrib.get("package") == self.APP_PKG
                    and "" in node.attrib.get("text", "")):
                if click_node(self.d, node):
                    time.sleep(1)
                    return True
        return False

    def preview_card_open(self):
        """
        检测地图预览卡是否当前可见。
        通过查找关闭按钮图标（\\uea37）来判断。

        :return: True = 预览卡可见；False = 不可见
        """
        root = dump(self.d)
        return any(
            "" in n.attrib.get("text", "")
            for n in root.iter("node")
            if n.attrib.get("package") == self.APP_PKG
        )

    # ══════════════════════════════════════════════════════════
    # 页面导航
    # ══════════════════════════════════════════════════════════

    def ensure_map_page(self):
        """
        确保当前处于 Map 页（地图可见、无全屏列表覆盖）。
        最多尝试 6 次，每次等待 1.5 秒。

        :return: True = 已在 Map 页；False = 6 次后仍失败
        """
        for _ in range(6):
            self.dismiss_alert()
            xml = self.d.dump_hierarchy()
            if "Station list" in xml:
                if "Total" in xml and "Google" not in xml:
                    self.d.press("back")
                    time.sleep(1.5)
                    continue
                self.close_preview_card()
                return True
            root = ET.fromstring(xml)
            map_btn = next(
                (n for n in root.iter("node")
                 if n.attrib.get("content-desc") == "Map"
                 and n.attrib.get("clickable") == "true"),
                None,
            )
            if map_btn:
                click_node(self.d, map_btn)
                time.sleep(2)
            else:
                self.d.press("back")
                time.sleep(1.5)
        return "Station list" in self.d.dump_hierarchy()

    def open_full_list(self):
        """
        点击 Map 页右侧 ≡ 图标（content-desc 含 \\ue9d9）进入全屏列表页。

        :return: True = 成功进入；False = 未找到图标或点击无效
        """
        xml = self.d.dump_hierarchy()
        root = ET.fromstring(xml)
        if self.is_on_list_page(xml):
            return True
        for node in self._app_nodes(root):
            if (node.attrib.get("clickable") == "true"
                    and "" in node.attrib.get("content-desc", "")):
                click_node(self.d, node)
                time.sleep(2)
                return self.is_on_list_page()
        return False

    def is_on_list_page(self, xml=None):
        """
        判断当前是否处于全屏站点列表页。
        同时满足含 'Total'、'Station list' 且无 'Google' 时为列表页。

        :param xml: 可选已有 UI XML；None 时实时抓取
        :return: True = 全屏列表页；False = 否
        """
        if xml is None:
            xml = self.d.dump_hierarchy()
        return "Total" in xml and "Station list" in xml and "Google" not in xml

    # ══════════════════════════════════════════════════════════
    # 全屏列表页：读取 & 滚动
    # ══════════════════════════════════════════════════════════

    def read_list_page(self):
        """
        解析全屏列表页当前可见的站点条目。
        每行 content-desc 格式：名称, 地址片段..., Open XX | ≈ Y km, 状态

        :return: list of dict，含 name/address/hours/distance/status
        """
        root = dump(self.d)
        stations, seen = [], set()
        for node in self._app_nodes(root):
            if node.attrib.get("clickable") != "true":
                continue
            desc = node.attrib.get("content-desc", "").strip()
            if not desc or desc in seen:
                continue
            if not re.search(r"\d+\.\d+ km", desc):
                continue
            seen.add(desc)
            parts = [p.strip() for p in desc.split(",")]
            name = parts[0]
            if name in self.STATUS_WORDS:
                continue
            addr_parts, hours_part, status = [], "", ""
            for i, p in enumerate(parts[1:], 1):
                if re.search(r"Open|Close", p):
                    hours_part = p
                    for s in parts[i + 1:]:
                        s = s.strip()
                        if s and all(ord(c) < 0xE000 or ord(c) > 0xF8FF for c in s):
                            status = s
                            break
                    break
                addr_parts.append(p)
            address = ", ".join(addr_parts)
            hours = distance = ""
            if "|" in hours_part:
                h, dist = hours_part.split("|", 1)
                hours, distance = h.strip(), dist.strip()
            else:
                hours = hours_part
            stations.append({
                "name": name, "address": address,
                "hours": hours, "distance": distance, "status": status,
            })
        return stations

    def scroll_list_page_down(self):
        """
        全屏列表页向下滚动一屏（y=1800 → y=700，避开顶部搜索栏）。
        遇到断线自动重连后重试。
        """
        for _ in range(2):
            try:
                self.d.swipe(540, 1800, 540, 700, duration=0.5)
                time.sleep(1.5)
                return
            except RemoteDisconnected:
                ensure_connected(self.d)

    def _fast_scroll_down(self):
        """快速滚动，用于跳过已知已处理区域，不等待列表稳定。"""
        for _ in range(2):
            try:
                self.d.swipe(540, 1800, 540, 700, duration=0.3)
                time.sleep(0.4)
                return
            except RemoteDisconnected:
                ensure_connected(self.d)

    def click_station_in_list(self, name):
        """
        在全屏列表页中找到指定名称的站点行并点击。
        用名称 + 距离信息双重匹配，防止误点同名异地站点。

        :param name: 目标站点名称
        :return: True = 点击成功；False = 未找到或失败
        """
        root = dump(self.d)
        for node in self._app_nodes(root):
            if node.attrib.get("clickable") != "true":
                continue
            desc = node.attrib.get("content-desc", "")
            if name in desc and re.search(r"\d+\.\d+ km", desc):
                return click_node(self.d, node)
        return False

    # ══════════════════════════════════════════════════════════
    # 详情页：充电桩 & 枪口读取（核心改造）
    # ══════════════════════════════════════════════════════════

    def _parse_connector_card(self, desc):
        """
        解析枪口卡片的 content-desc 字符串。
        标准格式：类型, 状态, 接口名, 功率|价格
        示例：'DC, Available, CCS COMBO 2, Max 40 kW|8.00 ฿/kWh'

        同时检测 content-desc 中是否含有位置名（含泰文字符或 -[A-Z] 结尾），
        若有则从 parts 中提取，避免二次查找。

        :param desc: 枪口 content-desc 字符串
        :return: dict 或 None（格式不符时）
        """
        parts = [p.strip() for p in desc.split(",")]
        if len(parts) < 4:
            return None

        # 从 parts 中提取位置名（优先从 content-desc 获取）
        position = ""
        clean_parts = []
        for p in parts:
            is_position = (
                (re.search(r"[฀-๿]", p) and len(p) <= 12)  # 含泰文且短
                or re.search(r"-[A-Z]$", p)                           # 以 -A/-B 结尾
            )
            if is_position and not position:
                position = p
            else:
                clean_parts.append(p)

        active_parts = clean_parts if position else parts

        if len(active_parts) < 3:
            return None

        power = price = ""
        tariff_idx = next(
            (i for i, p in enumerate(active_parts)
             if re.search(r"\bkW\b|฿\s*/\s*kWh", p, re.IGNORECASE)),
            None,
        )
        if tariff_idx is None:
            return None

        pp = active_parts[tariff_idx]
        if "|" in pp:
            pw, pr = pp.split("|", 1)
            power, price = pw.strip(), pr.strip()
        else:
            power = pp

        connector_name = " ".join(
            p for p in active_parts[2:tariff_idx]
            if p and not re.fullmatch(r"Book", p, re.IGNORECASE)
        ).strip()
        if not connector_name:
            connector_name = active_parts[2]

        return {
            "charger_type":   active_parts[0],              # DC / AC
            "status":         active_parts[1],              # Available / Occupied
            "connector_type": f"{active_parts[0]} {connector_name}",  # DC CCS COMBO 2
            "power":          power,
            "price":          price,
            "position":       position,                     # ซ้าย-A；可能为空，由调用方补全
        }

    def _find_position_in_bounds(self, root, card_y1, card_y2):
        """
        在 UI 树中查找位于枪口卡片 y 范围内的位置标签文本。

        位置标签特征：
          - 包含泰文字符（ซ้าย-A、ขวา-B、กลาง-A 等）
          - 长度 ≤ 12 个字符
          - 不含数字（排除功率/价格文本）
          - 不在 STATUS_WORDS 中

        :param root:    ElementTree 根节点
        :param card_y1: 枪口卡片 bounds 上边 y 坐标
        :param card_y2: 枪口卡片 bounds 下边 y 坐标
        :return: 位置标签字符串；未找到返回空字符串
        """
        for node in self._app_nodes(root):
            text = node.attrib.get("text", "").strip()
            if not text or len(text) > 12:
                continue
            if text in self.STATUS_WORDS:
                continue
            if re.search(r"\d", text):   # 含数字的是功率/价格，跳过
                continue
            if not re.search(r"[฀-๿]", text):  # 必须含泰文
                continue
            bounds = re.findall(r"\d+", node.attrib.get("bounds", ""))
            if len(bounds) != 4:
                continue
            ny1, ny2 = int(bounds[1]), int(bounds[3])
            # 文本节点的 y 范围须包含在卡片 y 范围内
            if ny1 >= card_y1 and ny2 <= card_y2:
                return text
        return ""

    def _read_charger_units(self):
        """
        滚动详情页，按充电桩分组收集所有枪口数据。

        页面布局（从上到下，重复若干组）：
          TS (133A Max Current)    ← 充电桩名称（text 节点）
          Charger ID : 240311      ← 充电桩 ID（text 节点）
            [枪口卡片] DC CCS COMBO 2 / ซ้าย-A / 40kW|8.00฿ / Available
            [枪口卡片] DC CCS COMBO 2 / ขวา-B  / 40kW|8.00฿ / Available
          IO (32A Max Current)     ← 下一个充电桩
          Charger ID : 2043
            [枪口卡片] AC Type 2 / กลาง-A / 7.4kW|9.00฿ / Occupied

        状态机：
          遇到"Charger ID"文本 → 切换 current_unit_id
          遇到含 ฿/kWh 的 content-desc → 枪口归入当前充电桩
          连续 3 次滚动无新枪口 → 停止

        :return: list of dict，格式：
                 [{"id": "240311", "name": "TS...", "connectors": [...]}]
        """
        units_dict  = {}   # unit_id → unit data dict
        unit_order  = []   # 保持充电桩出现顺序
        seen_cards  = set()
        stall       = 0
        current_uid = None
        current_uname = ""

        while stall < 3:
            prev_count = sum(len(u["connectors"]) for u in units_dict.values())
            root = dump(self.d)

            # 收集所有相关节点，按 y 中心坐标排序
            events = []
            for node in self._app_nodes(root):
                bounds = re.findall(r"\d+", node.attrib.get("bounds", ""))
                if len(bounds) != 4:
                    continue
                x1, y1, x2, y2 = map(int, bounds)
                y_mid = (y1 + y2) // 2

                text = node.attrib.get("text", "").strip()
                desc = node.attrib.get("content-desc", "").strip()

                if "฿/kWh" in desc:
                    events.append((y_mid, "card", desc, node, y1, y2))
                elif text:
                    events.append((y_mid, "text", text, node, y1, y2))

            events.sort(key=lambda e: e[0])

            for y_mid, kind, content, node, y1, y2 in events:
                if kind == "text":
                    # 充电桩名称行：含 "Max Current" 或符合大写字母+括号格式
                    if "Max Current" in content or re.match(r"^[A-Z]{1,3}\s*\(", content):
                        current_uname = content
                    # 充电桩 ID 行：开头为 "Charger ID"
                    elif re.match(r"^Charger ID", content, re.IGNORECASE):
                        uid = content.split(":")[-1].strip() if ":" in content else content
                        if uid and uid not in units_dict:
                            units_dict[uid] = {
                                "id": uid,
                                "name": current_uname,
                                "connectors": [],
                            }
                            unit_order.append(uid)
                        if uid:
                            current_uid = uid

                elif kind == "card" and current_uid:
                    card_key = f"{current_uid}::{content}"
                    if card_key in seen_cards:
                        continue
                    seen_cards.add(card_key)

                    connector = self._parse_connector_card(content)
                    if not connector:
                        continue

                    # content-desc 中未能提取位置名时，从卡片 y 范围内的文本节点查找
                    if not connector["position"]:
                        connector["position"] = self._find_position_in_bounds(root, y1, y2)

                    # 仍未找到则用序号兜底，确保 NOT NULL 字段不为空
                    if not connector["position"]:
                        idx = len(units_dict[current_uid]["connectors"]) + 1
                        connector["position"] = f"{connector['charger_type']}-{idx}"

                    units_dict[current_uid]["connectors"].append(connector)

            new_count = sum(len(u["connectors"]) for u in units_dict.values())
            stall = 0 if new_count > prev_count else stall + 1
            if stall < 3:
                self.d.swipe(540, 1800, 540, 900, duration=0.4)
                time.sleep(1)

        return [units_dict[uid] for uid in unit_order]

    def read_detail_info(self):
        """
        从详情页顶部可见区域读取站点元数据。
        按 y 坐标顺序扫描，提取：
          - overall_status : 顶部状态角标
          - last_update    : 最后更新时间
          - remarks        : 底部备注

        充电桩/枪口信息已由 _read_charger_units() 处理，此处不再读取。

        :return: dict，含上述三个字段
        """
        root = dump(self.d)
        items = []
        for n in self._app_nodes(root):
            t = n.attrib.get("text", "").strip()
            if not t:
                continue
            m = re.findall(r"\d+", n.attrib.get("bounds", ""))
            if len(m) == 4:
                items.append((int(m[1]), t))
        items.sort()

        info = {"overall_status": "", "last_update": "", "remarks": ""}
        for y, t in items:
            if t in self.STATUS_WORDS and y < 700:
                if not info["overall_status"]:
                    info["overall_status"] = t
            elif t.startswith("Last update"):
                info["last_update"] = t
            elif t.startswith("Remarks:"):
                info["remarks"] = t[len("Remarks:"):].strip()
        return info

    def read_more_information(self):
        """
        点击详情页的 'More information >' 按钮，读取完整地址和每日营业时间，
        然后按返回键回到详情页。

        完整地址通过泰国道路关键词（Road / Soi / Bangkok 等）识别；
        每日营业时间通过「星期名称行 → 紧跟的时间行」配对提取。

        :return: dict {"full_address": str, "hours_by_day": {day: hours}}；
                 未找到按钮时返回空 dict
        """
        root = dump(self.d)
        btn = next(
            (n for n in self._app_nodes(root)
             if "More information" in n.attrib.get("text", "")
             or "More information" in n.attrib.get("content-desc", "")),
            None,
        )
        if btn is None:
            return {}

        click_node(self.d, btn)
        time.sleep(2)

        root2 = dump(self.d)
        items, seen = [], set()
        for n in self._app_nodes(root2):
            m = re.findall(r"\d+", n.attrib.get("bounds", ""))
            if len(m) != 4:
                continue
            y = int(m[1])
            for attr in ("text", "content-desc"):
                t = re.sub(r"\s+", " ", n.attrib.get(attr, "")).strip()
                if not t or (y, t) in seen:
                    continue
                seen.add((y, t))
                items.append((y, t))
        items.sort()
        texts = [t for _, t in items]

        ADDR_KW = ("Road", "Rd", "Street", "St.", "Soi", "Bang", "Khlong",
                   "Bangkok", "Moo", "Thanon", "Phahon", "Sukhumvit",
                   "Alley", "Lane", "Avenue", "Ave", "Highway", "Hwy",
                   "Tambon", "Amphoe", "District", "Province", "Mueang")
        ADDR_LABELS = {"Address", "Location", "ที่อยู่", "ตำแหน่ง"}
        DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"}

        full_address = ""
        hours_by_day = {}
        day_buf = ""

        def is_hours_text(text):
            return bool(re.search(r"\d{1,2}:\d{2}|Open|Close|Closed|24\s*hours", text, re.I))

        def is_address_candidate(text):
            if not text or text in DAYS or text in ADDR_LABELS or is_hours_text(text):
                return False
            if len(text) < 15:
                return False
            has_addr_kw = any(k in text for k in ADDR_KW)
            has_thai = bool(re.search(r"[\u0E00-\u0E7F]", text))
            has_digit = bool(re.search(r"\d", text))
            return has_addr_kw or (has_thai and has_digit)

        for i, t in enumerate(texts):
            if not full_address and ":" in t:
                label, value = [p.strip() for p in t.split(":", 1)]
                if label in ADDR_LABELS and is_address_candidate(value):
                    full_address = value
                    continue

            if not full_address and t in ADDR_LABELS:
                for candidate in texts[i + 1:]:
                    if is_address_candidate(candidate):
                        full_address = candidate
                        break

            if not full_address and is_address_candidate(t):
                full_address = t

            if t in DAYS:
                day_buf = t
            elif day_buf and t:
                hours_by_day[day_buf] = t
                day_buf = ""

        self.d.press("back")
        time.sleep(1.5)
        return {"full_address": full_address, "hours_by_day": hours_by_day}

    # ══════════════════════════════════════════════════════════
    # 坐标获取
    # ══════════════════════════════════════════════════════════

    def _get_coords_via_google_maps(self):
        """
        终极兜底：通过 Google Maps 分享链接提取坐标。
        成功时同步将短链写入 self._last_google_url，供 collect() 存入 DB。

        流程：
          1. 点详情页左下角位置按钮（x1<300, y1>2000）
          2. 等待 Google Maps 打开（adb dumpsys 确认）
          3. 点分享按钮（兼容多语言）
          4. 从分享弹窗读取 maps.app.goo.gl 短链
          5. 展开短链，解析 !3d<lat>!4d<lng> 或 @lat,lng
          6. 返回两次回到详情页

        :return: (lat, lng) 浮点元组；任意步骤失败返回 None
        """
        import urllib.request as _urlreq

        self._last_google_url = None

        root = dump(self.d)
        maps_package = "com.google.android.apps.maps"
        nav_descs = {
            "Home", "Map", "Scan", "History", "Profile",
            "Check in", "Update", "More information >",
            "Show all", "Available connectors",
        }
        candidates = []
        for node in self._app_nodes(root):
            if node.attrib.get("clickable") != "true":
                continue
            if node.attrib.get("content-desc", "") in nav_descs:
                continue
            m = re.findall(r"\d+", node.attrib.get("bounds", ""))
            if len(m) != 4:
                continue
            x1, y1, x2, y2 = map(int, m)
            if x1 < 300 and y1 > 2000:
                candidates.append((y1, node))
        if not candidates:
            print("  !! 未找到位置按钮（Google Maps 兜底跳过）")
            return None
        candidates.sort(key=lambda t: -t[0])
        click_node(self.d, candidates[0][1])
        time.sleep(3)

        try:
            r = subprocess.run(
                ["adb", "-s", self.d.serial, "shell",
                 "dumpsys", "activity", "activities"],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=5,
            )
            if maps_package not in r.stdout:
                print("  !! Google Maps 未打开")
                self.d.press("back")
                time.sleep(1.5)
                return None
        except Exception:
            pass

        share_kw = ("分享", "Share", "share", "แชร์", "Partager", "Compartir")
        maps_root = ET.fromstring(self.d.dump_hierarchy())
        share_btn = next(
            (n for n in maps_root.iter("node")
             if n.attrib.get("package") == maps_package
             and n.attrib.get("clickable") == "true"
             and any(k in n.attrib.get("content-desc", "")
                     or k in n.attrib.get("text", "") for k in share_kw)),
            None,
        )
        if share_btn is None:
            print("  !! Maps 中未找到分享按钮")
            self.d.press("back")
            time.sleep(2)
            self.ensure_app_running()
            return None

        click_node(self.d, share_btn)
        time.sleep(2)

        share_root = ET.fromstring(self.d.dump_hierarchy())
        maps_url = None
        for node in share_root.iter("node"):
            val = (node.attrib.get("text", "")
                   or node.attrib.get("content-desc", ""))
            if "maps.app.goo.gl" in val or "google.com/maps" in val:
                maps_url = val.strip()
                break

        self.d.press("back")
        time.sleep(1)
        self.d.press("back")
        time.sleep(2.5)
        self.ensure_app_running()

        if maps_url is None:
            print("  !! 分享弹窗中未找到 Maps URL")
            return None

        # 展开短链，解析坐标
        try:
            req = _urlreq.Request(maps_url, headers={"User-Agent": "Mozilla/5.0"})
            resp = _urlreq.urlopen(req, timeout=10, context=_ssl_context())
            final_url = resp.geturl()
        except Exception as e:
            print(f"  !! 展开 URL 失败: {e}")
            return None

        m = re.search(r"!3d([\-\d\.]+)!4d([\-\d\.]+)", final_url)
        if m:
            self._last_google_url = maps_url
            return float(m.group(1)), float(m.group(2))
        m = re.search(r"@([\-\d\.]+),([\-\d\.]+)", final_url)
        if m:
            self._last_google_url = maps_url
            return float(m.group(1)), float(m.group(2))

        print(f"  !! URL 中未找到坐标: {final_url[:120]}")
        return None

    def get_location_coords(self, station_name, station_address="", full_address=""):
        """
        通过 Google Maps 分享链接获取站点坐标。

        :return: (lat, lng) 浮点元组；失败返回 None
        """
        coords = self._get_coords_via_google_maps()
        if coords:
            print(f"  → 坐标[GMaps]: {coords[0]}, {coords[1]}")
        return coords

    # ══════════════════════════════════════════════════════════
    # 采集主循环
    # ══════════════════════════════════════════════════════════

    def collect(self, results, processed, max_stations, run_id):
        """
        驱动完整的站点采集循环，支持断点续采。

        每站采集完成后调用 db.save_station() 写入 MySQL（事务）。
        DB 写入失败时跳过该站（不加入 processed），下次批次重试。

        :param results:      当前会话采集结果（内存列表，用于结束后打印汇总）
        :param processed:    已处理 key 集合，由 run.py 从 DB 预加载
        :param max_stations: 采集总量上限；None = 全部
        :param run_id:       当前采集批次 ID
        :return:             True = 正常完成（可标记批次 completed）；
                             False = 中途因错误退出（批次保持 running，下次续采）
        """
        def reached_max():
            return max_stations is not None and len(results) >= max_stations

        # 记录上次找到目标时的滚动计数，下次从附近继续（避免 O(n²) 滚动）
        resume_from = 0
        # 跟踪当前时段，跨时段时重新加载 processed
        active_period = self.get_time_period(datetime.now())

        while not reached_max():

            # 检测时段切换（如采集跨越 09:00 或 22:00）
            now_period = self.get_time_period(datetime.now())
            if now_period != active_period:
                print(f"\n[时段切换] {active_period} → {now_period}，重新加载已处理站点...")
                fresh = db.get_processed_stations(self.PLATFORM_CODE, run_id, now_period)
                processed.clear()
                processed.update(fresh)
                active_period = now_period
                resume_from = 0  # 从头重新扫描
                print(f"[时段切换] 当前时段已完成 {len(processed)} 站，其余将补采 {now_period} 价格\n")

            self.ensure_app_running()

            if not self.ensure_map_page():
                self.force_restart_app()
                if not self.ensure_map_page():
                    print("无法回到 Map 页，停止")
                    return False

            if not self.open_full_list():
                print("  !! 无法打开全屏列表页，尝试重启 App...")
                self.force_restart_app()
                if not self.open_full_list():
                    print("无法打开全屏列表页（重启后仍失败），停止")
                    return False

            # 快速跳过已知已处理区域（回退 3 格防边界遗漏）
            fast_to = max(0, resume_from - 3)
            for _ in range(fast_to):
                self._fast_scroll_down()

            # 从 fast_to 继续向下扫描，找第一个未处理站点
            target = None
            scrolls = fast_to
            max_scroll = max(len(processed) + 100, 1500)

            while scrolls <= max_scroll:
                for s in self.read_list_page():
                    if s["name"] + s["address"] not in processed:
                        target = s
                        break
                if target:
                    resume_from = scrolls
                    break
                scrolls += 1
                self.scroll_list_page_down()

            if target is None:
                if fast_to > 0:
                    # 部分扫描未找到，列表可能已重排；重置后从头全量扫描
                    print("部分扫描未找到未处理站点，从头全量扫描...")
                    resume_from = 0
                    continue
                print("没有更多未处理站点，采集完成")
                return True

            name = target["name"]
            key  = name + target["address"]

            if key in processed:
                print(f"  >> 已有记录，跳过：{name}")
                processed.add(key)
                continue

            idx   = len(results) + 1
            label = f"{idx}/{max_stations}" if max_stations is not None else str(idx)
            print(f"[{label}] {name}")
            station_start = time.time()

            # 点击站点，等待地图预览卡弹出
            if not self.click_station_in_list(name):
                print("  !! 点击失败，跳过")
                processed.add(key)
                continue
            time.sleep(2)
            self.ensure_app_running()
            self.dismiss_alert()

            if not self.preview_card_open():
                time.sleep(2)
                self.ensure_app_running()
                self.dismiss_alert()
                if not self.preview_card_open():
                    print("  !! 预览卡未出现，跳过")
                    self.d.press("back")
                    time.sleep(2)
                    self.dismiss_alert()
                    processed.add(key)
                    continue

            # 进入详情页
            if not self.click_view_more():
                time.sleep(1)
                self.dismiss_alert()
                if not self.click_view_more():
                    print("  !! View more 未找到，跳过")
                    self.close_preview_card()
                    processed.add(key)
                    continue
            time.sleep(3)
            self.ensure_app_running()
            self.dismiss_alert()

            # 按充电桩分组读取所有枪口
            charger_units = self._read_charger_units()
            target["charger_units"] = charger_units
            target["charger_count"] = sum(len(u["connectors"]) for u in charger_units)
            print(f"  → {len(charger_units)} 个充电桩  "
                  f"{target['charger_count']} 个枪口  ({label})")

            # 详情页头部（状态 / 更新时间 / 备注）
            detail = self.read_detail_info()
            target["overall_status"] = detail.get("overall_status", "")
            target["last_update"]    = detail.get("last_update", "")
            target["remarks"]        = detail.get("remarks", "")

            # More information 页面（完整地址 + 每日营业时间）
            more = self.read_more_information()
            target["full_address"]  = more.get("full_address", "")
            target["hours_by_day"]  = more.get("hours_by_day", {})
            if target["full_address"]:
                print(f"  → 地址: {target['full_address']}")

            # 坐标（打开 Google Maps 获取）—— 模拟采集时暂时禁用
            self._last_google_url = None
            # coords = self.get_location_coords(
            #     name,
            #     target.get("address", ""),
            #     target["full_address"],
            # )
            # target["lat"], target["lng"] = coords if coords else (None, None)
            # target["google_url"] = self._last_google_url
            target["lat"], target["lng"] = None, None
            target["google_url"] = None

            elapsed = time.time() - station_start
            target["elapsed_sec"]    = round(elapsed, 1)
            target["platform_code"]  = self.PLATFORM_CODE

            # 写入 MySQL（事务）
            collected_at = datetime.now()
            time_period  = self.get_time_period(collected_at)
            try:
                db.save_station(run_id, target, time_period, collected_at)
            except Exception as e:
                print(f"  !! DB 保存失败（{e}），跳过，下次重试")
                # 不加入 processed，下次批次会重试
                self.d.press("back")
                time.sleep(2)
                self.ensure_app_running()
                self.dismiss_alert()
                self.close_preview_card()
                time.sleep(1)
                continue

            results.append(target)
            processed.add(key)
            self._print_station(target, label, time_period, elapsed)

            # 返回 Map 页，准备下一轮
            self.d.press("back")
            time.sleep(2)
            self.ensure_app_running()
            self.dismiss_alert()
            self.close_preview_card()
            time.sleep(1)

        # while 循环因 reached_max() 退出
        return True

    # ══════════════════════════════════════════════════════════
    # 详情页辅助
    # ══════════════════════════════════════════════════════════

    def click_view_more(self):
        """
        点击预览卡中的 'View more' 按钮，进入站点详情页。

        特殊处理：
          - y 坐标取按钮上 1/4 处，避开底部导航栏遮挡
          - x 坐标避开 Scan 按钮区域（x 438–642），防止误触扫码

        :return: True = 找到并点击；False = 未找到
        """
        root = dump(self.d)
        nav_top = 9999
        for node in root.iter("node"):
            if node.attrib.get("content-desc", "") in (
                    "Home", "Map", "Scan", "History", "Profile"):
                m = re.findall(r"\d+", node.attrib.get("bounds", ""))
                if len(m) == 4:
                    nav_top = min(nav_top, int(m[1]))

        SCAN_X1, SCAN_X2 = 438, 642
        for node in self._app_nodes(root):
            text = node.attrib.get("text", "")
            desc = node.attrib.get("content-desc", "")
            if "View more" not in text and "View more" not in desc:
                continue
            m = re.findall(r"\d+", node.attrib.get("bounds", ""))
            if len(m) != 4:
                continue
            x1, y1, x2, y2 = map(int, m)
            cy = min(y1 + (y2 - y1) // 4, nav_top - 20)
            cy = max(cy, y1 + 5)
            cx = (x1 + x2) // 2
            if SCAN_X1 <= cx <= SCAN_X2:
                cx = SCAN_X2 + 60
            self.d.click(cx, cy)
            return True
        return False

    @staticmethod
    def _print_station(s, label, time_period, elapsed):
        """
        采集完成后立即打印单个站点的完整信息。
        在 collect() 中每站成功写入 DB 后调用。
        """
        period_tag = "🌞白天" if time_period == "day" else "🌙夜间"
        print(f"\n  ✓ [{label}] {period_tag}  用时 {elapsed:.1f}s")
        print(f"  {'─' * 52}")
        print(f"  站点    : {s['name']}")
        print(f"  状态    : {s.get('overall_status') or s.get('status', '')}")
        print(f"  更新    : {s.get('last_update', '')}")

        if s.get("hours"):
            print(f"  营业    : {s['hours']}")
        hbd = s.get("hours_by_day", {})
        if hbd:
            for day, hrs in hbd.items():
                print(f"            {day}: {hrs}")

        print(f"  地址    : {s.get('address', '')}")
        if s.get("full_address"):
            print(f"  详细    : {s['full_address']}")

        lat, lng = s.get("lat"), s.get("lng")
        if lat is not None:
            print(f"  坐标    : {lat}, {lng}")
        if s.get("google_url"):
            print(f"  GMaps   : {s['google_url']}")
        if s.get("remarks"):
            print(f"  备注    : {s['remarks']}")

        units = s.get("charger_units", [])
        print(f"  充电桩  : {len(units)} 桩 / {s.get('charger_count', 0)} 枪口")
        for cu in units:
            print(f"  ┌ {cu['name']}  ID:{cu['id']}")
            for j, c in enumerate(cu.get("connectors", []), 1):
                print(f"  │  ({j}) [{c['status']:10}] {c['connector_type']}"
                      f"  {c.get('position', ''):8}  {c['power']}  {c['price']}")
