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
def getClothes(type):
    base_url = "http://api.shopstyle.com/api/v2/products"
    apiKey = "pid=uid7936-31095456-22"
    filters = "&cat=%s&sort=Popular" % (type)
    clothes_request = "%s?%s%s" % (base_url, apiKey, filters)
    print (clothes_request)
    safe_request = safeGet(clothes_request)
    if not safe_request == None:
        clothes_request_json = safe_request.read()
        # print pretty(json.loads(clothes_request_json))
        return json.loads(clothes_request_json)


def getRating(brand):
    sbrand = brand.split()
    addBrand = ""
    # separate multiword brands with + signs for url
    if len(sbrand) > 1:
        for i in range(0, len(sbrand) - 1):
            addBrand = sbrand[i] + "+"
        addBrand = addBrand + sbrand[len(sbrand) - 1]
    else:  # single word brand
        addBrand = brand
    url = "https://rankabrand.org/sustainable-luxury-brands/" + addBrand
    #print url
    htmlstring = safeGet(url)
    if not htmlstring == None:  # there is an entry for x brand
        soup = BeautifulSoup(htmlstring, 'html.parser')
        scoreSpan = soup.find("span", {"class": "score"})
        if not scoreSpan == None:
            temp = unicode((scoreSpan.a).contents[0])
            temp = temp.encode('ascii', 'replace')
            return temp.split("?")[0]
        else:  # brand has an entry but no score
            return 1
    else:  # brand not entered on the sight
        return 0


# pass a single dictionary to this and make a product object
class Product():
    """ A singular item of clothing """

    def __init__(self, product):
        self.imgSrc = product["image"]["sizes"]["Large"]["url"]
        self.name = product["name"].encode('ascii', 'replace')
        self.price = product["price"]
        self.retailer = product["retailer"]["name"].encode('ascii', 'replace')
        # if a brand has a special character, it may not be included in json
        if "brand" in product:
            self.brand = product["brand"]["name"].encode('ascii', 'replace')
            self.brandRating = getRating(self.brand)
        else:
            self.brand = ""
            self.brandRating = 0
        self.locale = product["locale"]
        self.url = product["clickUrl"]
        self.id = product["id"]
        # <!--  value.0.name  --> to get just the first value in jinja

    def __str__(self):
        return ("%s, $%s, Retailer: %s" % (self.name, str(self.price), self.retailer))



def sortClothes(type):
    masterd = {}
    clothes_data = getClothes(type)
    # the json response data containing ten clothes items of a specified type
    allClothes = clothes_data["products"]
    objectList = []
    for single in allClothes:
        newitem = Product(single)
        objectList.append(newitem)

    sortClothes = sorted(objectList, key=lambda k: int(k.brandRating), reverse=True)
    masterd[type] = sortClothes
    return masterd

# for cat in masterd:
# for item in masterd[cat]:
# print item.name + ": " + str(item.brandRating)

# masterd =  {'sweaters': ['Product1', 'Proudct2', 'Product3 '],
# 'jeans' : ['Product1', 'Proudct2', 'Product3 '],
#  'tops' : ['Product1', 'Proudct2', 'Product3 '],}

# cannot get the individual product items to print as strings


JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
                                       extensions=['jinja2.ext.autoescape'],
                                       autoescape=True)


class MainHandler(webapp2.RequestHandler):
    def get(self):
        logging.info("In MainHandler")
        tvals = {}
        masterd = sortClothes("shoes")
        tvals['md'] = masterd
        template = JINJA_ENVIRONMENT.get_template('homepagetemplate.html')
        self.response.write(template.render(tvals))

class ProductsHandler(webapp2.RequestHandler):
    def get(self):
        # call getCloth
        cat = self.request.get("cat")
        logging.info(cat)
        # getClothes(cat)
        logging.info("In ProductsHandler")
        tvals = {}

        masterd = sortClothes(cat)

        tvals['md'] = masterd
        template = JINJA_ENVIRONMENT.get_template('productpagetemplate.html')
        self.response.write(template.render(tvals))

class SingleHandler(webapp2.RequestHandler):
    def get(self):
        pid = self.request.get("pid")
        logging.info(cat)
        logging.info("in Single Handler")
        # do i want to make another request or just use the information from before?

# for all URLs except alt.html, use MainHandler
application = webapp2.WSGIApplication([ \
                                        ('/' , MainHandler),
                                        ('/products', ProductsHandler),
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




