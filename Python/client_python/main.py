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
            self.instruments = []
            for instrument in response["instruments"]:
                self.instruments.append(instrument["instrument_name"])
            logger.info("Get Instruments: {}".format(self.instruments))

    # 初始化：获取 交易日信息 和 股票信息
    def init(self):
        response = self.api.sendGetGameInfo(self.token_ub)
        if response["status"] == "Success":
            self.start_time = response["next_game_start_time"]
            self.running_days = response["next_game_running_days"]
            self.running_time = response["next_game_running_time"]
            self.time_ratio = response["next_game_time_ratio"]
        self.GetInstruments()
        self.day = 0
    # 每个交易日开始时，交易策略的初始化
    def bod(self):
        pass
    # 交易策略的实现，可进行：查询、处理行情、下单、撤单等操作 (demo是随机买入某支股票的一手)
    def work(self):
        # 随机买
        buyID = random.randint(0, len(self.instruments) - 1)
        LOB = self.api.sendGetLimitOrderBook(self.token_ub, self.instruments[buyID])
        if LOB["status"] == "Success":
            # 以 AskPrice1 的卖家报价买入
            askprice_1 = float(LOB["lob"]["askprice"][0])
            t = ConvertToSimTime_us(self.start_time, self.time_ratio, self.day, self.running_time)
            response = self.api.sendOrder(self.token_ub, self.instruments[buyID], t, "buy", askprice_1, 100)

    # 每个交易日结束时会调用该函数，可用于每天交易结束时执行一些操作
    def eod(self):
        pass
    # 在所有交易日结束后会调用，可用于赛后处理一些工作和分析
    def final(self):
        pass

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

    # 发送操作请求：在 localtime时间 对 volume数量 的 股票instrument，以 price 的价格，执行 direction操作(如买、卖)
    def sendOrder(self, token_ub, instrument, localtime, direction, price, volume):
        logger.debug("Order: Instrument: {}, Direction:{}, Price: {}, Volume:{}".format(instrument, direction, price, volume))
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

    # 发送“撤单”请求
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

    # 发送“获取限价订单薄(LOB)”请求
    def sendGetLimitOrderBook(self, token_ub, instrument):
        logger.debug("GetLimitOrderBook: Instrument: {}".format(instrument))
        url = self.domain_name + "/api/TradeAPI/GetLimitOrderBook"
        data = {
            "token_ub": token_ub,
            "instrument": instrument
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    def sendGetUserInfo(self, token_ub):
        logger.debug("GetUserInfo: ")
        url = self.domain_name + "/api/TradeAPI/GetUserInfo"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    def sendGetGameInfo(self, token_ub):
        logger.debug("GetGameInfo: ")
        url = self.domain_name + "/api/TradeAPI/GetGameInfo"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 发送 获取股票信息请求
    def sendGetInstrumentInfo(self, token_ub):
        logger.debug("GetInstrumentInfo: ")
        url = self.domain_name + "/api/TradeAPI/GetInstrumentInfo"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 发送 “获取成交信息” 请求
    def sendGetTrade(self, token_ub, instrument):
        logger.debug("GetTrade: Instrment: {}".format(instrument))
        url = self.domain_name + "/api/TradeAPI/GetTrade"
        data = {
            "token_ub": token_ub,
            "instrument_name": instrument
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    # 发送 “获取当前外挂单” 请求
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
bot.login()  # 登录
bot.init()  # 初始化：获取 交易日信息 和 股票信息
SimTimeLen = 14400  # 一个交易日共交易4小时，对应 4*60*60 = 14400s。即一天 24h 有效交易时间为 4h，即交易所(9:30-11:30,13:00-15:00)
endWaitTime = 300  # 系统结算时间为 5分钟，对应 5*60 = 300s。是系统结算时间，不是交易日的 24h 时间
# 算出要进行至少 14400 次交易，交易天数应需要 day 天
while True:
    if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) < SimTimeLen:
        break
    else:
        bot.day += 1

while bot.day <= bot.running_days:
    # 留出 90s 时间，用于 交易日开始后 且 交易开启前，交易策略可能要用的参数的初始化
    while True:
        if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) > -900:
            break
    bot.bod()  # 每个交易日开始时，交易策略的初始化
    now = round(ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time))
    for s in range(now, SimTimeLen + endWaitTime):
        # 1s内时间，用于进行 交易操作前 的参数初始化
        while True:
            if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) >= s:
                break
        t = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
        logger.info("Work Time: {}".format(t))
        if t < SimTimeLen - 30:
            bot.work()  # 执行交易策略
    bot.eod()  # 用于每天交易结束时执行一些操作
    bot.day += 1
bot.final()  # 用于赛后处理一些工作和分析
