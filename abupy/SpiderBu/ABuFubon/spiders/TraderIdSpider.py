
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from bs4 import BeautifulSoup 
from string import Template
from datetime import date
from collections import defaultdict

import scrapy
import re

# scrapy
from ABuFubon.items import TraderIdItem
from ABuFubon.pipelines import TraderIdPipeline


class TraderIdSpider(scrapy.Spider):
    name = "TraderIdSpider"
    allowed_domains = ['fubon-ebrokerdj.fbs.com.tw']

    custom_settings = { 
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
    }
    # set post pipeline map table
    pipeline = set([
        TraderIdPipeline
    ])

    URL = 'https://fubon-ebrokerdj.fbs.com.tw/z/js/zbrokerjs.djjs'
 
    reBkr = re.compile(r".*g_BrokerList = \'(.*)\'", re.MULTILINE|re.DOTALL)
    reBkr2Id = re.compile(r"(.*),(.*)", re.DOTALL)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start_requests(self):
        url = self.URL
        yield scrapy.Request(url=url, callback=self.parse, dont_filter=True)

    def parse(self, response):

        def _debug():
            import json
            with open('traderid.json', 'w', encoding='utf-8') as f:
                json.dump(BkrMap, f, indent=4, ensure_ascii=False)

        try:
            text = response.body.decode('cp950')# 中文
            BkrMap = defaultdict(lambda: defaultdict(str))
            BkrGrps = self.reBkr.match(text).group(1).split(';') # slice to broker groups
            for bkrgrp in BkrGrps:
                bkrlist = bkrgrp.split('!') # slice to sub broker
                for i, bkr in enumerate(bkrlist[:-1]):
                    bmt = self.reBkr2Id.match(bkr)
                    if bmt:
                        top_bkr = bmt.group(2) if i == 0 else top_bkr
                        BkrMap[top_bkr].update({bmt.group(2): bmt.group(1)}) #group(1) = b
        except Exception as e:
            self.logger.exception("[SPIDER] parser ABuFubon.TraderIdSpider Error:{0}".format(e))
            return    

        # encode as flatten item list
        IdItems = []
        for brk_k,brk_v in BkrMap.items():
            for bb_k, bb_id in brk_v.items():
                SBH = {
                    'SBHID': bb_id,     # trader_id
                    'SBHNAME': bb_k     # trader_name
                }
                IdItems.append(SBH)

        item = TraderIdItem({'obj': IdItems})

        _debug()

        self.logger.info("[SPIDER] pass ABuFubon.TraderIdSpider SBHID:{0} SBHNAME:{1}".format(IdItems[0]['SBHID'], IdItems[0]['SBHNAME']))
        yield(item)