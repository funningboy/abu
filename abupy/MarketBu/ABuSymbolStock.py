# coding=utf-8
"""
    股票类型的symbol模块，台股
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os

import pandas as pd
import requests

from ..CoreBu.ABuFixes import six
from ..CoreBu.ABuBase import FreezeAttrMixin
from ..CoreBu import ABuEnv
from ..CoreBu.ABuEnv import EMarketTargetType, EMarketSubType
from ..UtilBu.ABuDTUtil import singleton
from ..UtilBu.ABuStrUtil import digit_str
from ..MarketBu.ABuSymbol import Symbol, code_to_symbol
from ..CrawlBu.ABuXqConsts import columns_map


__author__ = '阿布'
__weixin__ = 'abu_quant'

_rom_dir = ABuEnv.g_project_rom_data_dir
"""台股symbol，文件定期重新爬取，更新"""
_stock_code_tw = os.path.join(_rom_dir, 'stock_code_TW.csv')


class AbuStockBaseWrap(object):
    """做为类装饰器封装替换init 解析csv symbol数据操作，装饰替换init"""

    def __call__(self, cls):
        if isinstance(cls, six.class_types):
            # 只做为类装饰器使用，拿出原始的__init__
            init = cls.__init__

            def wrapped(*args, **kwargs):
                warp_self = args[0]
                warp_self.df = None

                init(*args, **kwargs)

                # 剔除重复数据
                warp_self.df.drop_duplicates(inplace=True)

                warp_self.df['industry_factorize'], industry_factorize_name = \
                    pd.factorize(warp_self.df.industry)
                # 用Series包装一下离散后的行业信息，以便方便对应行业索引
                warp_self.industry_factorize_name_series = pd.Series(industry_factorize_name)

                # 将映射中key和value进行互换，columns_map中中文的key和英文的value（详ABuXqConsts），即形成本地语言列名
                local_columns_map = {columns_map[col_key]: col_key for col_key in columns_map}
                # show_df中列名使用本地语言展示
                warp_self.show_df = warp_self.df.rename(columns=local_columns_map, inplace=False)
                # 冻结接口，只读
                # noinspection PyProtectedMember
                warp_self._freeze()

            # 使用wrapped替换初始的__init__
            cls.__init__ = wrapped
            wrapped.__name__ = '__init__'
            # 记录原始init的方法为deprecated_original
            wrapped.deprecated_original = init
            return cls
        else:
            raise TypeError('AbuStockBaseWrap just for class warp')


# noinspection PyUnresolvedReferences
class AbuSymbolStockBase(FreezeAttrMixin):
    """股票类型的symbol抽象基类"""

    def __str__(self):
        """打印对象显示：df.info， df.describe"""
        return 'info:\n{}\ndescribe:\n{}'.format(self.df.info(),
                                                 self.df.describe())

    __repr__ = __str__

    def __len__(self):
        """对象长度：df.shape[0]，即行数"""
        return self.df.shape[0]

    def __setitem__(self, key, value):
        """索引设置：对外抛出错误， 即不准许外部设置"""
        raise AttributeError("AbuFuturesCn set value!!!")

    def query_industry_symbols(self, query_symbol, local_df=True):
        """
        为ABuIndustries模块，提供查询股票所在的行业industry_df子集
        :param query_symbol: symbol str对象
        :param local_df: 是否基于show_df返回行业df
        :return: 查询query_symbol所在的行业对象，pd.DataFrame对象
        """
        industry_df = None
        # 使用in查询self，即子类都需要实现自己的__contains__
        if query_symbol in self:
            # 忽略一个问题，如果只使用000001不带子市场标识去查询，结果只取第一个，准确查询需要完整标示
            factorize = self[query_symbol]['industry_factorize'].values[0]
            # 参数local_df决定行业industry_df子集基于本地语言的show_df还是df，使用show_df更加方便外面查阅对应内容意义
            base_df = self.show_df if local_df else self.df
            # 切取行业factorize相同的子集
            industry_df = base_df[base_df['industry_factorize'] == factorize]
        return industry_df

    def query_industry_factorize(self, factorize, local_df=True):
        """
        为ABuIndustries模块，提行业的factorize值查询industry_df子集
        :param factorize: int
        :param local_df: 是否基于show_df返回行业df
        :return: 通过factorize值查询industry_df子集，pd.DataFrame对象
        """
        base_df = self.show_df if local_df else self.df
        # 切取行业factorize相同的子集
        industry_df = base_df[base_df['industry_factorize'] == factorize]
        return industry_df

    def all_symbol(self, index=False):
        """
        子类需要实现，获取市场中所有股票symbol str对象序列，即全市场symbol序列
        :param index: 是否需要返回大盘symbol
        :return: 全市场symbol序列
        """
        raise NotImplementedError('NotImplementedError AbuSymbolStockBase all_symbol!!!')

    def query_symbol_sub_market(self, *args, **kwargs):
        """
        子类需要实现，查询股票所在的子市场，即交易所信息
        :return: 返回EMarketSubType.value值，即子市场（交易所）字符串对象
        """
        raise NotImplementedError('NotImplementedError AbuSymbolStockBase query_symbol_sub_market!!!')

    def symbol_func(self, df):
        """
        子类需要实现，通过df组装支持ABuSymbolPd.make_kl_df使用的symbol
        :param df: pd.DataFrame对象
        :return: 支持ABuSymbolPd.make_kl_df使用的symbol序列
        """
        raise NotImplementedError('NotImplementedError AbuSymbolStockBase symbol_func!!!')


@singleton
@AbuStockBaseWrap()
class AbuSymbolTW(AbuSymbolStockBase):
    """台股symbol类，singleton"""

    # TODO
    def __init__(self):
        """被AbuStockBaseWrap替换__init__，即只需读取美股数据到self.df 后续在类装饰器完成"""
       
    def __contains__(self, item):
        """成员测试：是否item在self.df.symbol.values中"""
        return digit_str(item) in self.df.symbol.values

    def __getitem__(self, key):
        """
            索引获取：两种模式索引获取：
            1. 参数key为df的columns名称，返回self.df[key]，即get df的列
            2. 参数key为股票代码名称，标准化后查询，self.df[self.df.symbol == key]，即get df的行
        """

        # 参数key为df的columns名称，返回self.df[key]
        if key in self.df.columns:
            return self.df[key]

        # 参数key为股票代码名称，标准化后查询
        ds = digit_str(key)
        if ds in self.df.symbol.values:
            return self.df[self.df.symbol == ds]

    def symbol_func(self, df):
        """
        通过df组装支持ABuSymbolPd.make_kl_df使用的symbol，使用(df['symbol']).tolist()
        :param df: pd.DataFrame对象
        :return: 支持ABuSymbolPd.make_kl_df使用的symbol序列
        """
        # noinspection PyUnresolvedReferences
        return (df['symbol']).tolist()

    def all_symbol(self, index=False):
        """
        获取美股市场中所有股票symbol str对象序列，即美股全市场symbol序列
        :param index: 是否需要返回美股大盘symbol
        :return: 美股全市场symbol序列
        """

        # TWSE,TPEX
        df_filter = self.df[(self.df['exchange'].str.upper() == EMarketSubType.TW_TWSE.value) |
                            (self.df['exchange'].str.upper() == EMarketSubType.TW_TPEX.value)]
        # 通过symbol_func转换为外部可直接使用ABuSymbolPd.make_kl_df请求的symbol序列
        all_symbol = self.symbol_func(df_filter)
        all_symbol = list(set(all_symbol))
        #if index:
        #    # 需要返回大盘symbol
        #    all_symbol.extend(['{}{}'.format(EMarketTargetType.E_MARKET_TARGET_TW.value, symbol)
        #                       for symbol in Symbol.TW_INDEX])
        return all_symbol

    def query_symbol_sub_market(self, code, default=EMarketSubType.TW_TWSE.value):
        """
        查询股票所在的子市场，即交易所信息, 台股市场默认返回TWSE
        :return: 返回EMarketSubType.value值，即子市场（交易所）字符串对象
        """
        return default


def query_stock_info(symbol):
    """
    通过将symbol code转换为Symbol对象查询对应的市场，构造对应的市场对象，
    仅支持股票类型symbol
    :param symbol: eg：2330
    :return: 一行数据的pd.DataFrame对象
    """
    if isinstance(symbol, six.string_types):
        symbol = code_to_symbol(symbol)

    
    if symbol.is_tw_stock():
        sn = AbuSymbolTW()
    else:
        print('query_symbol_info just suit tw!')
        return
    # 直接使用类的__getitem__方法
    return sn[symbol.symbol_code]
