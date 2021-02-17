

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from bs4 import BeautifulSoup 
from string import Template
from datetime import date

import scrapy
import re


# scrapy
from ABuFubon.items import StockHisDataItem, SpiderErrItem
from ABuFubon.pipelines import StockHisDataPipeline, SpiderErrPipeline

from abupy.MarketBu.ABuMarket import all_symbol 
from abupy.UtilBu.ABuDateUtil import str_to_datetime


class StockHisDataSpider(scrapy.Spider):
    name = "StockHisDataSpider"
    allowed_domains = ['fubon-ebrokerdj.fbs.com.tw']

    # set post pipeline map table
    pipeline = set([
        SpiderErrPipeline,      # high prio
        StockHisDataPipeline    
    ])

    #ex: http://fubon-ebrokerdj.fbs.com.tw/Z/ZC/ZCX/ZCX_2330.djhtm
    URLStr = Template('http://fubon-ebrokerdj.fbs.com.tw/Z/ZC/ZCX/ZCX_$SYMBOL.djhtm')
    reDate = re.compile(r".*\:([0-9]*)\/([0-9]*)", re.DOTALL | re.MULTILINE) # MM/DD
    OHLCV_IDX = {
        'O': 0, # index to value map
        'H': 1,
        'L': 2,
        'C': 3,
        'V': 11
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.symbols = all_symbol()
        
    def start_requests(self):
        for symbol in self.symbols:
            url = self.URLStr.substitute({'SYMBOL': symbol})
            yield scrapy.Request(url=url, callback=self.parse, cb_kwargs={'symbol': symbol})

    def parse(self, response, symbol):
        to_float = lambda x: float(str(x.text).replace(',','').replace('%', '').replace(' ',''))
        to_str   = lambda x: str(x.text).replace(' ', '')
        try:
            text = response.body
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find_all('table', {'class': 't01'})[1]
            values = list(map(to_float, table.find_all('td', {'class': 't3n1'})))
            cdate = list(map(to_str, table.find_all('div', {'class': 't11'})))[0]
            grps = self.reDate.match(cdate).groups()
            mm, dd = grps[0], grps[1]
            yy = date.today().isoformat().split("-")[0] 
            cdate = "{0}-{1}-{2}".format(yy, mm, dd)
        except Exception as e:
            yy, mm, dd = date.today().isoformat().split("-")[0:3] 
            cdate = "{0}-{1}-{2}".format(yy, mm, dd)
            ERR = {
                'date': str_to_datetime(cdate),
                'cls': self.name,
                'msg': "symbol:{0}, fetch html.table Error".format(symbol)
            }
            item = SpiderErrItem({'obj': ERR, 'pipeline': SpiderErrPipeline})
            self.logger.exception("[SPIDER] parser ABuFubon.StockHisDataSpider symbol:{0} Error:{1}".format(symbol, e))
            yield(item)
            return    

        OHLCV = {}
        for k,v in self.OHLCV_IDX.items():
            OHLCV[k] = values[self.OHLCV_IDX[k]]

        OHLCV.update({
            'date': str_to_datetime(cdate),
            'symbol': symbol
        }) 
        item = StockHisDataItem({'obj': OHLCV, 'pipeline': StockHisDataPipeline})
        self.logger.debug("[SPIDER] pass ABuFubon.StockHisDataSpider symbol:{0} H:{1}".format(symbol, OHLCV['H']))
        yield(item)


