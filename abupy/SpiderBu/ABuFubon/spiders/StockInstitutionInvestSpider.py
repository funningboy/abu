from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from bs4 import BeautifulSoup 
from string import Template
from datetime import date

import scrapy
import re


# scrapy
from ABuFubon.items import StockInstitutionInvestItem, SpiderErrItem
from ABuFubon.pipelines import StockInstitutionInvestPipeline, SpiderErrPipeline

from abupy.MarketBu.ABuMarket import all_symbol 
from abupy.UtilBu.ABuDateUtil import str_to_datetime


class StockInstitutionInvestSpider(scrapy.Spider):
    name = "StockInstitutionInvestSpider"
    allowed_domains = ['fubon-ebrokerdj.fbs.com.tw']

    # set post pipeline map table
    pipeline = set([
        SpiderErrPipeline,      # high prio
        StockInstitutionInvestPipeline    
    ])

    #ex: http://fubon-ebrokerdj.fbs.com.tw/z/zc/zcl/zcl.djhtm?a=2330&c=2021-2-24&d=2021-3-3
    URLStr = Template('http://fubon-ebrokerdj.fbs.com.tw/z/zc/zcl/zcl.djhtml?a=$SYMBOL&c=$CDATE&d=$DDATE')
    reDate = re.compile(r".*\:([0-9]*)\/([0-9]*)", re.DOTALL | re.MULTILINE) # MM/DD
  
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cdateiso = (date.today() - timedelta(days=10)).isoformat()
        self.ddateiso = date.today().isoformat()  
        self.symbols = all_symbol()
        #self.cdateiso = '2020-12-04'
        #self.ddateiso = '2020-12-31'
        #self.symbols = ['2330']

    def start_requests(self):
        cdate = '-'.join(map(lambda x: str(int(x)), self.cdateiso.split("-")))
        ddate = '-'.join(map(lambda x: str(int(x)), self.ddateiso.split("-")))
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/48.0'}
        for symbol in self.symbols:
            url = self.URLStr.substitute({'SYMBOL': symbol, 'CDATE': cdate, 'DDATE': ddate})
            yield scrapy.Request(url=url, headers=headers, callback=self.parse, cb_kwargs={'symbol': symbol})

    def parse(self, response, symbol):
        to_str   = lambda x: str(x.text).replace(' ', '').replace(',','').replace('%', '').replace(' ','')
        try:
            text = response.body
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find_all('table', {'class': 't01'})[0]
            values = list(map(to_float, table.find_all('td', {'class': ['t3n1', 't3r1']})))
            print (values)
        except Exception as e:
           pass


