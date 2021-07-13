# coding=utf-8
"""
    symbol模块
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from fnmatch import fnmatch

import numpy as np

from ..CoreBu.ABuEnv import EMarketTargetType, EMarketSubType
from ..CoreBu.ABuFixes import six
from ..UtilBu.ABuStrUtil import to_unicode
from ..UtilBu.ABuLazyUtil import LazyFunc


# noinspection PyProtectedMember
def code_to_symbol(code, rs=True):
    """
    解析code成Symbol,如果code中带有市场编码直接用该市场，否则进行查询所属市场信息，
    如果最后也没有发现symbol所在的市场，会向外raise ValueError
    :param code: str对象，代码 如：300104，sz300104，usTSLA
    :param rs: 没有匹配上是否对外抛异常，默认True
    :return: Symbol对象
    """
    #from ..MarketBu.ABuSymbolFutures import AbuFuturesCn, AbuFuturesGB
    from ..MarketBu.ABuSymbolStock import AbuSymbolTW
    from ..MarketBu.ABuMarket import all_symbol

    if isinstance(code, Symbol):
        # code本身时symbol对象直接返回
        return code
    if not isinstance(code, six.string_types):
        # code必须是string_types
        raise TypeError('code must be string_types!!!，{} : type is {}'.format(code, type(code)))

    sub_market = None
    market = None

    if code.isdigit():
        if len(code) == 4:
            # 4位全数字，匹配查询台股子市场
            market = EMarketTargetType.E_MARKET_TARGET_TW
            sub_market = EMarketSubType(AbuSymbolTW().query_symbol_sub_market(code))
            return Symbol(market, sub_market, code)

    if rs:
        raise ValueError('arg code :{} format dt support'.format(code))


def __search(market_df, search_match, search_code, search_result, match_key='co_name'):
    """具体搜索执行接口"""

    def __search_whole_code(_match_code):
        _sc_df = market_df[market_df.symbol == _match_code]
        if not _sc_df.empty:
            search_result[_sc_df.symbol.values[0]] = _sc_df[match_key].values[0]
            return True
        return False

    def __search_pinyin_code(_match_code):
        from ..MarketBu.ABuDataFeed import query_symbol_from_pinyin
        # 使用query_symbol_from_pinyin对模糊拼音进行查询
        pinyin_symbol = query_symbol_from_pinyin(_match_code)
        if pinyin_symbol is not None:
            # 需要把拼音code标准化为可查询的code
            search_symbol = code_to_symbol(pinyin_symbol, rs=False)
            if search_symbol is not None:
                _search_code = search_symbol.symbol_code
                sc_df = market_df[market_df.symbol == _search_code]
                if not sc_df.empty:
                    search_result[sc_df.symbol.values[0]] = sc_df[match_key].values[0]

    def __search_fnmatch_info(_search_match):
        # 模糊匹配公司名称信息或者交易产品信息
        mc_df = market_df[market_df[match_key].apply(lambda name:
                                                     fnmatch(to_unicode(name),
                                                             _search_match))]
        if not mc_df.empty:
            for ind in np.arange(0, len(mc_df)):
                mcs = mc_df.iloc[ind]
                search_result[mcs.symbol] = mcs[match_key]

    # 首先全匹配search_code
    if not __search_whole_code(search_code):
        # 如果search_code没有能全匹配成功，使用拼音进行匹配一次
        __search_pinyin_code(search_code)
    # 模糊匹配公司名称或者产品等信息symbol
    __search_fnmatch_info(search_match)


def _tw_search(search_match, search_code, search_result):
    """台股市场symbol关键字搜索"""
    from ..MarketBu.ABuSymbolStock import AbuSymbolTW
    __search(AbuSymbolTW().df, search_match, search_code, search_result)


def search_to_symbol_dict(search, fast_mode=False):
    """
    symbol搜索对外接口，全匹配symbol code，拼音匹配symbol，别名匹配，模糊匹配公司名称，产品名称等信息
    eg：
        in：
        search_to_symbol_dict('黄金')
        out：
        {'002155': '湖南黄金',
         '600489': '中金黄金',
         '600547': '山东黄金',
         '600766': '园城黄金',
         '600988': '赤峰黄金',
         'ABX': '巴里克黄金',
         'AU0': '黄金',
         'DGL': '黄金基金-PowerShares',
         'DGLD': '黄金3X做空-VelocityShares',
         'DGP': '黄金2X做多-DB',
         'DGZ': '黄金做空-PowerShares',
         'DZZ': '黄金2X做空-DB',
         'EGO': '埃尔拉多黄金公司',
         'GC': '纽约黄金',
         'GEUR': 'Gartman欧元黄金ETF-AdvisorShares ',
         'GLD': '黄金ETF-SPDR',
         'GLL': '黄金2X做空-ProShares',
         'GYEN': 'Gartman日元黄金ETF-AdvisorShares',
         'HMY': '哈莫尼黄金',
         'IAU': '黄金ETF-iShares',
         'KGC': '金罗斯黄金',
         'LIHR': '利希尔黄金',
         'PRME': '全球黄金地段房地产ETF-First Trust Heitman',
         'RGLD': '皇家黄金',
         'UGL': '黄金2x做多-ProShares',
         'UGLD': '黄金3X做多-VelocityShares'}
    :param search: eg：'黄金'， '58'
    :param fast_mode: 是否尽快匹配，速度优先模式
    :return: symbol dict
    """
    search_symbol_dict = {}
    search = search.lower()
    while len(search_symbol_dict) == 0 and len(search) > 0:
        # 构建模糊匹配进行匹配带通配符的字符串
        search_match = u'*{}*'.format(search)
        # 构建精确匹配或拼音模糊匹配的symbol
        search_symbol = code_to_symbol(search, rs=False)
        search_code = ''
        if search_symbol is not None:
            search_code = search_symbol.symbol_code
        # 对search的内容进行递减匹配
        search = search[:-1]
        # 依次对各个市场进行搜索匹配操作
        _tw_search(search_match, search_code, search_symbol_dict)
        if fast_mode:
            break
    return search_symbol_dict


class Symbol(object):
    """统一所有市场的symbol，统一对外接口对象"""

    # 定义使用的台股大盘
    TW_INDEX = ['.TWSE', '.TPEX']

    def __init__(self, market, sub_market, symbol_code):
        """
        :param market: EMarketTargetType enum对象
        :param sub_market: EMarketSubType enum对象
        :param symbol_code: str对象，不包含市场信息的code
        """
        if isinstance(market, EMarketTargetType) and isinstance(sub_market, EMarketSubType):
            self.market = market
            self.sub_market = sub_market
            self.symbol_code = symbol_code
            self.source = None
        else:
            raise TypeError('market type error')

    def __str__(self):
        """打印对象显示：market， sub_market， symbol_code"""
        return '{}_{}:{}'.format(self.market.value, self.sub_market.value, self.symbol_code)

    __repr__ = __str__

    def __len__(self):
        """对象长度：拼接市场＋子市场＋code的字符串长度"""
        m_symbol = '{}_{}:{}'.format(self.market.value, self.sub_market.value, self.symbol_code)
        return len(m_symbol)

    @LazyFunc
    def value(self):
        # 其它市场直接返回symbol_code
        return self.symbol_code

    def is_tw_stock(self):
        """判定是否台股 symbol"""
        return self.market == EMarketTargetType.E_MARKET_TARGET_TW

    def is_tw_twse_stock(self):
        """判定是否台股 TWSE 交易所 symbol"""
        return self.sub_market == EMarketSubType.TW_TWSE

    def is_tw_tpex_stock(self):
        """判定是否台股 TPEX 交易所 symbol"""
        return self.sub_market == EMarketSubType.TW_TPEX

    def is_tw_index(self):
        """判定是否美股 大盘"""
        return self.is_tw_stock() and self.symbol_code in Symbol.TW_INDEX

    def is_futures(self):
        """判定是否期货symbol"""
        return False


class IndexSymbol(object):
    """定义IndexSymbol类，设定大盘指数Symbol对象的规范"""

    # 台股大盘TWSE Symbol对象
    TWSE = Symbol(EMarketTargetType.E_MARKET_TARGET_TW, EMarketSubType.TW_TWSE, '.TWSE')
    # 美股大盘IXIC Symbol对象
    TPEX = Symbol(EMarketTargetType.E_MARKET_TARGET_TW, EMarketSubType.TW_TPEX, '.TPEX')
 
