# cqCode

有绝大部分的 go-cqhttp cqCode 同名函数，大部分参数一致

因此你可以直接参考 go-cqhttp cqCode 文档来使用 cqCode

> [!note]
>
> go-cqhttp cqCode 文档地址
>
> [https://docs.go-cqhttp.org/cqcode](https://docs.go-cqhttp.org/cqcode)

## 内置处理函数

pycqBot 内置的函数可以帮助你简单的解析出 cqCode

也可以帮助你快速发送 cqCode

**解析 cqCode**

```python
from pycqBot.cqCode import strToCqCodeToDict

# 提取字符串中的所有 cqCode 字符串转换为字典列表
print(strToCqCodeToDict("[CQ:at,qq=xxxxxx] [CQ:image,file=testcqcode,type=1]"))
```

**设置 cqCode**

```python
# 引入 cqCode
from pycqBot import cqHttpApi
from pycqBot.cqCode import at, image
from pycqBot.data import *

cqapi = cqHttpApi()

def at_user(commandData, message: Message):
    # at
    message.reply(at(commandData[0]))

def show(commandData, message: Message):
    # image
    message.reply(image(
            "test.png",
            "https://img.sakuratools.top/bg.png@0x0x0x80"
        )
    )

bot = cqapi.create_bot(
    group_id_list=[
        123456 # 替换为你的QQ群号
    ],
)

bot.command(at_user, "at", {
    "help": [
        "#at - at 指定 qq 号"
    ]
})

bot.command(show, "show", {
    "help": [
        "#show - 显示我的网站背景"
    ]
})

bot.start()
# 成功启动可以用 #at+空格+qq号 来 at 人
# 也可以用 #show 显示一张图片
```

**`def node_list(message_list: list[str], name: str, uin: int) -> str:`**

设置可以被 `cqapi.send_group_forward_msg` 发送的转发消息

> `message_list` 发送消息列表
>
> `forward_name` 被转发的名称
>
> `forward_qq` 被转发的qq

**`def strToCqCodeToDict(message: str) -> list[dict[str, Union[str, dict[str, Any]]]]:`**

提取字符串中的所有 cqCode 字符串转换为字典列表

> **`message`** 当前字符串

返回一个包括一个或多个 cqCode 字典的列表

**`def get_cq_code(code_str: str) -> dict[str, Union[str, dict[str, Any]]]:`**

转换 cqCode 字符串为字典

> **`code`** cqCode 字符串

返回一个 cqCode 字典

**`def strToCqCode(message: str) -> list[str]:`**

提取字符串中的所有 cqCode 字符串

> **`message`** 当前字符串

返回一个包括一个或多个 cqCode 字符串的列表

**`def cqJsonStrToDict(cq_json_str: str) -> dict[str, Any]:`**

转换 cqCode 中的 json 字符串为字典

cqJsonStrToDict 会自动字符替换并解析 json 字符串

> **`cq_json_str`** cqCode 字典中的 json 字符串

> [!attention]
>
> cqCode 中的 json 字符串不进行字符替换无法正常解析

**`def DictTocqJsonStr(dict: dict[str, Any]) -> str:`**

转换字典为 cqCode 中的 json 字符串

DictTocqJsonStr 会转换字典为 json 字符串，并自动字符替换

> **`dict`** 字典数据

> [!attention]
>
> json 字符串不进行字符替换无法正常解析

**`def DictToCqCode(dict: dict) -> str:`**

转换字典为 cqCode json类型

DictToCqCode 会转换字典为 json 字符串并生成 cqCode

> **`dict`** 字典数据

**`def set_cq_code(code: dict[str, Any]) -> str:`**

转换 pycqBot 的 cqCode 字典为 cqCode 字符串

> **`code`** pycqBot 转换的出 cqCode 字典 (如 strToCqCodeToDict)
