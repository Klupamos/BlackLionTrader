import sys
import datetime
from HTTP_Singleton import HTTP_Singleton
import json


import util

class TradingPostOrder(object):
    def __init__(self, qty = 0, value = 0):
        self.qty = int(qty)
        self.value = int(value)

    def __repr__(self):
        return str(self.qty) + " @ " + util.gold_repr(self.value)



'''
Verbosity levels
1)
listing fetch error
listing parse error
Recipe Expense

3)
listing cache
'''


class TradingPostRecipe(object):
    def __init__(self):
        self._disciplines = []
        self._ingredients = []
        self._serving_size = 1
        self._flags = []

    @property
    def cost(self):
        _cost = 0
        for i in self._ingredients:
            _cost += i[0] * i[1].best_price()
        return _cost or float("inf")

    @cost.setter
    def cost(self, value):
        raise ValueError

    @property
    def serving(self):
        return self._serving_size

    @serving.setter
    def serving(self, value):
        self._serving_size = value

    def add_ingredient(self, qty, item):
        if isinstance(item, TradingPostItem):
            self._ingredients.append((qty, item, ))
        
    def add_flag(self, flag):
        self._flags.append(flag)

    def add_discipline(self, discipline):
        self._disciplines.append(discipline)
    
    def cost_per_unit(self):
        return self.cost / self.serving






class TradingPostItem(object):
    locations = {'Vendor':1, 'Crafting':2, 'Trading Post':3, }
    listing_timer = datetime.timedelta(minutes=15)
    default_recipe = TradingPostRecipe()
    
    def __init__(self, id_ = -1, name = None):
        self._id = int(id_)
        self._name = name
        self.best_location = TradingPostItem.locations['Trading Post']
        self.vendor_price = float("inf")
        self.buy_orders = []
        self.sell_orders = []
        self.recipes = []
        self.last_listing_update = datetime.datetime(2013, 1, 1)

    def __repr__(self):
        return "("+str(self.id)+")"+self.name
        

    @property
    def name(self):
        name_str = self._name
        if not self._name:
            client = HTTP_Singleton()
            resp, content = client.request("https://api.guildwars2.com/v1/item_details.json?item_id="+str(self.id), "GET")
            response_data = json.loads(content)
            name_str = self._name = response_data.get('name', None)
            
            if not self._name:
                name_str = "id: "+str(self.id)

        return name_str

    @name.setter
    def name(self, value):
        if value:
            self._name = value


    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        raise ValueError

    @property
    def best_recipe(self):
        _recipe = TradingPostItem.default_recipe
        for this_recipe in self.recipes:
            if this_recipe.cost < _recipe.cost:
                _recipe = this_recipe
        return _recipe 

    @best_recipe.setter
    def best_recipe(self, value):
        raise ValueError
        
    def best_price(self, verbosity=0):
        self.retrieve_listings(verbosity)
        
        running_best = float("inf")
        if self.sell_orders and self.sell_orders[0].value < running_best:
            running_best = self.sell_orders[0].value
            self.best_location = TradingPostItem.locations["Trading Post"]

        if self.best_recipe.cost < running_best:
            running_best = self.best_recipe.cost
            self.best_location = TradingPostItem.locations["Crafting"]
            
        if self.vendor_price < running_best:
            running_best = self.vendor_price
            self.best_location = TradingPostItem.locations["Vendor"]
            
        return running_best

    def average_buy_order(self):
        self.retrieve_listings()
        count = 0
        value = 0
        for order in self.buy_orders:
            count += order.qty
            value += order.value
        avg = value/float(count)
        return TradingPostOrder(count,avg)
        
    def average_sell_order(self):
        self.retrieve_listings()
        count = 0
        value = 0
        for order in self.sell_orders:
            count += order.qty
            value += order.qty * order.value
        avg = value/float(count)
        return TradingPostOrder(count,avg)

    def best_location_name(self):
        self.best_price()
        try:
            return TradingPostItem.locations.keys()[TradingPostItem.locations.values().index(self.best_location)]
        except:
            return "Unknown location value"

    def retrieve_listings(self, verbosity=0):
        if self.last_listing_update + TradingPostItem.listing_timer > datetime.datetime.now():
            if verbosity >= 3:
                util.STDERR.write("Using cached listings for "+str(self)+"\n")
            return 200
        
        client = HTTP_Singleton()
        client.authenticate()
        
        url = "https://tradingpost-live.ncplatform.net/ws/listings.json?id=" + str(self.id)
        headers = {'Cookie': "s="+client._session_id}
        
        response, content = client.request(url, "GET", headers = headers, verbosity=verbosity)
        if response.status != 200:
            if verbosity >= 1:
                util.STDERR.write(str(response.status)+" while fetching "+str(self)+" listing\n")
            return response.status

        response_data = json.loads(content)
        listings = response_data.get('listings', None)
        
        if listings is not None: # could be an empty dict
            buys = listings.get('buys', None)
            if buys:
                self.buy_orders = []
                for tran in response_data['listings']['buys']:
                    self.buy_orders.append(TradingPostOrder(tran['quantity'], tran['unit_price']))

            sells = listings.get('sells', None)
            if sells:
                self.sell_orders = []
                for tran in response_data['listings']['sells']:
                    self.sell_orders.append(TradingPostOrder(tran['quantity'], tran['unit_price']))
            self.last_listing_update = datetime.datetime.now()
        elif verbosity >= 1:
            util.STDERR.write("Could not parse listings for " + str(self) + "\n")
        return 200

    def get_shoping_list(self, qty=1):
        if self.best_location_name() !=  'Crafting': 
            return {self:qty}

        _shoping_list = {}
        for sub_qty, sub_item in self.best_recipe._ingredients:
            for k, v in sub_item.get_shoping_list().iteritems():
                _shoping_list[k] = _shoping_list.get(k, 0) + qty * sub_qty * v / self.best_recipe.serving

        return _shoping_list

    def detailed_recipe(self, make_qty=1, verbosity=0):
        if self.best_location_name() !=  'Crafting':
            # Name    Price @ Locations
            return self.name.ljust(45)+util.gold_repr(self.best_price()).rjust(12) + " @ " + self.best_location_name() + "\n"

        # Name  [Recipe_Disciplies][Recipe_Flags]
        part_str = self.name.ljust(45) + str(self.best_recipe._disciplines) + str(self.best_recipe._flags if self.best_recipe._flags else "") + "\n"
        
        # 10 x Name    Price @ Locations
        for sub_qty, sub_item in self.best_recipe._ingredients:
            part_str += str(make_qty * sub_qty / sub_item.best_recipe.serving) +" x "+ sub_item.detailed_recipe(make_qty * sub_qty / sub_item.best_recipe.serving)

        part_str = ("\n  ".join(part_str.split("\n")))[:-2]
        if verbosity >= 1:
            part_str += "Expense: " + util.gold_repr(self.best_price()) +" --- Revenue: "+ util.gold_repr(self.buy_orders[0].value * 0.85) + " --- Profit: "+ util.gold_repr(self.buy_orders[0].value*0.85 - self.best_price()) +"\n"
        return part_str

    def crafting_profit(self, verbosity=0):

        _recipe = self.best_recipe
        break_even_price = (_recipe.cost / _recipe.serving ) / 0.85
        profit = count = 0

        self.retrieve_listings(verbosity=verbosity)
        if self.best_location_name() == 'Crafting':
            for buyer in self.buy_orders:
                if buyer.value <= break_even_price:
                    break
                count += buyer.qty
                profit += buyer.qty*(buyer.value*0.85 - _recipe.cost)
                
        return count, profit
    





        
        


import collections
class TradingPostItemDict(collections.MutableMapping):
    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        if self.__keytransform__(key) not in self.store:
            self.store[self.__keytransform__(key)] = TradingPostItem(key)
            
        return self.store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self.store[self.__keytransform__(key)] = value
        

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __keytransform__(self, key):
        return int(key)


