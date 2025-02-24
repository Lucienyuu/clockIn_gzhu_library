# 导入标准库模块
import datetime  # 处理日期时间相关操作
import json      # JSON数据编码解码
import os        # 操作系统接口（环境变量获取）
import platform  # 获取操作系统信息
import time      # 时间相关操作（延时等）
import traceback # 异常堆栈跟踪

# 导入第三方库模块
from func_timeout import func_set_timeout, FunctionTimedOut  # 函数执行超时控制
from loguru import logger  # 日志记录工具
import requests  # 发送HTTP请求
import selenium.webdriver  # 浏览器自动化核心模块
from selenium.webdriver.chrome.options import Options  # Chrome浏览器配置
from selenium.webdriver.common.by import By  # 元素定位策略枚举
from selenium.webdriver.support import expected_conditions as EC  # 等待条件
from selenium.webdriver.support.wait import WebDriverWait  # 显式等待

class ClockIn:
    def __init__(self):
        """图书馆预约系统自动化类初始化方法"""
        # 从环境变量获取认证信息（使用getenv避免KeyError）
        self.xuhao = os.getenv('XUHAO', '')  # 学号/账号，默认空字符串
        self.mima = os.getenv('MIMA', '')    # 密码，默认空字符串
        self.SEATNO = os.getenv('SEATNO', '')  # 预约座位编号，默认空字符串
        self.pushplus = os.getenv('PUSHPLUS', '')  # PushPlus通知token，默认空字符串

        # 检查必要参数是否完整（座位号、学号、密码）
        if not all([self.SEATNO, self.xuhao, self.mima]):
            exit('请正确设置所有必要的环境变量')  # 参数不全时退出程序

        # 配置Chrome浏览器选项
        options = Options()
        options.add_argument("--headless")  # 启用无头模式（不显示浏览器界面）
        options.add_argument("--no-sandbox")  # 禁用沙盒模式（Linux服务器需要）
        options.add_argument("--disable-dev-shm-usage")  # 解决共享内存问题
        options.add_argument("--disable-gpu")  # 禁用GPU加速（避免兼容性问题）
        options.add_argument("--lang=zh-CN")  # 设置浏览器语言为简体中文
        options.add_experimental_option("excludeSwitches", ["enable-automation"])  # 隐藏自动化控制提示
        options.page_load_strategy = 'eager'  # 页面加载策略：DOM解析完成即视为加载完成

        try:
            # 初始化Chrome浏览器驱动实例
            self.driver = selenium.webdriver.Chrome(options=options)
        except Exception as e:
            logger.error(f"浏览器初始化失败: {str(e)}")  # 记录错误日志
            exit()  # 异常退出

        # 初始化显式等待对象（20秒超时）
        self.wait = WebDriverWait(self.driver, 20)
        self.retries = 3  # 最大重试次数（含首次尝试）
        self.success = False  # 预约结果状态标记

    def __call__(self):
        """执行完整的预约流程（含重试机制）"""
        # 重试循环（attempt从0到retries）
        for attempt in range(self.retries + 1):
            try:
                logger.info(f"第{attempt + 1}次尝试")  # 记录当前尝试次数
                self._perform_steps()  # 执行完整预约步骤
                if self.success:
                    logger.info("预定成功")  # 成功时记录日志
                    return  # 提前退出循环
            except Exception as e:
                logger.error(f"尝试{attempt + 1}失败: {str(e)}")  # 记录错误信息
                logger.debug(traceback.format_exc())  # 调试模式记录堆栈跟踪
                if attempt == self.retries:  # 最后一次尝试失败后
                    self._send_notification("图书馆预约最终失败，请手动处理")  # 发送失败通知
                self._reset_state()  # 重置浏览器状态
        
        self.driver.quit()  # 关闭浏览器实例
        exit(1)  # 非正常退出（状态码1）

    def _perform_steps(self):
        """执行完整的预约步骤序列"""
        self._step0_login()        # 步骤0：访问登录页面
        self._step1_authentication()  # 步骤1：身份认证
        self._step2_navigate()     # 步骤2：导航到预约页面
        self._step3_reservation()  # 步骤3：执行预约操作

    def _step0_login(self):
        """步骤0：访问统一身份认证登录页面"""
        logger.info("正在访问登录页面")
        # 打开图书馆登录页面
        self.driver.get('https://newcas.gzhu.edu.cn/cas/login?service=http://libbooking.gzhu.edu.cn/#/ic/home')
        
        # 检查是否已登录（通过页面标题判断）
        if "Information Commons" in self.driver.title:
            logger.info("检测到已登录状态")
            return  # 跳过后续步骤

        # 根据操作系统决定预期的登录页面标题
        expected_title = "统一身份认证" if platform.system() != "Linux" else "Unified Identity Authentication"
        # 等待直到标题包含预期内容（最多20秒）
        self.wait.until(EC.title_contains(expected_title))
        logger.info(f"成功进入认证页面: {self.driver.title}")

    def _step1_authentication(self):
        """步骤1：执行登录认证操作"""
        logger.info("正在执行身份认证")
        
        # 定位用户名输入框（等待元素出现）
        username = self.wait.until(
            EC.presence_of_element_located((By.ID, "un")),  # 通过ID定位
            message="找不到用户名输入框"
        )
        # 定位密码输入框
        password = self.wait.until(
            EC.presence_of_element_located((By.ID, "pd")),
            message="找不到密码输入框"
        )
        # 定位登录按钮（等待元素可点击）
        submit = self.wait.until(
            EC.element_to_be_clickable((By.ID, "index_login_btn")),
            message="登录按钮不可点击"
        )

        # 输入认证信息
        username.send_keys(self.xuhao)  # 输入学号
        password.send_keys(self.mima)   # 输入密码
        submit.click()  # 点击登录按钮

        # 等待登录成功后页面加载（检查标题）
        self.wait.until(lambda d: "Information Commons" in d.title)
        logger.info(f"登录成功，当前页面: {self.driver.title}")

    def _step2_navigate(self):
        """步骤2：导航到图书馆预约界面"""
        logger.info("正在跳转到预定页面")
        # 访问图书馆预约主页
        self.driver.get("http://libbooking.gzhu.edu.cn/#/ic/home")
        # 等待预约按钮出现（通过class定位）
        self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "reserve-btn")),
            message="预约页面加载失败"
        )
        logger.info("成功进入预定界面")

    def _step3_reservation(self):
        """步骤3：执行座位预约操作"""
        logger.info("开始执行预定流程")
        
        # 获取认证Cookie
        cookie = self._get_auth_cookie()
        if not cookie:
            raise ValueError("无法获取有效Cookie")

        # 计算明天的日期（格式：YYYY-MM-DD）
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        # 定义预约时间段列表
        time_slots = [
            ('10:00:00', '13:00:00'),  # 上午时段
            ('13:00:00', '16:00:00'),  # 下午第一时段
            ('16:00:00', '19:00:00'),  # 下午第二时段
            ('19:00:00', '22:00:00')   # 晚上时段
        ]

        results = []  # 存储各时段预约结果
        for start, end in time_slots:
            # 发送预约请求
            result = self._reserve_seat(cookie, tomorrow, start, end)
            results.append(result)
            time.sleep(1)  # 请求间隔1秒（防止频率限制）

        # 统计成功次数（code为0表示成功）
        success_count = sum(1 for r in results if r.get('code') == 0)
        # 生成通知消息
        message = self._format_message(tomorrow, results)
        # 发送通知
        self._send_notification(message)
        
        # 根据结果更新状态
        if success_count > 0:
            self.success = True  # 标记成功
        else:
            raise Exception("所有时间段预约失败")  # 抛出异常触发重试

    def _get_auth_cookie(self):
        """获取身份认证Cookie"""
        cookies = self.driver.get_cookies()  # 获取所有Cookie
        # 遍历查找目标Cookie（示例查找route）
        for cookie in cookies:
            if cookie['name'] == 'route':
                return f"{cookie['name']}={cookie['value']}"  # 拼接为Cookie字符串
        return None  # 未找到时返回空

    def _reserve_seat(self, cookie, date, start, end):
        """发送预约请求到图书馆API"""
        url = "http://libbooking.gzhu.edu.cn/ic-web/reserve"  # API地址
        headers = {
            'Cookie': cookie,  # 身份验证Cookie
            'User-Agent': 'Mozilla/5.0...',  # 浏览器UA伪装
            'Content-Type': 'application/json'  # JSON数据格式
        }
        payload = {
            "sysKind": 8,  # 系统类型（固定）
            "appAccNo": 101598216,  # 应用账号（固定）
            "memberKind": 1,  # 成员类型（个人）
            "resvMember": [101598216],  # 预约成员列表
            "resvBeginTime": f"{date} {start}",  # 开始时间
            "resvEndTime": f"{date} {end}",  # 结束时间
            "resvProperty": 0,  # 预约属性（普通）
            "resvDev": [self._calculate_seat_id()],  # 设备ID列表
            "memo": ""  # 备注
        }

        try:
            # 发送POST请求（10秒超时）
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            return response.json()  # 返回解析后的JSON响应
        except Exception as e:
            logger.error(f"预约请求异常: {str(e)}")
            return {"code": -1, "msg": "请求异常"}  # 返回错误信息

    def _calculate_seat_id(self):
        """根据座位号计算设备ID"""
        base_id = 101266684  # 基础设备ID（需根据实际情况调整）
        return base_id + int(self.SEATNO) - 1  # 计算实际设备ID

    def _format_message(self, date, results):
        """格式化通知消息内容"""
        messages = []
        # 遍历结果生成状态信息
        for i, res in enumerate(results):
            status = "成功" if res.get('code') == 0 else f"失败({res.get('msg', '未知错误')})"
            messages.append(f"{date} 时段{i+1}: {status}")
        return "\n".join(messages)  # 用换行符连接消息列表

    def _send_notification(self, content):
        """通过PushPlus发送通知"""
        if not self.pushplus:  # 未配置token时跳过
            return

        url = "http://www.pushplus.plus/send/"  # API地址
        payload = {
            "token": self.pushplus,  # 用户token
            "title": "图书馆预约结果",  # 通知标题
            "content": content,  # 通知内容
            "template": "txt"  # 文本格式
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            logger.info(f"通知发送状态: {response.status_code}")  # 记录发送状态
        except Exception as e:
            logger.error(f"通知发送失败: {str(e)}")  # 记录发送失败

    def _reset_state(self):
        """重置浏览器状态"""
        self.driver.delete_all_cookies()  # 删除所有Cookie
        self.driver.refresh()  # 刷新页面
        logger.info("浏览器状态已重置")  # 记录重置操作

@func_set_timeout(600)  # 设置函数超时时间（10分钟）
def main():
    """程序主入口"""
    try:
        clock = ClockIn()  # 创建预约实例
        clock()  # 执行预约流程
    except FunctionTimedOut:  # 超时异常处理
        logger.error("程序执行超时")
        exit(2)  # 超时退出码

if __name__ == "__main__":
    main()  # 脚本执行入口
