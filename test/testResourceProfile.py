import unittest
from src.parser import ResourceProfileParser, wordSimplificationEng
from glob import iglob
from PIL import Image
from Levenshtein import ratio

# @unittest.skip()
class Test_MainProfile(unittest.TestCase):

    MIN_EQUALS = 0.7

    def testingResourceProfile1(self):

        realName = 'Haron'
        realResource = {
            'сплавы': 19200,
            'вторсырье': 18000
        }
        path = r'test\resource\resource\resource1.png'

        self.equalResourceAndName(path, realName, realResource)
        
    def testingResourceProfile2(self):

        realName = 'JollyRay'
        realResource = {
            'наноспоры': 200000,
            'неироды': 1000
        }
        path = r'test\resource\resource\resource2.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile3(self):

        realName = '.NizelBack'
        realResource = {
            'галлии': 600,
            'вторсырье': 1084954,
            'неиронные датчики': 200,
            'оксиум': 44500,
            'пластиды': 20000,
            'полимеры': 266607,
            'рубедо': 100000,
            'сплавы': 300000,
        }
        path = r'test\resource\resource\resource3.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile4(self):

        realName = 'Haron'
        realResource = {
            'сплавы': 19200,
            'вторсырье': 18000
        }
        path = r'test\resource\resource\resource1.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile5(self):

        realName = 'GodFather_999'
        realResource = {
            'сплавы': 11200,
            'вторсырье': 10500
        }
        path = r'test\resource\resource\resource5.png'

        self.equalResourceAndName(path, realName, realResource)
                 
    def testingResourceProfile6(self):

        realName = 'Th3tty'
        realResource = {
            'наноспоры': 58200,
            'феррит': 46560,
        }
        path = r'test\resource\resource\resource6.png'

        self.equalResourceAndName(path, realName, realResource)
                 
    def testingResourceProfile7(self):

        realName = 'reaper_of_fate'
        realResource = {
            'наноспоры': 34000,
            'вторсырье': 25500
        }
        path = r'test\resource\resource\resource7.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile8(self):

        realName = 'ZEGUTMEN'
        realResource = {
            'вторсырье': 7500,
            'сплавы': 8000
        }
        path = r'test\resource\resource\resource8.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile9(self):

        realName = 'Sivataron'
        realResource = {
            'феррит': 9600,
            'сплавы': 9600
        }
        path = r'test\resource\resource\resource9.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile10(self):

        realName = 'Pesee'
        realResource = {
            'галлии': 27,
            'вторсырье': 13500
        }
        path = r'test\resource\resource\resource10.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile11(self):

        realName = 'Mad_Beaver'
        realResource = {
            'наноспоры': 12000,
            'вторсырье': 9000,
            'полимеры': 6000,
            'феррит': 9600,
            'сплавы': 9600
        }
        path = r'test\resource\resource\resource11.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile12(self):

        realName = 'Mr_Bionic'
        realResource = {
            'вторсырье': 15000,
            'рубедо': 10000,
            'наноспоры': 20000,
            'феррит': 20000
        }
        path = r'test\resource\resource\resource12.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile13(self):

        realName = 'Ne4tuneoS'
        realResource = {
            'астерит': 135,
            'изос': 90
        }
        path = r'test\resource\resource\resource13.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile14(self):

        realName = 'Arichidonome'
        realResource = {
            'вторсырье': 10500,
            'криотик': 3500
        }
        path = r'test\resource\resource\resource14.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile15(self):

        realName = 'Arorias87'
        realResource = {
            'наноспоры': 12000,
            'сплавы': 9600
        }
        path = r'test\resource\resource\resource15.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile16(self):

        realName = 'ShadowPhoenix911'
        realResource = {
            'феррит': 26000,
            'вторсырье': 15000
        }
        path = r'test\resource\resource\resource16.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile17(self):

        realName = 'LynxShadow'
        realResource = {
            'наноспоры': 58200,
            'вторсырье': 43650
        }
        path = r'test\resource\resource\resource17.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile18(self):

        realName = 'rdss0'
        realResource = {
            'феррит': 3200,
            'полимеры': 2000,
        }
        path = r'test\resource\resource\resource18.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile19(self):

        realName = 'Waimmerlin'
        realResource = {
            'наноспоры': 10000,
            'галлии': 15
        }
        path = r'test\resource\resource\resource19.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile20(self):

        realName = 'Zanaza'
        realResource = {
            'оксиум': 9000,
            'рубедо': 35000,
            'наноспоры': 60000
        }
        path = r'test\resource\resource\resource20.png'

        self.equalResourceAndName(path, realName, realResource)

    def testingResourceProfile21(self):

        realName = 'Rusty_Mordasty'
        realResource = {
            'феррит': 27200,
            'сплавы': 27200,
        }
        path = r'test\resource\resource\resource21.png'

        self.equalResourceAndName(path, realName, realResource)

    def equalResourceAndName(self, path, realName, realResource):

        with Image.open(path) as resourceImage:

            rpp = ResourceProfileParser(resourceImage)

            resourceCollect = {}
            for resource, value in rpp.resource.items():
                resourceCollect[resource.getName('rus')] = value

            self.assertEqual(realResource, resourceCollect, msg = f'Name: {realName}\nResource:\n{resourceCollect}\n{realResource}' )
            self.assertGreater(ratio(realName, rpp.userName, processor=wordSimplificationEng), self.MIN_EQUALS, msg = f'User {realName} - {rpp.userName}')
