"""
utils — 通用工具模块

与具体 App 解耦，供所有 scraper 复用。包含三类功能：
  1. 设备连接管理（uiautomator2 断线重连）
  2. UI 操作原语（dump / click / 坐标计算）
  3. HTTPS SSL 上下文
  4. 数据持久化（原子写入 JSON）
"""

import xml.etree.ElementTree as ET
import re
import time
import json
import os
from functools import lru_cache
from http.client import RemoteDisconnected


# ── 设备连接管理 ───────────────────────────────────────────────

def ensure_connected(d):
    """
    检测 ATX agent 连接是否正常，断线时自动重启 uiautomator2 服务。

    采用固定间隔重试，最多 3 次，每次等待 4 秒。
    适用于长时间采集过程中设备偶发断线的场景。

    :param d: uiautomator2 设备对象
    :return: True = 连接正常；False = 重试后仍失败
    """
    for attempt in range(3):
        try:
            d.info  # 轻量级探测，不触发实际 UI 操作
            return True
        except Exception:
            print(f"  !! u2 连接断开，重连中（{attempt + 1}/3）...")
            try:
                d.reset_uiautomator()
            except Exception:
                pass
            time.sleep(4)
    print("  !! 重连失败，请检查设备连接")
    return False


# ── UI 操作原语 ────────────────────────────────────────────────

def dump(d):
    """
    获取当前屏幕的完整 UI 层级树，解析为 ElementTree 根节点。

    uiautomator2 在网络不稳定时可能抛出 RemoteDisconnected，
    遇到该异常时自动重连并重试一次。

    :param d: uiautomator2 设备对象
    :return: xml.etree.ElementTree.Element 根节点
    """
    for _ in range(2):
        try:
            return ET.fromstring(d.dump_hierarchy())
        except RemoteDisconnected:
            ensure_connected(d)
    return ET.fromstring(d.dump_hierarchy())


def center(bounds_str):
    """
    从 UI 节点的 bounds 属性字符串中提取中心坐标。

    bounds 格式示例：[0,500][1080,800]
    中心坐标 = ((x1+x2)//2, (y1+y2)//2)

    :param bounds_str: 节点 bounds 属性字符串
    :return: (cx, cy) 整数坐标元组；解析失败返回 None
    """
    m = re.findall(r"\d+", bounds_str)
    if len(m) == 4:
        return (int(m[0]) + int(m[2])) // 2, (int(m[1]) + int(m[3])) // 2
    return None


def click_node(d, node):
    """
    点击 UI 节点的中心坐标。

    先从 bounds 属性计算中心点，再调用 d.click()。
    遇到 RemoteDisconnected 时自动重连后重试一次。

    :param d:    uiautomator2 设备对象
    :param node: xml.etree.ElementTree.Element UI 节点
    :return: True = 点击成功；False = 坐标无效或两次尝试均失败
    """
    pt = center(node.attrib.get("bounds", ""))
    if not pt:
        return False
    for _ in range(2):
        try:
            d.click(*pt)
            return True
        except RemoteDisconnected:
            ensure_connected(d)
    return False


# ── HTTPS ────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _ssl_context():
    """
    创建携带 certifi CA bundle 的 SSL 上下文，用于 HTTPS 请求。

    macOS 默认不信任系统根证书，必须通过 certifi 显式提供。
    使用 lru_cache 保证进程内只创建一次，避免重复 I/O。
    """
    import ssl, certifi
    return ssl.create_default_context(cafile=certifi.where())


# ── 数据持久化 ─────────────────────────────────────────────────

def save_results(data, output_file):
    """
    将采集结果原子写入 JSON 文件。

    先写临时文件（output_file + ".tmp"），再用 os.replace() 原子替换，
    防止写入途中断电或 Ctrl+C 导致 JSON 文件损坏或清零。

    :param data:        要写入的 Python 对象（可被 json.dump 序列化）
    :param output_file: 目标文件路径
    """
    tmp = output_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, output_file)
