import sys
import datetime
import unittest

import util
import HTTP_Singleton
import TradingPost


class Recipe_Test(unittest.TestCase):
    def test_Default_Recipe(self):
        recipe = TradingPost.TradingPostRecipe()
        self.assertNotEqual(recipe, None)
        self.assertEqual(recipe.cost, float("inf"))
        self.assertEqual(recipe.serving, 1)
        

    def test_Add_Recipe_Item(self):
        recipe = TradingPost.TradingPostRecipe()
        recipe.add_ingredient(1, TradingPost.TradingPostItem(12345))
        self.assertNotEqual(recipe._ingredients, [])
        self.assertGreater(recipe.cost, 0)
        self.assertLess(recipe.cost, float("inf"))

    @unittest.expectedFailure
    def test_Set_Cost(self):
        recipe = TradingPost.TradingPostRecipe()
        recipe.cost = 10

    def test_Set_Serving(self):
        recipe = TradingPost.TradingPostRecipe()
        recipe.serving = 10
        self.assertEqual(recipe.serving, 10)
        

class Item_Test(unittest.TestCase):
    def setUp(self):
        HTTP_Singleton.HTTP_Singleton().authenticate()

    def test_Default_Constructor(self):
        item = TradingPost.TradingPostItem()
        self.assertNotEqual(item, None)

    def test_Named_Constructor(self):
        item = TradingPost.TradingPostItem(5, "PlaceHolder")
        self.assertEqual(item.name, "PlaceHolder")

    def test_Unnamed_Constructor(self):
        item = TradingPost.TradingPostItem(12345)
        self.assertEqual(item.name, "Strawberry Cookie")

    def test_Change_Name(self):
        item = TradingPost.TradingPostItem(5)
        item.name = "Valid Name"
        self.assertEqual(item.name, "Valid Name")

    @unittest.expectedFailure
    def test_Change_Id(self):
        item = TradingPost.TradingPostItem(0)
        item.id = 18

    def test_Retrieve_Id(self):
        item = TradingPost.TradingPostItem(12347)
        self.assertEqual(item.id, 12347)

    def test_Price(self):
        item = TradingPost.TradingPostItem(12345)
        self.assertGreater(item.best_price(), 0)
        
    def test_CraftProfit(self):
        item = TradingPost.TradingPostItem(12345)
        count, profit = item.crafting_profit()
        self.assertGreaterEqual(count, 0)
        self.assertGreaterEqual(profit, 0)
        
    def test_ShoppingList(self):
        item = TradingPost.TradingPostItem(12345)
        sl = item.get_shoping_list()
        self.assertNotEqual(sl, {})
        

class HTTP_Test(unittest.TestCase):
    def setUp(self):
        '''Creates a HTTP_Singleton for each class'''
        self.connection  = HTTP_Singleton.HTTP_Singleton()

    def tearDown(self):
        '''Destroys the HTTP_Singleton between tests'''
        self.connection._instance = None


    def test_singleton(self):
        '''Test for single instance of singleton'''
        self.assertIs(self.connection, HTTP_Singleton.HTTP_Singleton())      

    def test_session_cookie(self):
        '''Session cookie is set test'''
        self.connection.authenticate()
        
        self.assertNotEqual(self.connection._session_id, None)
        self.assertIsInstance(self.connection._session_valid_thru, datetime.datetime)
        self.assertGreater(self.connection._session_valid_thru, datetime.datetime.now(HTTP_Singleton.GMT_timezone()))

    def test_multi_auth(self):
        '''multiple calls to auth'''
        self.connection.authenticate()
        _id = self.connection._session_id
        _expire = self.connection._session_valid_thru

        self.connection.authenticate()
        self.assertEqual(self.connection._session_id, _id)
        self.assertEqual(self.connection._session_valid_thru, _expire)

    def test_session_timeout_is_UTC(self):
        '''Session timeout is UTC based'''
        self.connection.authenticate()
        _expire = self.connection._session_valid_thru
        self.assertNotEqual(_expire.tzinfo, None)


    def test_reauth(self):
        '''Re-authorize after failed request'''
        self.connection.authenticate()
        test_item = TradingPost.TradingPostItem(12345)
        response1 = test_item.retrieve_listings()

        self.connection._session_id = ""
        response2 = test_item.retrieve_listings()

        self.assertEqual(response1,response2)
    

class Gold_Test(unittest.TestCase):
    def test_gold_representation_positive(self):
        price = 500
        str_price = util.gold_repr(price)
        self.assertEqual(" 5s 00c", str_price)

    def test_gold_representation_zero(self):
        price = 0
        str_price = util.gold_repr(price)
        self.assertEqual(" 0c", str_price)

    def test_gold_representation_negative(self):
        price = -500
        str_price = util.gold_repr(price)
        self.assertEqual("-5s 00c", str_price)
        
    def test_gold_representation_large(self):
        price = 1234567
        str_price = util.gold_repr(price)
        self.assertEqual(" 123g 45s 67c", str_price)

    def test_gold_representation_small(self):
        price = 12
        str_price = util.gold_repr(price)
        self.assertEqual(" 12c", str_price)

    def test_gold_representation_copper(self):
        price = 5
        str_price = util.gold_repr(price)
        self.assertEqual(" 5c", str_price)

    def test_gold_representation_silver(self):
        price = 123
        str_price = util.gold_repr(price)
        self.assertEqual(" 1s 23c", str_price)

    def test_gold_representation_gold(self):
        price =  12345
        str_price = util.gold_repr(price)
        self.assertEqual(" 1g 23s 45c", str_price)

    def test_gold_representation_float(self):
        price =  12.5
        str_price = util.gold_repr(price)
        self.assertEqual(" 12c", str_price)

    def test_gold_representation_inf(self):
        price =  float("inf")
        str_price = util.gold_repr(price)
        self.assertEqual("Non gold value (inf)", str_price)

    def test_gold_representation_inf(self):
        price =  float("inf")
        str_price = util.gold_repr(price)
        self.assertEqual("Non gold value (inf)", str_price)

    def test_gold_representation_str(self):
        price =  "hamburger"
        str_price = util.gold_repr(price)
        self.assertEqual("Non gold value (hamburger)", str_price)

    def test_gold_representation_str2(self):
        price =  "34"
        str_price = util.gold_repr(price)
        self.assertEqual(" 34c", str_price)



        
if __name__ == "__main__":
    '''
    suite = unittest.TestLoader().loadTestsFromTestCase(Recipe_Test)
    sys.exit(unittest.TextTestRunner(verbosity=5).run(suite))
    '''
    unittest.main()
    '''
    #'''
