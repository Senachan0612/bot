# QQ Bot

FengLiu大佬的pycqBot项目，稍微做了些自用修改  
[原项目 (移动至 Github Pages): https://github.com/FengLiuFeseliud/pycqBot/](https://github.com/FengLiuFeseliud/pycqBot/)

## 项目架构

```text
bin
    start 启动文件
    start_config.yml 启动配置
go-cqhttp
    *
    config.yml go-cqhttp配置
    go-cqhttp.exe go-cqhttp执行程序
plugin
    *
    plugin_config.yml 插件配置
pycqBot
    *
```

## 演示

### 项目搭建流程

1.在bin目录下创建start_config.yml配置文件

```yml
# 监听群号
groups:
  - 10001  # 群号01
  - 10002  # 群号02

# 启用的插件
plugins:
  - 'plugin.bilibili'
  - 'plugin.pixiv'
  - 'plugin.插件名'

# bot的自我称呼（bot的名字）
bot_name: 'アトリ'
```

2.在go-cqhttp目录下创建config.yml配置文件  
参考go-cqhttp帮助中心-[配置信息](https://docs.go-cqhttp.org/guide/config.html#%E9%85%8D%E7%BD%AE%E4%BF%A1%E6%81%AF)

3.在plugin目录下创建plugin_config.yml配置文件  
所有插件的配置放置在同一plugin_config.yml文件中，只需配置**步骤1**中启用的插件即可

&emsp;&emsp;bilibili插件配置

```yml
bilibili:
  # 直播间推送
  monitorLive:
    public: # 全局推送
      - 123456 # bid123456用户
    10001: # 10001群推送以下用户
      - 1234567 # bid1234567用户
    10002: # 10002群推送以下用户
      - 12345678 # bid12345678用户

  # 动态推送
  monitorDynamic:
    public: # 全局推送
      - 123456 # bid123456用户
    10001: # 10001群推送以下用户
      - 1234567 # bid1234567用户
    10002: # 10002群推送以下用户
      - 12345678 # bid12345678用户

  # 监听间隔(s) 每多少秒监听一次
  timeSleep: 30
```

&emsp;&emsp;chatgpt插件配置

```yml
chatgpt:
  # 请求链接
  url: 'https://api.openai.com/v1/chat/completions'
  # 模型
  model: 'gpt-3.5-turbo'
  # 密钥
  key: 'sk-fe...' # 根据自己的情况替换
  # 代理
  proxy: '127.0.0.1:1080' # 根据自己的情况替换
```

&emsp;&emsp;pixiv插件配置

```yml
pixiv:
  # 转发消息使用的 qq 号 (可以使用非登录用户的账号)
  forward_qq: 10001
  # 转发使用的名字
  forward_name: 'アトリ'
  # pixiv 用户 cookie
  cookie: '...' # 根据自己的情况替换
  # 浏览器请求头
  user_agent: '...' # 根据自己的情况替换
  # 代理 ip
  proxy: '127.0.0.1:1080' # 根据自己的情况替换
  # pid 最多返回多少图片
  max_pid_len: 20
  # 其它功能最多返回多少图片
  max_rlen: 10
  # 定时清理(秒)
  timeSleep: false # 感觉用不上 还是设为false吧
```

&emsp;&emsp;games插件配置

```yml
games:
  list: # 配置需要启用的游戏列表
    - '五子棋'
  canvas: # 画布，可以预设至多五个
    - 'C:\Users\....jpg' # 根据自己的情况替换
```