import MetaTrader5 as mt5
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class MatrixAITraderRobot:
    """
    Advanced Automated Forex Trading Robot using MetaTrader 5
    Features: 1:2 Risk/Reward Ratio, 1% Stop Loss, Take Profit Detection
    """

    def __init__(self, risk_percentage=1.0, max_trades=5, email_enabled=False):
        self.connected = False
        self.risk_percentage = risk_percentage  # 1% stop loss
        self.max_trades = max_trades
        self.active_trades = 0
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.email_enabled = email_enabled
        self.email_address = None
        self.email_password = None
        self.monitoring_active = False

    def connect(self):
        """Initialize connection to MetaTrader 5"""
        if not mt5.initialize():
            print("❌ MT5 Connection Failed")
            return False

        self.connected = True
        print("✅ Connected to MetaTrader 5")
        return True

    def disconnect(self):
        """Safely disconnect from MetaTrader 5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("📊 Disconnected from MetaTrader 5")

    def setup_email_notifications(self):
        """Setup email notifications for trades"""
        print("\n====== EMAIL NOTIFICATIONS SETUP ======")
        email = input("Enter your Gmail address: ").strip()
        password = input("Enter your Gmail app password: ").strip()
        
        self.email_address = email
        self.email_password = password
        self.email_enabled = True
        print("✅ Email notifications enabled\n")

    def send_email(self, subject, body):
        """Send email notification"""
        if not self.email_enabled or not self.email_address:
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = self.email_address
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email_address, self.email_password)
            server.send_message(msg)
            server.quit()
            print(f"📧 Email sent: {subject}")
        except Exception as e:
            print(f"⚠️ Email failed: {str(e)}")

    def get_account_info(self):
        """Retrieve and display account information"""
        if not self.connected:
            print("❌ Not connected to MT5")
            return None

        info = mt5.account_info()
        if info:
            print("\n====== ACCOUNT INFO ======")
            print(f"Login: {info.login}")
            print(f"Balance: ${info.balance:.2f}")
            print(f"Equity: ${info.equity:.2f}")
            print(f"Profit/Loss: ${info.profit:.2f}")
            print(f"Free Margin: ${info.margin_free:.2f}")
            print(f"Used Margin: ${info.margin:.2f}")
            print(f"Account Leverage: 1:{info.leverage}")
            print("==========================\n")
            return info
        return None

    def get_price(self, symbol):
        """Get current bid/ask price for a symbol"""
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            return {
                'symbol': symbol,
                'bid': tick.bid,
                'ask': tick.ask,
                'time': datetime.fromtimestamp(tick.time)
            }
        return None

    def calculate_lot_size_with_1percent_sl(self, symbol, account_info):
        """
        Calculate lot size with 1% stop loss
        1% = entire account risk per trade
        """
        if not account_info:
            return 0.01
        
        # Risk amount = 1% of account balance
        risk_amount = account_info.balance * (self.risk_percentage / 100)
        
        # Get symbol info
        sym_info = mt5.symbol_info(symbol)
        if not sym_info:
            return 0.01
        
        point = sym_info.point
        tick_value = sym_info.trade_tick_value
        
        # 1% stop loss = 100 pips for most pairs (0.01 change)
        stop_loss_pips = 100  # Standard 1% risk
        
        # Lot size = Risk Amount / (Stop Loss Pips * Point Value)
        lot_size = risk_amount / (stop_loss_pips * point * tick_value)
        
        # Ensure lot size is within reasonable limits
        lot_size = max(0.01, min(lot_size, 1.0))
        return round(lot_size, 2)

    def place_buy_order_with_1to2(self, symbol, lot_size):
        """
        Place BUY order with 1:2 Risk/Reward Ratio
        Stop Loss = 1% (100 pips)
        Take Profit = 2% (200 pips)
        """
        if not self.connected:
            print("❌ Not connected to MT5")
            return False

        price_info = self.get_price(symbol)
        if not price_info:
            print(f"❌ Could not get price for {symbol}")
            return False

        sym_info = mt5.symbol_info(symbol)
        point = sym_info.point
        
        # 1% Stop Loss = 100 pips
        stop_loss_pips = 100
        # 2% Take Profit = 200 pips (1:2 ratio)
        take_profit_pips = 200

        stop_loss = price_info['ask'] - (stop_loss_pips * point)
        take_profit = price_info['ask'] + (take_profit_pips * point)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price_info['ask'],
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 234000,
            "comment": "Matrix AI Robot BUY | 1:2 Ratio | 1% SL | 2% TP",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Buy order failed for {symbol}: {result.comment}")
            return False

        self.active_trades += 1
        self.total_trades += 1
        
        message = (
            f"✅ BUY ORDER PLACED\n"
            f"Symbol: {symbol}\n"
            f"Volume: {lot_size}\n"
            f"Entry: {price_info['ask']:.5f}\n"
            f"Stop Loss (1%): {stop_loss:.5f}\n"
            f"Take Profit (2%): {take_profit:.5f}\n"
            f"Risk/Reward: 1:2\n"
            f"Order Ticket: {result.order}"
        )
        print(message)
        
        self.send_email("Matrix AI Robot - BUY Order", message)
        return result.order

    def place_sell_order_with_1to2(self, symbol, lot_size):
        """
        Place SELL order with 1:2 Risk/Reward Ratio
        Stop Loss = 1% (100 pips)
        Take Profit = 2% (200 pips)
        """
        if not self.connected:
            print("❌ Not connected to MT5")
            return False

        price_info = self.get_price(symbol)
        if not price_info:
            print(f"❌ Could not get price for {symbol}")
            return False

        sym_info = mt5.symbol_info(symbol)
        point = sym_info.point
        
        # 1% Stop Loss = 100 pips
        stop_loss_pips = 100
        # 2% Take Profit = 200 pips (1:2 ratio)
        take_profit_pips = 200

        stop_loss = price_info['bid'] + (stop_loss_pips * point)
        take_profit = price_info['bid'] - (take_profit_pips * point)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price_info['bid'],
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 234000,
            "comment": "Matrix AI Robot SELL | 1:2 Ratio | 1% SL | 2% TP",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Sell order failed for {symbol}: {result.comment}")
            return False

        self.active_trades += 1
        self.total_trades += 1
        
        message = (
            f"✅ SELL ORDER PLACED\n"
            f"Symbol: {symbol}\n"
            f"Volume: {lot_size}\n"
            f"Entry: {price_info['bid']:.5f}\n"
            f"Stop Loss (1%): {stop_loss:.5f}\n"
            f"Take Profit (2%): {take_profit:.5f}\n"
            f"Risk/Reward: 1:2\n"
            f"Order Ticket: {result.order}"
        )
        print(message)
        
        self.send_email("Matrix AI Robot - SELL Order", message)
        return result.order

    def monitor_take_profit_detection(self):
        """
        Monitor all open positions and detect when Take Profit is hit
        """
        print("\n🔍 Starting Take Profit Detection Monitoring...")
        self.monitoring_active = True
        
        try:
            while self.monitoring_active:
                positions = self.get_open_positions()
                
                if not positions:
                    print("📭 No open positions to monitor")
                    time.sleep(5)
                    continue
                
                print(f"\n⏱️ Monitoring {len(positions)} position(s)...")
                
                for pos in positions:
                    profit_percent = (pos.profit / (pos.volume * pos.price_open * 100)) * 100
                    
                    # Check if take profit is close (within 10 pips)
                    if pos.type == mt5.ORDER_TYPE_BUY:
                        distance_to_tp = pos.tp - pos.price_current
                        pips_away = distance_to_tp / mt5.symbol_info(pos.symbol).point
                    else:
                        distance_to_tp = pos.price_current - pos.tp
                        pips_away = distance_to_tp / mt5.symbol_info(pos.symbol).point
                    
                    direction = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                    
                    print(f"\n  [{pos.symbol}] {direction} | Ticket: {pos.ticket}")
                    print(f"  Entry: {pos.price_open:.5f} | Current: {pos.price_current:.5f}")
                    print(f"  Profit: ${pos.profit:.2f} | Pips to TP: {pips_away:.1f}")
                    
                    # Alert when TP is close
                    if 0 < pips_away <= 10:
                        alert = f"⚠️ TAKE PROFIT ALERT! {pos.symbol} {direction} - {pips_away:.1f} pips away from TP!"
                        print(alert)
                        self.send_email("Matrix AI - TP Alert!", alert)
                    
                    # Alert if TP hit
                    if pos.profit >= 0 and pos.tp > 0:
                        if (pos.type == mt5.ORDER_TYPE_BUY and pos.price_current >= pos.tp) or \
                           (pos.type == mt5.ORDER_TYPE_SELL and pos.price_current <= pos.tp):
                            tp_message = f"🎯 TAKE PROFIT HIT! {pos.symbol} {direction}\nProfit: ${pos.profit:.2f}"
                            print(f"\n{tp_message}")
                            self.send_email("Matrix AI - TP HIT!", tp_message)
                
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            print("\n⛔ Monitoring stopped by user")
            self.monitoring_active = False

    def monitor_stop_loss_detection(self):
        """
        Monitor all open positions and detect when Stop Loss is hit
        """
        print("\n🔍 Starting Stop Loss Detection Monitoring...")
        self.monitoring_active = True
        
        try:
            while self.monitoring_active:
                positions = self.get_open_positions()
                
                if not positions:
                    print("📭 No open positions to monitor")
                    time.sleep(5)
                    continue
                
                print(f"\n⏱️ Monitoring {len(positions)} position(s) for SL...")
                
                for pos in positions:
                    # Check if stop loss is close (within 10 pips)
                    if pos.type == mt5.ORDER_TYPE_BUY:
                        distance_to_sl = pos.price_current - pos.sl
                        pips_away = distance_to_sl / mt5.symbol_info(pos.symbol).point
                    else:
                        distance_to_sl = pos.sl - pos.price_current
                        pips_away = distance_to_sl / mt5.symbol_info(pos.symbol).point
                    
                    direction = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                    
                    # Alert when SL is close
                    if 0 < pips_away <= 10:
                        alert = f"⚠️ STOP LOSS WARNING! {pos.symbol} {direction} - {pips_away:.1f} pips away from SL!"
                        print(f"\n  {alert}")
                        self.send_email("Matrix AI - SL Warning!", alert)
                    
                    # Alert if SL hit
                    if pos.profit <= 0 and pos.sl > 0:
                        if (pos.type == mt5.ORDER_TYPE_BUY and pos.price_current <= pos.sl) or \
                           (pos.type == mt5.ORDER_TYPE_SELL and pos.price_current >= pos.sl):
                            sl_message = f"❌ STOP LOSS HIT! {pos.symbol} {direction}\nLoss: ${pos.profit:.2f}"
                            print(f"\n{sl_message}")
                            self.send_email("Matrix AI - SL HIT!", sl_message)
                
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            print("\n⛔ Monitoring stopped by user")
            self.monitoring_active = False

    def close_order(self, ticket):
        """Close an open position by ticket"""
        if not self.connected:
            return False

        position = mt5.positions_get(ticket=ticket)
        if not position:
            print(f"❌ Position {ticket} not found")
            return False

        pos = position[0]
        
        # Determine if it's a buy or sell position
        if pos.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(pos.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(pos.symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Matrix AI Robot CLOSE",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Failed to close position {ticket}")
            return False

        self.active_trades -= 1
        profit = pos.profit
        
        if profit > 0:
            self.wins += 1
            print(f"✅ Position Closed - PROFIT: ${profit:.2f}")
        else:
            self.losses += 1
            print(f"❌ Position Closed - LOSS: ${profit:.2f}")
        
        return True

    def get_open_positions(self):
        """Get all open positions"""
        if not self.connected:
            return []

        positions = mt5.positions_get()
        return positions if positions else []

    def display_positions(self):
        """Display all open positions with risk/reward info"""
        positions = self.get_open_positions()
        
        if not positions:
            print("📭 No open positions")
            return

        print("\n====== OPEN POSITIONS (1:2 Risk/Reward) ======")
        for pos in positions:
            direction = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
            profit_percent = (pos.profit / (pos.volume * pos.price_open * 100)) * 100
            
            print(f"\nTicket: {pos.ticket} | {pos.symbol} | {direction}")
            print(f"  Volume: {pos.volume} | Entry: {pos.price_open:.5f}")
            print(f"  Current: {pos.price_current:.5f} | Profit: ${pos.profit:.2f} ({profit_percent:.2f}%)")
            print(f"  🛑 SL (1%): {pos.sl:.5f} | 🎯 TP (2%): {pos.tp:.5f}")
        print("=" * 50 + "\n")

    def display_statistics(self):
        """Display robot trading statistics"""
        win_rate = (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
        print("\n====== TRADING STATISTICS (1:2 Risk/Reward) ======")
        print(f"Total Trades: {self.total_trades}")
        print(f"Active Trades: {self.active_trades}")
        print(f"Wins: {self.wins}")
        print(f"Losses: {self.losses}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Stop Loss: 1% (100 pips)")
        print(f"Take Profit: 2% (200 pips)")
        print(f"Risk/Reward Ratio: 1:2")
        print("=" * 50 + "\n")

    def run_advanced_demo(self):
        """Run advanced demo with 1:2 ratio and monitoring"""
        if not self.connect():
            return

        try:
            account_info = self.get_account_info()
            
            symbols = ["XAUUSD", "EURUSD", "GBPUSD"]
            
            while True:
                print("\n" + "="*50)
                print(" MATRIX AI TRADER ROBOT - ADVANCED")
                print(" 1:2 Risk/Reward | 1% SL | 2% TP")
                print("="*50)
                print("1. View Prices")
                print("2. Place BUY Order (EURUSD) - 1:2 Ratio")
                print("3. Place SELL Order (EURUSD) - 1:2 Ratio")
                print("4. View Open Positions")
                print("5. Close All Positions")
                print("6. View Statistics")
                print("7. Monitor Take Profit Detection")
                print("8. Monitor Stop Loss Detection")
                print("9. Setup Email Notifications")
                print("10. Auto Trade Demo (5 trades)")
                print("11. Exit")
                print("="*50)
                
                choice = input("Select: ").strip()

                if choice == "1":
                    print("\n====== CURRENT PRICES ======")
                    for symbol in symbols:
                        price_info = self.get_price(symbol)
                        if price_info:
                            print(f"{symbol}: Bid {price_info['bid']:.5f} | Ask {price_info['ask']:.5f}")
                    print("============================\n")

                elif choice == "2":
                    lot_size = self.calculate_lot_size_with_1percent_sl("EURUSD", account_info)
                    self.place_buy_order_with_1to2("EURUSD", lot_size)

                elif choice == "3":
                    lot_size = self.calculate_lot_size_with_1percent_sl("EURUSD", account_info)
                    self.place_sell_order_with_1to2("EURUSD", lot_size)

                elif choice == "4":
                    self.display_positions()

                elif choice == "5":
                    positions = self.get_open_positions()
                    for pos in positions:
                        self.close_order(pos.ticket)

                elif choice == "6":
                    self.display_statistics()

                elif choice == "7":
                    self.monitor_take_profit_detection()

                elif choice == "8":
                    self.monitor_stop_loss_detection()

                elif choice == "9":
                    self.setup_email_notifications()

                elif choice == "10":
                    print("\n🤖 Starting Auto Trade Demo (5 trades) with 1:2 Ratio...")
                    for i in range(5):
                        symbol = "EURUSD"
                        lot_size = self.calculate_lot_size_with_1percent_sl(symbol, account_info)
                        if i % 2 == 0:
                            self.place_buy_order_with_1to2(symbol, lot_size)
                        else:
                            self.place_sell_order_with_1to2(symbol, lot_size)
                        time.sleep(3)
                    print("✅ Auto Trade Demo Complete\n")

                elif choice == "11":
                    print("\n👋 Shutting down robot...")
                    break

                else:
                    print("❌ Invalid choice")

        finally:
            self.disconnect()


if __name__ == "__main__":
    # Initialize advanced robot with 1% risk per trade
    robot = MatrixAITraderRobot(risk_percentage=1.0, max_trades=5)
    robot.run_advanced_demo()
