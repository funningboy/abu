from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from bs4 import BeautifulSoup 
from string import Template
from datetime import date, timedelta

import scrapy
import re

# scrapy
from ABuFubon.items import StockMarginDataItem, SpiderErrItem
from ABuFubon.pipelines import StockHisMarginPipeline, SpiderErrPipeline

from abupy.MarketBu.ABuMarket import all_symbol
#from abupy.MarketBu.ABuMarket import all_trader
from abupy.UtilBu.ABuDateUtil import str_to_datetime, twtime_to_utc_str
from abupy.CoreBu.ABuEnv import g_cdataiso, g_ddateiso


class StockHisMarginSpider(scrapy.Spider):
    name = "StockHisMarginSpider"
    allowed_domains = ['fubon-ebrokerdj.fbs.com.tw']

    # set post pipeline map table
    pipeline = set([
        SpiderErrPipeline,      # high prio
        StockHisMarginPipeline
    ])

    #ex: http://fubon-ebrokerdj.fbs.com.tw/z/zc/zcn/zcn.djhtm?a=2330&c=2021-2-1&d=2021-2-2
    URLStr = Template('http://fubon-ebrokerdj.fbs.com.tw/z/zc/zcn/zcn.djhtm?a=$SYMBOL&c=$CDATE&d=$DDATE')
    reDate = re.compile(r".*([0-9]*)\/([0-9]*)\/([0-9]*)", re.DOTALL | re.MULTILINE) # YY/MM/DD
    #reUnit = re.compile(r".*單位：張.*", re.DOTALL | re.MULTILINE)
    #reUint = #股/張 1張=1000股

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.symbols = all_symbol()
        self.cdateiso = g_cdataiso
        self.ddateiso = g_ddateiso

    def start_requests(self):
        cdate = '-'.join(map(lambda x: str(int(x)), self.cdateiso.split("-")))
        ddate = '-'.join(map(lambda x: str(int(x)), self.ddateiso.split("-")))
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/48.0'}
        for symbol in self.symbols:
            url = self.URLStr.substitute({'SYMBOL': symbol, 'CDATE': cdate, 'DDATE': ddate})
            yield scrapy.Request(url=url, headers=headers, callback=self.parse, cb_kwargs={'symbol': symbol})

    def parse(self, response, symbol):
        to_float = lambda x: float(str(x.text).replace(',','').replace('%', '').replace(' ',''))
        to_str   = lambda x: str(x.text).replace(' ', '')
        try:
            text = response.body
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find_all('table', {'class': 't01'})[0]
            values = list(map(to_float, table.find_all('td', {'class': 't3n1'})))
            cdates = list(map(to_str, table.find_all('td', {'class': 't3n0'})))
            # DateUtil
            yy, mm, dd = cdates[1].split('/') # cdata[0] is new line
            cdate = twtime_to_utc_str(yy, mm, dd)
        except Exception as e:
            yy, mm, dd = date.today().isoformat().split("-")[0:3] 
            cdate = "{0}-{1}-{2}".format(yy, mm, dd)
            ERR = {
                'date': str_to_datetime(cdate),
                'cls': self.name,
                'msg': "symbol:{0}, fetch html.table Error".format(symbol)
            }
            item = SpiderErrItem({'obj': ERR, 'pipeline': SpiderErrPipeline})
            self.logger.exception("[SPIDER] parser ABuFubon.StockHisMarginSpider symbol:{0} Error:{1}".format(symbol, e))
            yield(item)
            return   


        # update latest one
        MarginItem = {
            'date': str_to_datetime(cdate),
            'MagPurchBuy': values[0],     #融資 買進 
            'MagPurchSell': values[1], #融資 賣出 
            'MagPurchCashRepay': values[2], # 融資 現償
            'MagPurchBalance': values[3], #融資 餘額
            # values[4], 融資 增減   
            'MagPurchLimit': values[5], #融資 限額
            'MagPurchRatio': values[6], #融資 使用率
            'ShortSaleSell': values[7], #融券 賣出  
            'ShortSaleBuy':  values[8], #融券 買進  
            'ShortSaleCashRepay': values[9], #融券 券償  
            'ShortSaleBalance': values[10], #融券 餘額  
            #values[11], 融券 增減  
            'ShortDivMagRatio': values[12], #券資比
            'symbol': symbol
        }
        item = StockMarginDataItem({'obj': MarginItem, 'pipeline': StockHisMarginPipeline})
        self.logger.debug("[SPIDER] pass ABuFubon.StockHisMarginSpider symbol:{0} ShortDivMagRatio:{1}".format(symbol, MarginItem['ShortDivMagRatio']))
        yield(item)

