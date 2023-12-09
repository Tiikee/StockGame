# -*- coding: utf-8 -*-
import math
import os
import inline
import requests
import socket
import json
import time
import logging
import colorlog
import random

# 修改了日志输出方式，使得颜色对5个级别日志分级
log_format = '%(log_color)s%(asctime)s %(levelname)s: %(message)s'
console_format = colorlog.ColoredFormatter(log_format)
console_handler = colorlog.StreamHandler()
console_handler.setFormatter(console_format)

# 创建 logging 的文件处理器，设置格式。
current_time = time.strftime("%Y%m%d_%H%M")
log_folder = 'log'
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

log_file_path = os.path.join(log_folder, f'Gamelog_{current_time}.log')  # 日志输出到项目的log文件夹中
file_handler = logging.FileHandler(log_file_path)  # log文件以时间作为后缀
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

logger = logging.getLogger(__name__)
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)  # 设置日志级别

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
    def buy(self, instrument: str, totle: int):
        pass
    def sell(self, instrument: str, totle: int):
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
            logger.info("Get stockNumber: {}, Instruments: {}".format(self.stockNumber, self.instruments))

    # 初始化所有股票初始价格、当前我对所有股票的持仓
    def stocksInit(self):
        self.instrumentHash = {}        # hash映射 {“股票名称“: 股票下标}
        # self.stockBuyPrice = {}         # 29支股票的[购入总价，持股数，平均价格]
        self.stocksPriceUpDown = {}     # 所有股票历史差价列表。[股票名称，[历史涨跌差价情况]] 29个key，对应29股票
        self.stocksLOB = {}             # 所有股票的历史LOB。map[股票名称， map[LOB参数, [历史数据]]]。忽略localtime字段
        self.stockRatio = {}            # 所有股票的因子
        for i in range(self.stockNumber):
            instrument = self.instruments[i]
            # self.stockBuyPrice[instrument] = [0, 0, 0]
            self.instrumentHash[instrument] = i
            self.stocksPriceUpDown[instrument] = []
            self.stocksLOB[instrument] = {
                "localtime": [],
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
            self.stockRatio[instrument] = 0.0
        # stocksLOB 或许能写成指定大小的数据，这样就得用下标idx 访问最新元素了：stocksLOB[name][key] = [] * 14400。 O(1)时间写读
        logger.info("### StocksInit, \n stocksLOB: {}".format(self.stocksLOB))


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
        self.tradeList = []             # 股票成交历史列表
        self.userInfoData = []          # 用户历史持股信息: 记录每次work时，29支股票的持股信息
        self.dayEndAllStocksTrade = {}  # 用户所有交易日的全部股票结算列表，{交易日：当天交易结束时的股票信息列表}。用于每个交易日结束时统计
        self.totalTradeScore = {}       # 每个交易日结束后的总体收益
        self.day = 0

    # 获得上一次所有股票的买卖情况、获得所有股票本轮的LOB价格行情、所有股票和上次相比的差价。并算出各股票因子
    def getAllStocksInfo(self):
        preTradeList = []  # 记录上一次所有股票的成交列表(没交易的就是空)
        # 遍历所有股票，并存储此时LOB。同时记录此时所有股票的涨跌行情
        for instrument in self.instruments:
            lobResponse = self.api.sendGetLimitOrderBook(self.token_ub, instrument)
            # 成功获取LOB
            if lobResponse["status"] == "Success":
                # 比较是否上涨
                lastPrice = lobResponse["lob"]["last_price"]
                # 则计算出与上次的差价，并压入历史差价中(仅当 LOB 历史数组非空时)
                size = len(self.stocksLOB[instrument]["last_price"])
                if size:
                    self.stocksPriceUpDown[instrument].append(lastPrice - self.stocksLOB[instrument]["last_price"][-1])
                # 算出因子
                if size > 10:
                    preLastPrice10 = sum(self.stocksLOB[instrument]["last_price"][-10:]) / 10  # 倒数第10个 lastPrice
                    ratioTmp = (lastPrice - preLastPrice10) / preLastPrice10
                    # 忽略涨幅在 [-0.001, 0.001] 区间
                    if -0.001 < ratioTmp < 0.001: self.stockRatio[instrument] = 0
                    else: self.stockRatio[instrument] = ratioTmp

                # 存储本轮LOB
                for key, value in lobResponse["lob"].items():
                    self.stocksLOB[instrument][key].append(value)
            # logger.debug("### instrument: {}, lob: {}".format(instrument, lobResponse["lob"]))  # 打印该股票LOB
            # 获取该股票的成交列表
            tradeResponse = self.api.sendGetTrade(self.token_ub, instrument)
            if tradeResponse["status"] != "Success":
                return  # 此时无法获取上次成交列表，直接退出
            preTradeList.append([instrument, tradeResponse["trade_list"]])
        self.tradeList.append(preTradeList)                             # 存储上一次所有股票的成交列表
        logger.info("### Get preTradeList: {}".format(preTradeList))    # 打印上一次的股票成交列表

    # 进行买入
    def buy(self, instrument: str, totle: int):
        # 随机买。如果股票剩余仓不足100，就不买了。因为只会按错单来算。 todo : 如果外挂单(即未交易的単)超过10张，则删除低价外挂单
        buyLOB = self.api.sendGetLimitOrderBook(self.token_ub, instrument)
        if buyLOB["status"] == "Success":
            logger.info("##### buy! stock: {}, LOB: {}".format(instrument, buyLOB["lob"]))    # 打印本次所买股票的LOB
            # 优先买最低价，如果仓位够
            for i in range(10):
                askprice = float(buyLOB["lob"]["askprice"][i])
                askvolume = buyLOB["lob"]["askvolume"][i]
                # 此时该股票剩余仓不足100，跳过不买。
                if askvolume < 100:
                    # 打印该股票的 买家号、剩余仓
                    logger.debug("# Askvolume not enough! bidID: {}, askvolume: {}".format(i, askvolume))
                    continue
                t = ConvertToSimTime_us(self.start_time, self.time_ratio, self.day, self.running_time)
                response = self.api.sendOrder(self.token_ub, instrument, t, "buy", askprice, totle)
                return  # 买100支股就不再继续购买
            logger.info("### All Askvolume empty! stock: {}".format(instrument))   # 该股票剩余仓全空

    # 随机买入
    def randBuy(self):
        # 随机买三次
        for i in range(3):
            buyInstrument = self.instruments[random.randint(0, self.stockNumber - 1)]  # 随机购买的股票名
            self.buy(buyInstrument, 100)

    # 初始随机买，不卖出
    def initialBuy(self):
        self.getAllStocksInfo()  # 获得上轮交易情况、本轮LOB。并存入历史列表中

        # 获得当前用户信息
        userInfoResponse = self.api.sendGetUserInfo(self.token_ub)
        if userInfoResponse["status"] == "Success":
            self.userInfoData.append(userInfoResponse["rows"])  # 存入本轮交易时，用户手上的持股信息
            # 执行随机买
            # fund = userInfoResponse["remain_funds"]  # 手头资金
            # # 可用资金不足时，直接退出循环。此时无法购买任何股票
            # if fund < 500:
            #     logger.debug("# fund not enough: {}".format(fund))
            #     return
            # self.randBuy()
            # 本次交易时我的29支股票持股信息
            logger.warning("### Get User Stock Info: ")
            for stock in userInfoResponse["rows"]:
                logger.warning("### stock: {}".format(stock))

    # 卖股票(全抛)，参数： 股票名、股票总量
    def sell(self, instrument: str, totle: int):
        sellLOB = self.api.sendGetLimitOrderBook(self.token_ub, instrument)
        if sellLOB["status"] == "Success":
            logger.info("##### sell! stock: {}, LOB: {}".format(instrument, sellLOB["lob"]))    # 打印本次所买股票的LOB
            # 直接从高价到低价下单，仓位足够就卖
            for i in range(10):
                if totle == 0: return  # 此时已经卖完了
                bidprice = float(sellLOB["lob"]["bidprice"][i])
                bidvolume = sellLOB["lob"]["bidvolume"][i]
                # 此时该股票需求不足100，跳过不卖，因为卖不动。
                if bidvolume < 100:
                    # 打印该股票的 买家号、剩余仓
                    logger.info("# Bidvolume not enough! bidID: {}, bidvolume: {}".format(i, bidvolume))
                    continue
                t = ConvertToSimTime_us(self.start_time, self.time_ratio, self.day, self.running_time)
                # 一共卖多少
                sellcnt = totle
                if totle > bidvolume: sellcnt = max(100, bidvolume - 100)
                response = self.api.sendOrder(self.token_ub, instrument, t, "sell", bidprice, sellcnt)
                totle -= sellcnt
    # 所有股票全抛
    def sellAll(self):
        response = self.api.sendGetUserInfo(self.token_ub)
        stocks = []  # 记录所有 [股票名，持股数]
        if response["status"] == "Success":
            for i in range(self.stockNumber):
                if response["rows"][i]["share_holding"] > 0:
                    stocks.append([self.instruments[i], response["rows"][i]["share_holding"]])
        for stock in stocks:
            self.sell(stock[0], stock[1])
        logger.info("# Sell all stocks! stocks: {}".format(stocks))

    # 删掉所有买卖外挂单
    def deleteAllOrders(self):
        response = self.api.sendGetActiveOrder(self.token_ub)
        if response["status"] == "Success":
            for i in range(29):
                for activeOrder in response["instruments"][i]["active_orders"]:
                    order_index = activeOrder["order_index"]
                    t = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
                    cancleResponse = self.api.sendCancel(self.token_ub, self.instruments[i], t, order_index)
            logger.info("### Delete all buy and sell orders!")

    # 删掉所有买操作的外挂单 todo: 其实可以记录什么时候所有买单全删完了，然后直接return就行
    def deleteAllBuyOrder(self):
        response = self.api.sendGetActiveOrder(self.token_ub)
        if response["status"] == "Success":
            for i in range(29):
                for activeOrder in response["instruments"][i]["active_orders"]:
                    if activeOrder["direction"] == "buy":
                        order_index = activeOrder["order_index"]
                        t = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
                        cancleResponse = self.api.sendCancel(self.token_ub, self.instruments[i], t, order_index)
            logger.info("### Delete all buy orders!")

    # 每个交易日开始前，交易策略的初始化
    def bod(self):
        logger.info("### Trade begin! Day: {}, running_days: {}".format(self.day, self.running_days))  # 今天日期、截止日
        response = self.api.sendGetUserInfo(self.token_ub)  # 获取当前用户数据
        if response["status"] == "Success":
            # 打印本交易日开始前，我的所有股票收益情况
            logger.info("Get allStocksTrade: {}".format(response["rows"]))
            # 打印本交易日开始前，我的整体收益情况
            ls = [["pnl: ", response["pnl"]],
                  ["sharpe: ", response["sharpe"]],
                  ["orders: ", response["orders"]],
                  ["error_orders: ", response["error_orders"]],
                  ["order_value: ", response["order_value"]],
                  ["trade_value: ", response["trade_value"]],
                  ["commision: ", response["commision"]],
                  ["total_position: ", response["total_position"]],
                  ["remain_funds: ", response["remain_funds"]]]
            logger.info("Get totalTradeScore: {}".format(ls))

    # 交易策略的实现，可进行：查询、处理行情、下单、撤单等操作 (demo是随机买入某支股票的一手) todo: 后续需把buy、sell中的获取用户信息整合到一起
    def work(self):
        self.getAllStocksInfo()  # 获得上轮交易情况、本轮LOB

        # 获得当前用户信息
        userInfoResponse = self.api.sendGetUserInfo(self.token_ub)
        if userInfoResponse["status"] == "Success":
            logger.warning("### Start analyze !!!")
            holdStocks = {}                         # 手上有持股的股票 [股票名：持仓数]
            ratio = []                              # [股票因子， 股票名]
            posCnt, negCnt, f = 0, 0, 0             # 记录正、负因子数、临时因子、
            # 刷新持股价格。顺便知道哪些股有持股(持股数非0)
            for i in range(self.stockNumber):
                instrument = userInfoResponse["rows"][i]["instrument_name"]
                share_holding = userInfoResponse["rows"][i]["share_holding"]
                if share_holding != 0:
                    holdStocks[instrument] = share_holding
                # 只记录非0因子
                f = self.stockRatio[instrument]
                if f != 0:
                    ratio.append([self.stockRatio[instrument], instrument])
                    if f > 0: posCnt += 1
                    else: negCnt += 1

            self.userInfoData.append(userInfoResponse["rows"])  # 存入本轮交易时，用户手上的持股信息

            cnt = posCnt + negCnt  # 总因子数
            # 总因子数 > 0
            if cnt:
                # 对因子升序
                ratio.sort()
                volume = [0] * cnt
                diff = ratio[-1][0] - ratio[0][0]  # 最大值 - 最小值
                # 因子加权交易量
                for i in range(cnt):
                    vol = math.ceil(abs((ratio[i][0] - ratio[0][0]) / diff - 0.5) * 500)
                    volume[i] = vol - vol % 100  # 保证买卖量是100的倍数
                fund = userInfoResponse["remain_funds"]     # 手头资金
                sellcnt = int(posCnt * 0.3)                 # 卖正因子的前0.3个，涨的最猛的前0.3。向下取整
                buycnt = math.ceil(negCnt * 0.3)            # 买负因子的前0.3个，跌的最猛的前0.3。向上取整
                # 买 跌的最猛的前0.3
                if fund > 500:
                    for i in range(buycnt):
                        # self.buy(ratio[i][1], 100)
                        self.buy(ratio[i][1], volume[i])
                else:
                    logger.warning("### Fund not enough! fund: {}".format(fund))

                if holdStocks:
                    # 卖 涨的最猛的前0.3
                    for i in range(-1, - 1 - sellcnt, -1):
                        stockname = ratio[i][1]
                        if stockname in holdStocks:
                            # self.sell(ratio[i][1], holdStocks[stockname])
                            self.sell(ratio[i][1], min(holdStocks[stockname], volume[i]))
                else:
                    logger.warning("### Holding share empty!!!")  # 持仓为空

            # 本次交易时我的29支股票持股信息
            logger.warning("### Get User Stock Info: ")
            for stock in userInfoResponse["rows"]:
                logger.warning("### stock: {}".format(stock))

    # 每个交易日结束时会调用该函数，可用于每天交易结束时执行一些操作
    def eod(self):
        response = self.api.sendGetUserInfo(self.token_ub)  # 获取当前用户数据
        if response["status"] == "Success":
            # 打印本交易日我的所有股票收益情况
            self.dayEndAllStocksTrade[self.day] = response["rows"]
            logger.info("### Day end! Day: {}, running_days: {}, \nGet allStocksTrade: {}"
                        .format(self.day, self.running_days, self.dayEndAllStocksTrade))
            # 打印本交易日整体收益情况
            ls = [["pnl: ", response["pnl"]],
                  ["sharpe: ", response["sharpe"]],
                  ["orders: ", response["orders"]],
                  ["error_orders: ", response["error_orders"]],
                  ["order_value: ", response["order_value"]],
                  ["trade_value: ", response["trade_value"]],
                  ["commision: ", response["commision"]],
                  ["total_position: ", response["total_position"]],
                  ["remain_funds: ", response["remain_funds"]]]
            self.totalTradeScore[self.day] = ls
            logger.info("Get totalTradeScore: {}".format(ls))
        # 打印本交易日的历史LOB
        logger.info("Get all LOB: {}".format(self.stocksLOB))

    # 在所有交易日结束后会调用，可用于赛后处理一些工作和分析
    def final(self):
        logger.info("### Trade End! Get TotalTradeScore: {}".format(self.totalTradeScore))  # 打印全部交易日的交易信息

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
        # logger.debug("GetLimitOrderBook: Instrument: {}".format(instrument))
        url = self.domain_name + "/api/TradeAPI/GetLimitOrderBook"
        data = {
            "token_ub": token_ub,
            "instrument": instrument
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 获取 用户信息：
    # 用法1：response["下列参数"]                  用法2：response["rows"][i]["下列参数"]     i = 0~28 对应 29支股票
    #       pnl:              PNL                     instrument_name     股票名称
    #       sharpe:           Sharpe                  share_holding       持仓
    #       orders:           总下单数                  position            市值
    #       error_orders:     错单数                    pnl                 PNL
    #       order_value:      总下单金额                 orders              下单数
    #       trade_value:      总成交金额                 error_orders        错单数
    #       commision:        手续费                    order_value         总下单金额
    #       total_position:   多头市值                   trade_value        总成交金额
    #       remain_funds:     可用资金                   commision          手续费
    # 参数说明：
    #       PnL:
    #           买: pnl = (卖出价格 − 买入成本) × 持仓数量 - 手续费(commision) 卖: pnl = 卖出价格 × 数量
    #           左边response["pnl"]可以直接获取目前我一共亏赚了多少钱。右边的就是特定股票的亏赚多少
    #           pnl 包括我买、卖的pnl的和，即买卖的总收益.
    #       order_value: 计划买或卖的金额
    #       trade_value: 实际完成交易时的买/卖 价。由于价格波动等原因，实际成交的金额可能与下单时的金额有所不同。一定时间内，多个订单可能以不同的价格成交
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
        # logger.debug("GetTrade: Instrment: {}".format(instrument))
        url = self.domain_name + "/api/TradeAPI/GetTrade"
        data = {
            "token_ub": token_ub,
            "instrument_name": instrument
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 发送 “获取当前外挂单” 请求：  i为股票下标、j为外挂单下标
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
bot.init()          # 初始化：获取 交易日信息 和 股票信息。同时变量会被清空
SimTimeLen = 14400  # 一个交易日共交易4小时，对应 4*60*60 = 14400s。即一天 24h 有效交易时间为 4h，即交易所(9:30-11:30,13:00-15:00)
endWaitTime = 300   # 系统结算时间为 5分钟，对应 5*60 = 300s。是系统结算时间，不是交易日的 24h 时间
# 算出要进行至少 14400 次交易，交易天数应需要 day 天
while True:
    if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) < SimTimeLen:
        break
    else:
        bot.day += 1

# 一共8个交易日，每次交易拿上一次交易结束以后的剩余资金交易。如果本交易日结束后仍持股，则会强平，直接以跌停价给全卖掉。
# 每天资金会重置为100w，每天的交易都是隔离开的。所以下面while循环相当于重新启动交易
while bot.day <= bot.running_days:
    # 这里使得时间大于-100即可，此时为交易开启前
    while True:
        prepareTime = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
        logger.debug("prepareTime: {}".format(prepareTime))  # 打印准备时间
        if prepareTime > -100:
            break

    # [-100, 0]的时间是用于初始化：交易策略可能要用的参数。这段时间其实相当于空跑。详情见日志。0秒开始才正式交易
    while True:
        preprocessTime = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
        logger.debug("preprocessTime: {}".format(preprocessTime))  # 打印预处理时间
        if preprocessTime >= 0:
            break

    now = round(ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time))
    bot.bod()  # 每个交易日开始时，交易策略的初始化

    endTime = SimTimeLen + endWaitTime
    logger.info("The Whole Time Interval is now: {}, endTime: {}".format(now, endTime))
    workCnt = 0  # 当前work共运行了多少次
    delBuyOrder = True  # 判断当前是否要清空了所有买外挂单，只清空一次，清空完立马变False
    # s = [0, 14400 + 300]
    for s in range(now, endTime):
        # 保证当前时间大于等于s。1s内时间，用于进行 交易操作前 的参数初始化
        while True:
            initTime = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
            logger.debug("initTime: {}, s = {}".format(initTime, s))  # 打印初始化时间
            if initTime >= s:
                break
        t = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
        logger.info("Work Time: {}".format(t))

        # # 大杀器！手动直接全抛。删掉注释即可。保险就：将后面 605 - 622 行全注释掉
        # if t < SimTimeLen - 30:
        #     if delBuyOrder:
        #         bot.deleteAllOrders()  # 删掉所有买卖外挂单
        #         delBuyOrder = False
        #     bot.sellAll()
        #     continue

        # 待修正，以及注意：
        # 这里可以改成 s < 15，因为 s = [0, 14400 + 300]，这样前15次执行就是随机买。因为如果我中途断掉再运行，那么s会直接从now继续开始，
        # 如果用workCnt，那么又会重新随机买15次.
        # 前15次可以随机买，因为此时LOB历史数据还不足10条。一般是第5秒开始才能获取到LOB，此时一般够交易2次了。一次work结束大概30s
        if workCnt < 15:
            bot.initialBuy()
            workCnt += 1
        # 当前系统时间大于 14400 - 90 时不再进行 work交易
        elif t < SimTimeLen - 90:
            bot.work()  # 执行交易策略
            workCnt += 1
        # 最后 [14400 - 90, 14400 - 30] 不再买入，直接清仓全卖。[14400, 14400 + 300]为系统结算时间，不能交易。测试出全卖掉大概要30s
        if SimTimeLen - 90 < t < SimTimeLen - 30:
            if delBuyOrder:
                bot.deleteAllBuyOrder()  # 删掉所有买外挂单
                delBuyOrder = False
            bot.sellAll()
            logger.info("# Last 1.5min sell all! t: {}, SimTimeLen: {}".format(t, SimTimeLen))
    bot.eod()  # 用于每天交易结束时执行一些操作
    bot.day += 1
bot.final()  # 用于赛后处理一些工作和分析
