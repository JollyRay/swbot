from PIL import Image
import numpy as np
from pytesseract import pytesseract
from enum import Enum
import json
from time import sleep

def loadParam() -> str:
    pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    data = json.load( open('data.json', encoding='utf8') )

    if 'all_clans_name' in data.keys():
        MainProfileParser.allClansName = data['all_clans_name']
    else:
        return 'Key is missing "all_clans_name"'

    return None
    
#Utility
calcColorDifference = lambda firstPixle, secondPixel: abs(np.int16(firstPixle[0]) - np.int16(secondPixel[0])) + abs(np.int16(firstPixle[1]) - np.int16(secondPixel[1])) + abs(np.int16(firstPixle[2]) - np.int16(secondPixel[2]))

DIRECTION = Enum('Direction', ['NORTH', 'SOUTH', 'WEST', 'EAST'])

def levenstein(firstWord, secondWord):
    firstLen, secondLen = len(firstWord), len(secondWord)
    if firstLen > secondLen:
        firstWord, secondWord = secondWord, firstWord
        firstLen, secondLen = secondLen, firstLen

    currentRow = range(firstLen + 1)
    for iteratorLongWord in range(1, secondLen + 1):
        previousRow, currentRow = currentRow, [iteratorLongWord] + [0] * firstLen
        for iteratorShortWord in range(1, firstLen + 1):
            add, delete, change = previousRow[iteratorShortWord] + 1, currentRow[iteratorShortWord - 1] + 1, previousRow[iteratorShortWord - 1]
            if firstWord[iteratorShortWord - 1] != secondWord[iteratorLongWord - 1]:
                change += 1
            currentRow[iteratorShortWord] = min(add, delete, change)

    return currentRow[firstLen]

class ProfileParser:

    BONUS_MARGING = 8

    def __init__(self, fullProfileImage: Image.Image) -> None:
        self.fullProfileImage: Image.Image = fullProfileImage

        self.xSize, self.ySize = self.fullProfileImage.size

        self.language: str = 'eng'
        self.textColor: tuple[int] | None = None

    def _selectSymbolColor(self, symbolImage: Image.Image, banColors: tuple[tuple, int], colorEps: int = 25):

        def isColorInBan(banColors: tuple[tuple, int], color: list[int], colorEps: int) -> bool:
            for banColor in banColors:
                if calcColorDifference(color, banColor) < colorEps:
                    return True
            return False

        pixels = np.array(symbolImage)

        allColor = {}

        for pixelLine in pixels:

            for pixel in pixelLine:

                if not isColorInBan(banColors, pixel, colorEps):
                    
                    isFind = False

                    for nowColor in allColor.keys():

                        if calcColorDifference(pixel, nowColor) < colorEps:

                            isFind = True

                            allColor[nowColor] += 1

                            break
                    
                    if not isFind:

                        allColor[ (*pixel, ) ] = 1

        maxQuantity = max(*allColor.values())

        for color, quantity in allColor.items():
            
            if quantity == maxQuantity:
                Image.new('RGB', size= (1000, 100), color=color).save('b.png')
                return color[:3]
        
    def _setTextColor(self, injectorWord: str, startLineNumber: int = 1, allLine: list[str] | None = None, imageWithText: Image.Image | None = None, language: str | None = None) -> int:

        if language is None:
            language = self.language

        if imageWithText is None:
            imageWithText = self.fullProfileImage

        if allLine is None:
            allLine = pytesseract.image_to_data(imageWithText, lang = language).split('\n')

        lineNumber = startLineNumber

        while lineNumber < len(allLine):

            if injectorWord in allLine[lineNumber].casefold():

                lineItem = allLine[lineNumber].split()

                xStart, yStart, width, height = [int(item) for item in lineItem[6:10:1]]
                coordinateCrop = (
                        max(xStart - self.BONUS_MARGING, 0),
                        max(yStart - self.BONUS_MARGING, 0),
                        min(xStart + self.BONUS_MARGING + width, self.xSize),
                        min(yStart + self.BONUS_MARGING + height, self.ySize)
                    )
                
                imageWithInjection = imageWithText.crop(coordinateCrop)
                firstSymbol = pytesseract.image_to_boxes(imageWithInjection, lang = language).split()
                coordinateFirstSymbolCrop = (int(firstSymbol[1]), int(firstSymbol[2]), int(firstSymbol[1]) + int(firstSymbol[3]), int(firstSymbol[1]) + int(firstSymbol[4]))
                
                if xStart - self.BONUS_MARGING < 0:
                    banColor = (0, 0, 0)
                else:
                    banColor = imageWithInjection.convert('RGB').getpixel((0, 0))

                self.textColor = self._selectSymbolColor(imageWithInjection.crop(coordinateFirstSymbolCrop), (banColor, ))

                return lineNumber
            
            lineNumber += 1

        return -1

    def convertImageOnContrast(self, mainImage: Image.Image, selectColor: tuple[int] | None = None, colorEsp: int = 50) -> Image.Image:

        if selectColor is None:
            selectColor = self.textColor

        if selectColor is None:
            return None

        pix = np.array(mainImage)

        for iter in range(pix.shape[0]):

            for jtor in range(pix.shape[1]):

                if calcColorDifference(pix[iter][jtor], selectColor) > colorEsp:

                    pix[iter][jtor] = [255, 255, 255]

                else:

                    pix[iter][jtor] = [0, 0, 0]
                    
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

    FORBIDDEN_SYMBOL = [' ', '#', '&', '\r', '\n', '\t']

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
        for symbol in self.FORBIDDEN_SYMBOL:
            indexSymbol = selectWord.find(symbol)
            if indexSymbol != -1 and indexSymbol < firstForbiddenSymbol:
                firstForbiddenSymbol = indexSymbol
        
        #Delete extra symbols
        if firstForbiddenSymbol != -1:
            selectWord = selectWord[:firstForbiddenSymbol]

        return selectWord.strip()

class MainProfileParser(ProfileParser):
    allClansName = None

    _TOP_CLAN_NAME_BORDER_PROPROTION = 109/177
    _BOTTOM_CLAN_NAME_BORDER_PROPROTION = 140/177

    def _findClanName(self, topBorder: int, bottomBorder: int, leftBorder: int, rightBorder: int) -> str:
        clanSectorHeight = bottomBorder - topBorder

        topBorderSectorOfClanName = (int) (topBorder + clanSectorHeight * self._TOP_CLAN_NAME_BORDER_PROPROTION)
        bottomBorderSectorOfClanName = (int) (topBorder + clanSectorHeight * self._BOTTOM_CLAN_NAME_BORDER_PROPROTION)

        coordinateCrop = (leftBorder, topBorderSectorOfClanName, rightBorder, bottomBorderSectorOfClanName)

        clanNameImage = self.fullProfileImage.crop(coordinateCrop)

        return pytesseract.image_to_string(clanNameImage)

    _START_COLUMN_PROPOTION = 0.7
    _STEP_COLUMN_PROPOTION = 0.05

    def extractClanName(self):
        iteration = 0
        while self._START_COLUMN_PROPOTION + self._STEP_COLUMN_PROPOTION * iteration < 1:
            try:
                leftMarge = (int) (self.xSize * (self._START_COLUMN_PROPOTION + self._STEP_COLUMN_PROPOTION * iteration))

                bottomBorder, leftBorder, rightBorder, specialColor = self._findFirstLineWithSpecialColor(leftMarge, where = DIRECTION.SOUTH)
                generatorRowOfSpecialColor = self._generateLineWithSpecialColor(bottomBorder, leftBorder + 1, specialColor)

                next(generatorRowOfSpecialColor)
                bot = next(generatorRowOfSpecialColor)[0]
                top = next(generatorRowOfSpecialColor)[0]
                
                clanName = self._findClanName(top, bot, leftBorder, rightBorder).strip()
                if clanName in self.allClansName:
                    return clanName
            except StopIteration:
                pass
            finally:
                iteration += 1
        return None

    _FOR_LEFT_COLUMN_FOR_FIND_NAME_UNDERLINE = 7
    
    # Deprecated
    def _findLineUnerUserName(self, columnNumber: int = _FOR_LEFT_COLUMN_FOR_FIND_NAME_UNDERLINE, colorEPS: int = 50):

        coordinateCrop = (self.xSize - columnNumber, 0, self.xSize - columnNumber + 1, self.ySize)
        pixelColumn = self.fullProfileImage.crop(coordinateCrop)

        colorLine = np.array(pixelColumn)
        colorLine = colorLine.reshape(self.ySize, len(colorLine[0][0]))

        lastColor = colorLine[0]
        for pixelIndex in range(1, self.ySize):
            nowColor = colorLine[pixelIndex]
            if calcColorDifference(nowColor, lastColor) > colorEPS:
                return pixelIndex

    _TOP_MARGE_PROPOTION = 0.2
    _BOTTOM_MARGE_PROPOTION = 0.2
    _SIDE_MARGE_PROPOTION = 0.3

    def extractUserName(self):
        pixelWithUnderLine, _, _, _ = self._findFirstLineWithSpecialColor(self.xSize - self._FOR_LEFT_COLUMN_FOR_FIND_NAME_UNDERLINE, minLineSize = 1, startBottomPixel = 0, where = DIRECTION.NORTH)
        # pixelWithUnderLine = self.findLineUnerUserName()

        if pixelWithUnderLine == None:
            return None
        
        leftMarge = self.fullProfileImage.size[0] * self._SIDE_MARGE_PROPOTION
        topMarge = pixelWithUnderLine * self._TOP_MARGE_PROPOTION
        rightMarge = self.fullProfileImage.size[0] * ( 1 - self._SIDE_MARGE_PROPOTION )

        coordinateCrop = (leftMarge, topMarge, rightMarge, pixelWithUnderLine)

        userNameImage = self.fullProfileImage.crop(coordinateCrop)

        usersName: list[str] = pytesseract.image_to_string(userNameImage)

        return self._clearWord(usersName)

class ResourceProfileParser(ProfileParser):

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

    def __init__(self, fullProfileImage: Image, indentTopPropotion: float = 0.15, indentBottomPropotion: float = 0.5, indentSide: float = 0.2) -> None:
        super().__init__(fullProfileImage)

        self.indentTop: int = int(indentTopPropotion * self.ySize)
        self.indentBottom: int = int(indentBottomPropotion * self.ySize)
        self.indentSide: int = int(indentSide * self.xSize)

        self.__resourses = {}
        self.isValid: bool | None = None

        self.userName: str | None = None
        self.xStartResourse = None
        self.yStartResourse = None
        self.xCenterResourse = None
        self.cubeSideSize: float = 0
        self.grapBetweenCube: float = 0

    INTERVAL_BETWEEN_CELL_PROPORTION = 0.15
    Y_SIDE_EPS = 10

    def _setUserName(self, x: int, y: int, width: int, height: int) -> bool:
        coordinateCrop = (x + self.indentSide - self.BONUS_MARGING, y + self.indentTop - self.BONUS_MARGING, x + width + self.indentSide + self.BONUS_MARGING, y + height + self.indentTop + self.BONUS_MARGING)
        if coordinateCrop[0] < 0 or coordinateCrop[1] < 0 or coordinateCrop[2] >= self.xSize or coordinateCrop[3] >= self.ySize:
            return False    
        imageCrop = self.fullProfileImage.crop(coordinateCrop)
        imageCrop.save('name.png')

        self.userName: str = self._clearWord(pytesseract.image_to_string(imageCrop))

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

    #TODO: Check on shor or lower names
    def _searchUserName(self, lineNumber, allLine: list[str]) -> int:

        while lineNumber < len(allLine) - 1:

            if allLine[lineNumber].find(self.ALL_WORDS_FOR_SOURCH[self.language]['firstWord']) != -1:
                lineItem = allLine[lineNumber].split()

                lineItem = allLine[lineNumber + 1].split()
                if not self._setUserName(*[int(value) for value in lineItem[6:10:1]]):
                    return -1
                return lineNumber
            lineNumber += 1
        return -1

    # @param:
    #   lineNumber - is start header index
    #   allLine - all info about all words
    # @return:
    #   0* - is last line number in header
    #   1* - avg height header's 
    def _setXCenter(self, lineNumber: int, allLine: list[str]) -> int:
        xStart = int(allLine[lineNumber].split()[6])

        lineNumber += 2
        while lineNumber < len(allLine):
            if allLine[lineNumber].find(self.ALL_WORDS_FOR_SOURCH[self.language]['lastWord']) != -1:
                xLastWord = int(allLine[lineNumber].split()[6])
                widthLastWord = int(allLine[lineNumber].split()[8])
                
                self.xCenterResourse = round((xLastWord + widthLastWord + xStart) / 2 + self.indentSide)

                return lineNumber
            lineNumber += 1

        return -1

    def _setNorthEastEdgeCell(self, lineNumber: int, allLine: list[str], bottomEdge: int):

        while lineNumber < len(allLine):
            lineItem = allLine[lineNumber].split()
            if len(lineItem) == 12:

                xNow = int(lineItem[6])
                yNow = int(lineItem[7])

                if self.yStartResourse is None or yNow > bottomEdge and xNow < self.xStartResourse:
                    self.xStartResourse = xNow
                    self.yStartResourse = yNow

            lineNumber += 1
        
        self.xStartResourse += self.indentSide - self.BONUS_MARGING
        self.yStartResourse += self.indentTop - self.BONUS_MARGING

        return True

    MAX_ROW_WITH_RESOURCE = 3
    MAX_COLUM_WITH_RESOURCE = 3

    def _setResource(self):
        for columnNumber in range(self.MAX_COLUM_WITH_RESOURCE):
            for rowNumebr in range(self.MAX_ROW_WITH_RESOURCE):
                coordinateCrop = [
                        self.xStartResourse + (self.cubeSideSize + self.grapBetweenCube) * columnNumber - self.BONUS_MARGING,
                        self.yStartResourse + (self.cubeSideSize + self.grapBetweenCube) * rowNumebr - self.BONUS_MARGING, 
                        self.xStartResourse + self.cubeSideSize + (self.cubeSideSize + self.grapBetweenCube) * columnNumber + self.BONUS_MARGING,
                        self.yStartResourse +  self.cubeSideSize + (self.cubeSideSize + self.grapBetweenCube) * rowNumebr + self.BONUS_MARGING
                ]

                if coordinateCrop[2] > self.xSize or coordinateCrop[3] > self.ySize:
                    return

                cellImage = self.fullProfileImage.crop(coordinateCrop)
                cellImage = self.convertImageOnContrast(cellImage, self.textColor)
                cellImage.save('result/a%d%d0.png' % (rowNumebr, columnNumber))

                coordinateCrop = (0, 0, self.cubeSideSize, cellImage.size[1] / 4)
                valueImg = cellImage.crop(coordinateCrop)
                # valueImg.save('result/a%d%d1.png' % (rowNumebr, columnNumber))
                valueResource = pytesseract.image_to_string(valueImg, config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')

                coordinateCrop= (0, cellImage.size[1] / 2, self.cubeSideSize, cellImage.size[1])
                nameImg = cellImage.crop(coordinateCrop)
                # nameImg.save('result/a%d%d2.png' % (rowNumebr, columnNumber))
                nameResource = pytesseract.image_to_string(nameImg, lang = self.language)

                print('----------------------')
                print(nameResource, valueResource)


    def _setParam(self):

        coordinateCrop = (self.indentSide, self.indentTop, self.xSize - self.indentSide, self.indentBottom)
        imageCrop = self.fullProfileImage.crop(coordinateCrop)
        imageCrop.save('crop.png')

        #Choose languge 

        if not self._chooseLanguage(imageCrop):
            return False
        
        allWord: str = pytesseract.image_to_data(imageCrop, lang = self.language)
        allLine = allWord.split('\n')
        # print(allWord)

        # Set Color

        lineNumber = self._setTextColor(self.ALL_WORDS_FOR_SOURCH[self.language]['injector'], allLine = allLine, imageWithText = imageCrop, language = self.language)

        if lineNumber == -1:
            return False

        # Select Name

        lineNumber = self._searchUserName(lineNumber, allLine)

        if self.userName is None:
            return False
        
        # Set center header

        lineNumber = self._setXCenter(lineNumber, allLine)

        if lineNumber == -1:
            return False
        
        # Find first cell
        bottomEdge: int = int(allLine[lineNumber].split()[7]) + self.Y_SIDE_EPS
        if not self._setNorthEastEdgeCell(lineNumber + 1, allLine, bottomEdge):
            return False

        # Set cell Size
        self.cubeSideSize = round( ( self.xCenterResourse - self.xStartResourse ) / ( 1.5 + self.INTERVAL_BETWEEN_CELL_PROPORTION ) )
        self.grapBetweenCube = round( self.cubeSideSize * self.INTERVAL_BETWEEN_CELL_PROPORTION )

        # Extract resource 
        self._setResource()

        return True
    
    def isRepond(self):

        if self.isValid is not None:
            return self.isValid

        if not self._setParam():
            return False

    def getAllResourses(self):
        pass

if __name__ == '__main__':
    err = loadParam()

    if err:
        print(err)
        sleep(5)
    else:
        p2 = ResourceProfileParser(Image.open('resource/resource/resource4.png'))
        p2.isRepond()

        # img = Image.open('result/a002.png')
        # pix = np.array(img)
        # for iter in range(pix.shape[0]):
        #     for jtor in range(pix.shape[1]):
        #         if calcColorDifference(pix[iter][jtor], (207, 188, 121)) > 50:
        #             pix[iter][jtor] = [255, 255, 255, 255]
        #         else:
        #             pix[iter][jtor] = [0, 0, 0, 255]
                    
        # img = Image.fromarray(pix)
        # img.save('b.png')

        # img = Image.new("L", (104, 104))  # single band
        # newdata = list(range(0, 256, 4)) * 104
        # print(newdata)
        # img.putdata(newdata)
        # img.save('b.png')

        # img = Image.open('result/a021.png')
        # print(pytesseract.image_to_string(img, lang = 'rus'))

        # print('----------')
        # for iter in range(7):
        #     fullProfileImage = Image.open('resource/profile/profile%d.png' % iter)
        #     p = MainProfileParser(fullProfileImage)
        #     print(p.extractClanName())
            
        #     print(p.extractUserName())

        #     print('----------')

