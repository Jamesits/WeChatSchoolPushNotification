import hug
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy import parse_message
from wechatpy.replies import TextReply
from wechatpy import WeChatClient
from collections import defaultdict
import re
import traceback

wechat_appid = "wx915bb615a9511f33"
wechat_appsecret = "7703e65a9b337f04b71337eb5c249313"
wechat_token = "gLzMqah8NX"

signout_template_id = "5hWcB-MjluEujdEaYdPtAWNuQhJ4yMsiaT8k9uc27p0"

wechat_client = WeChatClient(wechat_appid, wechat_appsecret)

# 假的数据库
table_class_userid = defaultdict(list, {
    "101": [
        "o4SkFj5YKie5tgvui1PPnQzHm6RA",
    ],
})

table_deviceid_class = {
    "49985F": "101",
    "1779A3": "201",
}

table_authencated_teacher = {
    "48858EB9": "王老师",
    "F01CF318": "张老师",
    "41023B1A": "赵老师",
    "9B8865D9": "钱老师",
    "EEE56BD9": "孙老师",
}

queue_signed_out_classes = []

# 微信检查是否合法 API endpoint
@hug.get("/wechat_api", versions=1, output=hug.output_format.text)
def wechat_api_get(signature, timestamp, nonce, **kwargs):
    
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
def wechat_api_post(body, signature, timestamp, nonce, **kwargs):
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

def wechat_push_signout_msg(userid, classname):
    wechat_client.message.send_template(userid, signout_template_id, {
                "class": {
                       "value": classname,
                       "color": "#173177",
                },
            })

# 解析形如 A=1&B=2 的数据
def parse_device_msg(s):
    return dict(item.split("=") for item in s.split("&"))

# 教室端设备注册
@hug.post(versions=1)
def device_reg(body):
    try:
        msg = parse_device_msg(body)
        print("设备 {}（{}）从网络 {} 注册成功".format(msg["chipid"], table_deviceid_class[msg["chipid"]], msg["wifi"]))
        return None
    except KeyError:
        print("设备认证失败", msg)

# 教室端签退动作
@hug.post(versions=1)
def signout(body):
    try:
        msg = parse_device_msg(body)
        print("用户 {}（{}）从设备 {}（{}）宣布放学".format(msg["cardid"], table_authencated_teacher[msg["cardid"]], msg["chipid"], table_deviceid_class[msg["chipid"]]))
        if table_deviceid_class[msg["chipid"]] not in queue_signed_out_classes:
            queue_signed_out_classes.insert(0, table_deviceid_class[msg["chipid"]])
        users = table_class_userid[table_deviceid_class[msg["chipid"]]]
        seq = 1
        for user in users:
            print("正在推送 {}/{}".format(seq, len(users)))
            seq += 1
            try:
                wechat_push_signout_msg(user, table_deviceid_class[msg["chipid"]])
            except:
                traceback.print_exc()
        print("消息推送完成")
        return None
    except KeyError:
        print("设备或用户认证失败", msg)

# 网页端 API
@hug.get(versions=1, output=hug.output_format.pretty_json)
def signout_queue():
    print("获取已放学班级队列")
    return {"queue": queue_signed_out_classes}

@hug.post(versions=1, output=hug.output_format.pretty_json)
def clear_signout_queue():
    print("清除已放学班级队列")
    queue_signed_out_classes.clear()
    return {"result": "success"}

# 静态文件
@hug.static('/')
def my_static_dirs():
    return ("../screen", )
