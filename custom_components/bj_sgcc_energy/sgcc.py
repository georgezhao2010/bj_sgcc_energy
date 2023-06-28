import logging
import datetime
import json
import asyncio

from .const import PGC_PRICE

_LOGGER = logging.getLogger(__name__)

AUTH_URL = "http://weixin.bj.sgcc.com.cn/ott/app/auth/authorize?target=M_WYYT"
CONSNO_URL = "http://weixin.bj.sgcc.com.cn/ott/app/follower/bound/cons"
REMAIN_URL = "http://weixin.bj.sgcc.com.cn/ott/app/home/getElectricBill?consNo="
DETAIL_URL = "http://weixin.bj.sgcc.com.cn/ott/app/electric/bill/overview?consNo="
BILLINFO_URL = "http://weixin.bj.sgcc.com.cn/ott/app/electric/bill/queryElecBillInfoEveryYear"
DAILYBILL_URL = "http://weixin.bj.sgcc.com.cn/ott/app/electric/bill/daily"

LEVEL_CONSUME = ["levelOneSum", "levelTwoSum", "levelThreeSum"]
LEVEL_REMAIN = ["levelOneRemain", "levelTwoRemain"]


class AuthFailed(Exception):
    pass


class InvalidData(Exception):
    pass


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
        self._info = {}

    @staticmethod
    def tuple2list(tup: tuple):
        return {bytes.decode(tup[i][0]): bytes.decode(tup[i][1]) for i, _ in enumerate(tup)}

    async def async_get_token(self):
        headers = {
            "Host": "weixin.bj.sgcc.com.cn",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Cookie": f"user_openid={self._openid}",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 "
                          "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.7(0x1800072c) "
                          "NetType/WIFI Language/zh_CN",
            "Accept-Language": "zh-cn",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        r = await self._session.get(AUTH_URL, headers=headers, allow_redirects=False, timeout=10)
        if r.status == 200 or r.status == 302:
            response_headers = self.tuple2list(r.raw_headers)
            location = response_headers.get("Location") #这个OpenID有问题
            if location and str.find(location, "connect_redirect") > 0:
                raise AuthFailed("Invalid open-id")
        else:
            _LOGGER.error(f"async_get_token response status_code = {r.status}")
            raise AuthFailed(f"Authentication unexpected response code {r.status}")

    def commonHeaders(self):
        headers = {
            "Host": "weixin.bj.sgcc.com.cn",
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": "zh-cn, zh-Hans; q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "http://weixin.bj.sgcc.com.cn",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 "
                          "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.7(0x1800072c) "
                          "NetType/WIFI Language/zh_CN",
            "Connection": "keep-alive",
            "Cookie": f"user_openid={self._openid}"
        }
        return headers

    async def async_get_ConsNo(self):
        headers = self.commonHeaders()
        r = await self._session.post(CONSNO_URL, headers=headers, timeout=10)
        if r.status == 200:
            result = json.loads(await r.read())
            if result["status"] == 0:
                data = result["data"]
                for single in data:
                    consNo = single["consNo"]
                    if consNo not in self._info:
                        self._info[consNo] = {}
            else:
                raise InvalidData(f"async_get_ConsNo error: {result['msg']}")
        else:
            raise InvalidData(f"async_get_ConsNo response status_code = {r.status_code}")

    async def aysnc_get_balance(self, consNo):
        headers = self.commonHeaders()
        r = await self._session.get(REMAIN_URL + consNo, headers=headers, timeout=10)
        if r.status == 200:
            result = json.loads(await r.read())
            if result["status"] == 0:
                self._info[consNo]["balance"] = result["data"]["balanceSheet"]
                self._info[consNo]["last_update"] = result["data"]["asTime"]
            else:
                raise InvalidData(f"get_balance error:{result['msg']}")
        else:
            raise InvalidData(f"get_balance response status_code = {r.status_code}")

    async def async_get_detail(self, consNo):
        headers = self.commonHeaders()
        ret = True
        r = await self._session.get(DETAIL_URL + consNo, headers=headers, timeout=10)
        if r.status == 200:
            result = json.loads(await r.read())
            if result["status"] == 0:
                data = result["data"]
                bill_size = len(data["billDetails"])
                self._info[consNo]["isFlag"] = data["isFlag"]
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
                self._info[consNo]["year"] = int(data["CURRENT_YEAR"])
            else:
                ret = False
                _LOGGER.error(f"get_detail error: {result['msg']}")
        else:
            ret = False
            _LOGGER.error(f"get_detail response status_code = {r.status_code}")
        return ret

    async def get_monthly_bill(self, consNo):
        headers = self.commonHeaders()
        cur_year = self._info[consNo]["year"]
        period = 12
        ret = True
        for i in range(2):
            year = cur_year - i
            data = {
                "consNo": consNo,
                "currentYear": year,
                "isFlag": self._info[consNo]["isFlag"]
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
                        for n in range(period):
                            self._info[consNo]["history"][n] = {}
                            self._info[consNo]["history"][n]["name"] = monthBills[period - n - 1]["AMT_YM"]
                            self._info[consNo]["history"][n]["consume"] = monthBills[period - n - 1]["SUM_ELEC"]
                            self._info[consNo]["history"][n]["consume_bill"] = monthBills[period - n - 1]["SUM_ELECBILL"]
                    else:
                        for n in range(12 - period):
                            self._info[consNo]["history"][11 - n] = {}
                            self._info[consNo]["history"][11 - n]["name"] = monthBills[period + n]["AMT_YM"]
                            self._info[consNo]["history"][11 - n]["consume"] = monthBills[period + n]["SUM_ELEC"]
                            self._info[consNo]["history"][11 - n]["consume_bill"] = monthBills[period + n]["SUM_ELECBILL"]
                else:
                    _LOGGER.error(f"get_monthly_bill error: {result['msg']}")
                    ret = False
                    break
            else:
                _LOGGER.error(f"get_monthly_bill response status_code = {r.status_code}, params = {data}")
                ret = False
                break
        return ret

    async def get_daily_bills(self, consNo):
        headers = self.commonHeaders()
        data = {
            "consNo": consNo,
            "days": 30
        }
        ret = True
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
        else:
            ret = False
        return ret

    async def async_get_data(self):
        self._info = {}

        await self.async_get_token()
        await self.async_get_ConsNo()
        for consNo in self._info.keys():
            await self.async_get_detail(consNo)
            tasks = [
                self.aysnc_get_balance(consNo),
                self.get_monthly_bill(consNo),
                self.get_daily_bills(consNo)
            ]
            await asyncio.gather(*tasks)
            _LOGGER.debug(f"Data {self._info}")
        return self._info

