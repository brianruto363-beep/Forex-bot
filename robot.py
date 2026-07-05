import MetaTrader5 as mt5
from datetime import datetime
import time

class MatrixAITraderRobot:
    """
    Automated Forex Trading Robot using MetaTrader 5
    Executes trades based on predefined strategies
    """

    def __init__(self, risk_percentage=1.0, max_trades=5):
        self.connected = False
        self.risk_percentage = risk_percentage
        self.max_trades = max_trades
        self.active_trades = 0
        self.total_trades = 0
        self.wins = 0
        self.losses = 0

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

    def calculate_lot_size(self, stop_loss_pips, account_info):
        """Calculate lot size based on risk management"""
        if not account_info:
            return 0.01
        
        risk_amount = account_info.balance * (self.risk_percentage / 100)
        point_value = 10  # For most pairs
        lot_size = risk_amount / (stop_loss_pips * point_value)
        
        # Ensure lot size is within reasonable limits
        lot_size = max(0.01, min(lot_size, 1.0))
        return round(lot_size, 2)

    def place_buy_order(self, symbol, lot_size, stop_loss_pips=50, take_profit_pips=100):
        """Place a BUY market order"""
        if not self.connected:
            print("❌ Not connected to MT5")
            return False

        price_info = self.get_price(symbol)
        if not price_info:
            print(f"❌ Could not get price for {symbol}")
            return False

        # Calculate stop loss and take profit levels
        point = mt5.symbol_info(symbol).point
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
            "comment": "Matrix AI Robot BUY",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Buy order failed for {symbol}: {result.comment}")
            return False

        self.active_trades += 1
        self.total_trades += 1
        print(f"✅ BUY Order Placed - {symbol} | Volume: {lot_size} | Entry: {price_info['ask']:.5f}")
        print(f"   SL: {stop_loss:.5f} | TP: {take_profit:.5f}")
        return True

    def place_sell_order(self, symbol, lot_size, stop_loss_pips=50, take_profit_pips=100):
        """Place a SELL market order"""
        if not self.connected:
            print("❌ Not connected to MT5")
            return False

        price_info = self.get_price(symbol)
        if not price_info:
            print(f"❌ Could not get price for {symbol}")
            return False

        # Calculate stop loss and take profit levels
        point = mt5.symbol_info(symbol).point
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
            "comment": "Matrix AI Robot SELL",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Sell order failed for {symbol}: {result.comment}")
            return False

        self.active_trades += 1
        self.total_trades += 1
        print(f"✅ SELL Order Placed - {symbol} | Volume: {lot_size} | Entry: {price_info['bid']:.5f}")
        print(f"   SL: {stop_loss:.5f} | TP: {take_profit:.5f}")
        return True

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
        """Display all open positions"""
        positions = self.get_open_positions()
        
        if not positions:
            print("📭 No open positions")
            return

        print("\n====== OPEN POSITIONS ======")
        for pos in positions:
            direction = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
            print(f"Ticket: {pos.ticket} | {pos.symbol} | {direction}")
            print(f"  Volume: {pos.volume} | Entry: {pos.price_open:.5f}")
            print(f"  Current: {pos.price_current:.5f} | Profit: ${pos.profit:.2f}")
        print("============================\n")

    def display_statistics(self):
        """Display robot trading statistics"""
        win_rate = (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
        print("\n====== TRADING STATISTICS ======")
        print(f"Total Trades: {self.total_trades}")
        print(f"Active Trades: {self.active_trades}")
        print(f"Wins: {self.wins}")
        print(f"Losses: {self.losses}")
        print(f"Win Rate: {win_rate:.2f}%")
        print("================================\n")

    def run_demo(self):
        """Run demo trading robot"""
        if not self.connect():
            return

        try:
            account_info = self.get_account_info()
            
            symbols = ["XAUUSD", "EURUSD", "GBPUSD"]
            
            while True:
                print("\n" + "="*40)
                print(" MATRIX AI TRADER ROBOT")
                print("="*40)
                print("1. View Prices")
                print("2. Place BUY Order (EURUSD)")
                print("3. Place SELL Order (EURUSD)")
                print("4. View Open Positions")
                print("5. Close All Positions")
                print("6. View Statistics")
                print("7. Auto Trade (Demo)")
                print("8. Exit")
                print("="*40)
                
                choice = input("Select: ").strip()

                if choice == "1":
                    print("\n====== CURRENT PRICES ======")
                    for symbol in symbols:
                        price_info = self.get_price(symbol)
                        if price_info:
                            print(f"{symbol}: Bid {price_info['bid']:.5f} | Ask {price_info['ask']:.5f}")
                    print("============================\n")

                elif choice == "2":
                    lot_size = self.calculate_lot_size(50, account_info)
                    self.place_buy_order("EURUSD", lot_size)

                elif choice == "3":
                    lot_size = self.calculate_lot_size(50, account_info)
                    self.place_sell_order("EURUSD", lot_size)

                elif choice == "4":
                    self.display_positions()

                elif choice == "5":
                    positions = self.get_open_positions()
                    for pos in positions:
                        self.close_order(pos.ticket)

                elif choice == "6":
                    self.display_statistics()

                elif choice == "7":
                    print("\n🤖 Starting Auto Trade Demo (5 trades)...")
                    for i in range(5):
                        symbol = "EURUSD"
                        lot_size = self.calculate_lot_size(50, account_info)
                        if i % 2 == 0:
                            self.place_buy_order(symbol, lot_size)
                        else:
                            self.place_sell_order(symbol, lot_size)
                        time.sleep(2)
                    print("✅ Auto Trade Demo Complete\n")

                elif choice == "8":
                    print("\n👋 Shutting down robot...")
                    break

                else:
                    print("❌ Invalid choice")

        finally:
            self.disconnect()


if __name__ == "__main__":
    # Initialize robot with 1% risk per trade, max 5 concurrent trades
    robot = MatrixAITraderRobot(risk_percentage=1.0, max_trades=5)
    robot.run_demo()
