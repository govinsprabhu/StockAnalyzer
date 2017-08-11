def plotFigure(param,x_label,y_label):
    plt.clf()
    width  = 1/1.5
    x_plot = np.arange(len(param))
    y_plot = param
    plt.bar(x_plot,y_plot, width)
    plt.ylabel(y_label)
    plt.xlabel(x_label)
    x_ticks = getFirstWord(StockDetailsSpider.stock.names)
    plt.xticks(x_plot, x_ticks)
    locs, labels = plt.xticks()
    plt.setp(labels, rotation=90)
    pdf_name = ('data/%s/%s-%s.pdf' %(x_label,x_label,y_label))
    plt.savefig(pdf_name, format='pdf')
    logging.debug('Saving file %s' %pdf_name)

def plotAll(sector):
    plotFigure(StockDetailsSpider.stock.pe, sector,'PE')
    plotFigure(StockDetailsSpider.stock.eps, sector,'EPS')
    plotFigure(StockDetailsSpider.stock.market_cap, sector,'Market Cap')
    plotFigure(StockDetailsSpider.stock.book_value, sector,'Book Value')
    plotFigure(StockDetailsSpider.stock.price_by_book, sector,'Price by book')
    plotFigure(StockDetailsSpider.stock.share_price, sector,'Share Price')
    plotFigure(StockDetailsSpider.stock.div, sector,'div')


def writeToCSV(sector):
    headers = getHeaders()
    path  = 'data/%s' %sector
    makeSurePathExists(path)
    csvName = ('%s/fullData.csv' %path)
    f = open(csvName,'w+')
    for i in headers:
        f.write(str(i)+',')

    f.write('\n')
    ind = 0
    for name in StockDetailsSpider.stock.names:
        f.write(name+',')
        f.write(float(StockDetailsSpider.stock.share_price[ind])+',')
        f.write(float(StockDetailsSpider.stock.eps[ind])+',')
        f.write(float(StockDetailsSpider.stock.pe[ind])+',')
        f.write(float(StockDetailsSpider.stock.industry_pe[ind])+',')
        f.write(float(StockDetailsSpider.stock.market_cap[ind])+',')
        f.write(float(StockDetailsSpider.stock.book_value[ind])+',')
        f.write(float(StockDetailsSpider.stock.price_by_book[ind])+',') 
        f.write(float(StockDetailsSpider.stock.div[ind])+',')
        f.write(str(StockDetailsSpider.stock.url[ind]))
        f.write('\n')
        ind += 1
