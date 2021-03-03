# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class BasePipeLineItem(scrapy.Item):
    pipeline = scrapy.Field()

class StockHisDataItem(BasePipeLineItem):
    # define the fields for your item here like:
    obj = scrapy.Field()

class StockMarginDataItem(BasePipeLineItem):
    obj = scrapy.Field()

class StockInstitutionInvestItem(BasePipeLineItem):
	obj = scrapy.Field()

class StockHisTraderItem(BasePipeLineItem):
    obj = scrapy.Field()

class TraderHisDataItem(BasePipeLineItem):
    obj = scrapy.Field()

class TraderIdItem(BasePipeLineItem):
    obj = scrapy.Field()

class StockIdItem(BasePipeLineItem):
    obj = scrapy.Field()

class SpiderErrItem(BasePipeLineItem):
    obj = scrapy.Field()    

