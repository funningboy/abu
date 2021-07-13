

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from bs4 import BeautifulSoup 
from string import Template
from datetime import date
import json

import scrapy
import re
import urllib

# scrapy
from ABuFubon.items import StockHisDataItem, SpiderErrItem
from ABuFubon.pipelines import StockHisDataPipeline, SpiderErrPipeline

from abupy.MarketBu import ABuMarket  
from abupy.UtilBu import ABuDateUtil 
from abupy.CoreBu import ABuEnv

class StockHisDataSpider2(scrapy.Spider):
    name = "StockHisDataSpider2"
    allowed_domains = ['https://api.finmindtrade.com']

    # set post pipeline map table
    pipeline = set([
        SpiderErrPipeline,      # high prio
        StockHisDataPipeline    
    ])

    URLStr = "https://api.finmindtrade.com/api/v4/data"
    parameter = {
        "dataset": "TaiwanStockPrice",
        "data_id": "2330",
        "start_date": "2020-12-01",
        "end_date": "2021-02-25",
        "token": "", # 參考登入，獲取金鑰
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.symbols = ABuMarket.all_symbol()
        self.cdateiso = ABuEnv.g_cdataiso 
        self.ddateiso = ABuEnv.g_ddateiso

        
    def start_requests(self):
        for symbol in self.symbols:
            self.parameter.update({'data_id': symbol, 'start_date': self.cdateiso, 'end_date': self.ddateiso})
            url = "{0}?{1}".format(self.URLStr, urllib.parse.urlencode(self.parameter))
            yield scrapy.Request(url=url, callback=self.parse, cb_kwargs={'symbol': symbol})

    def parse(self, response, symbol):
        text = json.loads(response.text)
        if text['msg'] != 'success':
            return

        to_float = lambda x: float(str(x))
        H = None
        for it in text['data']:
            OHLCV = {
                'date': ABuDateUtil.str_to_datetime(it['date']),
                'symbol': it['stock_id'],
                'O': to_float(it['open']),
                'H': to_float(it['max']),
                'L': to_float(it['min']),
                'C': to_float(it['close']),
                'V': to_float(it['Trading_Volume'])
            }
            H = OHLCV['H']
            item = StockHisDataItem({'obj': OHLCV, 'pipeline': StockHisDataPipeline})
            yield(item)

        self.logger.debug("[SPIDER] pass ABuFubon.StockHisDataSpider2 symbol:{0} H:{1}".format(symbol, H))



