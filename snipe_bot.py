# 导入所需的库
import ccxt        # 加密货币交易库
import time        # 时间处理
import logging     # 日志记录
from datetime import datetime  # 日期时间处理
from typing import Optional, Dict, Any  # 类型提示

class SnipeBot:
    def __init__(self, api_key: str, secret: str, password: str, proxies: dict = None):
        """
        初始化交易机器人
        :param api_key: OKX API key
        :param secret: OKX API secret
        :param password: OKX API passphrase
        :param proxies: 代理设置
        """
        # 设置日志记录器
        self.logger = self._setup_logger()  # 确保 logger 被正确初始化
        
        # 初始化交易所连接
        self.exchange = self._initialize_exchange(api_key, secret, password, proxies)
        
        # 交易参数初始化
        self.target_symbol: str = None      # 交易对，如 'ETH/USDT'
        self.quote_amount: float = None     # 交易金额（USDT）
        self.max_price: float = None        # 最高接受价格
        self.order_type: str = 'market'     # 订单类型：'market'（市价） 或 'limit'（限价）
        self.limit_price: float = None      # 限价单价格
        
    def _initialize_exchange(self, api_key: str, secret: str, password: str, proxies: dict) -> ccxt.Exchange:
        """初始化交易所连接"""
        try:
            # 创建OKX交易所实例
            exchange = ccxt.okx({
                'apiKey': api_key,          # API密钥
                'secret': secret,           # API密钥
                'password': password,       # API密码
                'proxies': proxies,         # 代理设置
                'timeout': 30000,           # 超时时间（毫秒）
                'enableRateLimit': True,    # 启用请求频率限制
                'test': True,               # 使用测试网络
                'hostname': 'www.okx.com'   # OKX主机名
            })
            
            # 设置为测试网络模式
            exchange.set_sandbox_mode(True)
            
            # 加载市场数据
            self.logger.info("正在加载市场数据...")
            exchange.load_markets()
            self.logger.info("市场数据加载完成")
            
            return exchange
            
        except Exception as e:
            self.logger.error(f"初始化交易所失败: {str(e)}")
            raise
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        # 配置日志格式和输出
        logging.basicConfig(
            level=logging.INFO,    # 日志级别
            format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式
            handlers=[
                logging.StreamHandler(),     # 输出到控制台
                logging.FileHandler(         # 输出到文件
                    f'snipe_bot_{datetime.now().strftime("%Y%m%d")}.log'  # 日志文件名
                )
            ]
        )
        return logging.getLogger(__name__)

    def calculate_buy_amount(self, price: float) -> float:
        """
        根据资金量计算购买数量，并确保大于最小交易量
        :param price: 当前价格或限价
        :return: 计算出的购买数量
        """
        try:
            # 计算原始购买数量
            amount = self.quote_amount / price
            
            # 获取交易对信息
            market = self.exchange.market(self.target_symbol)
            # 获取最小交易量，默认为0.01
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0.01)
            
            # 确保大于最小交易量
            amount = max(amount, min_amount)
            
            # 使用4位小数精度格式化数量
            formatted_amount = "{:.4f}".format(amount)
            self.logger.info(f"计算入数量: {amount} -> {formatted_amount} (最小数量: {min_amount})")
            
            return float(formatted_amount)
            
        except Exception as e:
            self.logger.error(f"计算买入数量失败: {str(e)}")
            return None

    def get_current_price(self) -> Optional[float]:
        """获取当前价格"""
        try:
            ticker = self.exchange.fetch_ticker(self.target_symbol)  # 获取当前交易对的行情
            return ticker['last']  # 返回最新价格
        except Exception as e:
            self.logger.error(f"获取价格失败: {str(e)}")
            return None

    def check_balance(self) -> bool:
        """检查账户余额是否足够"""
        try:
            balance = self.exchange.fetch_balance()  # 获取账户余额
            quote_currency = self.target_symbol.split('/')[1]  # 获取计价货币（如USDT）
            available = balance[quote_currency]['free']  # 可用余额
            
            self.logger.info(f"可用{quote_currency}余额: {available}, 需要: {self.quote_amount}")
            return available >= self.quote_amount  # 检查是否足够
        except Exception as e:
            self.logger.error(f"检查余额失败: {str(e)}")
            return False

    def place_order(self) -> Optional[Dict[str, Any]]:
        """下单"""
        try:
            if not self.check_balance():  # 检查余额
                self.logger.error("余额不足")
                return None

            if self.order_type == 'market':  # 市价单
                current_price = self.get_current_price()  # 获取当前价格
                if current_price is None:
                    self.logger.error("无法获取当前价格")
                    return None
                    
                amount = self.calculate_buy_amount(current_price)  # 计算买入数量
                if amount is None:
                    self.logger.error("计算买入数量失败")
                    return None
                    
                # 获取最小交易量
                market = self.exchange.market(self.target_symbol)
                min_amount = market.get('limits', {}).get('amount', {}).get('min', 0.0001)  # 默认最小交易量
                
                # 打印调试信息
                self.logger.info(f"当前价格: {current_price}, 计算出的买入数量: {amount}, 最小交易量: {min_amount}")

                # 检查计算出的数量是否大于最小交易量
                if amount < min_amount:
                    self.logger.error(f"计算出的买入数量 {amount} 小于最小交易量 {min_amount}")
                    return None
                
                self.logger.info(f"准备下单: 数量={amount}, 预计金额≈{self.quote_amount} USDT")
                
                # 创建市价买入订单
                order = self.exchange.create_market_buy_order(
                    symbol=self.target_symbol,
                    amount=str(amount),  # 转换为字符串
                    params={
                        'tdMode': 'cash',
                        'tgtCcy': 'quote_ccy'  # 使用计价货币（USDT）模式
                    }
                )
                self.logger.info(f"市价买入成功: 数量={amount}, 金额≈{self.quote_amount} USDT")
                self.logger.info(f"订单详情: {order}")
            else:  # 限价单
                amount = self.calculate_buy_amount(self.limit_price)  # 计算买入数量
                if amount is None:
                    self.logger.error("计算买入数量失败")
                    return None
                    
                # 获取最小交易量
                market = self.exchange.market(self.target_symbol)
                min_amount = market.get('limits', {}).get('amount', {}).get('min', 0.0001)  # 默认最小交易量
                
                # 打印调试信息
                self.logger.info(f"计算出的买入数量: {amount}, 最小交易量: {min_amount}")

                # 检查计算出的数量是否大于最小交易量
                if amount < min_amount:
                    self.logger.error(f"计算出的买入数量 {amount} 小于最小交易量 {min_amount}")
                    return None
                
                self.logger.info(f"准备下单: 数量={amount}, 金额={self.quote_amount} USDT")
                
                # 创建限价买入订单
                order = self.exchange.create_limit_buy_order(
                    symbol=self.target_symbol,
                    amount=str(amount),  # 转换为字符串
                    price=self.limit_price,
                    params={
                        'tdMode': 'cash',
                        'tgtCcy': 'quote_ccy'  # 使用计价货币（USDT）模式
                    }
                )
                self.logger.info(f"限价买入成功: 数量={amount}, 金额={self.quote_amount} USDT")
                self.logger.info(f"订单详情: {order}")
            return order
        except Exception as e:
            self.logger.error(f"下单失败: {str(e)}")  # 记录下单失败的详细错误信息
            return None
def run(self):
    """主运行逻辑"""
    try:
        # 1. 重新加载市场数据
        self.logger.info("正在重新加载市场数据...")
        self.exchange.load_markets()
        self.logger.info("市场数据加载完成")

        # 2. 参数验证
        if not all([self.target_symbol, self.quote_amount]):
            self.logger.error("请设置交易对和买入金额")
            return
            
        if self.order_type == 'limit' and not self.limit_price:
            self.logger.error("使用限价单时必须设置限价")
            return
            
        if not self.max_price:
            if self.order_type == 'limit':
                self.max_price = self.limit_price * 1.01
                self.logger.info(f"未设置最高价格，自动设置为限价的1.01倍: {self.max_price}")
            else:
                self.logger.error("使用市价单时必须设置最高价格")
                return

        # 3. 检查交易对是否存在
        if self.target_symbol not in self.exchange.markets:
            self.logger.error(f"交易对 {self.target_symbol} 不存在")
            return

        # 4. 获取交易对信息
        market = self.exchange.market(self.target_symbol)
        min_cost = market.get('limits', {}).get('cost', {}).get('min', 0)  # 获取最小交易金额
        min_amount = market.get('limits', {}).get('amount', {}).get('min', 0.0001)  # 默认最小交易量

        # 5. 检查最小交易金额
        if min_cost and self.quote_amount < min_cost:
            self.logger.error(f"买入金额 {self.quote_amount} USDT 小于最小交易金额 {min_cost} USDT")
            return

        # 6. 打印交易信息
        self.logger.info("-" * 50)
        self.logger.info(f"开始监控 {self.target_symbol} (测试网环境)")
        self.logger.info(f"订单类型: {self.order_type}")
        self.logger.info(f"买入金额: {self.quote_amount} USDT")
        self.logger.info(f"最小交易金额: {min_cost} USDT")
        self.logger.info(f"最小交易数量: {min_amount}")
        if self.order_type == 'limit':
            self.logger.info(f"限价价格: {self.limit_price}")
        self.logger.info(f"最高价格: {self.max_price}")
        self.logger.info("-" * 50)
        
        # 7. 主循环
        retry_count = 0
        max_retries = 3

        while True:
            try:
                # 7.1 获取当前价格
                current_price = self.get_current_price()
                if current_price is None:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self.logger.error("连续获取价格失败，程序退出")
                        break
                    self.logger.info(f"获取价格失败，{retry_count}/{max_retries} 次重试")
                    time.sleep(1)
                    continue

                self.logger.info(f"当前价格: {current_price}")
                
                # 7.2 检查价格是否满足条件
                if current_price <= self.max_price:
                    # 7.3 尝试下单
                    order = self.place_order()
                    if order:
                        self.logger.info("交易完成，退出程序")
                        self.logger.info("-" * 50)
                        break
                    else:
                        self.logger.error("下单失败，继续监控...")
                else:
                    self.logger.info(f"当前价格 {current_price} 超过最高限价 {self.max_price}，继续监控...")
                
                # 7.4 重置重试计数和等待
                retry_count = 0
                time.sleep(1)  # 1秒轮询间隔
                
            except KeyboardInterrupt:
                self.logger.info("\n程序被手动中断")
                self.logger.info("-" * 50)
                break
            except Exception as e:
                self.logger.error(f"运行错误: {str(e)}")
                time.sleep(1)

    except Exception as e:
        self.logger.error(f"程序初始化错误: {str(e)}")
        self.logger.info("-" * 50)

def place_order(self) -> Optional[Dict[str, Any]]:
    """下单"""
    try:
        if not self.check_balance():  # 检查余额
            self.logger.error("余额不足")
            return None

        if self.order_type == 'market':  # 市价单
            current_price = self.get_current_price()  # 获取当前价格
            if current_price is None:
                self.logger.error("无法获取当前价格")
                return None
                
            amount = self.calculate_buy_amount(current_price)  # 计算买入数量
            if amount is None:
                self.logger.error("计算买入数量失败")
                return None
            
            # 获取最小交易量
            market = self.exchange.market(self.target_symbol)
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0.0001)  # 默认最小交易量
            
            # 打印调试信息
            self.logger.info(f"当前价格: {current_price}, 计算出的买入数量: {amount}, 最小交易量: {min_amount}")

            # 检查计算出的数量是否大于最小交易量
            if amount < min_amount:
                self.logger.error(f"计算出的买入数量 {amount} 小于最小交易量 {min_amount}")
                return None
            
            self.logger.info(f"准备下单: 数量={amount}, 预计金额≈{self.quote_amount} USDT")
            
            # 创建市价买入订单
            order = self.exchange.create_market_buy_order(
                symbol=self.target_symbol,
                amount=str(amount),  # 转换为字符串
                params={
                    'tdMode': 'cash',
                    'tgtCcy': 'quote_ccy'  # 使用计价货币（USDT）模式
                }
            )
            self.logger.info(f"市价买入成功: 数量={amount}, 金额≈{self.quote_amount} USDT")
            self.logger.info(f"订单详情: {order}")
        else:  # 限价单
            amount = self.calculate_buy_amount(self.limit_price)  # 计算买入数量
            if amount is None:
                self.logger.error("计算买入数量失败")
                return None
            
            # 获取最小交易量
            market = self.exchange.market(self.target_symbol)
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0.0001)  # 默认最小交易量
            
            # 打印调试信息
            self.logger.info(f"计算出的买入数量: {amount}, 最小交易量: {min_amount}")

            # 检查计算出的数量是否大于最小交易量
            if amount < min_amount:
                self.logger.error(f"计算出的买入数量 {amount} 小于最小交易量 {min_amount}")
                return None
            
            self.logger.info(f"准备下单: 数量={amount}, 金额={self.quote_amount} USDT")
            
            # 创建限价买入订单
            order = self.exchange.create_limit_buy_order(
                symbol=self.target_symbol,
                amount=str(amount),  # 转换为字符串
                price=self.limit_price,
                params={
                    'tdMode': 'cash',
                    'tgtCcy': 'quote_ccy'  # 使用计价货币（USDT）模式
                }
            )
            self.logger.info(f"限价买入成功: 数量={amount}, 金额={self.quote_amount} USDT")
            self.logger.info(f"订单详情: {order}")
        return order
    except Exception as e:
        self.logger.error(f"下单失败: {str(e)}")  # 记录下单失败的详细错误信息
        return None
    