from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import sys

from datetime import date
from datetime import timedelta, datetime
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
#from abupy.SpiderBu.ABuFubon.spiders.StockNowDataSpider import StockNowDataSpider


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

@defer.inlineCallbacks
def crawl_StockHisDataSpider():
    yield runner.crawl(StockHisDataSpider)
    reactor.stop()

@defer.inlineCallbacks
def crawl_StockHisTraderSpider():
    yield runner.crawl(StockHisTraderSpider)
    reactor.stop()

@defer.inlineCallbacks
def crawl_StockInstitutionInvestSpider():
    yield runner.crawl(StockInstitutionInvestSpider)
    reactor.stop()

@defer.inlineCallbacks
def crawl_StockHisMarginSpider():
    yield runner.crawl(StockHisMarginSpider)
    reactor.stop()

#@defer.inlineCallbacks
#def crawl_StockNowDataSpider():
#    yield runner.crawl(StockNowDataSpider)
#    reactor.stop()

def _add_runner(spider):
    runner.crawl(spider)

def _join_runner():
    d = runner.join()
    d.addBoth(lambda _: reactor.stop())


jobs = [
    #0
    {
        'spider': crawl_StockHisDataSpider, 
        'id': StockHisDataSpider.__name__, 
        'cspider': StockHisDataSpider,
        'day_of_week': 'mon-fri', 
        'hour':8, 
        'minute':30 
    },
    #1
    {
        'spider': crawl_StockHisTraderSpider, 
        'id': StockHisTraderSpider.__name__,
        'cspider': StockHisTraderSpider, 
        'day_of_week': 'mon-fri', 
        'hour':8, 
        'minute':30 
    },
    #2
    {
        'spider': crawl_StockInstitutionInvestSpider, 
        'id': StockInstitutionInvestSpider.__name__,
        'cspider': StockInstitutionInvestSpider, 
        'day_of_week': 'mon-fri', 
        'hour':8, 
        'minute':30 
    },
    #3
    {
        'spider': crawl_StockHisMarginSpider, 
        'id': StockHisMarginSpider.__name__, 
        'cspider': StockHisMarginSpider,
        'day_of_week': 'mon-fri', 
        'hour':8, 
        'minute':30 
    }
    #4
#    {
#        'spider': crawl_StockNowDataSpider,
#        'id': StockNowDataSpider.__name__,
#        'cspider': StockNowDataSpider,
#        'day_of_week': 'mon-fri', 
#        'hour':8, 
#        'minute':30     
#    }
    ]


def run_sched():
    for job in jobs:
        spider = job['spider']
        sched.add_job(spider, 'cron', **job)
    
    sched.start()
    reactor.run() # the script will block here until the last crawl call is finished


def run_cnow(jobid=0):
    job = jobs[jobid]
    spider = job['cspider']
    _crawl(None, spider)

def run_now(jobid):
    job = jobs[jobid]
    spider = job['spider']
    spider()
    reactor.run()
   
def get_dates(): 
    edate = date.fromisoformat(ABuEnv.g_ddateiso)
    sdate = date.fromisoformat(ABuEnv.g_cdataiso)
    cdates_iso = []
    while(True):
        if sdate.weekday() < 6:
            cdates_iso.append(sdate.isoformat())
        sdate = sdate + timedelta(days=1)
        if sdate >= edate:
            break
    return cdates_iso

def main(has_sched=True, jobid=0):
    if has_sched:
        run_sched()
    else:
        run_now(jobid)

if __name__ == '__main__':
    #ABuEnv.enable_example_env_ipython()

    #backup timestamp
    #ABuEnv.g_cdataiso = '2020-04-15' # end -1
    #ABuEnv.g_ddateiso = '2020-05-01'
    
    ABuEnv.g_cdataiso = '2021-07-12'
    ABuEnv.g_ddateiso = '2021-07-13'

    for date in get_dates():
        ABuEnv.g_ddateiso = date
        for jobid in range(1, 4): #0, 4
            job = jobs[jobid]
            cspider = job['cspider']
            _add_runner(cspider)

    _join_runner()
    reactor.run()

#    proc.start() #stop_after_crawl=False)

        