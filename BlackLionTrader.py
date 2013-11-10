#!/usr/bin/env python

import sys, os
import urllib, json
from operator import itemgetter, attrgetter
import datetime
import heapq

import pickle


import util
from HTTP_Singleton import HTTP_Singleton

from TradingPost import TradingPostOrder, TradingPostRecipe, TradingPostItem, TradingPostItemDict

import threading
class BlackLionTrader(threading.Thread):
    kill = False
    verbosity = 0
    item = TradingPostItemDict()
    recipe_items = []
    
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        super(BlackLionTrader, self).__init__(group=group, target=target, name=name, *args, **kwargs)
        
        try:
            self.pickle_file = os.path.join(os.path.dirname(__file__), "item_db.pickle")
        except:
            self.pickle_file = os.path.join(os.getcwd(), "item_db.pickle")
            
        self.client = HTTP_Singleton()
        self.client.authenticate()

        if os.path.exists(self.pickle_file):
            self.load()
        else:
            self.pull_batch_recipes()
            self.save()

        

    def save(self):
        pickle.dump(self.item, open(self.pickle_file, "wb" ))
            
    def load(self):
        self.item = pickle.load(open(self.pickle_file, "rb" ))
        self.recipe_items = [self.item[i] for i in self.item]

    def set_verbosity(self, value):
        self.verbosity = value
    
    '''
    def pull_batch_listings(self):
        util.STDOUT.write("Fetching Item Listings")
        
        url = "https://tradingpost-live.ncplatform.net/ws/search?" 
        headers = {'Cookie': "s="+self.client._session_id}
        count = 500
        offset = -count
        total_count = max(len(self.item), 30000)
        while offset <= total_count:
            offset += count
            
            util.STDOUT.write("\nFetching " + str(offset) +" -> " + str(offset+count) + " of " + str(total_count))
            request_time = datetime.datetime.now()
            response, content = self.client.request(url + urllib.urlencode({'count':count, 'offset':offset}), "GET", headers=headers)
            if response.status != 200:
                print response.status
                continue
            
            response_data = json.loads(content)

            total_count = int(response_data.get('total', total_count))
            results = response_data.get('results', None)
            
            if not results:
                print response_data
                continue
                
            for ritem in results:
                item_id = ritem.get('data_id', None)
                if not item_id:
                    continue
                self.item[item_id].id = item_id
                
                name = ritem.get('name', "")
                level = ritem.get('level', None)
                if level and level != "0":
                    name += " (lvl: "+str(level)+")"
                self.item[item_id].name = name
                
                value = ritem.get('sell_price', None)
                if value:
                    self.item[item_id].sell_orders = [TradingPostOrder(1, value)]
                
                value = ritem.get('buy_price', None)
                if value:
                    self.item[item_id].buy_orders = [TradingPostOrder(1, value)]
            
        util.STDOUT.write("\n")
    '''
    
    def pull_batch_recipes(self):
        import heapq
        self.recipe_items = []
        util.STDOUT.write("Fetching Recipes")
        
        resp, content = self.client.request("https://api.guildwars2.com/v1/recipes.json", "GET")
        if resp.status != 200:
            util.STDOUT.write("\n")
            util.STDERR.write("Error ("+str(resp.status)+") GET'ing recipe list\n")
            return
        
        recipe_list = json.loads(content)
        progress_total = len(recipe_list['recipes'])
        progress_current = 0
        util.STDOUT.write(str(0).rjust(3) + "%")
        for recipe_id in recipe_list['recipes']:
            if progress_current % 50 == 1:
                util.STDOUT.write('\b'*4 + str( int(progress_current*100.0/progress_total)  ).rjust(3) + "%")
            progress_current += 1
            
            resp, content = self.client.request("https://api.guildwars2.com/v1/recipe_details.json?recipe_id="+str(recipe_id), "GET")
            if resp.status != 200:
                util.STDERR.write("Error ("+str(resp.status)+") retrieving recipe:" + str(recipe_id) + "\n")
                continue
            
            response_data = json.loads(content)
            _id = response_data.get('output_item_id', None)
            if not _id:
                util.STDERR.write("Error parsing recipe:" + str(recipe_id) + "\n")
                continue
            
            _recipe = TradingPostRecipe()
            for x in response_data.get('ingredients', []):
                _recipe.add_ingredient(int(x['count']), self.item[x['item_id']])
            _recipe.serving = int(response_data.get('output_item_count', 1))
            for f in response_data.get('flags', []):
                _recipe.add_flag(f)
            
            _rating = response_data.get('min_rating','0')
            for d in response_data.get('disciplines', []):
                _recipe.add_discipline(str(d) +" " + str(_rating))
            
            self.item[_id].recipes.append(_recipe)

            self.recipe_items.append(self.item[_id])
        util.STDOUT.write("\n")
        
        

    class ProductionItem(object):
        def __init__(self, item):
            self._item = item

    class CostWeightedPrduction(ProductionItem):
        def __init__(self, *args, **kwargs):
            super(BlackLionTrader.CostWeightedPrduction, self).__init__(*args, **kwargs)

        def __cmp__(self, other):
            if not isinstance(other, BlackLionTrader.CostWeightedPrduction):
                raise NotImplementedError

            lhv = self._item.recipe_cost_per_unit
            rhv = other._item.recipe_cost_per_unit
            if lhv > rhv:
                return 1
            elif rhv > lhv:
                return -1
            return 0
        

    def profitable_crafting_items(self):
        self.profitable_items = {'Errors':[]}
        self.locks = {'Errors_lock':threading.Lock()}
        loop_count = 0

        for item in self.recipe_items:
            if self.kill:
                break;

            cmp_class = BlackLionTrader.CostWeightedPrduction
            try:
                item_qty, item_price = item.crafting_profit(verbosity = self.verbosity)
                if item_price > 0 and item_qty > 0:
                    disciplines = map(lambda d: d.split(' ')[0], item.recipe_disciplines)
                    for d in disciplines:
                        self.locks.setdefault(d+"_lock", threading.Lock()).acquire(True)
                        heapq.heappush( self.profitable_items.setdefault(d, []), cmp_class(item))
                        self.locks.get(d+"_lock").release()
                    
                        if self.verbosity >= 1:
                            util.STDOUT.write(str(item) + " " + str(item.best_recipe._disciplines) + " Is Profitable \n")
            except:
                if self.verbosity >= 1:
                    util.STDERR.write("Error on item " + str(item.id) + "\n")
                self.locks.setdefault("Errors_lock", threading.Lock()).acquire(True)
                self.profitable_items.get('Errors', []).append(cmp_class(item))
                self.locks.get("Errors_lock").release()
            loop_count+=1
            if self.verbosity >= 1:
                util.STDOUT.write( str(float(loop_count) * 100 / len(self.recipe_items)) + "%\n")
                
        util.STDOUT.write("Done\n")
        return

    run = profitable_crafting_items

    def thread_controller(self):
        while True:
            try:
                util.STDOUT.write("Choose Discipline:\n")
                for discipline in self.profitable_items.keys():
                    util.STDOUT.write("\t"+str(discipline)+"\n")
                util.STDOUT.write("\tRefresh\n\tKill\n")

                discipline = raw_input()

                if discipline == "Refresh":
                    continue
                elif discipline == "+v":
                    self.verbosity += 1
                    continue
                elif discipline == "-v":
                    self.verbosity -= 1
                    continue
                
                elif discipline == "Kill":
                    util.STDOUT.write("Killing thread\n")
                    self.kill = True
                    break

                elif discipline[:5] == "exec ":
                    exec discipline[5:]
                    continue
                
                
                if not self.locks.get(discipline+"_lock").acquire(False):
                    util.STDOUT.write("Could not acquire: "+discipline+"_lock\n")
                    continue
                
                hq = self.profitable_items.get(discipline, [])
                top_5 = []
                try:
                    for i in range(0,5):
                        top_5.append(heapq.heappop(hq)._item)
                except IndexError:
                    pass
                except Exception as e:
                    util.STDERR.write(str(e)+"\n")
                    
                self.locks.get(discipline+"_lock").release()
                
                for i in top_5:
                    qty, profit = i.crafting_profit(verbosity = self.verbosity)
                    util.STDOUT.write(i.detailed_recipe(qty))
                    util.STDOUT.write("Make "+ str(qty) +" for total profit: " + util.gold_repr(profit) + "\n")
                    for k, v in i.get_shoping_list(qty).iteritems():
                        util.STDOUT.write(str(v) + " x " + str(k))
                
            except Exception as e:
                util.STDERR.write(str(e)+"\n")
        
        
if __name__ == "__main__":
    blt = BlackLionTrader()
    
    blt.set_verbosity(1)
    blt.start()
    blt.thread_controller()
    
