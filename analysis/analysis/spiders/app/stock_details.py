import collections
import datetime
import logging
import scrapy
from scrapy.crawler import CrawlerProcess 

no_of_days = 10
max_value = 1000000000

sortMap = {}
j = 40
for i in range(25,-1,-1):
    sortMap[ord('A') + i] = j
    j += 80

sortMap[ord('+')] = 10
sortMap[ord('-')] = -10
sortMap[ord('*')] = 5
    
def addUrl(sector, db):
    domain = 'http://www.moneycontrol.com'
    f = list(db.portfolio.find({'sector':sector}))
    if len(f) == 0:
        return False
    for i in f:
        logging.debug('url to be crawled :%s' % (domain + i['url']))
        StockDetailsSpider.url.append(i['url'])

    return True

def getProcessor():
    logging.debug('Calling getProcess')
    return CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
        })

def getHeadersForPortfolio():
    return ['Name', 'Analysis Points','Points', 'Share Price', 'EPS', 'P/E', 'Industry P/e', 'Market Cap', 'Book value', 'Price By Book', 'Divident', 'Action','Expand']

def getHeadersForStock():
    return ['Name', 'Points', 'Share Price', 'EPS', 'P/E', 'Industry P/e', 'Market Cap', 'Book value', 'Price By Book', 'Divident', 'Action' ]

def getHeadersForIndividualStock():
    return ['Name', 'Points', 'Share Price', 'Graphams number', 'EPS', 'P/E', 'Industry P/e', 'Market Cap', 'Book value', 'Price By Book', 'Divident', 'Action' ]

def getData(sectorName, process, db, function):
    logging.debug('checking if present in db for function %s' % function)
    pre = list(db.portfolio.find({'sector':sectorName}))
    logging.debug('pre value %s' %pre)
    count = len(pre)
    if count == 0 or function == 'refresh':
        logging.debug('Data is not present db. Starting crawling for sector %s' % sectorName)
        return crawl(sectorName, process, db)
    
    url = pre[0]['url']
    logging.debug('pre value %s url %s' %(pre, url))
    now = datetime.datetime.now()
    pre = list(db.company.find({'url':url}, {'time':1, '_id':0}))
    logging.debug('pre value %s url' %(pre))
    day = (now - pre[0]['time']).days
    logging.debug('count %s days %s' % (count, day))
    if  day > no_of_days:
        logging.debug('Data is %s days old. Starting crawling' % day)
        return crawl(sectorName, process, db)

    logging.debug('Data is present in db. Fetching...')
    return getFromDb(sectorName, db)

def crawlAll(process, db):
    sectors = db.sectors.find({}, {'sectorName':1, '_id':0})
    for sector in sectors:
        sectorName = sector['sectorName']       
        logging.debug('sectorName name %s' % sectorName)
        addUrl(sectorName, db)
    return startCrawlAll(process, db)

def insertAll(db):
    stocks = getSectors(None)
    logging.debug('Removing all documents from collection company')
    count = db.company.remove({})
    portfolio_count = db.portfolio.remove({})
    logging.debug('%s records from company and %s from portfolio removed' % (count,portfolio_count))
    for stock in stocks:
        try:
            db.company.insert_one(stock)
            db.portfolio.insert_one({'url':stock['url'], 'sector':stock['sector']})
        except Exception:
            logging.debug('Duplicate Key exception')
    logging.debug('insertion completed...')

def crawl(sectorName, process, db):
    logging.debug('adding url for sector :%s' % sectorName)
    addUrl(sectorName, db)
    process.crawl(StockDetailsSpider)
    process.start()
    update(sectorName, db)
    logging.debug('*******closing spider *******')
    process.stop()   
    return getFromDb(sectorName, db)

def startCrawlAll(process, db):
    process.crawl(StockDetailsSpider)
    process.start()
    insertAll(db)
    logging.debug('*******closing spider *******')
    process.stop()
    count = db.company.find({}).count()
    return 'insertion completed. %s records inserted' % count 

    
def update(sectorName, db):
    logging.debug('inserting sector  %s ' % (sectorName))
    sectors = getSectors(sectorName)
    if len(sectors) == 0:
        logging.debug('sector is empty for sector name %s  ' % (sectorName))
        return
    for stock in sectors:
        logging.debug("sotcks url %s stock %s" % (stock['url'],stock))
        db.company.find_one_and_update({'url':stock['url']}, {'$set': stock})
        db.portfolio.update({'url':stock['url']},  {'$addToSet':{'sector': sectorName}})
    

def getDefaultIfZero(numarator, denominator, default):
    if  denominator == 0:
        return numarator / default
    return numarator / denominator 

def getFromDb(sectorName, db):
    logging.debug('Getting from db for sector :%s ' % (sectorName))
    stocks = db['portfolio'].find({'sector':sectorName})
    result = []
    for stock in stocks:
        comp = db.company.find_one({'url':stock['url']})
        logging.debug('company %s' %comp)
        result.append(comp)
    
    logging.debug('sorting based on points')
    result = sorted(result, key=lambda x:x['market_cap'], reverse=True)    
    Data = collections.namedtuple('Data', ['sectors', 'sectorName'])
    data = Data(result, sectorName)
    return data

def stockDetails(sector, process, db, function):
    logging.debug('********Sector name :%s  function %s***********' % (sector, function))
    return getData(sector, process, db, function)

def addToPortfolio(name, url, db):
    logging.debug('********Url to be added %s to portfolio %s***********' % (url, name))
    db.portfolio.find_one_and_update({'url':url},  {'$addToSet':{'sector': name}})
    
    
def sort(name,option, db):
    data = getFromDb(name, db)
    result = data.sectors
    logging.debug('********Sort %s based on %s***********' % ( name, option))
    if option == 'analysis_grades':
           
        result = sorted(result, key=pointSort, reverse=True)
               
    else: 
        result = sorted(result, key=lambda x:x[option], reverse=True)
    Data = collections.namedtuple('Data', ['sectors', 'sectorName'])
    data = Data(result, name)
    return data 

def pointSort(results):
    val = ''
    if 'analysis_grades' in results and results['analysis_grades'] != '':
        val =  results['analysis_grades'].replace('\t','').replace('\n','').replace('\r','').replace(' ','')
    totalPoint = 0
    #logging.debug('value %s' %val)
    for ch in val:
        #logging.debug('ch %s' %ch)
        totalPoint += sortMap[ord(ch)]
    
    logging.debug("totalPoints %s for val %s" %(totalPoint, val));
    return totalPoint

def removeFromPortfolio(name, url, db):
    logging.debug('********Url to be removed %s from portfolio %s***********' % (url, name))
    count= db.portfolio.find_one_and_update({'url':url},  {'$pull':{'sector': name}})
    logging.debug('removed record from %s and %s records removed' % (name, count))
    	
def refreshStock(url, process, db):
    logging.debug('Inside refresh stock. url to be crawled %s' % url)
    StockDetailsSpider.url.append(url)
    process.crawl(StockDetailsSpider)
    process.start()
    company = getSectors(None)
    db.company.update({'url':company.url}, {'set': company})
    logging.debug('company %s' % company)
    logging.debug('*******closing spider *******')
    process.stop()   
    return company

def getSectors(sectorName):
    ind = 0
    sectors = []
    logging.debug('number of companies %s' % len(StockDetailsSpider.stock.names))
    for name in StockDetailsSpider.stock.names:
        logging.debug('name %s len eps %s shre price %s' % (name, len(StockDetailsSpider.stock.eps), len(StockDetailsSpider.stock.share_price)))
        name = name
        share_price = float(StockDetailsSpider.stock.share_price[ind])
        eps = float(StockDetailsSpider.stock.eps[ind])
        pe = float(StockDetailsSpider.stock.pe[ind])
        industry_pe = float(StockDetailsSpider.stock.industry_pe[ind])
        market_cap = float(StockDetailsSpider.stock.market_cap[ind])
        book_value = float(StockDetailsSpider.stock.book_value[ind])
        price_by_book = float(StockDetailsSpider.stock.price_by_book[ind])
        div = float(StockDetailsSpider.stock.div[ind])
        url = str(StockDetailsSpider.stock.url[ind])
        time = datetime.datetime.now()
        if sectorName == None:
            sector_name = url.split('/')[len(url.split('/')) - 3].replace('-', '')
            
        else:
            sector_name = url.split('/')[len(url.split('/')) - 3].replace('-', '')
        # logging.debug('sectorName %s' %sector_name)
        points = round(((getDefaultIfZero(eps * 3, pe, 15) * 100 + getDefaultIfZero(industry_pe, pe * price_by_book, max_value) * 100 + getDefaultIfZero(1, price_by_book, max_value) * 200 + div / 10) / 600 * 100), 2)
        # points = getPoints(eps, pe, industry_pe, price_by_book,div)
        sector = {'name' :name, 'share_price' : share_price, 'eps' : eps, 'pe':pe, 'industry_pe':industry_pe, 'market_cap':market_cap, 'book_value': book_value, 'price_by_book':price_by_book, 'div':div, 'url':url, 'sector' : [sector_name], 'time':time, 'points': points}
        # logging.debug('sector %s' %sector)
        
        sectors.append(sector)
        ind += 1

    return sectors

class Stock:
    def __init__(self):
        self.names = []
        self.eps = []
        self.pe = []
        self.market_cap = []
        self.book_value = []
        self.price_by_book = []
        self.industry_pe = []
        self.book_value = []
        self.div = []
        self.face_value = []
        self.market_lot = []
        self.p_c = []
        self.div_yield = []
        self.share_price = []
        self.url = []

class StockDetailsSpider(scrapy.Spider):
    name = "stockDetails"
    url = []
    stock = Stock()
    ind = 0
    def __init__(self, *args, **kwargs):
        super(StockDetailsSpider, self).__init__(*args, **kwargs)
        self.start_urls = StockDetailsSpider.url
        # logging.debug('start url %s' %self.start_urls)

    def parse(self, response):
        share_price = response.xpath('//span[@id="Bse_Prc_tick"]/strong/text()')[0].extract()
        StockDetailsSpider.stock.share_price.append(float(str(share_price)))
        self.param = response.xpath('//div[@class="FL gL_10 UC"]/text()').extract()
        self.value = response.xpath('//div[@class="FR gD_12"]/text()').extract()
        name = response.xpath('//span[@typeof="v:Breadcrumb"]/text()')[8].extract()
        name = name.replace('\n', '')
        name = name.replace('\t', '')
        StockDetailsSpider.stock.names.append(name)
        StockDetailsSpider.stock.url.append(response.url)
        logging.debug('response url %s' % response.url)
        logging.debug('name : %s' % StockDetailsSpider.stock.names[StockDetailsSpider.ind])
        StockDetailsSpider.ind += 1
        index = 0
        for i, j in zip(self.param, self.value):
            if index == 11:
                break
            index += 1
            lis = self.getList(StockDetailsSpider.stock, str(i))
            j = j.strip()
            if (j == '-' or  j == '' or j == '-%'):
                j = 0
            else:
                j = j.replace('%', '').replace(',', '')
            logging.debug('%s %s ' % (i, j)) 
            lis.append(float(j))
            

    def getList(self, stock, key):
        return { 'MARKET CAP (Rs Cr)': stock.market_cap,
                 'P/E': stock.pe,
                 'BOOK VALUE (Rs)':stock.book_value,
                 'DIV (%)': stock.div,
                 'INDUSTRY P/E' : stock.industry_pe,
                 'EPS (TTM)': stock.eps,
                 'PRICE/BOOK' : stock.price_by_book,
                 'FACE VALUE (Rs)' : stock.face_value,
                 'Market Lot' : stock.market_lot,
                 'P/C' : stock.p_c,
                 'DIV YIELD.(%)':stock.div_yield
             }[key]

    



