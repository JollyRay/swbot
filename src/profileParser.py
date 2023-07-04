from PIL import Image
import numpy as np
from pytesseract import pytesseract, Output
from enum import Enum
import json
import os
from dotenv import load_dotenv
from math import sqrt, exp
from Levenshtein import ratio
from threading import Thread
import functools
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, wait
from threading import RLock

def timeout(timeout):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            res = [Exception('function [%s] timeout [%s seconds] exceeded!' % (func.__name__, timeout))]
            def newFunc():
                try:
                    res[0] = func(*args, **kwargs)
                except Exception as e:
                    res[0] = e
            t = Thread(target=newFunc)
            t.daemon = True
            try:
                t.start()
                t.join(timeout)
            except Exception as je:
                print ('error starting thread')
                raise je
            ret = res[0]
            if isinstance(ret, BaseException):
                raise ret
            return ret
        return wrapper
    return deco

def loadParam() -> str:

    if pytesseract.tesseract_cmd != 'tesseract':
        return None
    
    load_dotenv()
    
    pytesseract.tesseract_cmd = os.getenv('PYTESSERACT')

    with open('resource/data.json', encoding='utf8') as dataFile:
        data: dict[str, any] = json.load( dataFile )
    
    if 'all_resource' in data.keys():
        ResourceProfileParser.setAllResource(data['all_resource'])
    else:
        return 'Key is missing "all_resource"'
    
    if 'scaling_formula' in data.keys():
        Resource.setBaseScaling(data['scaling_formula'])
    else:
        return 'Key is missing "scaling_formula"'

    del data
    return None
    
#Utility
MINIMUM_PART_MATCH = 0.75

calcColorDifference = lambda firstPixle, secondPixel: abs(np.int16(firstPixle[0]) - np.int16(secondPixel[0])) + abs(np.int16(firstPixle[1]) - np.int16(secondPixel[1])) + abs(np.int16(firstPixle[2]) - np.int16(secondPixel[2]))

calcResourceEval = lambda rank, baseValue, formula: eval( formula, {'sqrt': sqrt, 'exp': exp, 'rank': rank, 'baseValue': baseValue} )

wordSimplificationEng = lambda word: word.strip().lower().replace('i', 'l')
wordSimplificationRus = lambda word: word.strip().lower().replace('ё', 'е').replace('й', 'и')

DIRECTION = Enum('Direction', ['NORTH', 'SOUTH', 'WEST', 'EAST'])

class ProfileParser:

    BONUS_MARGING = 8

    def __init__(self, fullProfileImage: Image.Image | str, isSave: bool = False) -> None:

        if type(fullProfileImage) is str:
            self.fullProfileImage = Image.open(fullProfileImage)
        else:
            self.fullProfileImage: Image.Image = fullProfileImage

        self.xSize, self.ySize = self.fullProfileImage.size

        self.language: str = 'eng'
        self.textColor: tuple[int] | None = None

        self._isSave = isSave

    def _selectSymbolColor(self, symbolImage: Image.Image, banColors: tuple[tuple, int], colorEps: int = 24):

        def isColorInBan(color: list[int]) -> bool:
            for banColor in banColors:
                if calcColorDifference(color, banColor) < colorEps:
                    return True
            return False

        pixels = np.array(symbolImage)
        pixels = np.reshape(pixels, (-1, pixels.shape[2]))
        extraPixel = np.apply_along_axis(isColorInBan, axis = 1, arr = pixels)

        pixels = np.delete(pixels, extraPixel, axis = 0)

        pixels[:3] = pixels[:3] // ( colorEps // 3 ) *  (colorEps // 3 )

        differenceColor = np.unique(pixels, return_counts = True, axis = 0)

        if len(differenceColor[0]) == 0:
            return None

        return tuple(differenceColor[0][np.argmax(differenceColor[1])][:3])
        
    def _setTextColor(self, injectorWord: str, startLineNumber: int = 0, dataFrameFindWord: pd.DataFrame | None = None, imageWithText: Image.Image | None = None, language: str | None = None) -> int:

        if language is None:
            language = self.language

        if imageWithText is None:
            imageWithText = self.fullProfileImage

        if dataFrameFindWord is None or dataFrameFindWord.ndim != 2:
            return -1

        lineNumber = startLineNumber

        seriesWithName = dataFrameFindWord.iloc[lineNumber:].loc[dataFrameFindWord['text'].str.contains(injectorWord, case = False)]

        if seriesWithName.empty:
            return -1
        

        xStart, yStart, width, height = seriesWithName.iloc[0][7:11].values
        coordinateCrop = (
            max(xStart - self.BONUS_MARGING, 0),
            max(yStart - self.BONUS_MARGING, 0),
            min(xStart + self.BONUS_MARGING + width, self.xSize),
            min(yStart + self.BONUS_MARGING + height, self.ySize)
        )

        imageWithInjection = imageWithText.crop(coordinateCrop)

        symblesOfWord = pytesseract.image_to_boxes(imageWithInjection, lang = language, output_type = Output.DICT)

        if len(symblesOfWord) == 0:
            return -1
        coordinateFirstSymbolCrop = (
            symblesOfWord['left'][0],
            symblesOfWord['bottom'][0],
            symblesOfWord['right'][0],
            symblesOfWord['top'][0]
        )

        banColor = (0, 0, 0) if xStart - self.BONUS_MARGING < 0 else imageWithInjection.convert('RGB').getpixel((0, 0))

        self.textColor = self._selectSymbolColor(imageWithInjection.crop(coordinateFirstSymbolCrop), (banColor, ))
                
        if self.textColor is None:
            return -1

        if self._isSave:
            Image.new('RGB', size = (100,100), color = self.textColor).save('result/color.png')

        return seriesWithName.index[0]

    def _convertImageOnContrast(self, mainImage: Image.Image, selectColor: tuple[int] | None = None, colorEsp: int = 128) -> Image.Image:

        if selectColor is None:
            selectColor = self.textColor

        if selectColor is None:
            return None

        pix = np.array(mainImage)
        if len(pix) > 0 and len(pix[0]) > 0:
            isWithAlpha = len(pix[0][0]) == 4

        for iter in range(pix.shape[0]):

            for jtor in range(pix.shape[1]):

                if calcColorDifference(pix[iter][jtor], selectColor) > colorEsp:

                    if isWithAlpha:
                        pix[iter][jtor] = [255, 255, 255, 255]
                    else:
                        pix[iter][jtor] = [255, 255, 255]

                else:

                    if isWithAlpha:
                        pix[iter][jtor] = [0, 0, 0, 255]

                        if iter != 0:
                            pix[iter-1][jtor] = [0, 0, 0, 255]
                    else:
                        pix[iter][jtor] = [0, 0, 0]

                        if iter != 0:
                            pix[iter-1][jtor] = [0, 0, 0]
                    
        return Image.fromarray(pix)

    def _getLimitHorizonBorder(self, rowNumber: int, columnNumber: int, pixelColor: list[np.uint8], colorEsp: int = 50, step: int = 1) -> tuple[int]:
        imgHorizonLine = self.fullProfileImage.crop((0, rowNumber, self.xSize, rowNumber + 1))
        pixelHorizonLine = np.array(imgHorizonLine)
        pixelHorizonLine = pixelHorizonLine.reshape(self.xSize, len(pixelHorizonLine[0][0]))
        
        leftLimit = columnNumber
        while leftLimit > step and calcColorDifference(pixelHorizonLine[leftLimit - step], pixelColor) < colorEsp:
            leftLimit -= step

        rightLimit = columnNumber
        while rightLimit < pixelHorizonLine.shape[0] - step and calcColorDifference(pixelHorizonLine[rightLimit + step], pixelColor) < colorEsp:
            rightLimit += step

        return (leftLimit, rightLimit)

    def _findFirstLineWithSpecialColor(self, lineNumber: int, colorEps: int = 50, minLineSize: int = 128, startBottomPixel: float | int = 0.1, where: Enum = DIRECTION.SOUTH):

        # Determination of direction

        if where is DIRECTION.NORTH or where is DIRECTION.SOUTH:
            coordinateCrop = (lineNumber, 0, lineNumber + 1, self.ySize)

            verticalLine = self.fullProfileImage.crop(coordinateCrop)
            colorLine = np.array(verticalLine)
            colorLine = colorLine.reshape(self.ySize, len(colorLine[0][0]))

            if type(startBottomPixel) is float:
                startBottomPixel = (int) (startBottomPixel * self.ySize)

        elif where is DIRECTION.WEST or where is DIRECTION.EAST:

            coordinateCrop = (0, lineNumber, self.xSize, lineNumber + 1)

            verticalLine = self.fullProfileImage.crop(coordinateCrop)
            colorLine = np.array(verticalLine)
            colorLine = colorLine.reshape(self.xSize, len(colorLine[0][0]))

            if type(startBottomPixel) is float:
                startBottomPixel = (int) (startBottomPixel * self.xSize)

        else:
            return None
        
        if where is DIRECTION.EAST or where is DIRECTION.NORTH:
            lastColor = colorLine[startBottomPixel]
            directionRange = range(startBottomPixel + 1, colorLine.shape[0], 1)
        else:
            lastColor = colorLine[-startBottomPixel]
            directionRange = range(colorLine.shape[0] - 1 - startBottomPixel, -1, -1)

        # Traversal of line

        for pixelIndex in directionRange:

            nowColor = colorLine[pixelIndex]
            # print(pixelIndex, nowColor, lastColor, calcColorDifference(nowColor, lastColor))

            if calcColorDifference(nowColor, lastColor) > colorEps:

                leftBorder, rightBorder = self._getLimitHorizonBorder(pixelIndex, lineNumber, nowColor)

                if rightBorder - leftBorder + 1 > minLineSize:
                    return (pixelIndex, leftBorder, rightBorder, nowColor)
                
            lastColor = nowColor

        return None
            
    def _generateLineWithSpecialColor(self, rowNumber: int, columnNumber: int, specialColor: list[np.uint8], colorEps: int = 50, minLineSize: int = 128):

        coordinateCrop = (columnNumber, 0, columnNumber + 1, rowNumber)
        vertiacalLine = self.fullProfileImage.crop(coordinateCrop)
        colorLine = np.array(vertiacalLine)
        colorLine = colorLine.reshape(rowNumber, len(colorLine[0][0]))

        isSeries = True

        for pixelIndex in range(colorLine.shape[0] - 1, -1, -1):
            nowColor = colorLine[pixelIndex]

            if calcColorDifference(nowColor, specialColor) < colorEps:

                if not isSeries:

                    leftBorder, rightBorder = self._getLimitHorizonBorder(pixelIndex, columnNumber, specialColor)

                    if rightBorder - leftBorder + 1 > minLineSize:
                        isSeries = True
                        yield (pixelIndex, leftBorder, rightBorder)
            else:
                isSeries = False

    _FORBIDDEN_SYMBOL = [' ', '#', '&', '\r', '\n', '\t']

    def _clearWord(self, line: str) -> str:

        #Choosing the longest word
        words = line.split()

        selectWord = ''

        for name in words:
            name = name.strip()
            if len(selectWord) < len(name):
                selectWord = name

        #Looking for last forbidden symbol
        firstForbiddenSymbol = 999
        for symbol in self._FORBIDDEN_SYMBOL:
            indexSymbol = selectWord.find(symbol)
            if indexSymbol != -1 and indexSymbol < firstForbiddenSymbol:
                firstForbiddenSymbol = indexSymbol
        
        #Delete extra symbols
        if firstForbiddenSymbol != -1:
            selectWord = selectWord[:firstForbiddenSymbol]

        return selectWord.strip()

class MainProfileParser(ProfileParser):

    #TODO: remove defualt clanNames
    def __init__(self, fullProfileImage: Image.Image | str, clanNames: list[str] = ['SacredWizardsCult', 'SacredWizardsDeceptio', 'SacredWizardsMortuus', 'SacredWizardsVita']) -> None:
        super().__init__(fullProfileImage)

        self.__userName: None | str = None
        self.__clanName: None | str = None
        self.__rank: None | int = None
        self.__clanNames = clanNames

        self.__generatorRowOfSpecialColor  = None

    __TOP_EXPERIENCE_AMOUNT = 140 / 222
    __BOTTOM_EXPERIENCE_AMOUNT = 170 / 222
    __SIDE_EXPERIENCE_AMOUNT = 210 / 560
    __EXPERIENCE_FOR_SUM_30_RANK = 2250000
    __EXPERIENCE_FOR_30_PLUS_RANK = 147500

    def __extractRank(self):

        if self.__generatorRowOfSpecialColor is None:
            self.__extractClanName()

            if self.__generatorRowOfSpecialColor is None:
                return None
            
        bottom, left, right = next(self.__generatorRowOfSpecialColor)
        top = next(self.__generatorRowOfSpecialColor)[0]
        height = bottom - top
        width = right - left

        coordinateCrop = (
                left + width * self.__SIDE_EXPERIENCE_AMOUNT,
                top + height * self.__TOP_EXPERIENCE_AMOUNT,
                right - width * self.__SIDE_EXPERIENCE_AMOUNT,
                top + height * self.__BOTTOM_EXPERIENCE_AMOUNT
            )
        
        experienceImage = self.fullProfileImage.crop(coordinateCrop)
        experienceStr = pytesseract.image_to_string(experienceImage, config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')
        exparienceInt = int(experienceStr)

        if exparienceInt < self.__EXPERIENCE_FOR_SUM_30_RANK:
            self.__rank = int( sqrt( 2 * exparienceInt / 5000 ) )
        else:
            self.__rank = 30 + int( ( exparienceInt - self.__EXPERIENCE_FOR_SUM_30_RANK ) / self.__EXPERIENCE_FOR_30_PLUS_RANK )

        return self.__rank

    __TOP_CLAN_NAME_BORDER_PROPROTION = 109/177
    __BOTTOM_CLAN_NAME_BORDER_PROPROTION = 140/177

    def __findClanName(self, topBorder: int, bottomBorder: int, leftBorder: int, rightBorder: int) -> str:
        clanSectorHeight = bottomBorder - topBorder

        topBorderSectorOfClanName = (int) (topBorder + clanSectorHeight * self.__TOP_CLAN_NAME_BORDER_PROPROTION)
        bottomBorderSectorOfClanName = (int) (topBorder + clanSectorHeight * self.__BOTTOM_CLAN_NAME_BORDER_PROPROTION)

        coordinateCrop = (leftBorder, topBorderSectorOfClanName, rightBorder, bottomBorderSectorOfClanName)

        clanNameImage = self.fullProfileImage.crop(coordinateCrop)

        return pytesseract.image_to_string(clanNameImage)

    __START_COLUMN_PROPOTION = 0.7
    __STEP_COLUMN_PROPOTION = 0.05

    def __extractClanName(self):

        iteration = 0

        while self.__START_COLUMN_PROPOTION + self.__STEP_COLUMN_PROPOTION * iteration < 1:

            try:

                leftMarge = (int) (self.xSize * (self.__START_COLUMN_PROPOTION + self.__STEP_COLUMN_PROPOTION * iteration))

                firstLineInfo = self._findFirstLineWithSpecialColor(leftMarge, where = DIRECTION.SOUTH)
                if firstLineInfo is None:
                    continue
                bottomBorder, leftBorder, rightBorder, specialColor = firstLineInfo
                generatorRowOfSpecialColor = self._generateLineWithSpecialColor(bottomBorder, leftBorder + 1, specialColor)

                next(generatorRowOfSpecialColor)
                bot = next(generatorRowOfSpecialColor)[0]
                top = next(generatorRowOfSpecialColor)[0]
                
                clanName = self.__findClanName(top, bot, leftBorder, rightBorder).strip()

                for exampleClanName in self.__clanNames:
                    if ratio(clanName, exampleClanName, processor = wordSimplificationEng) > MINIMUM_PART_MATCH:
                        self.__generatorRowOfSpecialColor = generatorRowOfSpecialColor
                        self.__clanName = exampleClanName
                        return clanName
                
            except StopIteration: pass
            finally:
                iteration += 1
        return None

    __FOR_LEFT_COLUMN_FOR_FIND_NAME_UNDERLINE = 7
    __TOP_MARGE_PROPOTION = 0.2
    __SIDE_MARGE_PROPOTION = 0.3

    def __extractUserName(self):

        pixelWithUnderLine, _, _, _ = self._findFirstLineWithSpecialColor(self.xSize - self.__FOR_LEFT_COLUMN_FOR_FIND_NAME_UNDERLINE, minLineSize = 1, startBottomPixel = 0, where = DIRECTION.NORTH)

        if pixelWithUnderLine == None:
            return None
        
        leftMarge = self.fullProfileImage.size[0] * self.__SIDE_MARGE_PROPOTION
        topMarge = pixelWithUnderLine * self.__TOP_MARGE_PROPOTION
        rightMarge = self.fullProfileImage.size[0] * ( 1 - self.__SIDE_MARGE_PROPOTION )

        coordinateCrop = (leftMarge, topMarge, rightMarge, pixelWithUnderLine)

        userNameImage = self.fullProfileImage.crop(coordinateCrop)

        usersName: list[str] = pytesseract.image_to_string(userNameImage)

        self.__userName = self._clearWord(usersName)
        return self.__userName

    @property
    def userName(self):
        if self.__userName is None:
            self.__userName = self.__extractUserName()
        return self.__userName

    @property
    def clanName(self):
        if self.__clanName is None:
            self.__clanName = self.__extractClanName()
        return self.__clanName

    @property
    def rank(self):
        if self.__rank is None:
            self.__rank = self.__extractRank()
        return self.__rank

    @property
    def isFull(self):
        return all((self.rank, self.clanName, self.userName))
    
    @property
    def isFullWithoutRank(self):
        return all((self.clanName, self.userName))

class Resource:

    BASE_SCALING = '1'

    MAX_RANK = 30

    @classmethod
    def setBaseScaling(cls, formulaStr: str):

        try:

            cls.BASE_SCALING = compile(formulaStr, '<string>', 'eval')
            
        except SyntaxError:

            return False
        
        return True
    
    def __init__(self, names: dict[str, str], baseValue: int, **otherScaling) -> None:
        
        self.names = names
        self.baseValue = baseValue

        self.otherSaling = {}

        for startRank, formula in otherScaling:

            try:

                self.otherSaling[int(startRank)] = compile(formula, '<string>', 'eval')

            except SyntaxError: pass

    def __str__(self):
        return f'''{self.names['rus']}'''

    def getQuantityOnRank(self, rank: int) -> int:

        maxRankForOtherScaling = -1

        for rankItar in self.otherSaling.keys():

            if rankItar <= rank and maxRankForOtherScaling < rankItar:
                maxRankForOtherScaling = rankItar

        if maxRankForOtherScaling == -1:

            return int( calcResourceEval(min(rank, self.MAX_RANK), self.baseValue, self.BASE_SCALING) )

        else:

            return int( calcResourceEval(min(rank, self.MAX_RANK), self.baseValue, self.otherSaling[maxRankForOtherScaling]) )

    def getName(self, language: str):
        return self.names[language]

    def isThisResource(self, words: str, language: str):
        quanityRight = 0
        realNameWords = self.names[language].split()

        for realNameWord in realNameWords:
            for word in words.split():

                if ratio(realNameWord, word, processor=wordSimplificationEng if language == 'eng' else wordSimplificationRus) > MINIMUM_PART_MATCH:
                    quanityRight += 1
                    break


        return quanityRight == len(realNameWords)

class ResourceProfileParser(ProfileParser):

    @staticmethod
    def __wordSimplification(word: str, language):
        if language == 'rus':
            return wordSimplificationRus(word)
        
        if language == 'eng':
            return wordSimplificationEng(word)
        
        return word

    ALL_RESOURCE: list[Resource] = None

    @classmethod
    def setAllResource(cls, allResource: list[dict[str, any]]):

        if allResource is None or len(allResource) == 0:
            return
        
        cls.ALL_RESOURCE: list[Resource] = []

        for resource in allResource:

            try: 
                names = { lang: cls.__wordSimplification(value, lang) for lang, value in resource['name'].items()}

                cls.ALL_RESOURCE.append(
                    Resource(names, resource['start_cost'], )
                )
            except KeyError: pass

    ALL_WORDS_FOR_SOURCH = {
        'eng': {
            'injector': '',
            'firstWord': '',
            'lastWord': ''
        },
        'rus': {
            'injector': 'клановые',
            'firstWord': 'Игрок',
            'lastWord': 'компоненты'
        }
    }

    def __init__(self, fullProfileImage: Image.Image | str, rank: int | None = None) -> None:
        super().__init__(fullProfileImage)

        self.__resourses: dict[Resource, int] = {}

        self.__userName: str | None = None
        self.__rank = rank
        self.__enoughQuantityResource = 0
        self.__resourceAddLocker = RLock()
        self.xStartResourse = None
        self.yStartResourse = None
        self.xCenterResourse = None
        self.cubeSideSize: float = 0
        self.grapBetweenCube: float = 0

        self._setParam()

    INTERVAL_BETWEEN_CELL_PROPORTION = 0.15
    Y_SIDE_EPS = 20

    def _setUserName(self, x: int, y: int, width: int, height: int) -> bool:

        coordinateCrop = (x - self.BONUS_MARGING, y - self.BONUS_MARGING, x + width + self.BONUS_MARGING, y + height + self.BONUS_MARGING)

        if coordinateCrop[0] < 0 or coordinateCrop[1] < 0 or coordinateCrop[2] >= self.xSize or coordinateCrop[3] >= self.ySize:
            return False    
        imageCrop = self.fullProfileImage.crop(coordinateCrop)
        if self._isSave:
            imageCrop.save('result/name.png')

        self.__userName: str = self._clearWord(pytesseract.image_to_string(imageCrop))

        return True

    def _chooseLanguage(self, imageCrop: Image.Image) -> bool:
        allWord: str = pytesseract.image_to_data(imageCrop, lang = 'rus')
        if self.ALL_WORDS_FOR_SOURCH['rus']['injector'] in allWord.casefold():
            self.language = 'rus'
        else:
            allWord: str = pytesseract.image_to_data(imageCrop, lang = 'eng')
            if self.ALL_WORDS_FOR_SOURCH['eng']['injector'] in allWord.casefold():
                self.language = 'eng'
            else:
                return False
        return True

    def __extractWordUnderHeader(self, lineNumber: int, dataFrameFindWord: pd.DataFrame) -> pd.DataFrame:
        firstWordUnderHeader = dataFrameFindWord[lineNumber:].loc[dataFrameFindWord['text'] == self.ALL_WORDS_FOR_SOURCH[self.language]['firstWord']]

        if firstWordUnderHeader.empty:
            return None
        
        wordHeight, pixelTop = firstWordUnderHeader.iloc[0][['height', 'top']]

        wordsUnderHeader = dataFrameFindWord[lineNumber:].loc[abs(dataFrameFindWord['top'] - pixelTop) < wordHeight/ 2]

        if wordsUnderHeader.empty:
            return None, None
        
        return wordsUnderHeader, wordsUnderHeader.tail(1).index[0]

    #TODO: Check on shor or lower names
    def _searchUserName(self, dataFrameFindWord: pd.DataFrame) -> bool:

        if dataFrameFindWord.ndim != 2 or dataFrameFindWord.shape[1] < 2:
            return False
        
        seriesWithName = dataFrameFindWord.iloc[1]

        if not self._setUserName(*seriesWithName[7:11]):
            return False
        
        return True

    # @param:
    #   lineNumber - is start header index
    #   allLine - all info about all words
    # @return:
    #   0* - is last line number in header
    #   1* - avg height header's 
    def _setXCenter(self, wordUnderHeader: pd.DataFrame) -> int:

        if wordUnderHeader.shape[0] != 2:
            return None
        
        leftLimit = wordUnderHeader.iloc[0]['left']
        rightLimit = wordUnderHeader.iloc[-1][['left', 'width']].sum()

        return round ( (rightLimit + leftLimit) / 2 )

    def __getBottomLimit(self, lineNumber: int, dataFrameFindWord: pd.DataFrame) -> int:

        wordLast = dataFrameFindWord[lineNumber:].loc[dataFrameFindWord['text'].str.contains(self.ALL_WORDS_FOR_SOURCH[self.language]['lastWord'], case = False)]
        if wordLast.empty:
            return None
        
        return wordLast.iloc[0][['top', 'height']].sum() + self.Y_SIDE_EPS

    def __getLeftEdgeCell(self, dataFrameFindWord: pd.DataFrame, xCenter: int):

        if dataFrameFindWord.shape[0] != 2:
            return None

        xWordFirst, wifthWordLast, xWordLast =  dataFrameFindWord[['width', 'left']].values.ravel()[[False, True, True, True]]
        
        return xCenter - ( wifthWordLast + xWordLast - xWordFirst)
    
    MAX_ROW_WITH_RESOURCE = 3
    MAX_COLUM_WITH_RESOURCE = 3

    def _setResource(self) -> bool:

        with ThreadPoolExecutor(9) as threadPool:

            threadWaitMarkers = []

            for rowNumebr in range(self.MAX_ROW_WITH_RESOURCE):
                for columnNumber in range(self.MAX_COLUM_WITH_RESOURCE):
                    threadWaitMarkers.append(threadPool.submit(self.__extractResourceFromCell, rowNumebr, columnNumber))
                    

            wait(threadWaitMarkers)
    
    def __extractResourceFromCell(self, rowNumber: int, columnNumber: int):
        coordinateCrop = [
            self.xStartResourse + (self.cubeSideSize + self.grapBetweenCube) * columnNumber - self.BONUS_MARGING,
            self.yStartResourse + (self.cubeSideSize + self.grapBetweenCube) * rowNumber - self.BONUS_MARGING, 
            self.xStartResourse + self.cubeSideSize + (self.cubeSideSize + self.grapBetweenCube) * columnNumber + self.BONUS_MARGING,
            self.yStartResourse +  self.cubeSideSize + (self.cubeSideSize + self.grapBetweenCube) * rowNumber + self.BONUS_MARGING
        ]

        if coordinateCrop[2] > self.xSize or coordinateCrop[3] > self.ySize:
            return

        cellImage = self.fullProfileImage.crop(coordinateCrop)
        cellImage = self._convertImageOnContrast(cellImage, self.textColor)
        if self._isSave:
            cellImage.save('result/a%d%d0.png' % (rowNumber, columnNumber))

        coordinateCrop = (0, 0, self.cubeSideSize, cellImage.size[1] / 4)
        valueImg = cellImage.crop(coordinateCrop)
        if self._isSave:
            valueImg.save('result/a%d%d1.png' % (rowNumber, columnNumber))
        valueResource: str = pytesseract.image_to_string(valueImg, config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')

        coordinateCrop = (0, cellImage.size[1] / 2, self.cubeSideSize, cellImage.size[1])
        nameImg = cellImage.crop(coordinateCrop)
        if self._isSave:
            nameImg.save('result/a%d%d2.png' % (rowNumber, columnNumber))
        nameResource: str = self.__wordSimplification(pytesseract.image_to_string(nameImg, lang = self.language), self.language)

        if nameResource == '':
            return
        
        for resourceIter in self.ALL_RESOURCE:
            
            if resourceIter.isThisResource(nameResource, self.language):
                self.__resourceAddLocker.acquire( timeout = 10)
                self.__resourses[resourceIter] = int(valueResource)

                if self.__rank is not None and resourceIter.getQuantityOnRank(self.__rank) <= self.__resourses[resourceIter]:

                    self.__enoughQuantityResource += 1

                self.__resourceAddLocker.release()
                return

    @timeout(20)
    def _setParam(self):

        #Choose languge 

        if not self._chooseLanguage(self.fullProfileImage):
            return False
        dataFrameFindWord: pd.DataFrame = pytesseract.image_to_data(self.fullProfileImage, lang = self.language, output_type = 'data.frame')
        dataFrameFindWord = dataFrameFindWord.dropna(subset = ['text', ]).reset_index()

        # Set Color

        lineNumber = self._setTextColor(self.ALL_WORDS_FOR_SOURCH[self.language]['injector'], dataFrameFindWord = dataFrameFindWord, imageWithText = self.fullProfileImage, language = self.language)
        
        xCenterResourse = self._setXCenter(dataFrameFindWord.iloc[lineNumber:lineNumber+2])
        self.xStartResourse: int = self.__getLeftEdgeCell(dataFrameFindWord.iloc[lineNumber:lineNumber+2], xCenterResourse)

        if lineNumber == -1:
            return False
        
        wordUnderHeader, lineNumber = self.__extractWordUnderHeader(lineNumber, dataFrameFindWord)

        # Select Name

        if not self._searchUserName(wordUnderHeader):
            return False

        # Find first cell

        self.yStartResourse: int = self.__getBottomLimit(lineNumber, dataFrameFindWord)

        # Set cell Size

        self.cubeSideSize = round( ( xCenterResourse - self.xStartResourse ) / ( 1.5 + self.INTERVAL_BETWEEN_CELL_PROPORTION ) )
        self.grapBetweenCube = round( self.cubeSideSize * self.INTERVAL_BETWEEN_CELL_PROPORTION )

        # Extract resource 
        self._setResource()

        return True

    @property
    def resource(self):
        return self.__resourses
    
    @property
    def userName(self):
        return self.__userName
    
    @property
    def enoughQuantityResource(self):
        return self.__enoughQuantityResource

# Load all data from /data.json

res = loadParam()

if not res is None:
    raise NameError(res)