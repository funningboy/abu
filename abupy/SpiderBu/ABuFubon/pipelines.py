# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from datetime import date
import functools
import pymongo
from pymongo import ReturnDocument
#import motor.motor_asyncio


def check_spider_pipeline(process_item_method):

    @functools.wraps(process_item_method)
    def wrapper(self, item, spider):
        item_pipeline = item['pipeline']

        # message template for debugging
        msg = '%%s %s pipeline step' % (self.__class__.__name__,)

        # if class is in the spider's pipeline, then use the
        # process_item method normally.
        if self.__class__ in spider.pipeline and self.__class__ == item_pipeline:
            spider.logger.debug(msg % 'executing')
            return process_item_method(self, item, spider)

        # otherwise, just return the untouched item (skip this step in
        # the pipeline)
        else:
            spider.logger.debug(msg % 'skipping')
            return item

    return wrapper


class BaseStockHisDB(object):

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
        mongo_uri=crawler.settings.get('MONGO_URI', 'mongodb://localhost:27017'),
        mongo_db=crawler.settings.get('MONGO_DATABASE', 'symbol-db')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()


class BaseMiscDB(object):

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
        mongo_uri=crawler.settings.get('MONGO_URI', 'mongodb://localhost:27017'),
        mongo_db=crawler.settings.get('MONGO_DATABASE', 'misc-db')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()


class BaseLoggerDB(object):

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
        mongo_uri=crawler.settings.get('MONGO_URI', 'mongodb://localhost:27017'),
        mongo_db=crawler.settings.get('MONGO_DATABASE', 'logger-db')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()


class SpiderErrPipeline(BaseLoggerDB):

    def __init__(self, mongo_uri, mongo_db):
        super().__init__(mongo_uri, mongo_db)
        self.collect = 'logger'

    @check_spider_pipeline
    def process_item(self, item, spider):
        obj = item['obj']
        
        try:
            self.db[self.collect].insert_one(obj)
        except Exception as e:
            self.logger.exception("[MONGODB] store ABuFubon.ErrorLogger Error:{0}".format(e))
            return    

        spider.logger.debug("[MONGODB] pass ABuFubon.ErrorLogger date:{0}, msg:{1}".format(obj['date'], obj['msg']))
        return item


class TraderIdPipeline(BaseMiscDB):

    def __init__(self, mongo_uri, mongo_db):
        super().__init__(mongo_uri, mongo_db)
        self.collect = 'TraderId'

    @check_spider_pipeline
    def process_item(self, item, spider):
        obj = item['obj']
        
        try:
            self.db[self.collect].drop()
            self.db[self.collect].insert_many(obj)
        except Exception as e:
            self.logger.exception("[MONGODB] store ABuFubon.TraderId Error:{0}".format(e))
            return    

        spider.logger.debug("[MONGODB] pass ABuFubon.TraderId SBHID:{0} SBHNAME:{1}".format(obj[0]['SBHID'], obj[0]['SBHNAME']))
        return item


class StockIdPipeline(BaseMiscDB):

    def __init__(self, mongo_uri, mongo_db):
        super().__init__(mongo_uri, mongo_db)
        self.collect = 'StockId'

    @check_spider_pipeline
    def process_item(self, item, spider):
        obj = item['obj']
        
        try:
            self.db[self.collect].drop()
            self.db[self.collect].insert_many(obj)
        except Exception as e:
            self.logger.exception("[MONGODB] store ABuFubon.StockId Error:{0}".format(e))
            return    

        spider.logger.debug("[MONGODB] pass ABuFubon.StockId STID:{0}".format(obj[0]['STID']))
        return item


class StockHisDataPipeline(BaseStockHisDB):

    def __init__(self, mongo_uri, mongo_db):
        super().__init__(mongo_uri, mongo_db)
        self.collect = 'StockHisData'

    @check_spider_pipeline
    def process_item(self, item, spider):
        obj = item['obj']
        symbol = obj['symbol']
        
        try:
            oo = self.db[self.collect].find_one_and_update(
                            {'date': obj['date'], 'symbol': obj['symbol'] }, # find
                            {'$set': obj },   # update
                            return_document = ReturnDocument.AFTER)
            if oo == None:
                self.db[self.collect].insert_one(obj)
        except Exception as e:
            spider.logger.exception("[MONGODB] store ABuFubon.StockHisData symbol:{0} Error:{1}".format(symbol, e))
            return    

        oo = self.db[self.collect].find_one(
                            {'date': obj['date'], 'symbol': obj['symbol']}) # find

        obj = oo
        spider.logger.debug("[MONGODB] pass ABuFubon.StockHisData symbol:{0} H:{1}".format(symbol, obj['H']))
        return item


class StockHisTraderPipeline(BaseStockHisDB):

    def __init__(self, mongo_uri, mongo_db):
        super().__init__(mongo_uri, mongo_db)
        self.collect = 'StockHisTrader'

    @check_spider_pipeline
    def process_item(self, item, spider):
        obj = item['obj']
        symbol = obj['symbol']
        
        try:
            oo = self.db[self.collect].find_one_and_update(
                            {'date': obj['date'],'symbol': obj['symbol']}, #find
                            {'$set': obj },  # update
                            return_document = ReturnDocument.AFTER)
            if oo == None:
                self.db[self.collect].insert_one(obj)
        except Exception as e:
            spider.logger.exception("[MONGODB] store ABuFubon.StockHisTrader symbol:{0} Error:{1}".format(symbol, e))
            return    

        oo = self.db[self.collect].find_one(
                            {'date': obj['date'],'symbol': obj['symbol']}) #find
        obj = oo
        spider.logger.debug("[MONGODB] pass ABuFubon.StockHisTrader symbol:{0} tdname:{1} call:{2}".format(symbol, obj['traders'][0]['tdname'], obj['traders'][0]['call']))
        return item

