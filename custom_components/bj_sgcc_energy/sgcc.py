import logging
import datetime
import json
from .const import PGC_PRICE

_LOGGER = logging.getLogger(__name__)

AUTH_URL = "http://weixin.bj.sgcc.com.cn/ott/app/auth/authorize?target=M_YECX"
CONSNO_URL = "http://weixin.bj.sgcc.com.cn/ott/app/follower/consumer/prepaid/list"
REMAIN_URL = "http://weixin.bj.sgcc.com.cn/ott/app/elec/account/query"
DETAIL_URL = "http://weixin.bj.sgcc.com.cn/ott/app/electric/bill/overview"
BILLINFO_URL = "http://weixin.bj.sgcc.com.cn/ott/app/electric/bill/queryElecBillInfoEveryYear"
DAILYBILL_URL = "http://weixin.bj.sgcc.com.cn/ott/app/electric/bill/daily"

LEVEL_CONSUME = ["levelOneSum", "levelTwoSum", "levelThreeSum"]
LEVEL_REMAIN = ["levelOneRemain", "levelTwoRemain"]


def get_pgv_type(bill_range):
    dt = datetime.datetime.now()
    for pgc_price in PGC_PRICE:
        # month is none or month matched
        if pgc_price.get("moon") is None or pgc_price.get("moon")[0] <= dt.month <= pgc_price.get("moon")[1]:
            slot_len = len(pgc_price.get("time_slot"))
            for n in range(0, slot_len):
                if (((pgc_price.get("time_slot")[n][0] <= pgc_price.get("time_slot")[n][1] and
                      pgc_price.get("time_slot")[n][0] <= dt.hour < pgc_price.get("time_slot")[n][1]) or
                     (pgc_price.get("time_slot")[n][0] > pgc_price.get("time_slot")[n][1] and
                      (pgc_price.get("time_slot")[n][0] <= dt.hour or pgc_price.get("time_slot")[n][1] > dt.hour))) and
                        pgc_price.get("key") in bill_range):
                    return pgc_price.get("key")
    return "Unknown"


class SGCCData:
    def __init__(self, session, openid):
        self._session = session
        self._openid = openid
        self._session_code = "e7d569dc-0806-4b30-9379-169ccf33e92a"
        self._info = {}

    @staticmethod
    def tuple2list(tup: tuple):
        return {bytes.decode(tup[i][0]): bytes.decode(tup[i][1]) for i, _ in enumerate(tup)}

    async def async_get_token(self):
        headers = {
            "Host": "weixin.bj.sgcc.com.cn",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Cookie": f"SESSION={self._session_code}; user_openid={self._openid}",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 "
                          "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.7(0x1800072c) "
                          "NetType/WIFI Language/zh_CN",
            "Accept-Language": "zh-cn",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        ret = True
        try:
            r = await self._session.get(AUTH_URL, headers=headers, allow_redirects=False, timeout=10)
            if r.status == 200 or r.status == 302:
                response_headers = self.tuple2list(r.raw_headers)
                if "Set-Cookie" in response_headers:
                    set_cookie = response_headers["Set-Cookie"]
                    self._session_code = set_cookie.split(";")[0].split("=")[1]
                    _LOGGER.debug(f"Got a new session {self._session_code}")
            else:
                ret = False
                _LOGGER.error(f"async_get_token response status_code = {r.status}")
        except Exception as e:
            ret = False
            _LOGGER.error(f"async_get_token response got error: {e}")
        return ret

    def commonHeaders(self):
        headers = {
            "Host": "weixin.bj.sgcc.com.cn",
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": "zh-cn",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "http://weixin.bj.sgcc.com.cn",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 "
                          "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.7(0x1800072c) "
                          "NetType/WIFI Language/zh_CN",
            "Connection": "keep-alive",
            "Cookie": f"SESSION={self._session_code}; user_openid={self._openid}"
        }
        return headers

    async def async_get_ConsNo(self):
        headers = self.commonHeaders()
        ret = True
        try:
            r = await self._session.post(CONSNO_URL, headers=headers, timeout=10)
            if r.status == 200:
                result = json.loads(await r.read())
                if result["status"] == 0:
                    data = result["data"]
                    for single in data:
                        consNo = single["consNo"]
                        if consNo not in self._info:
                            _LOGGER.debug(f"Got ConsNo {consNo}")
                            self._info[consNo] = {}
                else:
                    ret = False
                    _LOGGER.error(f"async_get_ConsNo error: {result['msg']}")
            else:
                ret = False
                _LOGGER.error(f"async_get_ConsNo response status_code = {r.status_code}")

        except Exception as e:
            _LOGGER.error(f"async_get_ConsNo response got error: {e}")
            ret = False
        return ret

    async def get_balance(self, consNo):
        headers = self.commonHeaders()
        data = {
            "consNo": consNo
        }
        ret = True
        try:
            r = await self._session.post(REMAIN_URL, data=data, headers=headers, timeout=10)
            if r.status == 200:
                result = json.loads(await r.read())
                if result["status"] == 0:
                    self._info[consNo]["balance"] = result["data"]["BALANCE_SHEET"]
                    self._info[consNo]["last_update"] = result["data"]["AS_TIME"]
                else:
                    ret = False
                    _LOGGER.error(f"get_balance error:{result['msg']}")
            else:
                ret = False
                _LOGGER.error(f"get_balance response status_code = {r.status_code}")
        except Exception as e:
            ret = False
            _LOGGER.error(f"get_balance response got error: {e}")
        return ret

    async def get_detail(self, consNo):
        headers = self.commonHeaders()
        data = {
            "consNo": consNo
        }
        ret = True
        try:
            r = await self._session.post(DETAIL_URL, data=data, headers=headers, timeout=10)
            if r.status == 200:
                result = json.loads(await r.read())
                if result["status"] == 0:
                    data = result["data"]
                    bill_size = len(data["billDetails"])
                    if data["isFlag"] == "1":  # 阶梯用户是否这么判断？ 瞎蒙的
                        self._info[consNo]["current_level"] = 3
                        for n in range(0, len(LEVEL_REMAIN)):
                            if int(data[LEVEL_REMAIN[n]]) > 0:
                                self._info[consNo]["current_level"] = n + 1
                                break
                        for n in range(0, bill_size):
                            if int(data["billDetails"][n]["LEVEL_NUM"]) == self._info[consNo]["current_level"]:
                                self._info[consNo]["current_price"] = data["billDetails"][n]["KWH_PRC"]
                                break
                        key = LEVEL_CONSUME[self._info[consNo]["current_level"] - 1]
                        self._info[consNo]["current_level_consume"] = int(data[key])
                        if self._info[consNo]["current_level"] < 3:
                            key = LEVEL_REMAIN[self._info[consNo]["current_level"] - 1]
                            self._info[consNo]["current_level_remain"] = int(data[key])
                        else:
                            self._info[consNo]["current_level_remain"] = "∞"
                    else:
                        bill_range = []
                        for n in range(0, bill_size):
                            bill_range.append(data["billDetails"][n]["PRC_TS_NAME"])
                        pgv_type = get_pgv_type(bill_range)
                        for n in range(0, bill_size):
                            if data["billDetails"][n]["PRC_TS_NAME"] == pgv_type:
                                self._info[consNo]["current_price"] = data["billDetails"][n]["KWH_PRC"]
                                self._info[consNo]["current_pgv_type"] = data["billDetails"][n]["PRC_TS_NAME"]
                                break
                    self._info[consNo]["year_consume"] = data["TOTAL_ELEC"]
                    self._info[consNo]["year_consume_bill"] = data["TOTAL_ELECBILL"]
                    self._info[consNo]["year"] = int(data["currentYear"])
                else:
                    ret = False
                    _LOGGER.error(f"get_detail error: {result['msg']}")
            else:
                ret = False
                _LOGGER.error(f"get_detail response status_code = {r.status_code}")
        except Exception as e:
            ret = False
            _LOGGER.error(f"get_detail response got error: {e}")
        return ret

    async def get_monthly_bill(self, consNo):
        headers = self.commonHeaders()
        cur_year = self._info[consNo]["year"]
        period = 12
        try:
            for i in range(2):
                year = cur_year - i
                data = {
                    "consNo": consNo,
                    "currentYear": year,
                    "isFlag": 1
                }
                r = await self._session.post(BILLINFO_URL, data=data, headers=headers, timeout=10)
                if r.status == 200:
                    result = json.loads(await r.read())
                    if result["status"] == 0:
                        monthBills = result["data"]["monthBills"]
                        if period == 12:
                            for month in range(12):
                                if monthBills[month]["SUM_ELEC"] == "--":
                                    period = month
                                    break
                        if i == 0:
                            self._info[consNo]["history"] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
                            for i in range(period):
                                self._info[consNo]["history"][i] = {}
                                self._info[consNo]["history"][i]["name"] = monthBills[period - i - 1]["AMT_YM"]
                                self._info[consNo]["history"][i]["consume"] = monthBills[period - i - 1]["SUM_ELEC"]
                                self._info[consNo]["history"][i]["consume_bill"] = monthBills[period - i - 1]["SUM_ELECBILL"]
                        else:
                            for i in range(12 - period):
                                self._info[consNo]["history"][11 - i] = {}
                                self._info[consNo]["history"][11 - i]["name"] = monthBills[period + i]["AMT_YM"]
                                self._info[consNo]["history"][11 - i]["consume"] = monthBills[period + i]["SUM_ELEC"]
                                self._info[consNo]["history"][11 - i]["consume_bill"] = monthBills[period + i]["SUM_ELECBILL"]
                    else:
                        _LOGGER.error(f"get_monthly_bill error: {result['msg']}")
                else:
                    _LOGGER.error(f"get_monthly_bill response status_code = {r.status_code}, params = {params}")
        except Exception as e:
            pass

    async def get_daily_bills(self, consNo):
        headers = self.commonHeaders()
        data = {
            "consNo": consNo,
            "days": 30
        }
        try:
            r = await self._session.post(DAILYBILL_URL, data=data, headers=headers, timeout=10)
            if r.status == 200:
                result = json.loads(await r.read())
                if result["status"] == 0:
                    dayBills = len(result["data"])
                    self._info[consNo]["daily_bills"] = []
                    for count in range(dayBills):
                        daily_bills = result["data"][dayBills - count - 1]
                        self._info[consNo]["daily_bills"].append({
                            "bill_date": daily_bills.get("DATA_DATE"),
                            "bill_time": daily_bills.get("COL_TIME"),
                            "day_consume": daily_bills.get("PAP_R"),
                            "day_consume1": daily_bills.get("PAP_R1"),
                            "day_consume2": daily_bills.get("PAP_R2"),
                            "day_consume3": daily_bills.get("PAP_R3"),
                            "day_consume4": daily_bills.get("PAP_R4"),
                        })
        except Exception as e:
            pass

    async def async_get_data(self):
        if await self.async_get_token() and await self.async_get_ConsNo():
            for consNo in self._info.keys():
                await self.get_balance(consNo)
                await self.get_detail(consNo)
                await self.get_monthly_bill(consNo)
                await self.get_daily_bills(consNo)
            _LOGGER.debug(f"Data {self._info}")
        return self._info
