#ifndef API_CLIENT_HH
#define API_CLIENT_HH

#include "oatpp/web/client/ApiClient.hpp"
#include "oatpp/core/data/mapping/type/Object.hpp"
#include "oatpp/core/macro/codegen.hpp"

#include "dto/user_dto.hpp"

namespace oatpp { namespace consul { namespace rest {
    class MessageClient: public oatpp::web::client::ApiClient{
        public:
            #include OATPP_CODEGEN_BEGIN(ApiClient)
            API_CLIENT_INIT(MessageClient)
            API_CALL("POST", "/api/Login", sendLogin, BODY_DTO(Object<DTO_SPACE::LoginDTO>, login))
            API_CALL("POST", "/api/TradeAPI/Order", sendOrder, BODY_DTO(Object<DTO_SPACE::OrderDTO>, order))
            API_CALL("POST", "/api/TradeAPI/Cancel", sendCancel, BODY_DTO(Object<DTO_SPACE::CancelDTO>, cancel))
            API_CALL("POST", "/api/TradeAPI/GetTrade", sendGetTrade, BODY_DTO(Object<DTO_SPACE::GetTradeDTO>, gettrade))
            API_CALL("POST", "/api/TradeAPI/GetLimitOrderBook", sendGetLimitOrderBook, BODY_DTO(Object<DTO_SPACE::GetLOBDTO>, getlob))
            API_CALL("POST", "/api/TradeAPI/GetGameInfo", sendGetGameInfo, BODY_DTO(Object<DTO_SPACE::GetGameInfoDTO>, getgameinfo))
            API_CALL("POST", "/api/TradeAPI/GetUserInfo", sendGetUserInfo, BODY_DTO(Object<DTO_SPACE::GetUserInfoDTO>, getuserinfo))
            API_CALL("POST", "/api/TradeAPI/GetInstrumentInfo", sendGetInstrumentInfo, BODY_DTO(Object<DTO_SPACE::GetInstrumentInfoDTO>, getinstrumentinfo))
            API_CALL("POST", "/api/TradeAPI/GetActiveOrder", sendGetActiveOrder, BODY_DTO(Object<DTO_SPACE::GetActiveOrderDTO>, getactiveor))
            #include OATPP_CODEGEN_END(ApiClient)
    };
}
}
}


#endif
