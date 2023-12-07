# -*- coding: utf-8 -*-
import inline
import requests
import socket
import json
import time
import logging
import colorlog
import random

# 修改了日志输出方式，使得颜色对5个级别日志分级
logger = colorlog.getLogger(__name__)
console_handler = colorlog.StreamHandler()
logger.addHandler(console_handler)
logger.setLevel(colorlog.DEBUG)
log_format = '%(log_color)s%(asctime)s %(levelname)s: %(message)s'
console_format = colorlog.ColoredFormatter(log_format)
console_handler.setFormatter(console_format)

# (当前时间 - 起始时间) - 交易天数 * 每天运行时间 = 开始交易时间戳，开始交易时间戳 * 时间比率 = 平台开始交易的模拟时间。
# 其中 时间比率 time_ratio = 24h/25min。 所以 25分钟 就表示了一天 24小时 的交易日
def ConvertToSimTime_us(start_time, time_ratio, day, running_time):
    return (time.time() - start_time - (day - 1) * running_time) * time_ratio

# LocalTime: 每秒，共有14400s=4hour
# last price: 最终成交价
# bid price: 买家报价
# ask price: 卖家报价
# bid priceA: 买家最低报价
# ask priceA: 卖家最高报价
# volume: 成交量

class BotsClass:
    def __init__(self, username, password):
        self.username = username
        self.password = password
    def login(self):
        pass
    def init(self):
        pass
    def bod(self):
        pass
    def work(self):
        pass
    def eod(self):
        pass
    def final(self):
        pass

class BotsDemoClass(BotsClass):
    # 初始化 账号、密码
    def __init__(self, username, password):
        super().__init__(username, password)
        self.api = InterfaceClass("https://trading.competition.ubiquant.com")
    # 发送账号密码，登录平台
    def login(self):
        response = self.api.sendLogin(self.username, self.password)
        if response["status"] == "Success":
            self.token_ub = response["token_ub"]
            logger.info("Login Success: {}".format(self.token_ub))
        else:
            logger.info("Login Error: ", response["status"])
    # 获取股票
    def GetInstruments(self):
        response = self.api.sendGetInstrumentInfo(self.token_ub)
        if response["status"] == "Success":
            self.stockNumber = response["instrument_number"]  # 股票总数
            self.instruments = []  # 股票名称列表

            # 遍历所有股票信息
            for instrument in response["instruments"]:
                instrumentName = instrument["instrument_name"]
                self.instruments.append(instrumentName)  # 股票名称
            logger.info("Get Instruments: {}".format(self.instruments))

    # 初始化所有股票初始价格、当前我对所有股票的持仓
    def stocksInit(self):
        self.stocksIncome = {}  # 所有股票当前盈利状况。map[股票名称， 盈利(正或负)]。没有购买的盈利为0
        self.stocksBuy = {}     # 我当前手上持股情况。map[股票名称, map[购入价格，数量]]
        self.stocksLOB = {}   # 所有股票的历史LOB。map[股票名称， map[LOB参数, [历史数据]]]。忽略localtime字段
        for instrument in self.instruments:
            self.stocksIncome[instrument] = 0
            self.stocksBuy[instrument] = {}
            self.stocksLOB[instrument] = {
                "limit_up_price": [],
                "limit_down_price": [],
                "bidprice": [],
                "askprice": [],
                "bidvolume": [],
                "askvolume": [],
                "last_price": [],
                "trade_volume": [],
                "trade_value": []
            }

    # 初始化：获取 交易日信息 和 股票信息
    def init(self):
        response = self.api.sendGetGameInfo(self.token_ub)
        if response["status"] == "Success":
            self.start_time = response["next_game_start_time"]
            self.running_days = response["next_game_running_days"]
            self.running_time = response["next_game_running_time"]
            self.time_ratio = response["next_game_time_ratio"]
        self.GetInstruments()
        self.stocksInit()
        self.tradeList = []  # 股票成交历史列表
        self.userStocksInfo = {}  # 用户股票信息历史列表，{交易日：当天交易结束时的股票信息列表}。用于每个交易日结束时统计
        self.day = 0
    # 每个交易日开始前，交易策略的初始化
    def bod(self):
        logger.info("### Trade begin! Day: {}, running_days: {}".format(self.day, self.running_days))  # 今天日期、截止日
    # 交易策略的实现，可进行：查询、处理行情、下单、撤单等操作 (demo是随机买入某支股票的一手)
    def work(self):
        preTradeList = []  # 记录上一次的股票成交列表
        # 获得上一次所有股票的买卖情况、获得所有股票本轮的LOB 价格行情
        for instrument in self.instruments:
            # 获取该股票的成交列表
            getTrade = self.api.sendGetTrade(self.token_ub, instrument)
            preTradeList.append(getTrade["trade_list"])
            # 存储该股票的LOB
            lobResponse = self.api.sendGetLimitOrderBook(self.token_ub, instrument)
            for key, value in lobResponse["lob"].items():
                if key == 'localtime': continue  # 跳过 localtime 字段
                self.stocksLOB[instrument][key].append(value)
            logger.debug("### instrument: {}, lob: {}".format(instrument, lobResponse["lob"]))  # 打印该股票LOB

        self.tradeList.append(preTradeList)                             # 存储上一次股票成交列表
        logger.info("### Get preTradeList: {}".format(preTradeList))    # 打印上一次的股票成交列表

        # 随机买三次
        for i in range(3):
            # 可用资金不足时，直接退出循环。此时无法购买任何股票
            userinfoResponse = self.api.sendGetUserInfo(self.token_ub)
            if userinfoResponse["status"] == "Success":
                fund = userinfoResponse["remain_funds"]
                if fund < 500:
                    logger.debug("# fund not enough: {}".format(fund))
                    break  # 此时手上可用资金不足500块，无法购买任何股票
            # 随机买 todo 如果股票剩余仓不足100，就不买了。因为只会按错单来算
            buyID = random.randint(0, len(self.instruments) - 1)
            buyLOB = self.api.sendGetLimitOrderBook(self.token_ub, self.instruments[buyID])
            if buyLOB["status"] == "Success":
                # 以 AskPrice1 的卖家报价买入
                askprice_1 = float(buyLOB["lob"]["askprice"][0])
                t = ConvertToSimTime_us(self.start_time, self.time_ratio, self.day, self.running_time)
                response = self.api.sendOrder(self.token_ub, self.instruments[buyID], t, "buy", askprice_1, 100)
        # 获得当前手上持股数量
        # # 随机卖
        # sellID = random.randint(0, len(self.instruments) - 1)
        # sellLOB = self.api.sendGetLimitOrderBook(self.token_ub, self.instruments[sellID])
        # if sellLOB["status"] == "Success":
        #     # 以 BidPrice1 的买家报价卖出
        #     bidprice_1 = float(sellLOB["lob"]["bidprice"][0])
        #     # bidvolume_1 = sellLOB["lob"]["bidvolume"][0]
        #     t = ConvertToSimTime_us(self.start_time, self.time_ratio, self.day, self.running_time)
        #     response = self.api.sendOrder(self.token_ub, self.instruments[sellID], t, "sell", bidprice_1, 1000)

    # 每个交易日结束时会调用该函数，可用于每天交易结束时执行一些操作
    def eod(self):
        # 获取当前用户数据
        response = self.api.sendGetUserInfo(self.token_ub)
        # 获得当天的股票信息列表
        self.userStocksInfo[self.day] = response["rows"]
        logger.info("### Day end! Day: {}, running_days: {}, Get userStocksInfo: {}"
                    .format(self.day, self.running_days, self.userStocksInfo))

    # 在所有交易日结束后会调用，可用于赛后处理一些工作和分析
    def final(self):
        # 获取当前用户数据
        response = self.api.sendGetUserInfo(self.token_ub)
        ls = [response["pnl"], response["sharpe"], response["orders"], response["error_orders"],
              response["order_value"], response["trade_value"], response["commision"], response["total_position"],
              response["remain_funds"]]
        logger.info("### Trade End! Get userInfo: {}".format(ls))  # 打印最终交易信息

class InterfaceClass:
    # 获取登录域名
    def __init__(self, domain_name):
        self.domain_name = domain_name
        self.session = requests.Session()
    # 发送登录请求
    def sendLogin(self, username, password):
        url = self.domain_name + "/api/Login"
        data = {
            "user": username,
            "password": password
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 获取比赛信息的 url
    def sendGetGameInfo(self, token_ub):
        url = self.domain_name + "/api/TradeAPI/GetGAmeInfo"

    # 发送下单请求：
    # token_ub:             令牌
    # instrument:           股票名称
    # localtime:            当前时间
    # direction:            下单方向，“buy”或“sell”
    # price:                下单价格
    # volume:               下单数量
    # response[”index”]:    获取这次下单的索引，需使用该索引来进行撤单.
    def sendOrder(self, token_ub, instrument, localtime, direction, price, volume):
        logger.debug("Order: Instrument: {}, Direction: {}, Price: {}, Volume: {}".format(instrument, direction, price, volume))
        url = self.domain_name + "/api/TradeAPI/Order"
        data = {
            "token_ub": token_ub,
            "user_info": "NULL",
            "instrument": instrument,
            "localtime": localtime,
            "direction": direction,
            "price": price,
            "volume": volume,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 发送“撤单”请求:
    # token_ub:         令牌
    # instrument:       股票名称
    # localtime:        当前时间
    # index:            撤单索引，Order函数中获取
    def sendCancel(self, token_ub, instrument, localtime, index):
        logger.debug("Cancel: Instrument: {}, index:{}".format(instrument, index))
        url = self.domain_name + "/api/TradeAPI/Cancel"
        data = {
            "token_ub": token_ub,
            "user_info": "NULL",
            "instrument": instrument,
            "localtime": 0,
            "index": index
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 发送“获取限价订单薄(LOB)”请求:
    # token_ub:                             令牌
    # instrument:                           股票名称
    # response["lob"]["limit_up_price"]     涨停价                response["lob"]["limit_down_price"]   跌停价
    # response["lob"]["bidprice"]           买价[数组(len=10)]     response["lob"]["askprice"]           卖价[数组(len=10)]
    # response["lob"]["bidvolume"]          买量[数组(len=10)]     response["lob"]["askvolume"]          卖量[数组(len=10)]
    # response["lob"]["last_price"]         最终成交价
    # response["lob"]["trade_volume"]       成交量
    # response["lob"]["trade_value"]        成交额
    def sendGetLimitOrderBook(self, token_ub, instrument):
        logger.debug("GetLimitOrderBook: Instrument: {}".format(instrument))
        url = self.domain_name + "/api/TradeAPI/GetLimitOrderBook"
        data = {
            "token_ub": token_ub,
            "instrument": instrument
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 获取 用户信息：
    # 用法1：response["下列参数"]                  用法2：response["rows"][i]["下列参数"]
    #       pnl:              PNL                     instrument_name     股票名称
    #       sharpe:           Sharpe                  share_holding       持仓
    #       orders:           总下单数                  position            市值
    #       error_orders:     错单数                    pnl                 PNL
    #       order_value:      总下单金额                 orders              下单数
    #       trade_value:      总成交金额                 error_orders        错单数
    #       commision:        手续费                    order_value         总下单金额
    #       total_position:   多头市值                   trade_value        总成交金额
    #       remain_funds:     可用资金                   commision          手续费
    def sendGetUserInfo(self, token_ub):
        logger.debug("GetUserInfo: ")
        url = self.domain_name + "/api/TradeAPI/GetUserInfo"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 获取比赛信息
    def sendGetGameInfo(self, token_ub):
        logger.debug("GetGameInfo: ")
        url = self.domain_name + "/api/TradeAPI/GetGameInfo"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 发送 获取股票信息 请求：
    # response["instruments"]                           获取股票的列表
    # response["instrument_number”]                     获取股票的数量。
    # response["instruments"][i]["instrument_name”]     获取第 i+1 个股票名称。
    def sendGetInstrumentInfo(self, token_ub):
        logger.debug("GetInstrumentInfo: ")
        url = self.domain_name + "/api/TradeAPI/GetInstrumentInfo"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 发送 “获取成交信息” 请求：
    # response["trade_list"]:                       获取成交列表
    # response["trade_list"][i][“trade_time"]:      成交时间
    # response["trade_list"][i][“trade_index"]:     成交索引
    # response["trade_list"][i][“order_index"]:     (你的) 下单索引
    # response["trade_list"][i][“trade_price"]:     成交价
    # response["trade_list"][i][“trade_volume"]:    成交量
    # response["trade_list"][i][“remain_volume"]:   剩余量
    def sendGetTrade(self, token_ub, instrument):
        logger.debug("GetTrade: Instrment: {}".format(instrument))
        url = self.domain_name + "/api/TradeAPI/GetTrade"
        data = {
            "token_ub": token_ub,
            "instrument_name": instrument
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 发送 “获取当前外挂单” 请求：
    # response["instruments”]:                                          获取当前外挂的股票列表
    # response["instruments"][i]["instrument"]:                         获取股票名称
    # response["instruments"][i]["active_orders"]:                      获取当前股票的外挂单列表
    # response["instruments"][i]["active orders"][j]["order_index"]:    下单索引。
    # response["instruments"][i]["active orders"][j]["order_price"]:    下单价
    # response["instruments"][i]["active orders"][j]["volume"]:         下单量
    # response["instruments"][i]["active orders"][j]["direction"]:      下单方向
    def sendGetActiveOrder(self, token_ub):
        logger.debug("GetActiveOrder: ")
        url = self.domain_name + "/api/TradeAPI/GetActiveOrder"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response


# 默认 时间比率为: 24h/25min
bot = BotsDemoClass("UBIQ_TEAM106", "f7ugVlef0")  # 初始化：账号、密码
bot.login()         # 登录
bot.init()          # 初始化：获取 交易日信息 和 股票信息
SimTimeLen = 14400  # 一个交易日共交易4小时，对应 4*60*60 = 14400s。即一天 24h 有效交易时间为 4h，即交易所(9:30-11:30,13:00-15:00)
endWaitTime = 300   # 系统结算时间为 5分钟，对应 5*60 = 300s。是系统结算时间，不是交易日的 24h 时间
# 算出要进行至少 14400 次交易，交易天数应需要 day 天
while True:
    if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) < SimTimeLen:
        break
    else:
        bot.day += 1

while bot.day <= bot.running_days:
    # 这里使得时间大于-100即可，此时为交易开启前
    while True:
        prepareTime = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
        logger.debug("prepareTime: {}".format(prepareTime))  # 打印准备时间
        if prepareTime > -100:
            break

    # [-100, 0]的时间是用于初始化：交易策略可能要用的参数。这段时间其实相当于空跑。详情见日志。0秒开始才正式交易

    now = round(ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time))
    bot.bod()  # 每个交易日开始时，交易策略的初始化

    for s in range(now, SimTimeLen + endWaitTime):
        # 保证当前时间大于等于s。1s内时间，用于进行 交易操作前 的参数初始化
        while True:
            initTime = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
            logger.debug("initTime: {}, s = {}".format(initTime, s))  # 打印初始化时间
            if initTime >= s:
                break
        t = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
        logger.info("Work Time: {}".format(t))
        if t < SimTimeLen - 30:
            bot.work()  # 执行交易策略
    bot.eod()  # 用于每天交易结束时执行一些操作
    bot.day += 1
bot.final()  # 用于赛后处理一些工作和分析
