# coding=utf-8
"""
    内置数据源示例实现模块：

    所有数据接口仅供学习使用，以及最基本使用测试，如需进一步使用，请购买数据
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import os

import random
import math
import sqlite3 as sqlite
import requests
import pandas as pd

from ..CoreBu.ABuEnv import EMarketTargetType, EMarketSubType
from ..CoreBu import ABuEnv
from ..MarketBu import ABuNetWork
from ..MarketBu.ABuDataBase import StockBaseMarket, SupportMixin, FuturesBaseMarket, TCBaseMarket
from ..MarketBu.ABuDataParser import TXParser
from ..MarketBu.ABuDataParser import SINOPACParser, FINMINDParser
from ..UtilBu import ABuStrUtil, ABuDateUtil, ABuMd5
from ..UtilBu.ABuDTUtil import catch_error
from ..CoreBu.ABuDeprecated import AbuDeprecated
# noinspection PyUnresolvedReferences
from ..CoreBu.ABuFixes import xrange, range, filter

import shioaji as sj

"""网络请求（连接10秒，接收60秒）超时时间"""
K_TIME_OUT = (10, 60)


def random_from_list(array):
    """从参数array中随机取一个元素"""
    # 在array长度短的情况下，测试比np.random.choice效率要高
    return array[random.randrange(0, len(array))]


@AbuDeprecated('only read old symbol db, miss update!!!')
def query_symbol_sub_market(symbol):
    path = TXApi.K_SYMBOLS_DB
    conn = sqlite.connect(path)
    cur = conn.cursor()
    symbol = symbol.lower()
    query = "select {} from {} where {} like \'{}.%\'".format(TXApi.K_DB_TABLE_SN, TXApi.K_DB_TABLE_NAME,
                                                              TXApi.K_DB_TABLE_SN, symbol)
    cur.execute(query)
    results = cur.fetchall()
    conn.close()
    sub_market = ''
    if results is not None and len(results) > 0:
        try:
            if results[0][0].find('.') > 0:
                sub_market = '.' + results[0][0].split('.')[1].upper()
        except:
            logging.info(results)
    return sub_market


@catch_error(return_val=None, log=False)
def query_symbol_from_pinyin(pinyin):
    """通过拼音对symbol进行模糊查询"""
    path = TXApi.K_SYMBOLS_DB
    conn = sqlite.connect(path)
    cur = conn.cursor()
    pinyin = pinyin.lower()
    query = "select stockCode from {} where pinyin=\'{}\'".format(TXApi.K_DB_TABLE_NAME, pinyin)
    cur.execute(query)
    results = cur.fetchall()
    conn.close()
    if len(results) > 0:
        code = results[0][0]
        # 查询到的stcok code eg：sh111111，usabcd.n
        start = 2
        end = len(code)
        if '.' in code:
            # 如果是美股要截取.
            end = code.find('.')
        return code[start:end]




class TXApi(StockBaseMarket, SupportMixin):
    """tx数据源，支持港股，美股，a股"""

    K_NET_BASE = "http://ifzq.gtimg.cn/appstock/app/%sfqkline/get?p=1&param=%s,day,,,%d," \
                 "qfq&_appName=android&_dev=%s&_devId=%s&_mid=%s&_md5mid=%s&_appver=4.2.2&_ifChId=303&_screenW=%d" \
                 "&_screenH=%d&_osVer=%s&_uin=10000&_wxuin=20000&__random_suffix=%d"

    K_NET_HK_MNY = 'http://proxy.finance.qq.com/ifzqgtimg/stock/corp/hkmoney/sumary?' \
                   'symbol=%s&type=sum&jianjie=1&_appName=android' \
                   '&_dev=%s&_devId=%s&_mid=%s&_md5mid=%s&_appver=5.5.0&_ifChId=277' \
                   '&_screenW=%d&_screenH=%d&_osVer=%s&_uin=10000&_wxuin=20000&_net=WIFI&__random_suffix=%d'

    K_DB_TABLE_NAME = "values_table"
    K_DB_TABLE_SN = "stockCode"
    p_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))
    K_SYMBOLS_DB = os.path.join(p_dir, 'RomDataBu/symbols_db.db')

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(TXApi, self).__init__(symbol)
        # 设置数据源解析对象类
        self.data_parser_cls = TXParser

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        cuid = ABuStrUtil.create_random_with_num_low(40)
        cuid_md5 = ABuMd5.md5_from_binary(cuid)
        random_suffix = ABuStrUtil.create_random_with_num(5)
        dev_mod = random_from_list(StockBaseMarket.K_DEV_MODE_LIST)
        os_ver = random_from_list(StockBaseMarket.K_OS_VERSION_LIST)
        screen = random_from_list(StockBaseMarket.K_PHONE_SCREEN)

        days = ABuEnv.g_market_trade_year * n_folds + 1
        # start 不为空时计算 获取天数，获取的数据肯定比预期的数据多，因为同一时间内，交易日的天数一定不比实际的天数多
        if start:
            temp_end = ABuDateUtil.current_str_date()
            days = ABuDateUtil.diff(start, temp_end, check_order=False)

        sub_market = None
        if self._symbol.market == EMarketTargetType.E_MARKET_TARGET_US:
            # sub_market = self.query_symbol_sub_market(self._symbol.value)
            market = self._symbol.market.value
            if '.' in self._symbol.value:
                # 如果已经有.了说明是大盘，大盘不需要子市场，eg：us.IXIC
                sub_market = ''
            else:
                # 这里tx的source不支持US_PINK, US_OTC, US_PREIPO
                sub_market_map = {EMarketSubType.US_N.value: 'n',

                                  EMarketSubType.US_PINK.value: 'n',
                                  EMarketSubType.US_OTC.value: 'n',
                                  EMarketSubType.US_PREIPO.value: 'n',
                                  EMarketSubType.US_AMEX.value: 'n',

                                  EMarketSubType.US_OQ.value: 'oq'}
                sub_market = '.{}'.format(sub_market_map[self._symbol.sub_market.value])
            url = TXApi.K_NET_BASE % (
                market, self._symbol.value + sub_market, days,
                dev_mod, cuid, cuid, cuid_md5, screen[0], screen[1], os_ver, int(random_suffix, 10))
        elif self._symbol.market == EMarketTargetType.E_MARKET_TARGET_HK:
            market = self._symbol.market.value
            url = TXApi.K_NET_BASE % (
                market, self._symbol.value, days,
                dev_mod, cuid, cuid, cuid_md5, screen[0], screen[1], os_ver, int(random_suffix, 10))
        else:
            market = ''
            url = TXApi.K_NET_BASE % (
                market, self._symbol.value, days,
                dev_mod, cuid, cuid, cuid_md5, screen[0], screen[1], os_ver, int(random_suffix, 10))

        data = ABuNetWork.get(url, timeout=K_TIME_OUT)
        if data is not None:
            kl_pd = self.data_parser_cls(self._symbol, sub_market, data.json()).df
        else:
            return None

        return StockBaseMarket._fix_kline_pd(kl_pd, n_folds, start, end)

    def hkmoney(self):
        """港股概要信息接口"""
        if self._symbol.market != EMarketTargetType.E_MARKET_TARGET_HK:
            raise TypeError('hkmoney only support hk!!')

        cuid = ABuStrUtil.create_random_with_num_low(40)
        cuid_md5 = ABuMd5.md5_from_binary(cuid)
        random_suffix = ABuStrUtil.create_random_with_num(5)
        dev_mod = random_from_list(StockBaseMarket.K_DEV_MODE_LIST)
        os_ver = random_from_list(StockBaseMarket.K_OS_VERSION_LIST)
        screen = random_from_list(StockBaseMarket.K_PHONE_SCREEN)

        url = TXApi.K_NET_HK_MNY % (self._symbol.value, dev_mod, cuid, cuid, cuid_md5, screen[0], screen[1], os_ver,
                                    int(random_suffix, 10))
        return ABuNetWork.get(url, timeout=K_TIME_OUT)

    def minute(self, n_fold=5, *args, **kwargs):
        """分钟k线接口"""
        raise NotImplementedError('TXApi minute NotImplementedError!')



class FINMINDApi(StockBaseMarket, SupportMixin):
    """finmindtrader 数据源，支持台股"""

    LOGIN_URL = "https://api.finmindtrade.com/api/v4/login"
    URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(FINMINDApi, self).__init__(symbol)
        self.token = ''
        #self.connect()

        # 设置数据源解析对象类
        self.data_parser_cls = FINMINDParser

    def connect(self):
        try:
            userid = EFINDMINDGateWay.E_FINDMIND_USERID
            password = EFINDMINDGateWay.E_FINDMIND_PASSWORD
            parameter = {
                "user_id": userid,
                "password": password,
            }
            resp = requests.post(FINMINDApi.LOGIN_URL, data=parameter)
            data = resp.json()
            self.token = data['token']
        except Exception as exc:
            logging.info(u'FinMind GateWay 登入失敗')
            return
        logging.info(u'FinMind GateWay 登入成功')
        # wait while for connect
        sleep(2.0)

    def _support_market(self):
        """声明数据源支持台股"""
        return [EMarketTargetType.E_MARKET_TARGET_TW]

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口"""
        temp_end = ABuDateUtil.current_str_date()
        temp_start = ABuDateUtil.begin_date(n_folds*365, temp_end)
        if start != None:
            temp_start = start
        if end != None:
            temp_end = end

        parameter = {
            "dataset": "TaiwanStockPrice",
            "data_id": self._symbol.value,
            "start_date": temp_start,
            "end_date": temp_end,
            "token": '',
        }
        resp = requests.get(FINMINDApi.URL, params=parameter)
        if resp is not None:
            kl_pd = self.data_parser_cls(self._symbol, resp.json()).df
        else:
            return None
        return StockBaseMarket._fix_kline_pd(kl_pd, n_folds, start, end)

    def minute(self, n_fold=5, *args, **kwargs):
        """分钟k线接口"""
        raise NotImplementedError('FINMINDApi minute NotImplementedError!')


class SINOPACApi(StockBaseMarket, SupportMixin):
    """sinopac 数据源，支持台股"""

    def __init__(self, symbol):
        """
        :param symbol: Symbol类型对象
        """
        super(SINOPACApi, self).__init__(symbol)
        self.api = sj.Shioaji()
        self.connect()

        try:
            self.contract = self.api.Contracts.Stocks(symbol)
        except Exception as exc:
            logging.info(u'Sinopac contract not found {}'.format(symbol))
        # 设置数据源解析对象类
        self.data_parser_cls = SINOPACParser

    def connect(self):
        try:
            userid = ESINOPACGateWay.E_SINOPAC_USERID
            password = ESINOPACGateWay.E_SINOPAC_PASSWORD
            selt.api.login(userid, password)
        except Exception as exc:
            logging.info(u'Sinopac GateWay 登入失敗')
            return
        logging.info(u'Sinopac GateWay 登入成功')
        # wait while for connect
        sleep(2.0)

    def _support_market(self):
        """声明数据源支持台股"""
        return [EMarketTargetType.E_MARKET_TARGET_TW]

    def kline(self, n_folds=2, start=None, end=None):
        """日k线接口 高頻交易"""
        # TODO: no daily kline, it's 1Minute kine
        raise NotImplementedError('SINOPACApi kline NotImplementedError!')

        temp_end = ABuDateUtil.current_str_date()
        temp_start = ABuDateUtil.begin_date(n_folds*365, temp_end)
        if start != None:
            temp_start = start
        if end != None:
            temp_end = end
        kbars = api.kbars(self.connect, start=temp_start, end=temp_end)
        kl_pd = self.data_parser_cls(self._symbol, pd.DataFrame({**kbars}).to_josn()).df
        if kl_pd is None:
            return None
        return StockBaseMarket._fix_kline_pd(kl_pd, n_folds, start, end)

    def minute(self, n_fold=5, *args, **kwargs):
        """分钟k线接口"""
        raise NotImplementedError('SINOPACApi minute NotImplementedError!')

