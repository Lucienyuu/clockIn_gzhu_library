import datetime
import json
import os
import platform
import time
import traceback

import requests
import selenium.webdriver
from func_timeout import func_set_timeout
from loguru import logger
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class clockIn():
    def __init__(self):
        # 从环境变量中获取信息
        self.xuhao = str(os.environ['XUHAO'])
        self.mima = str(os.environ['MIMA'])
        self.SEATNO = str(os.environ['SEATNO'])
        self.pushplus = str(os.environ['PUSHPLUS'])

        if self.SEATNO == '':
            exit('请在Github Secrets中设置SEATNO')
        if self.xuhao == '':
            exit('请在Github Secrets中设置XUHAO')
        if self.mima == '':
            exit('请在Github Secrets中设置MIMA')

        # 加载配置
        options = Options()
        optionsList = [
            "--headless",
            # "--disable-gpu",
            "--lang=zh-CN",
            "--enable-javascript",
            "start-maximized",
            "--disable-extensions",
            "--no-sandbox",
            "--disable-browser-side-navigation",
            "--disable-dev-shm-usage"
        ]

        for option in optionsList:
            options.add_argument(option)

        options.page_load_strategy = 'none'
        options.add_experimental_option(
            "excludeSwitches",
            ["ignore-certificate-errors", "enable-automation"])
        options.keep_alive = True

        self.driver = selenium.webdriver.Chrome(options=options)

        self.wdwait = WebDriverWait(self.driver, 30)
        self.titlewait = WebDriverWait(self.driver, 20)

        # self.page用来表示当前页面标题，0表示初始页面
        self.page = 0

        # self.fail表示打卡失败与否
        self.fail = False

    def __call__(self):
        for retries in range(4):
            try:
                logger.info(f"第{retries + 1}次运行")
                if retries:
                    # 恢复状态，让它重来
                    self.page = 0
                    self.fail = False

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
                        logger.error(
                            f'第{retries + 1}次运行失败，当前页面标题为：{self.driver.title}')
                except Exception:
                    logger.error(f'第{retries + 1}次运行失败，获取当前页面标题失败')

                if retries == 3:
                    self.fail = True
                    logger.error("图书馆预定失败")

        self.driver.quit()

    def step0(self):
        """转到图书馆界面
        """
        logger.info('step0 正在转到转到图书馆界面')

        self.driver.get('''
                https://newcas.gzhu.edu.cn/cas/login?service=http://libbooking.gzhu.edu.cn/#/ic/home
                ''')

        if self.driver.title == 'Information Commons':
            # 说明验证通过，直接进入了界面
            return self.step3()

        logger.info('标题1: ' + self.driver.title)

        # 计算时间
        start = datetime.datetime.now()

        # 获取当前的操作系统
        system = platform.system()
        # 如果是Ubuntu
        if system == 'Linux':
            logger.info("当前操作系统为Linux")
            self.titlewait.until(EC.title_contains("Unified Identity Authentication"))
        else:
            logger.info("当前操作系统为非Linux")
            self.titlewait.until(EC.title_contains("统一身份认证"))

        end = datetime.datetime.now()
        logger.info('等待时间: ' + str((end - start).seconds))

        logger.info('标题2: ' + self.driver.title)

    def step1(self):
        """登录融合门户
        """
        self.wdwait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[@class='robot-mag-win small-big-small']")))

        logger.info('step1 正在尝试登陆统一身份认证')
        logger.info('标题: ' + self.driver.title)

        for script in [
            f"document.getElementById('un').value='{self.xuhao}'",
            f"document.getElementById('pd').value='{self.mima}'",
            "document.getElementById('index_login_btn').click()"
        ]:
            self.driver.execute_script(script)

    def step2(self):
        """正在转到图书馆界面
        """
        wait = WebDriverWait(self.driver, 15)
        wait.until(EC.title_contains("Information Commons"))

        logger.info('step2 正在转到图书馆界面')
        logger.info('标题: ' + self.driver.title)
        
        # 等待额外的时间，确保完全加载并建立会话
        time.sleep(5)

    def step3(self):
        """准备进行图书馆预定座位操作
        """
        logger.info('step3 准备进行图书馆预定座位操作')
        logger.info('标题: ' + self.driver.title)

        # 确保我们在正确的页面上
        if "Information Commons" not in self.driver.title:
            logger.info('当前不在图书馆页面，尝试访问图书馆页面')
            self.driver.get("http://libbooking.gzhu.edu.cn/#/ic/home")
            
            # 等待页面加载
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.title == "Information Commons"
                )
                logger.info("图书馆页面加载成功")
            except Exception:
                logger.error("等待图书馆页面加载超时")
        
        # 确保JS执行完毕，等待一些关键元素
        time.sleep(5)
        
        # 获取cookie
        cookie = self.get_cookie()

        if not cookie:
            logger.info('没找到cookie，尝试执行一些页面操作以获取cookie')
            try:
                # 尝试刷新页面
                self.driver.refresh()
                time.sleep(5)
                
                # 尝试访问主页
                self.driver.get("http://libbooking.gzhu.edu.cn/#/ic/home")
                time.sleep(3)
                
                cookie = self.get_cookie()
            except Exception as e:
                logger.error(f"尝试重新获取cookie失败: {str(e)}")

        if not cookie:
            logger.error('无法获取有效的cookie，预约失败')
            self.fail = True
            return

        logger.info('获取到有效cookie: ' + cookie)

        # 计算明天的日期，yyyy-MM-dd
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        tomorrow = tomorrow.strftime('%Y-%m-%d')

        # 直接使用学号作为账号
        user_account = int(self.xuhao)
        logger.info(f"直接使用学号作为账号: {user_account}")
        
        # 进行预约
        reserve1 = json.loads(self.reserve_lib_seat(cookie, tomorrow, '9:00:00', '12:00:00', user_account))
        reserve2 = json.loads(self.reserve_lib_seat(cookie, tomorrow, '14:00:00', '18:00:00', user_account))
        
        logger.info(f"预约结果: {reserve1}")
        logger.info(f"预约结果: {reserve2}")

        # 获取最终结果
        message = f'''{tomorrow} 座位101-{self.SEATNO}，上午预定：{'预约成功' if reserve1.get('code') == 0 else '预约失败，' + reserve1.get('message', '未知原因')}
            {tomorrow} 座位101-{self.SEATNO}，下午预定：{'预约成功' if reserve2.get('code') == 0 else '预约失败，' + reserve2.get('message', '未知原因')}
        '''

        logger.info(message)

        # 发送消息
        self.notify(message)

        # 发送请求成功，可以结束程序了
        self.fail = False
        self.driver.quit()
        exit(0)

    def reserve_lib_seat(self, cookie, tomorrow, startTime, endTime, user_account):
        """预约图书馆座位
        """
        url = "http://libbooking.gzhu.edu.cn/ic-web/reserve"
        
        payload = json.dumps({
            "sysKind": 8,
            "appAccNo": user_account,
            "memberKind": 1,
            "resvMember": [user_account],
            "resvBeginTime": f"{tomorrow} {startTime}",
            "resvEndTime": f"{tomorrow} {endTime}",
            "testName": "",
            "captcha": "",
            "resvProperty": 0,
            "resvDev": [
                self.calc_dev_no(int(self.SEATNO))
            ],
            "memo": ""
        })
        
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.41',
            'Content-Type': 'application/json',
            'Referer': 'http://libbooking.gzhu.edu.cn/',
            'Origin': 'http://libbooking.gzhu.edu.cn'
        }
        
        logger.info(f"发送预约请求，账号: {user_account}, 时间: {startTime}-{endTime}")
        response = requests.request("POST", url, headers=headers, data=payload)
        
        return response.text

    def calc_dev_no(self, no):
        """计算设备编号
        """
        return 101266684 + no - 1

    def decalc_devno(self, no):
        """反向计算设备编号
        """
        return no - 101266684 + 1

    def get_cookie(self):
        """获取所需的cookie
        """
        try:
            # 确保页面完全加载
            time.sleep(3)
            
            # 直接构建所需的cookie字符串
            cookies = self.driver.get_cookies()
            logger.info(f'获取到 {len(cookies)} 个cookies')
            
            if not cookies:
                return ''
            
            # 打印所有cookie便于调试
            for cookie in cookies:
                logger.info(f"Cookie: {cookie['name']}={cookie['value']}")
            
            # 组合所有cookie（这很重要，因为认证可能需要多个cookie）
            cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
            logger.info(f"Combined cookies: {cookie_str}")
            
            return cookie_str
        except Exception as e:
            logger.error(f"获取cookie时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return ''

    def notify(self, content):
        """图书馆预约信息
        """
        if self.pushplus:
            data = {"token": self.pushplus, "title": "图书馆预约信息", "content": content}
            url = "http://www.pushplus.plus/send/"
            logger.info(requests.post(url, data=data).text)


# 限制10分钟内，必须运行完成，否则失败处理
@func_set_timeout(60 * 3)
def main():
    cl = clockIn()
    cl()


if __name__ == "__main__":
    main()
