from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from bs4 import BeautifulSoup 
from string import Template
from datetime import date, timedelta

import scrapy
import re


# scrapy
from ABuFubon.items import StockInstitutionInvestItem, SpiderErrItem
from ABuFubon.pipelines import StockInstitutionInvestPipeline, SpiderErrPipeline

from abupy.MarketBu.ABuMarket import all_symbol 
from abupy.UtilBu.ABuDateUtil import str_to_datetime, twtime_to_utc_str
from abupy.CoreBu.ABuEnv import g_cdataiso, g_ddateiso


class StockInstitutionInvestSpider(scrapy.Spider):
    name = "StockInstitutionInvestSpider"
    allowed_domains = ['fubon-ebrokerdj.fbs.com.tw']

    # set post pipeline map table
    pipeline = set([
        SpiderErrPipeline,      # high prio
        StockInstitutionInvestPipeline    
    ])

    #ex: http://fubon-ebrokerdj.fbs.com.tw/z/zc/zcl/zcl.djhtm?a=2330&c=2021-2-24&d=2021-3-3
    URLStr = Template('http://fubon-ebrokerdj.fbs.com.tw/z/zc/zcl/zcl.djhtm?a=$SYMBOL&c=$CDATE&d=$DDATE')
    reDate = re.compile(r".*\:([0-9]*)\/([0-9]*)", re.DOTALL | re.MULTILINE) # MM/DD
  
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
        to_float = lambda x: float(x)
        to_str   = lambda x: str(x.text).replace(',','').replace('%', '').replace(' ','')

        try:
            text = response.body
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find_all('table', {'class': 't01'})[0]
            # not sure why to_float doesn't work 
            values = list(map(to_str, table.find_all('td', {'class': ['t3n1', 't3r1']})))[:10]
            values = list(map(to_float, values))
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
            self.logger.exception("[SPIDER] parser ABuFubon.StockInstitutionInvestSpider symbol:{0} Error:{1}".format(symbol, e))
            yield(item)
            return   

        InstitutionInvestItem = {
            'date': str_to_datetime(cdate),
            'ForeignInvestor': values[0], #外資買賣
            'InvestmentTrust': values[1], #投信買賣
            'DealerSelf': values[2], #自營商買賣
            '1DayTotal': values[3], #單日合計
            'ForeignInvestorHold': values[4], #外資 估計持股
            'InvestmentTrustHold': values[5], #投信 估計持股
            'DealerSelfHold': values[6],  #自營商 估計持股
            '1DayHold': values[7], # 單日合計
            'ForeignInvestorHoldRat': values[8], #外資 持股比重
            '3MainTopHoldRat': values[9], #三大法人 持股比重
            'symbol': symbol
        }
        item = StockInstitutionInvestItem({'obj': InstitutionInvestItem, 'pipeline': StockInstitutionInvestPipeline})
        self.logger.debug("[SPIDER] pass ABuFubon.StockInstitutionInvestSpider symbol:{0} 1DayHold:{1}".format(symbol, InstitutionInvestItem['1DayHold']))
        yield(item)

