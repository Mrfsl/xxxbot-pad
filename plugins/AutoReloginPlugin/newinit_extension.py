import aiohttp
from loguru import logger
from WechatAPI.errors import UserLoggedOut

async def newinit(bot, max_synckey="", current_synckey=""):
    """执行Newinit初始化，同步最新数据

    Args:
        bot: WechatAPIClient实例
        max_synckey: 最大同步键，默认为空
        current_synckey: 当前同步键，默认为空

    Returns:
        dict: 初始化结果

    Raises:
        UserLoggedOut: 未登录时抛出
    """
    if not bot.wxid:
        raise UserLoggedOut("请先登录")

    # 确定API路径前缀
    # 根据协议版本选择正确的API路径前缀
    api_path_prefix = getattr(bot, 'api_path_prefix', None)

    # 如果bot实例没有api_path_prefix属性，尝试根据协议版本判断
    if api_path_prefix is None:
        # 尝试获取协议版本
        protocol_version = getattr(bot, 'protocol_version', None)
        if protocol_version:
            # 根据协议版本选择路径前缀
            if protocol_version == 849:
                api_path_prefix = '/VXAPI'
            else:
                api_path_prefix = '/api'
        else:
            # 默认使用/api作为路径前缀
            api_path_prefix = '/api'

    logger.debug(f"使用API路径前缀: {api_path_prefix}")

    async with aiohttp.ClientSession() as session:
        json_param = {
            "wxid": bot.wxid,
            "MaxSynckey": max_synckey,
            "CurrentSynckey": current_synckey
        }

        logger.debug(f"调用Newinit接口，参数: {json_param}")

        try:
            # 构建完整的API URL
            api_url = f'http://{bot.ip}:{bot.port}{api_path_prefix}/Login/Newinit'
            logger.debug(f"请求URL: {api_url}")

            response = await session.post(
                api_url,
                data=json_param
            )

            # 检查HTTP状态码
            if response.status != 200:
                logger.error(f"Newinit接口HTTP错误: {response.status}, URL: {api_url}")
                return None

            # 检查内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type and 'text/json' not in content_type:
                logger.warning(f"Newinit接口返回非JSON内容: {content_type}")
                # 尝试读取文本内容以便调试
                text = await response.text()
                logger.debug(f"响应内容: {text[:200]}...")  # 只记录前200个字符
                return None

            # 解析JSON响应
            json_resp = await response.json()

            if json_resp.get("Success"):
                logger.debug("Newinit接口调用成功")
                return json_resp.get("Data")
            else:
                logger.warning(f"Newinit接口调用失败: {json_resp.get('Message')}")
                return None

        except aiohttp.ClientError as e:
            logger.error(f"Newinit接口请求错误: {e}")
            return None
        except Exception as e:
            logger.error(f"Newinit接口调用异常: {e}")
            return None
