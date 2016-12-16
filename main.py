import urllib
import urllib2
import json
import jinja2
import os
import logging
import webapp2
import sys

sys.path.insert(0, 'lib')

from bs4 import BeautifulSoup
from google.appengine.api import memcache

### Utility functions you may want to use
def pretty(obj):
    return json.dumps(obj, sort_keys=True, indent=2)


def safeGet(url):
    try:
        return urllib2.urlopen(url)
    except urllib2.URLError, e:
        if hasattr(e, "code"):
            print " The server couldn't fulfill the request"
            print "Error code: ", e.code
        elif hasattr(e, 'reason'):
            print "We failed to reach a server"
            print "Reason: ", e.reason
        return None

# use handler to look at paramter that comes from url, show what products
# comes from hardcoded url hyperlinks
# pass in type of clothing you want results for, returns 10 items based on popularity on the site
#from Products API
def getClothes(type, numLim):
    base_url = "http://api.shopstyle.com/api/v2/products"
    apiKey = "pid=uid7936-31095456-22"
    filters = "&cat=%s&sort=Popular" % (type)
    limit = "&limit=%s" % (numLim)
    clothes_request = "%s?%s%s%s" % (base_url, apiKey, filters, limit)
    print (clothes_request)
    safe_request = safeGet(clothes_request)
    if not safe_request == None:
        clothes_request_json = safe_request.read()
        # print pretty(json.loads(clothes_request_json))
        return json.loads(clothes_request_json)

# since the product id is not a parameter, i use a different REST call

# returns a single product object if given Product id
# from Products API
def getSingle(id):
    base_url = "http://api.shopstyle.com/api/v2/products"
    apiKey = "pid=uid7936-31095456-22"
    clothes_request = "%s/%s?%s" % (base_url, id, apiKey)
    print (clothes_request)
    safe_request = safeGet(clothes_request)
    if not safe_request == None:
        clothes_request_json = safe_request.read()
        # print pretty(json.loads(clothes_request_json))
        return json.loads(clothes_request_json)
# http://api.shopstyle.com/api/v2/products/359131344?pid=YOUR_API_KEY


# from Categories API
def getCategories():
    #http: // api.shopstyle.com / api / v2 / categories?pid = YOUR_API_KEY
    url = "http://api.shopstyle.com/api/v2/categories?pid=uid7936-31095456-22&cat=women&depth=2"
    logging.info(url)
    cats = safeGet(url)
    if not cats == None:
        cats_request_json = cats.read()
        return json.loads(cats_request_json)

def getRating(brand):

    data = memcache.get(key=brand)
    if data is not None:
        logging.info("from memcash: " + str(data))
        return data
    else:
        sbrand = brand.split()
        addBrand = ""
        val = ""
        # separate multiword brands with + signs for url
        if len(sbrand) > 1:
            for i in range(0, len(sbrand) - 1):
                addBrand = sbrand[i] + "+"
            addBrand = addBrand + sbrand[len(sbrand) - 1]
        else:  # single word brand
            addBrand = brand

        url = "https://rankabrand.org/sustainable-luxury-brands/" + addBrand
        htmlstring = safeGet(url)
        if not htmlstring == None:  # there is an entry for x brand
            soup = BeautifulSoup(htmlstring, 'html.parser')
            scoreSpan = soup.find("span", {"class": "score"})
            if not scoreSpan == None:
                temp = unicode((scoreSpan.a).contents[0])
                temp = temp.encode('ascii', 'replace')
                val = temp.split("?")[0]
            else:  # brand has an entry but no score
                val =  1
        else:  # brand not entered on the sight
            val =  0
        memcache.add(key=brand, value=val, time=3600)
        return val

    #ANN TAYLOR and OLD NAVY brand names are not showin up


# pass a single dictionary to this and make a product object
class Product():
    """ A singular item of clothing """
    def __init__(self, product):
        self.imgSrc = product["image"]["sizes"]["Large"]["url"]
        self.bestImgSrc = product["image"]["sizes"]["Best"]["url"]
        self.name = product["name"].encode('ascii', 'replace')
        self.brandedName = product["brandedName"].encode('ascii', 'replace')
        self.price = int(product["price"])
        self.retailer = product["retailer"]["name"].encode('ascii', 'replace')
        self.description = product["description"]
        # if a brand has a special character, it may not be included in json
        if "brand" in product:
            self.brand = product["brand"]["name"].encode('ascii', 'replace')
            self.brandRating = getRating(self.brand)
        else:
            self.brand = ""
            self.brandRating = 0
        numfilled = round(int(self.brandRating) / 6.0)
        self.filled = int(numfilled)
        self.unfilled = 6 - int(numfilled)
        self.locale = product["locale"]
        self.url = product["clickUrl"]
        self.id = product["id"]
        # <!--  value.0.name  --> to get just the first value in jinja

    def __str__(self):
        return ("%s, $%s, Retailer: %s" % (self.name, str(self.price), self.retailer))

class Category():
    """"A category that exists on ShopStyle"""
    def __init__(self, category):
        self.name = category["name"]
        self.id = category["id"]
        firstitem_data = getClothes(self.id, 1)
        #currently displays the most popular item, not the most popular and "greenest"
        firstitem = firstitem_data["products"][0]
        #firstitem = Product(firstitem)
        self.imgSrc = firstitem["image"]["sizes"]["Large"]["url"]

# sort a list of Product objects based on their brandRating and return the sorted list
def sortClothes(type):
    masterd = {}
    clothes_data = getClothes(type, 20)
    # the json response data containing ten clothes items of a specified type
    allClothes = clothes_data["products"]
    objectList = []
    for single in allClothes:
        newitem = Product(single)
        objectList.append(newitem)

    sortClothes = sorted(objectList, key=lambda k: int(k.brandRating), reverse=True)
    masterd[type] = sortClothes
    return masterd

# masterd =  {'sweaters': ['Product1', 'Proudct2', 'Product3 '],
# 'jeans' : ['Product1', 'Proudct2', 'Product3 '],
#  'tops' : ['Product1', 'Proudct2', 'Product3 '],}
JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
                                       extensions=['jinja2.ext.autoescape'],
                                       autoescape=True)


class MainHandler(webapp2.RequestHandler):
    def get(self):
        tvals = {}
        masterd = {}
        # get all the general categories of clothes in women's fashion
        response = getCategories()
        allCats = response["categories"]
        objectList = []
        for single in allCats:
            #make Category instances with category name and image url
            newitem =  Category(single)
            objectList.append(newitem)
        masterd["cats"] = objectList # masterd["cats"] is a list of category objects
        tvals['md'] = masterd
        template = JINJA_ENVIRONMENT.get_template('homepagetemplate.html')
        self.response.write(template.render(tvals))

class ProductsHandler(webapp2.RequestHandler):
    def get(self):
        cat = self.request.get("cat")
        tvals = {}
        masterd = sortClothes(cat)
        tvals['md'] = masterd
        template = JINJA_ENVIRONMENT.get_template('productpagetemplate.html')
        self.response.write(template.render(tvals))

class SingleHandler(webapp2.RequestHandler):
    def get(self):
        pid = self.request.get("id")
        tvals = {}
        data = getSingle(pid)
        data = Product(data)
        logging.info(data)
        masterd = {}
        masterd[id] = data
        tvals['md'] = masterd
        template = JINJA_ENVIRONMENT.get_template('singleproducttemplate.html')
        self.response.write(template.render(tvals))

class WhyHandler(webapp2.RequestHandler):
    def get(self):
        logging.info("in Why Handler")
        template = JINJA_ENVIRONMENT.get_template('whypage.html')
        self.response.write(template.render())

class WhatHandler(webapp2.RequestHandler):
    def get(self):
        logging.info("in What Handler")
        template = JINJA_ENVIRONMENT.get_template('whatpage.html')
        self.response.write(template.render())



application = webapp2.WSGIApplication([ \
                                        ('/' , MainHandler),
                                        ('/products', ProductsHandler),
                                        ('/id', SingleHandler),
                                        ('/why', WhyHandler),
                                        ('/what', WhatHandler),
                                        ('/.*', MainHandler)
                                     #'/', #generates homepage # this should be new code to use the cat api
                                     #'/products'   , ProductsHandler # this should be what is currently in te main handler
                                      ],
                                    debug=True)

# to do paging
#
# offset = page number * 10 -1
# for doing pagination with the rrquests


# if page number is 1, show only a next
# if page number is greater than 1, forward and backward page is page nuber + 1 _ 1
# dynamically generate the links

#dynamically generate the categories and the images to display




