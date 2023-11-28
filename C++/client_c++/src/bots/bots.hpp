#include <cmath>
#include <vector>
#include <string>
#include <sstream>
#include <fstream>
#include <iomanip>
#include <iostream>

#include "interface/interface.hpp"
namespace BOTS_SPACE{
    class BotsClass{
        public:
        std::string username;
        std::string password;
        std::string token_ub;
        std::chrono::system_clock::time_point start_time;
        double running_time, time_ratio;
        int running_days;
        int day;
        public:
        BotsClass(
            std::string username, 
            std::string password
        ):username(username),password(password){}
        virtual void init() = 0;
        virtual void bod() = 0;
        virtual void work() = 0;
        virtual void eod() = 0;
        virtual void final() = 0;
    };
    class BotsDemoClass:public BotsClass{
        public:
        std::vector<std::string>instruments;
        BotsDemoClass(
            std::string username,
            std::string password
        ):BotsClass(username, password){

        }
        void login(){
            /*登录选手个人信息账号,不需要修改。*/
            auto login_response = INTERFACE_SPACE::sendLogin(username, password);
            LOG_REPONSE(login_response);
            token_ub = login_response->token_ub;
        }
        void init(){
            /*交易开始前初始化交易状态,不需要修改。*/
            day = 0;
            auto getgameinfo_response = INTERFACE_SPACE::sendGetGameInfo(token_ub);
            LOG_REPONSE(getgameinfo_response);
            if (getgameinfo_response->status != "Success") {printf("Get Game Info Fail!\n"); exit(0);}
            start_time = UTIL_SPACE::ConvertToTimePoint_s(getgameinfo_response->next_game_start_time);
            running_days = getgameinfo_response->next_game_running_days;
            running_time = getgameinfo_response->next_game_running_time;
            time_ratio = getgameinfo_response->next_game_time_ratio;
            auto getinstrumentinfo_response = INTERFACE_SPACE::sendGetInstrumentInfo(token_ub);
            for (int i = 0;i < getinstrumentinfo_response->instruments->size(); i++)
                instruments.push_back(getinstrumentinfo_response->instruments[i]->instrument_name);
            LOG_REPONSE(getinstrumentinfo_response);
        }
        void bod(){
            /*Begin of Day.交易日开始前（或日间程序开始执行前）,需要执行的个人操作。*/
            /*在盘前的时候，不能访问任何交易所关于交易的接口*/
        }
        void work(){
            /*盘中交易实时调用的自动化交易策略,以下为一个autotrader demo。*/
            int stockID = rand()%instruments.size();
            auto LimitOrderBook = INTERFACE_SPACE::sendGetLimitOrderBook(token_ub, instruments[stockID]); // 获取股票 stockID 的LOB行情。
            // LOG_REPONSE(LimitOrderBook); // 将LOB行情输出。
            double askprice_1 = LimitOrderBook->lob->askprice[0]; // 获取当前最优ask报价。
            auto _t = UTIL_SPACE::ConvertToSimTime_us(start_time, time_ratio, day, running_time); // 记录发单时间。
            auto order_response = INTERFACE_SPACE::sendOrder(token_ub, instruments[stockID], _t, "buy", askprice_1, 100); // 用最优报价去买100单。
            LOG_REPONSE(order_response); // 将订单信息输出。
        }
        void eod(){
            /*End of Day.交易日结束时,需要执行的个人操作。*/
        }
        void final(){
            /*所有交易日的交易结束后，选手可以自行统计一些数据。*/
        }
    };
}
