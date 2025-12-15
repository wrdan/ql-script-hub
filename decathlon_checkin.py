"""
cron "11 12 * * *" script-path=xxx.py,tag=匹配cron用
new Env('迪卡侬小程序签到')
"""

import os
import random
import requests
import time
from datetime import datetime

# ---------------- 统一通知模块加载 ----------------
hadsend = False
send = None
try:
    from notify import send

    hadsend = True
    print("✅ 已加载notify.py通知模块")
except ImportError:
    print("⚠️  未加载通知模块，跳过通知功能")

# 配置项
decathlon_cookie = os.environ.get('DECATHLON_COOKIE', '')
max_random_delay = int(os.getenv("MAX_RANDOM_DELAY", "3600"))
random_signin = os.getenv("RANDOM_SIGNIN", "true").lower() == "true"
privacy_mode = os.getenv("PRIVACY_MODE", "true").lower() == "true"

# 迪卡侬小程序配置
BASE_URL = 'https://api-cn.decathlon.com.cn/membership/membership-portal/mp/api/v1/'
CREDIT_URL = f'{BASE_URL}/memberships'
CHECKIN_URL = f'{BASE_URL}/business-center/reward/CHECK_IN_DAILY'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541510) XWEB/17071",
    "xweb_xhr": "1",
    "content-type": "application/json",
    "sec-fetch-site": "cross-site",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": "https://servicewechat.com/wxdbc3f1ac061903dd/494/page-frame.html",
    "accept-language": "zh-CN,zh;q=0.9",
    "priority": "u=1, i"
}

def mask_username(username):
    """用户名脱敏处理"""
    if not username:
        return username

    if privacy_mode:
        if len(username) <= 2:
            return '*' * len(username)
        elif len(username) <= 4:
            return username[0] + '*' * (len(username) - 2) + username[-1]
        else:
            return username[0] + '*' * 3 + username[-1]
    return username

def format_time_remaining(seconds):
    """格式化时间显示"""
    if seconds <= 0:
        return "立即执行"
    hours, minutes = divmod(seconds, 3600)
    minutes, secs = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}小时{minutes}分{secs}秒"
    elif minutes > 0:
        return f"{minutes}分{secs}秒"
    else:
        return f"{secs}秒"

def wait_with_countdown(delay_seconds, task_name):
    """带倒计时的随机延迟等待"""
    if delay_seconds <= 0:
        return
    print(f"{task_name} 需要等待 {format_time_remaining(delay_seconds)}")
    remaining = delay_seconds
    while remaining > 0:
        if remaining <= 10 or remaining % 10 == 0:
            print(f"{task_name} 倒计时: {format_time_remaining(remaining)}")
        sleep_time = 1 if remaining <= 10 else min(10, remaining)
        time.sleep(sleep_time)
        remaining -= sleep_time

def notify_user(title, content):
    """统一通知函数"""
    if hadsend:
        try:
            send(title, content)
            print(f"✅ 通知发送完成: {title}")
        except Exception as e:
            print(f"❌ 通知发送失败: {e}")
    else:
        print(f"📢 {title}\n📄 {content}")

def parse_cookies(cookie_str):
    """解析Cookie字符串，支持多账号"""
    if not cookie_str:
        return []

    # 先按换行符分割
    lines = cookie_str.strip().split('\n')
    cookies = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 再按&&分割
        parts = line.split('&&')
        for part in parts:
            part = part.strip()
            if part:
                cookies.append(part)

    # 去重并过滤空值
    unique_cookies = []
    for cookie in cookies:
        if cookie and cookie not in unique_cookies:
            unique_cookies.append(cookie)

    return unique_cookies

class Decathlon:
    name = "迪卡侬小程序"

    def __init__(self, cookie: str, index: int = 1):
        self.cookie = cookie
        self.index = index
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.headers['authorization'] = cookie

        # 用户信息
        self.user_name = None
        self.point_before = None
        self.point_after = None
        self.uid = None

    def get_user_info(self, is_after=False):
        """获取用户信息和燃值"""
        try:
            print(f"👤 正在获取{'签到后' if is_after else '签到前'}用户信息...")

            # 添加随机延迟
            time.sleep(random.uniform(2, 5))

            response = self.session.get(url=CREDIT_URL, timeout=15)

            print(f"🔍 用户信息响应状态码: {response.status_code}")

            if response.status_code == 200:
                # 提取燃值信息
                point = response.json()['data']['dktPointBalance']

                if is_after:
                    self.point_after = point
                    print(f"💰 签到后 - 燃值: {point}")
                else:
                    self.point_before = point
                    print(f"💰 签到前 - 燃值: {point}")

                # 只在第一次获取用户名等信息
                if not is_after:
                    # 提取用户名
                    self.user_name = response.json()['data']['dktName']
                    print(f"👤 用户: {mask_username(self.user_name)}")


                return True, "用户信息获取成功"
            else:
                error_msg = f"获取用户信息失败，状态码: {response.status_code}"
                print(f"❌ {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"获取用户信息异常: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def perform_checkin(self):
        """执行签到"""
        try:
            print("📝 正在执行签到...")

            data = {}

            response = self.session.post(CHECKIN_URL, data=data, timeout=15)
            print(f"🔍 签到响应状态码: {response.status_code}")

            if response.status_code == 200:
                # 解析JSON响应
                try:
                    result = response.json()
                    if isinstance(result, dict):
                        if result['code'] == 0:
                            return True, f"签到成功"
                        elif result['code'] == "ENP_1006":
                            return False, f"已经签到"
                        elif result['code'] != 0:
                            return False, f"签到失败：{result['code']}"
                except ValueError:
                    return False, "响应格式错误，无法解析JSON"
            else:
                return False, f"签到请求失败，状态码: {response.status_code}"

        except Exception as e:
            return False, f"签到异常: {str(e)}"

    def main(self):
        """主执行函数"""
        print(f"\n==== 迪卡侬账号{self.index} 开始签到 ====")

        if not self.cookie.strip():
            error_msg = """账号配置错误

❌ 错误原因: Cookie为空

🔧 解决方法:
1. 在青龙面板中添加环境变量decathlon_cookie
2. 多账号用换行分隔或&&分隔
3. Cookie需要包含完整的登录信息

💡 提示: 请确保Cookie有效且格式正确"""
            print(f"❌ {error_msg}")
            return error_msg, False

        # 1. 获取签到前用户信息
        user_success, user_msg = self.get_user_info(is_after=False)
        if not user_success:
            print(f"⚠️ 获取用户信息失败: {user_msg}")

        # 2. 随机等待
        time.sleep(random.uniform(2, 5))

        # 3. 执行签到
        signin_success, signin_msg = self.perform_checkin()

        # 4. 获取签到后用户信息
        time.sleep(random.uniform(2, 4))
        after_success, after_msg = self.get_user_info(is_after=True)

        # 5. 通过燃值变化判断签到是否真的成功
        if after_success and self.point_before and self.point_after:
            try:
                point_before = self.point_before
                point_after = self.point_after
                point_gain = point_after - point_before

                print(f"📊 燃值变化: 燃值 {point_before}→{point_after} (+{point_gain})")

                if point_gain > 0:
                    signin_success = True
                    signin_msg = f"签到成功，获得 {point_gain} 燃值"
                    print(f"✅ 通过燃值变化确认签到成功: +{point_gain} 燃值")
                elif  point_gain == 0:
                    # 燃值没变化，可能已经签到过了
                    signin_success = True
                    signin_msg = "今日已签到（燃值无变化）"
                    print("📅 燃值无变化，今日已签到")
                else:
                    print("⚠️ 燃值变化异常，但仍认为签到成功")
                    signin_success = True

            except Exception as e:
                print(f"⚠️ 燃值变化计算异常: {e}")
                # 如果燃值计算失败，使用原始签到结果
                print("🔄 使用原始签到结果")

        # 6. 组合结果消息
        final_msg = f"""🌟 迪卡侬签到结果

👤 用户: {mask_username(self.user_name)}
📊 燃值: {self.point_before} → {self.point_after or self.point_before}

📝 签到: {signin_msg}
⏰ 时间: {datetime.now().strftime('%m-%d %H:%M')}"""

        print(f"{'✅ 任务完成' if signin_success else f'❌ 任务失败: {signin_msg}'}")
        return final_msg, signin_success
def main():
    """主程序入口"""
    print(f"==== 迪卡侬签到开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")

    # 显示配置状态
    print(f"🔒 隐私保护模式: {'已启用' if privacy_mode else '已禁用'}")

    # 随机延迟（整体延迟）
    if random_signin:
        delay_seconds = random.randint(0, max_random_delay)
        if delay_seconds > 0:
            print(f"🎲 随机延迟: {format_time_remaining(delay_seconds)}")
            wait_with_countdown(delay_seconds, "迪卡侬签到")

    # 获取Cookie配置
    if not decathlon_cookie:
        error_msg = """❌ 未找到decathlon_cookie环境变量

    🔧 配置方法:
    1. decathlon_cookie: 迪卡侬小程序Cookie
    2. 多账号用换行分隔或&&分隔

    示例:
    单账号: decathlon_cookie=完整的Cookie字符串
    多账号: decathlon_cookie=cookie1&&cookie2 或换行分隔

    💡 提示: 登录迪卡侬小程序后，抓包获取完整Cookie"""

        print(error_msg)
        notify_user("迪卡侬签到失败", error_msg)
        return

    # 使用Cookie解析函数
    cookies = parse_cookies(decathlon_cookie)

    if not cookies:
        error_msg = """❌ Cookie解析失败

    🔧 可能原因:
    1. Cookie格式不正确
    2. Cookie为空或只包含空白字符
    3. 分隔符使用错误

    💡 请检查decathlon_cookie环境变量的值"""

        print(error_msg)
        notify_user("迪卡侬签到失败", error_msg)
        return

    print(f"📝 共发现 {len(cookies)} 个账号")

    success_count = 0
    total_count = len(cookies)
    results = []

    for index, cookie in enumerate(cookies):
        try:
            # 账号间随机等待
            if index > 0:
                delay = random.uniform(10, 20)
                print(f"⏱️  随机等待 {delay:.1f} 秒后处理下一个账号...")
                time.sleep(delay)

            # 执行签到
            signer = Decathlon(cookie, index + 1)
            result_msg, is_success = signer.main()

            if is_success:
                success_count += 1

            results.append({
                'index': index + 1,
                'success': is_success,
                'message': result_msg,
                'username': mask_username(signer.user_name) if signer.user_name else f"账号{index + 1}"
            })

            # 发送单个账号通知
            status = "成功" if is_success else "失败"
            title = f"迪卡侬账号{index + 1}签到{status}"
            notify_user(title, result_msg)

        except Exception as e:
            error_msg = f"账号{index + 1}: 执行异常 - {str(e)}"
            print(f"❌ {error_msg}")
            notify_user(f"迪卡侬账号{index + 1}签到失败", error_msg)

    # 发送汇总通知
    if total_count > 1:
        summary_msg = f"""📊 迪卡侬签到汇总

    📈 总计: {total_count}个账号
    ✅ 成功: {success_count}个
    ❌ 失败: {total_count - success_count}个
    📊 成功率: {success_count / total_count * 100:.1f}%
    ⏰ 完成时间: {datetime.now().strftime('%m-%d %H:%M')}"""

        # 添加详细结果（最多显示5个账号的详情）
        if len(results) <= 5:
            summary_msg += "\n\n📋 详细结果:"
            for result in results:
                status_icon = "✅" if result['success'] else "❌"
                summary_msg += f"\n{status_icon} {result['username']}"

        notify_user("迪卡侬签到汇总", summary_msg)

    print(
        f"\n==== 迪卡侬签到完成 - 成功{success_count}/{total_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")

if __name__ == '__main__':
    main()
