import asyncio
import time
from loguru import logger
from utils.decorators import schedule
from utils.plugin_base import PluginBase
from WechatAPI.Client import WechatAPIClient

class AutoReloginPlugin(PluginBase):
    """自动二次登录插件，保持微信长时间在线"""

    description = "定期执行二次登录，保持微信长时间在线"
    author = "Augment Agent"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.enable = True
        self.last_relogin_time = 0
        self.relogin_interval = 7200  # 默认7200秒执行一次二次登录
        self.max_retry_count = 3  # 最大重试次数
        self.retry_interval = 60  # 重试间隔（秒）
        self.consecutive_failures = 0  # 连续失败次数

    async def on_enable(self, bot=None):
        """插件启用时调用"""
        await super().on_enable(bot)
        logger.info("自动二次登录插件已启用，将每{}秒执行一次二次登录", self.relogin_interval)
        self.last_relogin_time = time.time()

    @schedule('interval', seconds=7200)  # 每7200秒执行一次
    async def auto_relogin(self, bot: WechatAPIClient):
        """定期执行二次登录"""
        if not self.enable:
            return

        if not bot.wxid:
            logger.warning("未登录状态，无法执行二次登录")
            return

        logger.info("开始执行定期二次登录...")

        # 执行二次登录，包含重试机制
        success = await self._perform_relogin_with_retry(bot)

        if success:
            self.last_relogin_time = time.time()
            self.consecutive_failures = 0
            logger.success("二次登录成功，会话已刷新")
        else:
            self.consecutive_failures += 1
            logger.error(f"二次登录失败，已达到最大重试次数，连续失败次数: {self.consecutive_failures}")

            # 如果连续失败3次，尝试完整重新登录
            if self.consecutive_failures >= 3:
                logger.warning("连续失败次数过多，尝试完整重新登录")
                success = await self._perform_complete_relogin(bot)
                if success:
                    self.consecutive_failures = 0
                    self.last_relogin_time = time.time()
                    logger.success("完整重新登录成功")
                else:
                    logger.error("完整重新登录失败")

    @schedule('interval', seconds=300)  # 每5分钟检查一次登录状态
    async def check_login_status(self, bot: WechatAPIClient):
        """定期检查登录状态"""
        if not self.enable:
            return

        if not bot.wxid:
            logger.warning("未登录状态，无法检查登录状态")
            return

        try:
            # 检查登录状态的最简单方法是尝试获取个人信息
            profile = await bot.get_profile()
            if profile:
                logger.debug("登录状态正常")
            else:
                logger.warning("登录状态异常，可能已掉线")

                # 如果距离上次二次登录超过10分钟，尝试重新二次登录
                if time.time() - self.last_relogin_time > 600:
                    logger.info("尝试执行紧急二次登录...")
                    success = await self._perform_relogin_with_retry(bot)

                    if success:
                        self.last_relogin_time = time.time()
                        self.consecutive_failures = 0
                        logger.success("紧急二次登录成功，会话已恢复")
                    else:
                        self.consecutive_failures += 1
                        logger.error(f"紧急二次登录失败，连续失败次数: {self.consecutive_failures}")

                        # 如果连续失败3次，尝试完整重新登录
                        if self.consecutive_failures >= 3:
                            logger.warning("连续失败次数过多，尝试完整重新登录")
                            success = await self._perform_complete_relogin(bot)
                            if success:
                                self.consecutive_failures = 0
                                self.last_relogin_time = time.time()
                                logger.success("完整重新登录成功")
                            else:
                                logger.error("完整重新登录失败")
        except Exception as e:
            logger.error(f"检查登录状态出错: {e}")

            # 如果出现异常，可能是登录已失效，尝试紧急二次登录
            if time.time() - self.last_relogin_time > 600:
                logger.info("检测到异常，尝试执行紧急二次登录...")
                try:
                    success = await self._perform_relogin_with_retry(bot)

                    if success:
                        self.last_relogin_time = time.time()
                        self.consecutive_failures = 0
                        logger.success("紧急二次登录成功，会话已恢复")
                    else:
                        self.consecutive_failures += 1
                        logger.error(f"紧急二次登录失败，连续失败次数: {self.consecutive_failures}")
                except Exception as e2:
                    logger.error(f"紧急二次登录出错: {e2}")
                    self.consecutive_failures += 1

    async def _perform_relogin_with_retry(self, bot: WechatAPIClient) -> bool:
        """执行二次登录，包含重试机制

        Args:
            bot: WechatAPIClient实例

        Returns:
            bool: 是否成功
        """
        retry_count = 0

        while retry_count < self.max_retry_count:
            try:
                # 执行二次登录
                result = await bot.twice_login(bot.wxid)

                if result:
                    # 二次登录成功后，执行数据同步
                    await self._perform_data_sync(bot)
                    return True
                else:
                    logger.warning(f"二次登录返回空结果，尝试重试 ({retry_count+1}/{self.max_retry_count})")
            except Exception as e:
                logger.error(f"二次登录出错: {e}，尝试重试 ({retry_count+1}/{self.max_retry_count})")

            # 增加重试计数并等待
            retry_count += 1
            if retry_count < self.max_retry_count:
                await asyncio.sleep(self.retry_interval)

        return False

    async def _perform_data_sync(self, bot: WechatAPIClient):
        """执行数据同步

        Args:
            bot: WechatAPIClient实例
        """
        # 检测协议版本
        protocol_version = getattr(bot, 'protocol_version', None)

        # 如果无法获取协议版本，尝试从api_path_prefix判断
        if protocol_version is None:
            api_path_prefix = getattr(bot, 'api_path_prefix', '')
            if api_path_prefix == '/VXAPI':
                protocol_version = 849
            else:
                protocol_version = 0  # 非849协议

        logger.debug(f"当前协议版本: {protocol_version}")

        try:
            # 根据协议版本选择同步方法
            if protocol_version == 849:
                # 849协议使用Newinit
                logger.debug("使用Newinit进行数据同步")
                await self._perform_newinit_sync(bot)
            else:
                # 非849协议直接使用sync_message
                logger.debug("使用sync_message进行数据同步")
                ok, data = await bot.sync_message()
                if ok:
                    logger.info("数据同步成功")
                else:
                    logger.warning(f"数据同步失败: {data}")
        except Exception as e:
            logger.error(f"数据同步出错: {e}")

            # 如果出现异常，尝试使用sync_message
            try:
                ok, data = await bot.sync_message()
                if ok:
                    logger.info("使用sync_message同步成功")
                else:
                    logger.warning(f"使用sync_message同步失败: {data}")
            except Exception as e2:
                logger.error(f"使用sync_message同步出错: {e2}")

    async def _perform_newinit_sync(self, bot: WechatAPIClient):
        """使用Newinit进行数据同步

        Args:
            bot: WechatAPIClient实例
        """
        # 导入newinit扩展
        from .newinit_extension import newinit

        # 执行Newinit初始化
        result = await newinit(bot)
        if result:
            logger.info("Newinit初始化成功")

            # 检查是否需要继续同步
            continue_flag = result.get("ContinueFlag")
            if continue_flag == 1:
                logger.info("需要继续同步数据")

                # 获取同步键
                current_synckey = result.get("CurrentSynckey", {}).get("Buffer", "")
                max_synckey = result.get("MaxSynckey", {}).get("Buffer", "")

                # 再次执行Newinit，带入同步键
                await newinit(bot, max_synckey, current_synckey)
        else:
            # 如果Newinit失败，回退到使用sync_message
            logger.warning("Newinit初始化失败，回退到使用sync_message")
            ok, data = await bot.sync_message()
            if ok:
                logger.info("数据同步成功")
            else:
                logger.warning(f"数据同步失败: {data}")

    async def _perform_complete_relogin(self, bot: WechatAPIClient):
        """执行完整重新登录

        Args:
            bot: WechatAPIClient实例

        Returns:
            bool: 是否成功
        """
        logger.warning("开始执行完整重新登录...")

        try:
            # 获取之前的登录信息
            wxid = bot.wxid
            device_id = ""
            device_name = ""

            # 尝试从缓存获取设备信息
            try:
                cached_info = await bot.get_cached_info(wxid)
                if cached_info:
                    # 提取设备信息
                    device_id = cached_info.get("device_id", "")
                    device_name = cached_info.get("device_name", "")
            except Exception as e:
                logger.error(f"获取缓存信息失败: {e}")

            # 如果没有设备信息，创建新的
            if not device_name:
                device_name = bot.create_device_name()
            if not device_id:
                device_id = bot.create_device_id()

            # 尝试唤醒登录
            try:
                logger.info("尝试唤醒登录...")
                awaken_result = await bot.awaken_login(wxid)
                if awaken_result:
                    logger.success("唤醒登录成功")
                    # 唤醒登录成功后，执行数据同步
                    await self._perform_data_sync(bot)
                    return True
            except Exception as e:
                logger.error(f"唤醒登录失败: {e}")

            # 如果唤醒登录失败，尝试二维码登录
            logger.info("尝试二维码登录...")
            uuid, url = await bot.get_qr_code(device_id=device_id, device_name=device_name)

            if not uuid or not url:
                logger.error("获取二维码失败")
                return False

            logger.info(f"请扫描二维码登录: {url}")

            # 等待扫码
            max_wait_time = 300  # 最多等待5分钟
            wait_time = 0

            while wait_time < max_wait_time:
                stat, data = await bot.check_login_uuid(uuid, device_id=device_id)
                if stat:
                    logger.success("二维码登录成功")
                    # 登录成功后，执行数据同步
                    await self._perform_data_sync(bot)
                    return True

                await asyncio.sleep(5)
                wait_time += 5
                logger.info(f"等待扫码中... {wait_time}/{max_wait_time}秒")

            logger.error("二维码登录超时")
            return False
        except Exception as e:
            logger.error(f"完整重新登录出错: {e}")
            return False
