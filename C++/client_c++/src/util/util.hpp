#ifndef UTIL_HH
#define UTIL_HH

#include <map>
#include <string>
#include <fstream>
#include <iostream>
#define LOG_REPONSE(dto) OATPP_LOGD("RESPONSE", "DTO: %s", oatpp::parser::json::mapping::ObjectMapper::createShared()->writeToString(dto)->c_str());
namespace UTIL_SPACE{
    time_t ConvertToTimestamp_us(std::chrono::system_clock::time_point now){
        auto duration = now.time_since_epoch();
        auto microseconds = std::chrono::duration_cast<std::chrono::microseconds>(duration).count();
        return microseconds;
    }
    time_t ConvertToTimestamp_s(std::chrono::system_clock::time_point now){
        auto duration = now.time_since_epoch();
        auto seconds = std::chrono::duration_cast<std::chrono::seconds>(duration).count();
        return seconds;
    }
    long long GetCurrentTime_us(std::chrono::system_clock::time_point start_time){
        auto end_time = std::chrono::system_clock::now();
        auto result = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time).count();
        return result;
    }
    double ConvertToSimTime_us(std::chrono::system_clock::time_point start_time, double time_ratio, int day, int running_time){
        auto end_time = std::chrono::system_clock::now();
        auto result = (std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time).count() / 1000000. - (day - 1) * running_time ) * time_ratio;
        return result;
    }
    std::chrono::system_clock::time_point ConvertToTimePoint_s(int year, int month, int day, int hour, int minute, int second){
        std::tm tm = {};
        tm.tm_year = year - 1900;
        tm.tm_mon = month - 1;
        tm.tm_mday = day;
        tm.tm_hour = hour;
        tm.tm_min = minute;
        tm.tm_sec = second;
        tm.tm_isdst = -1;
        std::time_t tt = std::mktime(&tm);
        std::chrono::system_clock::time_point tp = std::chrono::system_clock::from_time_t(tt);
        return tp;
    }
    std::chrono::system_clock::time_point ConvertToTimePoint_s(std::time_t tt){
        std::chrono::system_clock::time_point timePoint = std::chrono::system_clock::from_time_t(tt);
        return timePoint;
    }
    void ConvertToYMDHMS(std::chrono::system_clock::time_point tp) {
        std::time_t tt = std::chrono::system_clock::to_time_t(tp);
        std::tm* timeinfo = std::localtime(&tt);
        std::cout << "Year: " << timeinfo->tm_year + 1900 << std::endl;
        std::cout << "Month: " << timeinfo->tm_mon + 1 << std::endl;
        std::cout << "Day: " << timeinfo->tm_mday << std::endl;
        std::cout << "Hour: " << timeinfo->tm_hour << std::endl;
        std::cout << "Minute: " << timeinfo->tm_min << std::endl;
        std::cout << "Second: " << timeinfo->tm_sec << std::endl;
    }
    double ConvertToExchangeTime(std::string str){
        int h = stoi(str.substr(0,2));
        int m = stoi(str.substr(3,2));
        int s = stoi(str.substr(6,2));
        int us = stoi(str.substr(9,6));
        if (h < 12){
            return (h - 9) * 3600. + (m - 30.) * 60. + s + us * 0.000001;
        }
        else return (h - 11) * 3600. + (m - 0.) * 60. + s + us * 0.000001;
    }
    std::map<std::string, std::string> read_ini_file(const std::string& filename) {
        std::map<std::string, std::string> config;
        std::ifstream file(filename);
        if (!file.is_open()) {
            std::cerr << "Failed to open file: " << filename << std::endl;
            return config;
        }
        std::string line;
        while (std::getline(file, line)) {
            if (line.empty() || line[0] == '#') {
                continue;
            }
            size_t delimiter_pos = line.find('=');
            if (delimiter_pos == std::string::npos) {
                continue;
            }
            std::string key = line.substr(0, delimiter_pos);
            std::string value = line.substr(delimiter_pos + 1);
            config[key] = value;
        }
        return config;
    }
}

#endif
