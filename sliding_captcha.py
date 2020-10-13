# 代码整体拼接而来
# 实现过腾讯滑动验证
# 总体参考链接
# https://blog.csdn.net/Tracy_LeBron/article/details/84567419?utm_medium=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-2.nonecase&depth_1-utm_source=distribute.pc_relevant.none-task-blog-BlogCommendFromMachineLearnPai2-2.nonecase
# 默认selenium的ActionChains拖动不流畅，修改源码： PointerInput类中 DEFAULT_MOVE_DURATION = 30
# 参考链接
# https://blog.csdn.net/qq_36250766/article/details/100541705
# 实际测试于 2020/10/13
# 部分验证需要多次，运气好一次过


from selenium import webdriver
from selenium.webdriver.common.by import By
from PIL import Image, ImageEnhance
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import urllib
import cv2
import numpy as np
from io import BytesIO
import time
import requests
from time import sleep

test_qq = '3402496934'

# 输入qq跳转到验证阶段
browser = webdriver.Chrome()
browser.get('https://aq.qq.com/cn2/login_limit/index_smart')
WebDriverWait(browser, 10).until(
    EC.element_to_be_clickable, (By.ID, 'next_step'))

browser.find_element_by_id('input_account_str').send_keys(test_qq)
browser.find_element_by_id('next_step').click()
time.sleep(1)

driver = browser
search_window = driver.current_window_handle
WebDriverWait(browser, 10).until(
    EC.visibility_of_element_located, (By.TAG_NAME, 'iframe'))
frame = driver.find_element_by_css_selector('body > iframe')
driver.switch_to_frame(1)
time.sleep(1)
# 获取验证码中的图片


def get_image(driver):
    image1 = driver.find_element_by_id('slideBg').get_attribute('src')
    image2 = driver.find_element_by_id('slideBlock').get_attribute('src')
    req = urllib.request.Request(image1)
    bkg = open('slide_bkg.png', 'wb+')
    bkg.write(urllib.request.urlopen(req).read())
    bkg.close()
    req = urllib.request.Request(image2)
    blk = open('slide_block.png', 'wb+')
    blk.write(urllib.request.urlopen(req).read())
    blk.close()
    return 'slide_bkg.png', 'slide_block.png'


# 计算缺口的位置，由于缺口位置查找偶尔会出现找不准的现象，这里进行判断，如果查找的缺口位置x坐标小于450，我们进行刷新验证码操作，重新计算缺口位置，知道满足条件位置。（设置为450的原因是因为缺口出现位置的x坐标都大于450）
def get_distance(bkg, blk):
    block = cv2.imread(blk, 0)
    template = cv2.imread(bkg, 0)
    cv2.imwrite('template.jpg', template)
    cv2.imwrite('block.jpg', block)
    block = cv2.imread('block.jpg')
    block = cv2.cvtColor(block, cv2.COLOR_BGR2GRAY)
    block = abs(255 - block)
    cv2.imwrite('block.jpg', block)
    block = cv2.imread('block.jpg')
    template = cv2.imread('template.jpg')
    result = cv2.matchTemplate(block, template, cv2.TM_CCOEFF_NORMED)
    x, y = np.unravel_index(result.argmax(), result.shape)
    # 这里就是下图中的绿色框框
    cv2.rectangle(template, (y+20, x+20),
                  (y + 136-25, x + 136-25), (7, 249, 151), 2)
    # 之所以加20的原因是滑块的四周存在白色填充
    print('x坐标为：%d' % (y+20))
    if y+20 < 450:
        elem = driver.find_element_by_xpath('//*[@id="reload"]/div')
        sleep(1)
        elem.click()
        bkg, blk = get_image(driver)
        y, template = get_distance(bkg, blk)
    return y, template


# 这个是用来模拟人为拖动滑块行为，快到缺口位置时，减缓拖动的速度，服务器就是根据这个来判断是否是人为登录的。
def get_tracks(dis):
    v = 0
    t = 0.9
    # 保存0.3内的位移
    tracks = []
    current = 0
    mid = distance*4/5
    while current <= dis:
        if current < mid:
            a = 2
        else:
            a = -3
        v0 = v
        s = v0*t+0.5*a*(t**2)
        current += s
        tracks.append(round(s))
        v = v0+a*t
    return tracks

# 轨迹参考：
# https://blog.csdn.net/qq_38685503/article/details/81187105?utm_medium=distribute.pc_relevant_t0.none-task-blog-BlogCommendFromMachineLearnPai2-1.nonecase&depth_1-utm_source=distribute.pc_relevant_t0.none-task-blog-BlogCommendFromMachineLearnPai2-1.nonecase


def get_tracks2(distance):
    """
    根据偏移量获取移动轨迹
    :param distance:偏移量
    :return:移动轨迹
    """
    # 移动轨迹
    tracks = []
    # 当前位移
    current = 0
    # 减速阈值
    mid = distance * 4 / 5
    # 计算间隔
    t = 0.2
    # 初速度
    v = 0
    while current < distance:
        if current < mid:
            # 加速度为正2
            a = 5
        else:
            # 加速度为负3
            a = -3
        # 初速度v0
        v0 = v
        # 当前速度
        v = v0 + a * t
        # 移动距离
        move = v0 * t + 1 / 2 * a * t * t
        # 当前位移
        current += move
        # 加入轨迹
        tracks.append(round(move))
    return tracks


# 原图的像素是680*390，而网页的是340*195，图像缩小了一倍。
# 经过尝试，发现滑块的固定x坐标为70，这个地方有待加强，这里加20的原因上面已经解释了。
while True:
    bkg, blk = get_image(driver)
    distance, template = get_distance(bkg, blk)
    double_distance = int((distance-70+20)/2)
    tracks = get_tracks2(double_distance)
    # 由于计算机计算的误差，导致模拟人类行为时，会出现分布移动总和大于真实距离，这里就把这个差添加到tracks中，也就是最后进行一步左移。
    tracks.append(-(sum(tracks)-double_distance))
    tracks.append(-25)
    element = driver.find_element_by_id('tcaptcha_drag_thumb')
    ActionChains(driver).click_and_hold(on_element=element).perform()
    # 实际中他这个比准确位置多了25的xoffset，所以减去25
    d = double_distance-(sum(tracks)-double_distance) - 25
    for track in tracks:
        ActionChains(driver).move_by_offset(xoffset=track, yoffset=0).perform()
    time.sleep(0.5)
    ActionChains(driver).release(on_element=element).perform()
    try:
        driver.find_element_by_id('tcaptcha_drag_thumb')
        sleep(1)
    except:
        break
