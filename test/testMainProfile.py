import unittest
from glob import iglob
from itertools import chain
import os
from PIL import Image
from src.parser import MainProfileParser, wordSimplificationEng
from Levenshtein import ratio

class Test_MainProfile(unittest.TestCase):

    MIN_EQUALS = 0.7

    CLANS = ['SacredWizardsMortuus', 'SacredWizardsDeceptio', 'SacredWizardsVita', 'SacredWizardsCult']

    LINK_PROFILE = 'test\\resource\\profile\\'

    @unittest.skip()
    def testingMainProfile(self):
            
        for direct in next(os.walk(self.LINK_PROFILE))[1]:

            for infile in chain(iglob(self.LINK_PROFILE + direct + r'\*.png'), iglob(self.LINK_PROFILE + direct + r'\.*.png')):

                with Image.open(infile) as im:
                    
                    realName = os.path.basename(infile)[:-4]
                    realClan = direct
                    mp = MainProfileParser(im, self.CLANS)

                    with self.subTest(mp=mp):

                        self.assertEqual(
                            mp.clanName,
                            realClan,
                            msg = f'Clan({realClan}) not equals {realName}'
                        )
                        
                        self.assertGreater(
                            ratio(mp.userName, realName, processor = wordSimplificationEng),
                            self.MIN_EQUALS,
                            msg = f'Name not equals {realName} - {mp.userName} from {realClan}'
                        )


if __name__ == '__main__':
    unittest.main()