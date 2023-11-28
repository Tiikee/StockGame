# client

## 安装

```
sh ./utility/install-oatpp-modules.sh
mkdir build && cd build
cmake ..
make
./websocket-server-exe
```

## 使用 
**相关说明：**

**股票数据**：本数据抽取真实市场中 29 支股票数据构建数据池。

**推送频率**：交易所会每 1 秒推送一笔市场行情数据，行情数据中主要包括以下数据：

  1. 十档价量
  
  2. 最近 20s 每秒的成交量。

**交易时长**：模拟真实交易所交易规则，每次测试（含最终测试）独立，每次测试会连续交易若干天，真实交易所每天交易时长为四小时，真实测试中会等比例压缩。

**评价指标**：主要有以下指标，最终指标以 Score 为主。
PNL:
Sharpe：
Score:

**交易限制**：

**工具使用**：

**BotsDemoClass**:

你可以使用我们提供的工具，完善相关类函数可即可。

**公用参数说明**：

username&password: 用户名和密码，我们通过邮件发送给各位。 

start_time: 下一场比赛开始的时间，格式为时间戳格式，可以采用 UTIL_SPACE 的工具转化为标准格式。

running_days：下一次比赛运行的天数。

running_time: 下一场比赛每天运行的时间。

**基础函数说明**:

1. login&init: 你需要在比赛开始前运行程序，并执行 login 函数和 init 函数，在 init 函数中用于你当场比赛的初始化。

2. bod: 在每天比赛开始的时候会调用这个函数，你可以用于每天交易的初始化。

3. work:  在交易所时间内，每 1 秒会调用一次，共调用 14400 次。每次调用你可进行查询并处理行情，下单，撤单等操作，具体函数接口见表。

4. eod：在每天比赛结束的时候会调用这个函数，你可以用于每天交易结束时执行一些操作。

5. final：在每天比赛结束的时候会调用这个函数，你可以在比赛结束后自己做一些处理工作，以供分析。

**可调用函数说明**：

1. Login/GetGameInfo/Order/Cancel/GetTrade/GetLimitOrderBook

**用户接口**

你也可以通过我们提供的用户接口，自行实现客户端。

Login

GetGameInfo

Order

Cancel

GetTrade

GetLimitOrderBook
