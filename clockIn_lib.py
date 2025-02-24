import datetime  # 导入日期时间模块
import json  # 导入JSON处理模块
import os  # 导入操作系统接口模块
import platform  # 导入平台模块，用于检测操作系统
import time  # 导入时间模块
import traceback  # 导入跟踪模块，用于异常处理

import requests  # 导入requests模块，用于HTTP请求
import selenium.webdriver  # 导入Selenium WebDriver模块
from func_timeout import func_set_timeout  # 导入函数超时模块
from loguru import logger  # 导入日志记录模块
from selenium.webdriver.chrome.options import Options  # 导入Chrome浏览器选项模块
from selenium.webdriver.common.by import By  # 导入元素定位策略
from selenium.webdriver.support import expected_conditions as EC  # 导入期望条件模块
from selenium.webdriver.support.wait import WebDriverWait  # 导入显式等待模块

class clockIn():  # 定义一个自动打卡类
    def __init__(self):
        # 从环境变量中获取账号、密码、座位号和推送密钥
        self.xuhao = str(os.environ['XUHAO'])
        self.mima = str(os.environ['MIMA'])
        self.SEATNO = str(os.environ['SEATNO'])
        self.pushplus = str(os.environ['PUSHPLUS'])

        # 如果座位号没有设置，程序退出并提示
        if self.SEATNO == '':
            exit('请在Github Secrets中设置SEATNO')
        if self.xuhao == '':
            exit('请在Github Secrets中设置XUHAO')
        if self.mima == '':
            exit('请在Github Secrets中设置MIMA')

        # 加载浏览器配置
        options = Options()
        optionsList = [
            "--headless",  # 无头模式，不显示浏览器界面
            "--lang=zh-CN",  # 设置语言为中文
            "--enable-javascript",  # 启用JavaScript
            "start-maximized",  # 窗口最大化
            "--disable-extensions",  # 禁用扩展
            "--no-sandbox",  # 禁用沙盒模式
            "--disable-browser-side-navigation",  # 禁用浏览器侧导航
            "--disable-dev-shm-usage"  # 禁用/dev/shm使用
        ]

        # 添加配置选项
        for option in optionsList:
            options.add_argument(option)

        options.page_load_strategy = 'none'  # 设置页面加载策略为none
        options.add_experimental_option("excludeSwitches", ["ignore-certificate-errors", "enable-automation"])
        options.keep_alive = True  # 保持连接

        # 初始化WebDriver
        self.driver = selenium.webdriver.Chrome(options=options)

        self.wdwait = WebDriverWait(self.driver, 30)  # 设置显式等待时间为30秒
        self.titlewait = WebDriverWait(self.driver, 20)  # 设置标题等待时间为20秒

        self.page = 0  # 当前页面标题，初始页面为0
        self.fail = False  # 打卡失败与否

    def __call__(self):  # 定义调用方法
        for retries in range(4):  # 尝试4次运行
            try:
                logger.info(f"第{retries + 1}次运行")
                if retries:
                    # 恢复状态，让它重来
                    self.page = 0
                    self.fail = False

                # 依次执行步骤
                self.step0()
                self.step1()
                self.step2()
                self.step3()

            except Exception:
                logger.error(traceback.format_exc())
                try:
                    if not self.driver.title:
                        logger.error(f'第{retries + 1}次运行失败，当前页面标题为空')
                    else:
                        logger.error(f'第{retries + 1}次运行失败，当前页面标题为：{self.driver.title}')
                except Exception:
                    logger.error(f'第{retries + 1}次运行失败，获取当前页面标题失败')

                if retries == 3:  # 如果运行了4次仍然失败，标记为打卡失败
                    self.fail = True
                    logger.error("图书馆预定失败")

        self.driver.quit()  # 关闭浏览器
        # self.notify()  # 通知打卡结果

    def step0(self):  # 定义步骤0：转到图书馆界面
        logger.info('step0 正在转到转到图书馆界面')

        # 打开图书馆登录页面
        self.driver.get('https://newcas.gzhu.edu.cn/cas/login?service=http://libbooking.gzhu.edu.cn/#/ic/home')

        # 如果验证通过，直接进入界面，跳到步骤3
        if self.driver.title == 'Information Commons':
            return self.step3()

        logger.info('标题1: ' + self.driver.title)

        start = datetime.datetime.now()  # 记录开始时间

        system = platform.system()  # 获取当前的操作系统
        if system == 'Linux':
            logger.info("当前操作系统为Linux")
            self.titlewait.until(EC.title_contains("Unified Identity Authentication"))  # 等待标题包含“Unified Identity Authentication”
        else:
            logger.info("当前操作系统为非Linux")
            self.titlewait.until(EC.title_contains("统一身份认证"))  # 等待标题包含“统一身份认证”

        end = datetime.datetime.now()  # 记录结束时间
        logger.info('等待时间: ' + str((end - start).seconds))

        logger.info('标题2: ' + self.driver.title)

    def step1(self):  # 定义步骤1：登录融合门户
        self.wdwait.until(EC.visibility_of_element_located((By.XPATH, "//div[@class='robot-mag-win small-big-small']")))

        logger.info('step1 正在尝试登陆统一身份认证')
        logger.info('标题: ' + self.driver.title)

        # 执行JavaScript脚本填充账号密码并点击登录按钮
        for script in [
            f"document.getElementById('un').value='{self.xuhao}'",
            f"document.getElementById('pd').value='{self.mima}'",
            "document.getElementById('index_login_btn').click()"
        ]:
            self.driver.execute_script(script)

    def step2(self):  # 定义步骤2：转到图书馆界面
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.title_contains("Information Commons"))

        logger.info('step2 正在转到图书馆界面')
        logger.info('标题: ' + self.driver.title)

    def step3(self):  # 定义步骤3：预定座位操作
        logger.info('step3 准备进行图书馆预定座位操作')
        logger.info('标题: ' + self.driver.title)

        cookie = self.get_cookie()  # 获取Cookie

        if cookie == '':
            logger.info('没找到cookie')

            # 尝试访问图书馆主页
            self.driver.get("http://libbooking.gzhu.edu.cn/#/ic/home")

            start = datetime.datetime.now()  # 记录开始时间
            time.sleep(5)  # 等待5秒
            end = datetime.datetime.now()  # 记录结束时间
            logger.info('等待时间: ' + str((end - start).seconds))

            self.step3()  # 重新执行步骤3
            return

        logger.info('primary cookie: ' + cookie)

        tomorrow = datetime.date.today() + datetime.timedelta(days=1)  # 计算明天的日期
        tomorrow = tomorrow.strftime('%Y-%m-%d')

        # 预定三个时段
        reserve1 = json.loads(self.reserve_lib_seat(cookie, tomorrow, '10:00:00', '13:00:00'))
        reserve2 = json.loads(self.reserve_lib_seat(cookie, tomorrow, '13:00:00', '16:00:00'))
        reserve3 = json.loads(self.reserve_lib_seat(cookie, tomorrow, '16:00:00', '19:00:00'))
        reserve4 = json.loads(self.reserve_lib_seat(cookie, tomorrow, '19:00:00', '22:00:00'))

        logger.info(reserve1)
        logger.info(reserve2)
        logger.info(reserve3)
        logger.info(reserve4)

        message = f'''{tomorrow} 座位101-{self.SEATNO}，上午预定：{'预约成功' if reserve1.get('code') == 0 else '预约失败，设备在该时间段内已被预约'}
            {tomorrow} 座位101-{self.SEATNO}，下午预定：{'预约成功' if reserve2.get('code') == 0 else '预约失败，设备在该时间段内已被预约'}
            {tomorrow} 座位101-{self.SEATNO}，下午预定：{'预约成功' if reserve3.get('code') == 0 else '预约失败，设备在该时间段内已被预约'}
            {tomorrow} 座位101-{self.SEATNO}，晚上预定：{'预约成功' if reserve4.get('code') == 0 else '预约失败，设备在该时间段内已被预约'}
        '''

        logger.info(message)

        self.notify(message)  # 发送预约消息

        self.fail = False  # 预约成功，程序结束
        self.driver.quit()
        exit(0)

    def reserve_lib_seat(self, cookie, tomorrow, startTime, endTime):  # 定义图书馆座位预约方法
        url = "http://libbooking.gzhu.edu.cn/ic-web/reserve"

        payload = json.dumps({
            "sysKind": 8,
            "appAccNo": 101598216,
            "memberKind": 1,
            "resvMember": [101598216],
            "resvBeginTime": f"{tomorrow} {startTime}",
            "resvEndTime": f"{tomorrow} {endTime}",
            "testName": "",
            "captcha": "",
            "resvProperty": 0,
            "resvDev": [self.calc_dev_no(int(self.SEATNO))],
            "memo": ""
        })
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.41',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)

        return response.text

    def calc_dev_no(self, no):  # 计算设备编号
        return 101266684 + no - 1

    def decalc_devno(self, no):  # 反向计算设备编号
        return no - 101266684 + 1

    def get_cookie(self):  # 获取Cookie字符串
        ans = self.driver.get_cookies()
        logger.info('cookies' + str(ans))

        if len(ans) != 0:
            logger.info(ans[0])
            logger.info(ans[0].get('name'))
            return ans[0].get('name') + "=" + ans[0].get('value')

        return ''

    def notify(self, content):  # 发送预约信息
        if self.pushplus:
            data = {"token": self.pushplus, "title": "图书馆预约信息", "content": content}
            url = "http://www.pushplus.plus/send/"
            logger.info(requests.post(url, data=data).text)

# 限制10分钟内必须运行完成，否则失败处理
@func_set_timeout(60 * 3)
def main():
    cl = clockIn()
    cl()

if __name__ == "__main__":
    main()
