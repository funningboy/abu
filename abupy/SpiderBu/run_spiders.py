from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import sys


from apscheduler.schedulers.twisted import TwistedScheduler
from scrapy.crawler import CrawlerRunner, CrawlerProcess
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from twisted.internet import defer
from twisted.internet import reactor

sys.path.insert(0, os.path.abspath('../../'))
import abupy
from abupy.CoreBu import ABuEnv

# spiders
from abupy.SpiderBu.ABuFubon.spiders.StockHisDataSpider import StockHisDataSpider
from abupy.SpiderBu.ABuFubon.spiders.StockHisTraderSpider import StockHisTraderSpider
from abupy.SpiderBu.ABuFubon.spiders.StockMarginDataSpider import StockHisMarginSpider
from abupy.SpiderBu.ABuFubon.spiders.StockInstitutionInvestSpider import StockInstitutionInvestSpider


configure_logging()

# get free proxy list to avoid blocking access
# int_proxy()

runner = CrawlerRunner(get_project_settings())
proc = CrawlerProcess(get_project_settings())
sched = TwistedScheduler()

def example_process():
    proc.crawl(StockHisDataSpider)
    proc.start()

def example_runner():
    runner.crawl(StockHisDataSpider)
    d = runner.join()
    d.addBoth(lambda _: reactor.stop())
    reactor.run()


@sched.scheduled_job('cron', id=StockHisDataSpider.__name__, day_of_week='mon-fri', hour=5, minute=30)
@defer.inlineCallbacks
def crawl_StockHisDataSpider():
    yield runner.crawl(StockHisDataSpider)
    reactor.stop()

@sched.scheduled_job('cron', id=StockHisTraderSpider.__name__, day_of_week='mon-fri', hour=6, minute=30)
@defer.inlineCallbacks
def crawl_StockHisTraderSpider():
    yield runner.crawl(StockHisTraderSpider)
    reactor.stop()

@sched.scheduled_job('cron', id=StockInstitutionInvestSpider.__name__, day_of_week='mon-fri', hour=7, minute=30)
@defer.inlineCallbacks
def crawl_StockInstitutionInvestSpider():
    yield runner.crawl(StockInstitutionInvestSpider)
    reactor.stop()

@sched.scheduled_job('cron', id=StockHisMarginSpider.__name__, day_of_week='mon-fri', hour=8, minute=30)
@defer.inlineCallbacks
def crawl_StockHisMarginSpider():
    yield runner.crawl(StockHisMarginSpider)
    reactor.stop()


def main():
    #crawl_StockHisDataSpider
    #crawl_StockHisTraderSpider
    #crawl_StockInstitutionInvestSpider
    #crawl_StockHisMarginSpider
    sched.start()
    reactor.run() # the script will block here until the last crawl call is finished


if __name__ == '__main__':
    ABuEnv.enable_example_env_ipython()
    ABuEnv.g_cdataiso = '2021-03-01'
    ABuEnv.g_ddateiso = '2021-03-08'
    main()