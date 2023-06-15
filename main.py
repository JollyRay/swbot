import time
import sys
sys.path.append('src')
from profileParser import ResourceProfileParser, loadParam

if __name__ == '__main__':
    err = loadParam()

    if err:
        print(err)
        time.sleep(5)
    else:
        start = time.time() 
        p2 = ResourceProfileParser('resource/resource/resource4.png')
        p2.isRepond()
        print(time.time() - start)
        for r, value in p2.resource.items():
            print(r, value)

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
        #     print(p.rank)

        #     print('----------')

