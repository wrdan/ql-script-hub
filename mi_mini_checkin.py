"""
cron "0 7 2 * * *" script-path=xxx.py,tag=匹配cron用
new Env('小米社区小程序签到')

最后更新日期：2025-12-17
食用方法：变量输入export MI_MINI_COOKIE=cookie1&&cookie2
支持多用户运行
多用户用&&或换行隔开
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

# 配置项（统一全大写命名，提高可读性）
MI_MINI_COOKIE = os.environ.get('MI_MINI_COOKIE', '')
MAX_RANDOM_DELAY = int(os.getenv("MAX_RANDOM_DELAY", "3600"))
RANDOM_SIGNIN = os.getenv("RANDOM_SIGNIN", "true").lower() == "true"
PRIVACY_MODE = os.getenv("PRIVACY_MODE", "true").lower() == "true"

# 小米社区小程序配置
BASE_URL = 'https://api.vip.miui.com/mtop/planet/wechat'
CREDIT_URL = f'{BASE_URL}/checkin/mypagedata'
CHECKIN_URL = f'{BASE_URL}/member/addCommunityGrowUpPointByActionV2'
USERINFO_URL = f'{BASE_URL}/userinfo'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 "
                  "Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows "
                  "WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541510) XWEB/17071",
    'Accept': "application/json, text/plain, */*",
    'Origin': "https://servicewechat.com",
    'Content-Type': "application/x-www-form-urlencoded",
    'xweb_xhr': "1",
    'Sec-Fetch-Site': "cross-site",
    'Sec-Fetch-Mode': "cors",
    'Sec-Fetch-Dest': "empty",
    'Referer': "https://servicewechat.com/wx240a4a764023c444/22/page-frame.html",
    'Accept-Language': "zh-CN,zh;q=0.9",
}


def mask_username(username):
    """用户名脱敏处理"""
    if not username:
        return "未知用户"

    if PRIVACY_MODE:
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
    """解析cookie字符串，支持多账号"""
    if not cookie_str:
        return []

    # 先按换行符分割，再按&&分割
    cookies = []
    lines = cookie_str.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split('&&')
        for part in parts:
            part = part.strip()
            if part and part not in cookies:
                cookies.append(part)

    return cookies


class MiCommunityMini:
    name = "小米社区小程序"

    def __init__(self, cookie: str, index: int = 1):
        self.cookie = cookie
        self.index = index
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.headers['cookie'] = cookie

        # 用户信息
        self.user_name = None
        self.point_before = 0  # 签到前成长值
        self.point_after = 0  # 签到后成长值
        self.point_change = 0  # 本次变更成长值

    def get_user_info(self):
        """仅获取签到前的用户信息和初始成长值"""
        try:
            print("👤 正在获取用户信息...")
            time.sleep(random.uniform(2, 5))
            response = self.session.get(url=USERINFO_URL, timeout=15)
            if response.status_code != 200:
                error_msg = f"获取用户信息失败，状态码: {response.status_code}"
                print(f"❌ {error_msg}")
                return False, error_msg

            # 安全解析JSON，避免KeyError
            result = response.json()
            data = result.get('entity', {})
            if not data:
                error_msg = "接口返回entity字段为空"
                print(f"❌ {error_msg}")
                return False, error_msg

            # 提取用户名
            self.user_name = data.get('username', '未知用户')

            print("👤 正在获取用户签到信息...")
            time.sleep(random.uniform(2, 5))
            response = self.session.get(url=CREDIT_URL, timeout=15)
            if response.status_code != 200:
                error_msg = f"获取用户签到信息失败，状态码: {response.status_code}"
                print(f"❌ {error_msg}")
                return False, error_msg

            # 安全解析JSON，避免KeyError
            result = response.json()
            # 1. 获取 entity 字典（默认空字典）
            entity = result.get("entity", {})
            # 2. 获取 data 列表（默认空列表）
            data_list = entity.get("data", [])
            jump_text = data_list[1].get("jumpText", "")
            # 用 / 分割字符串
            num_part = jump_text.split('/')[0]
            # 转换为整数（如果需要数值计算）
            current_num = int(num_part)

            # 提取签到前成长值
            self.point_before = current_num

            print(f"💰 初始成长值: {self.point_before}")
            print(f"👤 用户: {mask_username(self.user_name)}")

            return True, "用户信息获取成功"

        except Exception as e:
            error_msg = f"获取用户信息异常: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def perform_checkin(self):
        """执行签到（充分利用接口返回数据，无需二次请求）"""
        try:
            print("📝 正在执行签到...")
            data = {
                'action': "WECHAT_CHECKIN_TASK"
            }
            response = self.session.post(CHECKIN_URL, data=data, timeout=15)
            if response.status_code != 200:
                return False, f"签到请求失败，状态码: {response.status_code}"

            # 安全解析响应
            result = response.json()
            if not isinstance(result, dict):
                return False, "响应格式错误，无法解析JSON"

            # 关键修改：默认值改为字符串，与接口返回类型一致
            code = result.get('status', "unknown")
            if code == 200:
                # 直接从签到接口提取成长值数据（核心优化）
                data = result.get('status', {})
                self.point_change = data.get('score', 0)
                self.point_after = self.point_before + self.point_change

                success_msg = f"签到成功，获得 {self.point_change} 成长值，当前成长值 {self.point_after}"
                print(f"✅ {success_msg}")
                return True, success_msg
            elif code == -1:
                # 签到失败（已签到），成长值不变
                self.point_after = self.point_before
                return False, "今日已签到"
            else:
                # 其他失败情况，成长值不变
                self.point_after = self.point_before
                return False, f"签到失败：{code} - {result.get('message', '未知错误')}"

        except Exception as e:
            # 异常情况，成长值不变
            self.point_after = self.point_before
            return False, f"签到异常: {str(e)}"

    def main(self):
        """主执行函数"""
        print(f"\n==== 小米社区小程序账号{self.index} 开始签到 ====")

        if not self.cookie.strip():
            error_msg = """账号配置错误
❌ 错误原因: cookie为空
🔧 解决方法:
1. 在青龙面板中添加环境变量MI_MINI_COOKIE
2. 多账号用换行分隔或&&分隔
3. cookie需要包含完整的登录信息
💡 提示: 请确保cookie有效且格式正确"""
            print(f"❌ {error_msg}")
            return error_msg, False

        # 1. 仅获取一次用户信息（签到前）
        user_success, user_msg = self.get_user_info()
        if not user_success:
            print(f"⚠️ 获取用户信息失败，将继续执行签到流程...")

        # 2. 执行签到（直接获取所有成长值数据）
        signin_success, signin_msg = self.perform_checkin()

        # 3. 组合结果消息
        final_msg = f"""🌟 小米社区小程序签到结果
👤 用户: {mask_username(self.user_name)}
📊 成长值: {self.point_before} → {self.point_after}
📝 签到: {signin_msg}
⏰ 时间: {datetime.now().strftime('%m-%d %H:%M')}"""

        status = "✅ 任务完成" if signin_success else f"❌ 任务失败"
        print(f"{status}: {signin_msg}")
        return final_msg, signin_success


def main():
    """主程序入口"""
    print(f"==== 小米社区小程序签到开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")
    print(f"🔒 隐私保护模式: {'已启用' if PRIVACY_MODE else '已禁用'}")

    # 整体随机延迟
    if RANDOM_SIGNIN:
        delay_seconds = random.randint(0, MAX_RANDOM_DELAY)
        wait_with_countdown(delay_seconds, "小米社区小程序签到")

    # 检查cookie配置
    if not MI_MINI_COOKIE:
        error_msg = """❌ 未找到MI_MINI_COOKIE环境变量
🔧 配置方法:
1. MI_MINI_COOKIE: 小米社区小程序cookie
2. 多账号用换行分隔或&&分隔
示例:
单账号: MI_MINI_COOKIE=完整的cookie字符串
多账号: MI_MINI_COOKIE=cookie1&&cookie2 或换行分隔
💡 提示: 登录小米社区小程序后，抓包获取完整cookie"""
        print(error_msg)
        notify_user("小米社区小程序签到失败", error_msg)
        return

    # 解析cookie
    cookies = parse_cookies(MI_MINI_COOKIE)
    if not cookies:
        error_msg = """❌ cookie解析失败
🔧 可能原因:
1. cookie格式不正确
2. cookie为空或只包含空白字符
3. 分隔符使用错误
💡 请检查MI_MINI_COOKIE环境变量的值"""
        print(error_msg)
        notify_user("小米社区小程序签到失败", error_msg)
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
                print(f"⏱️ 随机等待 {delay:.1f} 秒后处理下一个账号...")
                time.sleep(delay)

            # 执行签到
            signer = MiCommunityMini(cookie, index + 1)
            result_msg, is_success = signer.main()

            success_count += 1 if is_success else 0
            results.append({
                'index': index + 1,
                'success': is_success,
                'message': result_msg,
                'username': mask_username(signer.user_name) if signer.user_name else f"账号{index + 1}"
            })

            # 单个账号通知
            status = "成功" if is_success else "失败"
            notify_user(f"小米社区小程序账号{index + 1}签到{status}", result_msg)

        except Exception as e:
            error_msg = f"账号{index + 1}: 执行异常 - {str(e)}"
            print(f"❌ {error_msg}")
            notify_user(f"小米社区小程序账号{index + 1}签到失败", error_msg)
            results.append({
                'index': index + 1,
                'success': False,
                'message': error_msg,
                'username': f"账号{index + 1}"
            })

    # 汇总通知
    if total_count > 1:
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        summary_msg = f"""📊 小米社区小程序签到汇总
📈 总计: {total_count}个账号
✅ 成功: {success_count}个
❌ 失败: {total_count - success_count}个
📊 成功率: {success_rate:.1f}%
⏰ 完成时间: {datetime.now().strftime('%m-%d %H:%M')}"""

        # 添加详细结果（最多5个）
        if len(results) <= 5:
            summary_msg += "\n\n📋 详细结果:"
            for result in results:
                status_icon = "✅" if result['success'] else "❌"
                summary_msg += f"\n{status_icon} {result['username']}"

        notify_user("小米社区小程序签到汇总", summary_msg)

    print(
        f"\n==== 小米社区小程序签到完成 - 成功{success_count}/{total_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")


if __name__ == '__main__':
    main()
