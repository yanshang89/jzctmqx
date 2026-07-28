import os
import sys
import json
import threading
import time
import re
import hashlib
import uuid
import socket
import urllib3
from datetime import datetime
from xml.etree import ElementTree
from flask import Flask, render_template, request, jsonify, send_file, Response

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ========== CORS 跨域支持（小程序需要）==========
@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


# 统一处理 OPTIONS 预检请求
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        from flask import make_response
        r = make_response()
        r.headers["Access-Control-Allow-Origin"] = "*"
        r.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return r


AES_KEY = b"16byteskey123456"
AES_IV = b"16bytesiv4567890"

AMAP_KEYS = [
    "2b4da1173625c8054cb1bc4e94b79cdf",
    "51d8d467c612eff85819651bf8ab1e33"
]

# ========== 微信公众号配置 ==========
# 在 mp.weixin.qq.com 后台「基本配置」中填入相同 Token
WECHAT_TOKEN = "jzctmqx2024"

SAVE_CONFIG_PATH = "config.json"
AUTH_SAVE_PATH = "auth.dat"
SAVE_DATA_PATH = "output"
SAVE_IMG_PATH = os.path.join(SAVE_DATA_PATH, "shop_img")
PROGRESS_PATH = "collect_progress.json"
os.makedirs(SAVE_DATA_PATH, exist_ok=True)
os.makedirs(SAVE_IMG_PATH, exist_ok=True)

INDUSTRY_KEYWORDS = [
    "餐饮", "餐厅", "火锅", "烧烤", "快餐", "小吃", "奶茶", "咖啡", "蛋糕店", "水果店",
    "酒店", "宾馆", "民宿", "旅馆", "招待所",
    "超市", "便利店", "商店", "小卖部",
    "美容", "美发", "理发", "美甲", "足浴", "按摩", "养生", "SPA",
    "药店", "诊所", "医院", "牙科", "体检",
    "银行", "ATM", "保险", "证券",
    "加油站", "汽修", "洗车", "停车场", "充电站",
    "教育", "培训", "学校", "幼儿园", "驾校", "托班",
    "健身房", "瑜伽", "游泳", "篮球", "羽毛球",
    "KTV", "网吧", "电影院", "酒吧", "棋牌",
    "房产", "中介", "装修", "建材", "家具",
    "快递", "物流", "快递点", "配送",
    "宠物", "花店", "书店", "文具店", "五金店",
    "服装", "鞋店", "箱包", "眼镜店", "钟表",
    "手机", "电脑", "数码", "家电", "维修",
]

CATEGORY_MAP = {
    "05": "餐饮服务", "06": "购物服务", "07": "生活服务",
    "08": "体育休闲", "09": "住宿服务", "10": "医疗保健",
    "11": "住宿服务", "12": "科教文化", "13": "交通设施",
    "14": "金融保险", "15": "公司企业", "16": "政府机构",
    "17": "公共设施",
}

# 全局状态
app_state = {
    "auth_pass": False,
    "auth_info": {},
    "collect_running": False,
    "collect_result": [],
    "healthy_keys": list(AMAP_KEYS),
    "amap_key_index": 0,
    "tel_seen": set(),
    "img_download_count": 0,
    "stat": {"current": 0, "history": 0, "skip_repeat": 0, "no_tel": 0, "hotline": 0},
    "logs": [],
    "config": {
        "city": "",
        "keyword": "",
        "max_page": "5",
        "delay": "0.8",
        "only_tel": False,
        "filter_hotline": False,
        "download_img": False,
        "use_proxy": False,
        "proxy_addr": "",
        "export_type": "excel"
    }
}


def get_machine_code():
    parts = []
    try:
        parts.append(str(uuid.getnode()))
    except Exception:
        pass
    try:
        parts.append(socket.gethostname())
    except Exception:
        pass
    try:
        import platform
        parts.append(platform.processor())
    except Exception:
        pass
    try:
        parts.append(platform.system() + platform.release())
    except Exception:
        pass
    if not parts:
        return f"ERR{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
    return hashlib.md5(''.join(parts).encode()).hexdigest().upper()


def verify_auth(auth_code: str):
    try:
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        raw_hex = bytes.fromhex(auth_code.strip())
        decode_bytes = unpad(cipher.decrypt(raw_hex), AES.block_size)
        auth_data = json.loads(decode_bytes.decode("utf8"))
        return True, auth_data
    except ValueError as e:
        return False, f"解密失败: {str(e)}"
    except json.JSONDecodeError as e:
        return False, f"授权数据解析失败: {str(e)}"
    except Exception as e:
        return False, str(e)


def clean_phone(phone):
    return re.sub(r'\D', '', phone.strip())


def standardize_phone(phone):
    p = clean_phone(phone)
    if not p:
        return ""
    if re.match(r'^1[3-9]\d{9}$', p):
        return f"{p[:3]}-{p[3:7]}-{p[7:]}"
    if re.match(r'^[48]00\d{7}$', p):
        return f"{p[:3]}-{p[3:6]}-{p[6:]}"
    if re.match(r'^0\d{9,11}$', p):
        return f"{p[:3]}-{p[3:]}"
    return phone.strip()


def is_hotline(phone):
    p = clean_phone(phone)
    if not p:
        return False
    if p.startswith("400") or p.startswith("800"):
        return True
    if p.startswith("0") and not p.startswith("01"):
        return True
    return False


def typecode_to_category(typecode):
    if not typecode:
        return ""
    tc = typecode.split(";")[0].strip()
    if len(tc) >= 2:
        return CATEGORY_MAP.get(tc[:2], typecode)
    return typecode


def download_shop_img(url, save_name):
    if not url or not url.startswith("http"):
        return ""
    save_file = os.path.join(SAVE_IMG_PATH, save_name)
    try:
        clean_url = url.split('?')[0] if '?' in url else url
        resp = requests.get(clean_url, timeout=15, verify=False)
        if resp.status_code == 200 and len(resp.content) > 1024:
            with open(save_file, "wb") as f:
                f.write(resp.content)
            return save_file
    except Exception:
        pass
    return ""


def add_log(text):
    ts = time.strftime('%H:%M:%S')
    app_state["logs"].append(f"{ts} {text}")
    if len(app_state["logs"]) > 200:
        app_state["logs"] = app_state["logs"][-200:]


def get_amap_key():
    if not app_state["healthy_keys"]:
        return None
    key = app_state["healthy_keys"][app_state["amap_key_index"] % len(app_state["healthy_keys"])]
    app_state["amap_key_index"] += 1
    return key


def disable_amap_key(key):
    if key in app_state["healthy_keys"]:
        app_state["healthy_keys"].remove(key)
        add_log(f"Key {key[:8]}... 已移出轮换池")


def request_amap_poi(keyword, city, page):
    url = "https://restapi.amap.com/v3/place/text"
    proxies = None
    cfg = app_state["config"]
    if cfg.get("use_proxy") and cfg.get("proxy_addr", "").strip():
        p = cfg["proxy_addr"].strip()
        proxies = {"http": p, "https": p}
    max_retry = len(app_state["healthy_keys"])
    for attempt in range(max_retry):
        key = get_amap_key()
        if not key:
            add_log("所有高德Key均已失效!")
            return []
        params = {
            "keywords": keyword, "city": city, "citylimit": "true",
            "offset": 25, "page": page, "key": key, "extensions": "all"
        }
        try:
            resp = requests.get(url, params=params, timeout=15, verify=False, proxies=proxies)
            data = resp.json()
            if data.get("status") == "1":
                return data.get("pois", [])
            info = data.get("info", "")
            if info in ("INVALID_USER_IP", "INVALID_USER_KEY",
                        "DAILY_QUERY_OVER_LIMIT", "USERKEY_PLAT_NOMATCH"):
                add_log(f"Key {key[:8]}... 报错: {info}")
                disable_amap_key(key)
                continue
            else:
                add_log(f"高德返回: {info}")
                return []
        except Exception as e:
            add_log(f"请求异常: {e}")
            return []
    return []


def collect_thread(city_list, keyword_str):
    keywords = [k.strip() for k in keyword_str.split(",") if k.strip()]
    if not keywords:
        keywords = [""]

    cfg = app_state["config"]
    only_tel = cfg.get("only_tel", False)
    filter_hotline = cfg.get("filter_hotline", False)
    download_img = cfg.get("download_img", False)
    use_proxy = cfg.get("use_proxy", False)
    proxy_addr = cfg.get("proxy_addr", "")
    delay = float(cfg.get("delay", "0.8")) if str(cfg.get("delay", "0.8")).replace('.', '').isdigit() else 0.8
    max_page = int(cfg.get("max_page", "5")) if str(cfg.get("max_page", "5")).isdigit() else 5

    add_log(f"采集启动, 城市{len(city_list)}个, 关键词{len(keywords)}个")

    for city in city_list:
        if not app_state["collect_running"]:
            break
        add_log(f"===== 城市：{city} =====")

        for kw in keywords:
            if not app_state["collect_running"]:
                break
            add_log(f"--- 关键词：{kw} ---")

            for page in range(1, max_page + 1):
                if not app_state["collect_running"]:
                    break
                time.sleep(delay)
                pois = request_amap_poi(kw, city, page)
                if not pois:
                    add_log(f"第{page}页无数据")
                    break
                add_log(f"第{page}页获取 {len(pois)} 条")

                for poi in pois:
                    if not app_state["collect_running"]:
                        break

                    shop_name = poi.get("name", "")
                    address = poi.get("address", "") or poi.get("location", "")
                    phone_raw = poi.get("tel", "") or ""
                    phone_raw = phone_raw.split(";")[0].strip() if phone_raw else ""

                    phone_std = standardize_phone(phone_raw)
                    phone_clean = clean_phone(phone_raw)

                    if filter_hotline and is_hotline(phone_raw):
                        app_state["stat"]["hotline"] += 1
                        continue
                    if only_tel and not phone_clean:
                        app_state["stat"]["no_tel"] += 1
                        continue
                    if phone_clean and phone_clean in app_state["tel_seen"]:
                        app_state["stat"]["skip_repeat"] += 1
                        continue
                    if phone_clean:
                        app_state["tel_seen"].add(phone_clean)

                    location = poi.get("location", "")
                    lng, lat = "", ""
                    if location and "," in location:
                        parts = location.split(",")
                        lng, lat = parts[0].strip(), parts[1].strip()

                    category = typecode_to_category(poi.get("typecode", ""))

                    img_path = ""
                    if download_img:
                        img_url = ""
                        photos = poi.get("photos", [])
                        if photos and isinstance(photos, list) and len(photos) > 0:
                            img_url = photos[0].get("url", "") or photos[0].get("src", "")
                        if not img_url:
                            img_url = poi.get("pic_url", "")
                        if not img_url:
                            img_url = poi.get("navi_poi_pic", "")

                        if img_url and img_url.startswith("http"):
                            fname = hashlib.md5(f"{shop_name}{time.time()}".encode()).hexdigest() + ".jpg"
                            img_path = download_shop_img(img_url, fname)
                            if img_path:
                                app_state["img_download_count"] += 1

                    idx = len(app_state["collect_result"]) + 1
                    rec = {
                        "idx": idx, "name": shop_name, "address": address,
                        "phone": phone_std, "lng": lng, "lat": lat,
                        "img_path": img_path, "category": category
                    }
                    app_state["collect_result"].append(rec)
                    app_state["stat"]["current"] += 1
                    app_state["stat"]["history"] += 1

    app_state["collect_running"] = False
    add_log(f"采集结束, 共采集 {app_state['stat']['current']} 条")


# ========== Flask 路由 ==========

@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/machine_code")
def api_machine_code():
    return jsonify({"machine_code": get_machine_code()})


@app.route("/api/verify_auth", methods=["POST"])
def api_verify_auth():
    data = request.get_json()
    code = data.get("auth_code", "").strip()
    if not code:
        return jsonify({"ok": False, "msg": "请输入激活码"})

    ok, res = verify_auth(code)
    if ok:
        app_state["auth_pass"] = True
        app_state["auth_info"] = res
        try:
            with open(AUTH_SAVE_PATH, "w", encoding="utf8") as f:
                f.write(code)
        except Exception:
            pass
        add_log("授权成功")
        return jsonify({"ok": True, "msg": "授权校验通过"})
    else:
        return jsonify({"ok": False, "msg": f"授权失败: {res}"})


@app.route("/api/check_auth")
def api_check_auth():
    if os.path.exists(AUTH_SAVE_PATH):
        try:
            with open(AUTH_SAVE_PATH, "r", encoding="utf8") as f:
                saved_code = f.read().strip()
            if saved_code:
                ok, res = verify_auth(saved_code)
                if ok:
                    app_state["auth_pass"] = True
                    app_state["auth_info"] = res
                    return jsonify({"ok": True, "msg": "授权已自动通过"})
        except Exception:
            pass
    return jsonify({"ok": False, "msg": "未授权"})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        data = request.get_json()
        app_state["config"].update(data)
        try:
            with open(SAVE_CONFIG_PATH, "w", encoding="utf8") as f:
                json.dump(app_state["config"], f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        add_log("配置已保存")
        return jsonify({"ok": True, "msg": "配置已保存"})
    else:
        if os.path.exists(SAVE_CONFIG_PATH):
            try:
                with open(SAVE_CONFIG_PATH, "r", encoding="utf8") as f:
                    cfg = json.load(f)
                app_state["config"].update(cfg)
            except Exception:
                pass
        return jsonify(app_state["config"])


@app.route("/api/keywords")
def api_keywords():
    q = request.args.get("q", "").lower().strip()
    if q:
        results = [kw for kw in INDUSTRY_KEYWORDS if q in kw.lower()]
    else:
        results = INDUSTRY_KEYWORDS
    return jsonify(results)


@app.route("/api/start_collect", methods=["POST"])
def api_start_collect():
    if not app_state["auth_pass"]:
        return jsonify({"ok": False, "msg": "请先完成授权校验！"})
    if app_state["collect_running"]:
        return jsonify({"ok": False, "msg": "采集正在运行"})

    cfg = app_state["config"]
    page = int(cfg.get("max_page", "5")) if str(cfg.get("max_page", "5")).isdigit() else 5
    if page < 1 or page > 25:
        return jsonify({"ok": False, "msg": "采集页数范围：1~25"})

    keyword = cfg.get("keyword", "").strip()
    if not keyword:
        return jsonify({"ok": False, "msg": "请填写行业关键词！"})

    city = cfg.get("city", "").strip()
    if not city:
        return jsonify({"ok": False, "msg": "请填写采集城市！"})

    app_state["collect_running"] = True
    app_state["img_download_count"] = 0

    threading.Thread(target=collect_thread,
                    args=([city], keyword), daemon=True).start()

    return jsonify({"ok": True, "msg": "采集已启动"})


@app.route("/api/stop_collect")
def api_stop_collect():
    app_state["collect_running"] = False
    add_log("已停止采集")
    return jsonify({"ok": True, "msg": "已停止采集"})


@app.route("/api/clear_data")
def api_clear_data():
    app_state["collect_result"].clear()
    app_state["tel_seen"].clear()
    app_state["stat"]["current"] = 0
    add_log("表格已清空")
    return jsonify({"ok": True, "msg": "数据已清空"})


@app.route("/api/data")
def api_data():
    return jsonify({
        "data": app_state["collect_result"],
        "stat": app_state["stat"],
        "running": app_state["collect_running"],
        "logs": app_state["logs"]
    })


@app.route("/api/export")
def api_export():
    if not app_state["collect_result"]:
        return jsonify({"ok": False, "msg": "无数据导出"})

    t = app_state["config"].get("export_type", "excel")
    ext = "xlsx" if t == "excel" else t

    try:
        data = {
            "序号": [str(r["idx"]) for r in app_state["collect_result"]],
            "商家名称": [r["name"] for r in app_state["collect_result"]],
            "详细地址": [r["address"] for r in app_state["collect_result"]],
            "联系电话": [r["phone"] for r in app_state["collect_result"]],
            "经度": [r["lng"] for r in app_state["collect_result"]],
            "纬度": [r["lat"] for r in app_state["collect_result"]],
            "门头照路径": [r["img_path"] for r in app_state["collect_result"]],
        }
        df = pd.DataFrame(data)

        save_path = os.path.join(SAVE_DATA_PATH,
                                f"商户数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")

        if t == "excel":
            df.to_excel(save_path, index=False)
        elif t == "csv":
            df.to_csv(save_path, index=False, encoding="utf_8_sig")
        else:
            df.to_csv(save_path, sep="\t", index=False)

        add_log(f"数据导出完成: {save_path}")
        # 小程序 downloadFile 需要正确的 Content-Disposition 才能识别文件类型
        resp = send_file(save_path, as_attachment=True)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Content-Disposition"] = f'attachment; filename="商户数据.{ext}"'
        return resp
    except Exception as e:
        return jsonify({"ok": False, "msg": f"导出失败: {str(e)}"})


# ========== 微信公众号接入 ==========
def wechat_check_signature(signature, timestamp, nonce):
    """校验微信服务器签名"""
    if not all([signature, timestamp, nonce]):
        return False
    tmp = sorted([WECHAT_TOKEN, timestamp, nonce])
    sha1 = hashlib.sha1("".join(tmp).encode("utf-8")).hexdigest()
    return sha1 == signature


def build_text_reply(from_user, to_user, content):
    """构造微信文本消息回复 XML"""
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{from_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{to_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    # GET: 微信服务器接入校验
    if request.method == "GET":
        sig = request.args.get("signature", "")
        ts = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")
        if wechat_check_signature(sig, ts, nonce):
            return echostr
        return "check sign fail", 403

    # POST: 接收用户消息
    sig = request.args.get("signature", "")
    ts = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")
    if not wechat_check_signature(sig, ts, nonce):
        return "sign fail", 403

    try:
        xml_data = request.data.decode("utf-8")
        root = ElementTree.fromstring(xml_data)
        to_user = root.findtext("ToUserName", "")
        from_user = root.findtext("FromUserName", "")
        msg_type = root.findtext("MsgType", "")
        content = (root.findtext("Content", "") or "").strip()

        base_url = request.host_url.rstrip("/")

        if msg_type == "text":
            # 用户发送机器码（32 位大写 hex）申请激活码
            if re.match(r'^[A-F0-9]{32}$', content):
                reply = (
                    "已收到您的机器码：\n"
                    f"{content}\n\n"
                    "请将上面这串机器码发给管理员获取激活码，"
                    "拿到激活码后在工具页面「授权」标签粘贴校验即可使用。\n\n"
                    f"工具页面：{base_url}/\n"
                    "如需复制机器码，请进入工具页面点「复制机器码」。"
                )
            elif content in ("采集", "开始", "使用", "工具", "网页", "h5", "H5", "链接"):
                reply = (
                    "欢迎使用「小飞拓客」商户采集工具！\n\n"
                    "【使用步骤】\n"
                    "1. 打开下方工具页面\n"
                    "2. 在「授权」标签复制您的机器码\n"
                    "3. 将机器码发给本公众号\n"
                    "4. 管理员会回复对应激活码\n"
                    "5. 在工具页面粘贴激活码校验后即可使用\n\n"
                    f"👉 工具页面：{base_url}/\n\n"
                    "采集到的数据支持 Excel / CSV / TXT 导出，"
                    "建议在微信内置浏览器中点击右上角「在浏览器打开」获得最佳体验。"
                )
            elif content in ("帮助", "help", "？", "?", "怎么用", "怎么使用"):
                reply = (
                    "【小飞拓客 使用帮助】\n\n"
                    "1. 关键词回复\n"
                    "   - 发送「采集/使用/工具」获取工具入口\n"
                    "   - 直接发送 32 位机器码申请激活\n"
                    "   - 发送「帮助」查看本说明\n\n"
                    "2. 操作流程\n"
                    "   - 打开工具页面 → 授权页复制机器码\n"
                    "   - 公众号回复机器码 → 等待管理员发放激活码\n"
                    "   - 输入激活码校验 → 配置城市/关键词 → 开始采集\n\n"
                    "3. 采集说明\n"
                    "   - 支持多城市、多关键词（英文逗号分隔）\n"
                    "   - 默认每页 25 条，最多 25 页\n"
                    "   - 可选只采有电话商户、过滤 400/座机、下载门头照\n"
                    "   - 支持 Excel/CSV/TXT 导出\n"
                )
            elif content in ("关于", "about"):
                reply = (
                    "【关于】\n"
                    "小飞拓客 - 商户数据采集工具\n"
                    "微信公众号版 · 保留授权码机制\n"
                    "微信：jzctmqx\n"
                )
            else:
                reply = (
                    "您好，我是「小飞拓客」公众号。\n\n"
                    "回复关键词获取服务：\n"
                    "· 发送「采集」或「使用」获取工具页面\n"
                    "· 发送「帮助」查看详细使用说明\n"
                    "· 发送「关于」查看工具介绍\n"
                    "· 直接发送 32 位机器码申请激活码\n\n"
                    f"工具页面：{base_url}/"
                )
        elif msg_type == "event":
            event = root.findtext("Event", "")
            if event == "subscribe":
                reply = (
                    "🎉 欢迎关注「小飞拓客」！\n\n"
                    "本公众号提供商户数据采集工具（按城市+关键词采集高德地图商户信息，"
                    "含名称、地址、电话、坐标、门头照）。\n\n"
                    "回复「使用」开始使用，或回复「帮助」查看详细说明。\n"
                    f"工具页面：{base_url}/"
                )
            elif event == "CLICK":
                key = root.findtext("EventKey", "")
                if key in ("use_tool", "start"):
                    reply = (
                        "【工具入口】\n"
                        f"{base_url}/\n\n"
                        "首次使用请在「授权」页复制机器码，"
                        "将机器码发给本公众号申请激活码。"
                    )
                elif key == "help":
                    reply = "已为您发送使用帮助，请回复「帮助」查看。"
                else:
                    reply = ""
            else:
                reply = ""
        else:
            reply = (
                "收到您的消息。回复「帮助」查看使用说明，"
                "回复「采集」获取工具页面。"
            )

        if not reply:
            return "success"
        return Response(
            build_text_reply(from_user, to_user, reply),
            content_type="application/xml; charset=utf-8"
        )
    except Exception as e:
        add_log(f"微信消息处理异常: {e}")
        return "success"


if __name__ == "__main__":
    # 自动检查授权
    if os.path.exists(AUTH_SAVE_PATH):
        try:
            with open(AUTH_SAVE_PATH, "r", encoding="utf8") as f:
                saved_code = f.read().strip()
            if saved_code:
                ok, res = verify_auth(saved_code)
                if ok:
                    app_state["auth_pass"] = True
                    app_state["auth_info"] = res
                    print("[系统] 自动授权成功")
        except Exception:
            pass

    # 加载配置
    if os.path.exists(SAVE_CONFIG_PATH):
        try:
            with open(SAVE_CONFIG_PATH, "r", encoding="utf8") as f:
                cfg = json.load(f)
            app_state["config"].update(cfg)
        except Exception:
            pass

    # 端口：Render 注入 PORT 环境变量，本地默认 5000
    port = int(os.environ.get("PORT", "5000"))

    print("=" * 50)
    print("商户采集工具 - Web 版")
    print("=" * 50)
    print(f"访问地址: http://127.0.0.1:{port}")
    print("=" * 50)

    app.run(host="0.0.0.0", port=port, debug=False)