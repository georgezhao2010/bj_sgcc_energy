import requests
import logging
import datetime
from .const import PGC_PRICE

_LOGGER = logging.getLogger(__name__)

AUTH_URL = "http://weixin.bj.sgcc.com.cn/ott/app/auth/authorize?target=M_YECX"
CONSNO_URL = "http://weixin.bj.sgcc.com.cn/ott/app/follower/consumer/prepaid/list"
REMAIN_URL = "http://weixin.bj.sgcc.com.cn/ott/app/elec/account/query"
DETAIL_URL = "http://weixin.bj.sgcc.com.cn/ott/app/electric/bill/overview"
BILLINFO_URL = "http://weixin.bj.sgcc.com.cn/ott/app/electric/bill/queryElecBillInfoEveryYear"

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
    def __init__(self, openid):
        self._openid = openid
        self._session = "e7d569dc-0806-4b30-9379-169ccf33e92a"
        self._info = {}

    def getToken(self):
        headers = {
            "Host": "weixin.bj.sgcc.com.cn",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Cookie": f"SESSION={self._session}; user_openid={self._openid}",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 "
                          "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.7(0x1800072c) "
                          "NetType/WIFI Language/zh_CN",
            "Accept-Language": "zh-cn",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        ret = True
        try:
            r = requests.get(AUTH_URL, headers=headers, allow_redirects=False, timeout=10)
            if r.status_code == 200 or r.status_code == 302:
                response_headers = r.headers
                if "Set-Cookie" in response_headers:
                    set_cookie = response_headers["Set-Cookie"]
                    self._session = set_cookie.split(";")[0].split("=")[1]
                    _LOGGER.debug(f"Got new session {self._session}")
            else:
                ret = False
                _LOGGER.error(f"getToken response status_code = {r.status_code}")
        except Exception as e:
            ret = False
            _LOGGER.error(f"getToken response got error: {e}")
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
            "Cookie": f"SESSION={self._session}; user_openid={self._openid}"
        }
        return headers

    def getConsNo(self):
        headers = self.commonHeaders()
        ret = True
        try:
            r = requests.post(CONSNO_URL, headers=headers, timeout=10)
            if r.status_code == 200:
                result = r.json()
                if result["status"] == 0:
                    data = result["data"]
                    for single in data:
                        consNo = single["consNo"]
                        if consNo not in self._info:
                            _LOGGER.debug(f"Got ConsNo {consNo}")
                            self._info[consNo] = {}
                else:
                    ret = False
                    _LOGGER.error(f"getConsNo error: {result['msg']}")
            else:
                ret = False
                _LOGGER.error(f"getConsNo response status_code = {r.status_code}")

        except Exception as e:
            _LOGGER.error(f"getConsNo response got error: {e}")
            ret = False
        return ret

    def getBalance(self, consNo):
        headers = self.commonHeaders()
        data = {
            "consNo": consNo
        }
        ret = True
        try:
            r = requests.post(REMAIN_URL, data, headers=headers, timeout=10)
            if r.status_code == 200:
                _LOGGER.debug(f"getBalance response: {r.text}")
                result = r.json()
                if result["status"] == 0:
                    self._info[consNo]["balance"] = result["data"]["BALANCE_SHEET"]
                    self._info[consNo]["last_update"] = result["data"]["AS_TIME"]
                else:
                    ret = False
                    _LOGGER.error(f"getBalance error:{result['msg']}")
            else:
                ret = False
                _LOGGER.error(f"getBalance response status_code = {r.status_code}")
        except Exception as e:
            ret = False
            _LOGGER.error(f"getBalance response got error: {e}")
        return ret

    def getDetail(self, consNo):
        headers = self.commonHeaders()
        params = {
            "consNo": consNo
        }
        ret = True
        try:
            r = requests.get(DETAIL_URL, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                _LOGGER.debug(f"getDetail response: {r.text}")
                result = r.json()
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
                    _LOGGER.error(f"getDetail error: {result['msg']}")
            else:
                ret = False
                _LOGGER.error(f"getDetail response status_code = {r.status_code}")
        except Exception as e:
            ret = False
            _LOGGER.error(f"getDetail response got error: {e}")
        return ret

    def getBillByYear(self, consNo):
        headers = self.commonHeaders()
        cur_year = self._info[consNo]["year"]
        period = 12
        try:
            for i in range(2):
                year = cur_year - i
                params = f"consNo={consNo}&currentYear={year}&isFlag=1"
                r = requests.post(BILLINFO_URL, headers=headers, data=params, timeout=10)
                if r.status_code == 200:
                    _LOGGER.debug(f"getBillByYear {params} response: {r.text}")
                    result = r.json()
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
                        _LOGGER.error(f"getBillByYear error: {result['msg']}")
                else:
                    _LOGGER.error(f"getBillByYear response status_code = {r.status_code}, params = {params}")
        except:
            pass

    def getData(self):
        if self.getToken() and self.getConsNo():
            for consNo in self._info.keys():
                self.getBalance(consNo)
                self.getDetail(consNo)
                self.getBillByYear(consNo)
            _LOGGER.debug(f"Data {self._info}")
        return self._info
