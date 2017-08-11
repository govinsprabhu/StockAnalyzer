from flask import render_template,request    
import logging
from flask import Flask
import scrapy
from stock_details import stockDetails,crawlAll,CrawlerProcess,addToPortfolio,removeFromPortfolio,getHeadersForStock,getHeadersForPortfolio,refreshStock,getHeadersForIndividualStock, sort
from pymongo import MongoClient
from sector_wise_analysis import runSector
import math

app = Flask(__name__)
client = MongoClient()
db = client.all_sectors
process = CrawlerProcess({'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'})

@app.route("/")
def run():
    headers = {'sector' : 'SECTOR'}
    sectors = []
    logging.debug('loading from db')
    sectors = list(db.sectors.find().sort('name'))
    logging.debug('parsing completed :%s ' %len(sectors))
    comapanies = db.company.find({},{'name':1, 'url':1}).sort([("name", 1)])
    collections = db.collection_names()
    portfolios = []
    for collection in collections:
        if '_portfolio' in collection:
            portfolios.append(collection.replace('_portfolio', ''));
        
    return render_template('template_main.html',headers=headers, sectors = sectors,comapanies = comapanies, portfolios = portfolios)

@app.route("/get")
def getCompany():
    url = request.args.get('url')
    logging.debug('inside getCompany() ... url %s'  %url)
    return getCompanyFromUrl(url)

def getCompanyFromUrl(url):
    logging.debug('url to be get %s' %url)
    sector = db.company.find_one({'url' : url})
    sector['graphams_number'] = grahamsNumber(sector)
    analysis = list(db.analysis.find({'url' : url}))
    logging.debug('analysis %s' %analysis)
    if len(analysis) == 0:
        analysis = [{'comparison':'Just compare','return_on_capital':'','url':'','price_by_book':'BV:\n','asset_liability':'','eps':'','points':'','financial_report':'','pe':'','grahams_number':''}]
    logging.debug('analysis :%s ' %analysis)
    return render_template('template_stock.html',headers=getHeadersForIndividualStock(), sector = sector,analysis = analysis)

def grahamsNumber(sector):
    return round(math.sqrt(22.5 * float(sector['book_value']) * float(sector['eps'])), 2)

@app.route("/send", methods=['POST'])
def updateAnalysis():
    params = dict(request.form)
    logging.debug('Inside UpdateAnalysis. Incoming params %s and type ' %params)
    stock = {}
    for param in params:
        logging.debug(" key :%s value %s" %(param, params[param][0]))
        stock[param] = params[param][0]
        
    logging.debug('stock %s' %stock)
    count = db.analysis.find_one_and_update({'url':stock['url']},{'$set':stock})
    db.company.find_one_and_update({'url':stock['url']},{'$set':{'analysis_grades':stock['analysis_grades']}})
    #logging.debug('successfully updated :{}',count)
    return 'Successfully Updated';

@app.route("/all")
def displayAll():
    logging.debug('inside display all ')
    sectors = list(db.company.find({}).sort([("points", -1)]))
    logging.debug('total number of companies :%s ' %len(sectors))
    return render_template('template_sector.html',headers=getHeadersForPortfolio(), sectors = sectors)

@app.route("/refresh/company/get")
def refreshStockFromUrl():
    url = request.args.get('url')
    logging.debug('inside refreshSotck from Url. url to refresh  %s' %url)
    sectors =  refreshStock(url, process, db)
    return render_template('template_sector.html',headers=getHeadersForPortfolio(), sectors = sectors)

@app.route("/insert/sectors")
def insertSectors():
    logging.debug('Deleting collection sector..')
    db.sectors.remove({})
    process = getProcessor()
    process.crawl(AllSectorsSpider)
    process.start()
    count = 0
    logging.debug('Inserting to collection sector..')
    for key in AllSectorsSpider.sector_map:
        value = AllSectorsSpider.sector_map[key]
        sectorName = value.split('/')[len(value.split('/')) - 1].replace('-','').replace('.html','')
        sector = {'name':str(key), 'link': str(value), 'sectorName' : str(sectorName)}
        user_id = db.sectors.insert_one(sector).inserted_id
        #logging.debug('User id %s' %user_id)
        count += 1
    logging.debug('%s recrods are inserted' %count)
    

@app.route("/stocks/top-companies-in-india/market-capitalisation-bse/<sector>")
def sectorWise(sector):
    logging.debug('Fetching for sector %s' %sector)
    function = 'update'
    data =  stockDetails(sector.replace('.html','').replace('-',''),process, db, function)
    return render_template('template_sector.html',sectorName = data.sectorName, headers=getHeadersForStock(), sectors = data.sectors)

@app.route("/sector/<sector>/refresh")
def refresh(sector):
    logging.debug('Refresh for sector %s' %sector)
    function = 'refresh'
    data =  stockDetails(sector.replace('.html','').replace('-',''),process, db, function)
    return render_template('template_sector.html',sectorName = data.sectorName, headers=getHeadersForStock(), sectors = data.sectors)

@app.route("/all_refresh")
def crawlSectors():
    logging.debug('Crawling all sectors..')
    return crawlAll(process, db)

@app.route("/insert/companies/<sector>")
def insertSectorName(sector):
    logging.debug('sectors to be crawled %s' %sector)
    count = runSector(sector,process, db)
    return '%s Companies are inserted ' %count


@app.route("/portfolio_add/<name>/add")
def addCompanyToPortfolio(name):
    url = request.args.get('url')
    logging.debug('Adding stock with url %s to %s portfolio' %(url, name))
    addToPortfolio(name,url, db)
    return 'Inserted to portfolio'

@app.route("/portfolio_sort/<name>/sort")
def sortPortfolio(name):
    option = request.args.get('option')
    logging.debug('Sorting portfolio %s with option %s ' %(name, option))
    data =  sort(name,option, db)
    logging.debug("length :%s" %len(data.sectors))
    comapanies = db.company.find({},{'name':1, 'url':1}).sort([("name", 1)])
    return render_template('template_portfolio.html',sectorName = data.sectorName, headers=getHeadersForPortfolio(), sectors = data.sectors, comapanies = comapanies, portFolioName = name)

@app.route("/portfolio/<name>")
def getPortfolio(name):
    logging.debug('Getting portfolio with name %s' %name)
    function = 'update'
    data =  stockDetails(name,process, db, function)
    comapanies = db.company.find({},{'name':1, 'url':1}).sort([("name", 1)])
    return render_template('template_portfolio.html',sectorName = data.sectorName, headers=getHeadersForPortfolio(), sectors = data.sectors, comapanies = comapanies, portFolioName = name)

@app.route("/portfolio/<name>/refresh")
def refreshPortFolio(name):
    logging.debug('Refreshing portfolio %s' %name)
    function = 'refresh'
    data =  stockDetails(name,process, db, function)
    return render_template('template_sector.html',sectorName = data.sectorName, headers=getHeadersForPortfolio(), sectors = data.sectors)


@app.route("/portfolio/<name>/remove")
def removeCompanyFromPortfolio(name):
    url = request.args.get('url')
    logging.debug('Removing url %s from %s  portfolio' %(url, name))
    removeFromPortfolio(name,url, db)
    return 'Removed from portfolio'

class AllSectorsSpider(scrapy.Spider):
    name = "allSectors"
    sector_map = {}
    start_urls = [
        'http://www.moneycontrol.com/stocks/marketinfo/marketcap/bse/',
    ]

    def parse(self, response):
        link = response.css('div.lftmenu ul li a::attr(href)').extract()
        industry = response.css('div.lftmenu ul li a::text').extract()
        filename = 'data/SectorWiseUrls.txt'
        f = open(filename,'w+')
        for i,j in zip(industry,link):
            f.write(i+":"+j +'\n')
            AllSectorsSpider.sector_map[i] = j


def getProcessor():
    return CrawlerProcess({'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'})
    

if __name__ == "__main__":    
    logging.debug('running app')
    app.run()

