from snipe_bot import SnipeBot

if __name__ == "__main__":
    # API配置
    api_key = "fa054e21-26b3-4298-bb25-3b94b7633f57"    # 替换为您的 API KEY
    secret_key = "73C15C4689EC2F337FF4E5E0D7C6198F"    # 替换为您的 SECRET KEY
    passphrase = "Zhonglei1985@"    # 替换为您的密码短语

        # 代理配置
    proxies = {
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890'
    }

    try:
        # 创建机器人实例
        bot = SnipeBot(
            api_key=api_key,
            secret=secret_key,
            password=passphrase,
            proxies=proxies
        )

        # 市价单模式
        bot.target_symbol = 'ETH/USDT'
        bot.quote_amount = 100          # 买入50 USDT
        bot.order_type = 'market'      # 使用市价单
        bot.max_price = 3000          # 市价单必须设置最高价格作为保护

        # 或者限价单模式
        # bot.target_symbol = 'ETH/USDT'
        # bot.quote_amount = 50          # 买入50 USDT
        # bot.order_type = 'limit'       # 使用限价单
        # bot.limit_price = 2100        # 限价单价格
        # bot.max_price = 2200          # 建议设置一个最高价格作为保护

        # 运行机器人
        bot.run()
    except Exception as e:
        print(f"程序出错: {str(e)}")