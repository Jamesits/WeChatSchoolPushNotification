from collections import defaultdict

wechat_appid = "wxe97b8b07afb3b197"
wechat_appsecret = "0e4d7cab4cc0dbe6708cccc641d0e4ba"
wechat_token = "gLzMqah8NX"
wechat_encodingaeskey = "BN2TYcvmPE9Kqe2NRdKwbJUz7daieS3KZefFnSjFKqL"

seniverse_secret = "2huleldkhf6rkbol"

# 添加 OPENTM204533457 班级通知 模板
signout_template_id = "vhbZQwNW2CsQ39mzE0iya1fQlGBfpP1Wgx-Z_-Lgz2w"

default_table_class_userid = defaultdict(list, {
    "101": [
        "oeom10dOZEnNJg8QUN6g-E3anfF0",
    ],
    "201": [
        "oeom10Ya8-7e51msFbSXuGr2Sh1E", # Mr. Tang
    ]
})

default_table_deviceid_class = {
    "49985F": "101",
    "1779A3": "201",
}

default_table_authencated_teacher = {
    "48858EB9": "王老师",
    "F01CF318": "张老师",
    "41023B1A": "赵老师",
    "9B8865D9": "钱老师",
    "EEE56BD9": "孙老师",
}

default_queue_signed_out_classes = [
]
