
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from bs4 import BeautifulSoup 
from string import Template
from datetime import date

import scrapy
import re

# scrapy
from ABuFubon.items import StockHisTraderItem, SpiderErrItem
from ABuFubon.pipelines import StockHisTraderPipeline, SpiderErrPipeline

from abupy.MarketBu import ABuMarket 
#from abupy.MarketBu.ABuMarket import all_trader
from abupy.UtilBu import ABuDateUtil 
from abupy.CoreBu import ABuEnv 

class StockHisTraderSpider(scrapy.Spider):
    name = "StockHisTraderSpider"
    allowed_domains = ['fubon-ebrokerdj.fbs.com.tw']

    # set post pipeline map table
    pipeline = set([
        SpiderErrPipeline,      # high prio
        StockHisTraderPipeline
    ])

    #ex: http://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a=2330&e=2021-2-1&f=2021-2-2
    URLStr = Template('http://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a=$SYMBOL&e=$EDATE&f=$EDATE')
    reDate = re.compile(r".*([0-9]*)\/([0-9]*)\/([0-9]*)", re.DOTALL | re.MULTILINE) # YY/MM/DD
    reUnit = re.compile(r".*單位：張.*", re.DOTALL | re.MULTILINE)
    #reUint = #股/張 1張=1000股

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dateiso = ABuEnv.g_ddateiso 
        self.symbols = ABuMarket.all_symbol()
        #self.symbols = ['020003']

    def start_requests(self):
        edate = '-'.join(map(lambda x: str(int(x)), self.dateiso.split("-")))
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/48.0'}
        for symbol in self.symbols:
            url = self.URLStr.substitute({'SYMBOL': symbol, 'EDATE': edate})
            yield scrapy.Request(url=url, headers=headers, callback=self.parse, cb_kwargs={'symbol': symbol})

    def parse(self, response, symbol):
        to_float = lambda x: float(str(x.text).replace(',','').replace('%', '').replace(' ',''))
        to_str   = lambda x: str(x.text).replace(' ', '')
        try:
            text = response.body
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find_all('table', {'class': 't01'})[0]
            values = list(map(to_float, table.find_all('td', {'class': 't3n1'})))
            traders = list(map(to_str, table.find_all('td', {'class': 't4t1'})))[:-4]
            cdate = list(map(to_str, table.find_all('div', {'class': 't11'})))[0]
            cunit = self.reUnit.match(cdate)
            #grps = self.reDate.match(cdate).groups()
            #yy, mm, dd = grps[0], grps[1], grps[2]
            #yy = date.today().isoformat().split("-")[0] 
            #cdate = "{0}-{1}-{2}".format(yy, mm, dd)
        except Exception as e:
            yy, mm, dd = date.today().isoformat().split("-")[0:3] 
            cdate = "{0}-{1}-{2}".format(yy, mm, dd)
            ERR = {
                'date': ABuDateUtil.str_to_datetime(cdate),
                'cls': self.name,
                'msg': "symbol:{0}, fetch html.table Error".format(symbol)
            }
            item = SpiderErrItem({'obj': ERR, 'pipeline': SpiderErrPipeline})
            self.logger.exception("[SPIDER] parser ABuFubon.StockHisTraderSpider symbol:{0} Error:{1}".format(symbol, e))
            yield(item)
            return   

        cdate = self.dateiso
        TraderItem = {}
        TdItems = []
        for i,trader in enumerate(traders):
            TRADER = {
                'tdname': trader,
                'call'  : values[i*4] if cunit else values[i*4]//1000,
                'put'   : values[i*4+1] if cunit else values[i*4+1]//1000,
                'weight': values[i*4+3]
            }
            TdItems.append(TRADER)

        TraderItem.update({
            'date': ABuDateUtil.str_to_datetime(cdate),
            'traders': TdItems,
            'symbol': symbol
        }) 
        item = StockHisTraderItem({'obj': TraderItem, 'pipeline': StockHisTraderPipeline})
        self.logger.debug("[SPIDER] pass ABuFubon.StockHisTraderSpider symbol:{0} BHNAME:{1}".format(symbol, TraderItem['traders'][0]['tdname']))
        yield(item)
