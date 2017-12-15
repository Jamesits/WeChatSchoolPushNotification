import hug
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy import parse_message
from wechatpy.replies import TextReply
from wechatpy import WeChatClient
from collections import defaultdict
from datetime import datetime
import re
import traceback
import requests

from config import *

wechat_client = WeChatClient(wechat_appid, wechat_appsecret)

# 假的数据库
table_class_userid = default_table_class_userid
table_deviceid_class = default_table_deviceid_class
table_authencated_teacher = default_table_authencated_teacher
queue_signed_out_classes = default_queue_signed_out_classes

# 禁用对 API endpoint 的缓存
@hug.directive()
def nocache(response=None, **kwargs):
    '''Returns passed in parameter multiplied by itself'''
    response \
    and response.set_header('Cache-Control', "no-cache, no-store, must-revalidate") \
    and response.set_header('Pragma', "no-cache") \
    and response.set_header('Expires', 0)

# 微信检查是否合法 API endpoint
@hug.get("/wechat_api", versions=1, output=hug.output_format.text)
def wechat_api_get(hug_nocache, signature, timestamp, nonce, **kwargs):
    
    try:
        print("kwargs", kwargs)
        check_signature(wechat_token, signature, timestamp, nonce)
        if "echostr" in kwargs:
            print("微信接口配置成功")
            return kwargs["echostr"]
        raise NotImplementedError("Unknown GET request")
    except InvalidSignatureException:
        print("Failed to check signature")


# 处理微信消息
@hug.post("/wechat_api", versions=1, output=hug.output_format.text)
def wechat_api_post(hug_nocache, body, signature, timestamp, nonce, **kwargs):
    try:
        print("kwargs", kwargs)
        check_signature(wechat_token, signature, timestamp, nonce)
        msg = parse_message(body.read())
        print("msg", msg)
        if msg.type == "event":
            print("Receive event", msg.event)
            return ""
        elif msg.type == "text":
            print("Received text", msg.content, "from", msg.source)
            if msg.content.startswith("我是"):
                # 处理用户注册到班级
                classname = re.findall(r'\d+', msg.content)[0]
                print("用户 {} 注册到班级 {}".format(msg.source, classname))
                if msg.source not in table_class_userid[classname]:
                    table_class_userid[classname].append(msg.source)
                print(table_class_userid)
                reply = TextReply(content="注册成功", message=msg)
                return reply.render()
            elif msg.content == "openid":
                # 测试用，返回用户的 openid
                ret = "openid={}\nsource={}".format(kwargs["openid"], msg.source)
                print(ret)
                return TextReply(content=ret, message=msg).render()
            elif msg.content == "ping":
                # 测试用
                return TextReply(content="pong", message=msg).render()
            # 其他情况无需处理
            return ""
        else:
            print("Unknown data")
            raise NotImplementedError("Unknown POST request")
    except InvalidSignatureException:
        print("Failed to check signature")

def wechat_push_signout_msg(userid, teachername, classname):
    wechat_client.message.send_template(userid, signout_template_id, {
                "first": {
                       "value": "您好，您的孩子已放学。",
                       "color": "#173177",
                },
                "keyword1": {
                       "value": classname,
                       "color": "#173177",
                },
                "keyword2": {
                       "value": teachername,
                       "color": "#173177",
                },
                "keyword3": {
                       "value": get_current_time(),
                       "color": "#173177",
                },
                "remark": {
                       "value": "请尽快接走您的孩子！",
                       "color": "#173177",
                },
            })

# 解析形如 A=1&B=2 的数据
def parse_device_msg(s):
    #print(s)
    #try:
    #    return dict(s)
    print('::: Payload: {}'.format(repr(s)))
    try:
        payload = s.read().decode('utf-8', 'replace')
    except Exception:
        if isinstance(s, dict):
            return s
        elif isinstance(s, bytes):
            payload = s.decode('utf-8', 'replace')
        elif isinstance(s, str):
            payload = s
        else:
            print(s)
            assert False
    return dict(item.split("=") for item in payload.split("&"))

# 获取当前时间
def get_current_time():
    return datetime.now().strftime('%H:%M')

# 教室端设备注册
@hug.post(versions=1)
def device_reg(hug_nocache, body):
    try:
        msg = parse_device_msg(body)
        print("设备 {}（{}）从网络 {} 注册成功".format(msg["chipid"], table_deviceid_class[msg["chipid"]], msg["wifi"]))
        return None
    except KeyError:
        print("设备认证失败", msg)

# 教室端签退动作
@hug.post(versions=1)
def signout(hug_nocache, body):
    try:
        msg = parse_device_msg(body)
        print("用户 {}（{}）从设备 {}（{}）宣布放学".format(msg["cardid"], table_authencated_teacher[msg["cardid"]], msg["chipid"], table_deviceid_class[msg["chipid"]]))
        if table_deviceid_class[msg["chipid"]] not in [item["class"] for item in queue_signed_out_classes]:
            queue_signed_out_classes.insert(0, {
                "class": table_deviceid_class[msg["chipid"]],
                "time": get_current_time(),
            })
        users = table_class_userid[table_deviceid_class[msg["chipid"]]]
        seq = 1
        for user in users:
            print("正在推送 {}/{}".format(seq, len(users)))
            seq += 1
            try:
                wechat_push_signout_msg(user, table_authencated_teacher[msg["cardid"]], table_deviceid_class[msg["chipid"]])
            except:
                traceback.print_exc()
        print("消息推送完成")
        return None
    except KeyError:
        print("设备或用户认证失败", msg)

# 网页端 API
@hug.get(versions=1, output=hug.output_format.pretty_json)
def signout_queue(hug_nocache):
    return {"queue": queue_signed_out_classes}

@hug.post(versions=1, output=hug.output_format.pretty_json)
def clear_signout_queue(hug_nocache):
    print("清除已放学班级队列")
    queue_signed_out_classes.clear()
    return {"result": "success"}

@hug.get(versions=1, output=hug.output_format.pretty_json)
def weather(location, unit="c"):
    result = requests.get("https://api.seniverse.com/v3/weather/now.json", params={
        'key': seniverse_secret,
        'location': location,
        'unit': unit,
    })
    print(result.text)
    return result.json()

# 静态文件
@hug.static('/')
def my_static_dirs():
    return ("../screen", )
