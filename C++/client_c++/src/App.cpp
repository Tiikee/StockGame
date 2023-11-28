#include "websocket/WSListener.hpp"

#include "oatpp/parser/json/mapping/ObjectMapper.hpp"
#include "oatpp-websocket/WebSocket.hpp"
#include "oatpp-websocket/Connector.hpp"

#include "oatpp/web/client/ApiClient.hpp"
#include "oatpp/core/macro/codegen.hpp"
#include "oatpp/network/tcp/client/ConnectionProvider.hpp"

#include <string>
#include <thread>
#include <chrono>
#include <iostream>

#include "AppComponent.hpp"
#include "util/util.hpp"
#include "dto/user_dto.hpp"
#include "interface/interface.hpp"
#include "api_client/api_client.hpp"
#include "bots/bots.hpp"

namespace {
    const char* TAG = "websocket-client";
    bool finished = false;
    void socketTask(const std::shared_ptr<oatpp::websocket::WebSocket>& websocket) {
        websocket->listen();
        OATPP_LOGD(TAG, "SOCKET CLOSED!!!");
        finished = true;
    }
}

void run() {
    OATPP_LOGI(TAG, "Application Started");
    INTERFACE_SPACE::init();
    auto jsonObjectMapper = oatpp::parser::json::mapping::ObjectMapper::createShared();
    // 请在这里输入参赛选手的账号和密码
    auto bot = BOTS_SPACE::BotsDemoClass("USERNAME", "PASSWORD");
    
    bot.login();
    bot.init();
    int SimTimeLen = 14400; // 交易所一天共14400秒。
    int eodWaitTime = 300; // 预留交易所五分钟计算收盘强平及各项指标。
    
    while (true){
        auto t = UTIL_SPACE::ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time);
        if (t < SimTimeLen) {break;}
        bot.day += 1;
    }
    while (bot.day < bot.running_days){
        while (true){
            auto t = UTIL_SPACE::ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time);
            if (t > -900) break;
        }
        bot.bod(); 
        // 此处demo为：从当前时刻开始，之后每一秒执行一次work()，一直到交易所收盘。可根据程序的速度及延迟进行调整，最高频率为一秒执行一次。
        double skipTime = 5.0; //开盘后进场、收盘前退场的预留时间，尽量避免由于效率原因在非交易时间访问交易所。可自行改动。
        auto now = UTIL_SPACE::ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time);
        now = std::max(now, skipTime);
        for (double s = now; s < SimTimeLen + eodWaitTime; s += 1.){
            while (true){
                auto t = UTIL_SPACE::ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time);
                if (t >= s) break;
            }
            auto t = UTIL_SPACE::ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time);
            if (t < SimTimeLen-skipTime) bot.work();
        }
        bot.eod();
        bot.day += 1;
    }
}

int main() {
    oatpp::base::Environment::init();
    run();
    oatpp::base::Environment::destroy();
    return 0;
}
