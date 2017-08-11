import scrapy
import logging
from scrapy.crawler import CrawlerProcess 
from pymongo import MongoClient

def addUrl(sector, db):
    logging.debug('sector %s' %sector)
    domain = 'http://www.moneycontrol.com'
    SectorWiseSpider.db = db
    if sector[0] == 'all':
        logging.debug('fetching all sectors')
        sectors = db.sectors.find()
        for sec in sectors:
            logging.debug('url ******* %s' %(domain + sec.get('link')))
            SectorWiseSpider.url.append((domain + sec.get('link').replace('\n','')))
    else:
        logging.debug('only specific sectors, no of sectors :%s' %sector)
        cursor = db.sectors.find({'sectorName' : sector}, {'link' : 1})
        url = domain + cursor[0]['link']
        logging.debug('url to be crawled %s' %url)
        count = db[sector].remove({})
        logging.debug('removing %s recoreds  from sector %s' %(count, sector))
        SectorWiseSpider.url.append(url)


def getProcessor():
    return CrawlerProcess({'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'})

class SectorWiseSpider(scrapy.Spider):
    name = "sectorWise"
    url = []

    def __init__(self,*args, **kwargs):
        super(SectorWiseSpider, self).__init__(*args, **kwargs)
        self.start_urls = SectorWiseSpider.url 
        logging.debug('start url %s' %self.start_urls)

    def parse(self, response):
        stocks = response.css('td.brdrgtgry a.bl_12 ::attr(href)').extract()
        logging.debug('Response url :%s' %response.url)
        #sector = response.url.split('/')[len(response.url.split('/')) -1 ].replace('.html','')
        #logging.debug('Creating sector %s' %sector)
        #SectorWiseSpider.db[sector].remove({})
        for i in stocks:
            logging.debug('url %s \n' %i)
            sector = i.split('/')[len(i.split('/')) - 3]
            logging.debug('Creating sector %s' %sector)
            SectorWiseSpider.db[sector].insert_one({'url':i})
            
            


def runSector(sector, process, db):    
    addUrl(sector, db)
    process.crawl(SectorWiseSpider)
    process.start()
    
     


#runSector('paper')

