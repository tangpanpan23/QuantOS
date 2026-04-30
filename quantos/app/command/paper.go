package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"quantos/app/model/market/papertrading"
	"quantos/common"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	dbHost     string
	dbPort     int
	dbUser     string
	dbPassword string
	dbDatabase string
	commonSvc  *common.Common
)

// ========== 根命令 ==========

var paperCmd = &cobra.Command{
	Use:   "paper",
	Short: "模拟盘交易系统",
	Long:  "QuantOS 模拟盘交易 - 支持买入/卖出/状态查询/历史回测/真实数据/自主进化",
}

// ========== 初始化数据库连接 ==========

func initDB() *common.Common {
	if commonSvc != nil {
		return commonSvc
	}

	// 尝试从配置文件读取
	if viper.GetString("DB_HOST") != "" {
		dbHost = viper.GetString("DB_HOST")
		dbPort = viper.GetInt("DB_PORT")
		dbUser = viper.GetString("DB_USER")
		dbPassword = viper.GetString("DB_PASSWORD")
		dbDatabase = viper.GetString("DB_DATABASE")
	}

	// 如果命令行参数优先级更高
	if envDBHost := os.Getenv("DB_HOST"); envDBHost != "" {
		dbHost = envDBHost
	}
	if envDBPort := os.Getenv("DB_PORT"); envDBPort != "" {
		if p, err := strconv.Atoi(envDBPort); err == nil {
			dbPort = p
		}
	}
	if envDBUser := os.Getenv("DB_USER"); envDBUser != "" {
		dbUser = envDBUser
	}
	if envDBPassword := os.Getenv("DB_PASSWORD"); envDBPassword != "" {
		dbPassword = envDBPassword
	}
	if envDBDatabase := os.Getenv("DB_DATABASE"); envDBDatabase != "" {
		dbDatabase = envDBDatabase
	}

	// 使用默认值（本地MySQL）
	if dbHost == "" {
		dbHost = "localhost"
	}
	if dbPort == 0 {
		dbPort = 3306
	}
	if dbUser == "" {
		dbUser = "root"
	}
	if dbDatabase == "" {
		dbDatabase = "quantos"
	}

	commonSvc = common.NewCommon(dbHost, dbPort, dbUser, dbPassword, dbDatabase, 10, 100, 300)
	return commonSvc
}

// ========== 状态命令 ==========

var paperStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "查看账户状态（使用数据库）",
	Run: func(cmd *cobra.Command, args []string) {
		ctx := context.Background()
		c := initDB()
		paperDB := papertrading.NewPaperTradingDB(c)

		account, err := paperDB.GetOrCreateAccount(ctx, 1)
		if err != nil {
			fmt.Printf("❌ 获取账户失败: %v\n", err)
			return
		}

		positions, err := paperDB.GetPositionsByAccountID(ctx, account.ID)
		if err != nil {
			fmt.Printf("❌ 获取持仓失败: %v\n", err)
			return
		}

		// 获取实时行情
		marketClient := papertrading.NewMarketClient()
		pnls, err := marketClient.GetPositionPnls(ctx, positions)
		if err != nil {
			fmt.Printf("⚠️ 获取行情失败: %v\n", err)
		}

		// 计算总市值
		var positionsValue float64
		for _, p := range pnls {
			positionsValue += p.MarketValue
		}
		totalValue := account.CurrentCapital + positionsValue
		totalPnl := totalValue - account.InitialCapital

		arrow := "↑"
		if totalPnl < 0 {
			arrow = "↓"
		}
		returnRate := 0.0
		if account.InitialCapital > 0 {
			returnRate = totalPnl / account.InitialCapital * 100
		}

		fmt.Printf(`
╔══════════════════════════════════════════════════════════════╗
║  📊 模拟账户状态 (数据库)                               ║
╠══════════════════════════════════════════════════════════════╣
║  现金: ¥%.0f | 总资产: ¥%.0f (%s%.1f%%)                  ║
║  持仓: %d只 | 持仓市值: ¥%.0f                               ║
║  总盈亏: ¥%.0f                                           ║
╠══════════════════════════════════════════════════════════════╣
║  📋 持仓 %d只                                              ║`,
			account.CurrentCapital, totalValue, arrow, returnRate,
			len(positions), positionsValue, totalPnl, len(positions))

		if len(pnls) == 0 {
			fmt.Println("║  (空仓)                                                   ║")
		} else {
			for _, p := range pnls {
				pnlArrow := ""
				if p.Pnl > 0 {
					pnlArrow = "+"
				}
				fmt.Printf("\n║  • %s %s: %d股@¥%.2f → ¥%.2f %s¥%.0f(%.1f%%)    ║",
					p.Symbol, p.SymbolName, p.Shares, p.AvgCost, p.CurrentPrice,
					pnlArrow, p.Pnl, p.PnlPct)
			}
		}
		fmt.Println("\n╚══════════════════════════════════════════════════════════════╝")
	},
}

// ========== 每日数据更新命令 ==========

var paperDailyCmd = &cobra.Command{
	Use:   "daily",
	Short: "获取每日市场数据 + 更新持仓状态",
	Run: func(cmd *cobra.Command, args []string) {
		ctx := context.Background()
		c := initDB()
		paperDB := papertrading.NewPaperTradingDB(c)
		marketClient := papertrading.NewMarketClient()

		account, err := paperDB.GetOrCreateAccount(ctx, 1)
		if err != nil {
			fmt.Printf("❌ 获取账户失败: %v\n", err)
			return
		}

		positions, err := paperDB.GetPositionsByAccountID(ctx, account.ID)
		if err != nil {
			fmt.Printf("❌ 获取持仓失败: %v\n", err)
			return
		}

		if len(positions) == 0 {
			fmt.Println("📊 当前无持仓，跳过持仓检查")
		} else {
			fmt.Printf("📊 检查 %d 只持仓的行情...\n", len(positions))

			pnls, err := marketClient.GetPositionPnls(ctx, positions)
			if err != nil {
				fmt.Printf("❌ 获取行情失败: %v\n", err)
				return
			}

			// 打印持仓状态
			papertrading.PrintPnls(pnls)

			// 检查止损止盈
			var actions []string
			for _, p := range pnls {
				switch p.Action {
				case "STOP_LOSS":
					actions = append(actions, fmt.Sprintf("⚠️ %s 触发止损", p.Symbol))
				case "TAKE_PROFIT1":
					actions = append(actions, fmt.Sprintf("💰 %s 触发止盈1", p.Symbol))
				case "TAKE_PROFIT2":
					actions = append(actions, fmt.Sprintf("💰 %s 触发止盈2", p.Symbol))
				}
			}

			if len(actions) > 0 {
				fmt.Println("\n🚨 建议操作:")
				for _, a := range actions {
					fmt.Printf("  %s\n", a)
				}
			}
		}

		// 记录每日统计
		today := time.Now().Format("2006-01-02")
		var positionsValue float64
		for _, p := range positions {
			positionsValue += p.AvgCost * float64(p.Shares)
		}
		totalValue := account.CurrentCapital + positionsValue
		totalPnl := totalValue - account.InitialCapital

		// 获取今日交易数
		todayTrades, _ := paperDB.GetTodayTrades(ctx, account.ID)

		stats := &papertrading.DailyStats{
			StatDate:       today,
			InitialCapital: papertrading.InitialCapital,
			TotalValue:     totalValue,
			PositionsValue: positionsValue,
			Cash:           account.CurrentCapital,
			DailyPnl:       totalPnl,
			TotalPnl:       totalPnl,
			Positions:      len(positions),
			Trades:         len(todayTrades),
		}

		if err := paperDB.UpsertDailyStats(ctx, stats); err != nil {
			fmt.Printf("⚠️ 记录每日统计失败: %v\n", err)
		} else {
			fmt.Printf("\n✅ 每日统计已记录: %s\n", today)
		}
	},
}

// ========== 信号命令 ==========

var paperSignalCmd = &cobra.Command{
	Use:   "signal [股票代码]",
	Short: "生成选股信号（基于真实数据）",
	Example: `  paper signal           # 扫描默认股票池
  paper signal 600036    # 分析单只股票
  paper signal --list    # 显示可用股票池`,
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx := context.Background()
		marketClient := papertrading.NewMarketClient()

		// 默认股票池
		stocks := []struct {
			code string
			name string
		}{
			{"600036", "招商银行"}, {"600900", "长江电力"}, {"601288", "农业银行"},
			{"000858", "五粮液"}, {"300750", "宁德时代"}, {"601318", "中国平安"},
			{"002475", "立讯精密"}, {"600519", "贵州茅台"},
		}

		// 单只股票分析
		if len(args) > 0 {
			symbol := args[0]
			quote, err := marketClient.GetRealtimeQuote(ctx, symbol)
			if err != nil {
				return fmt.Errorf("获取行情失败: %w", err)
			}

			fmt.Printf("\n📊 %s %s 实时行情\n", symbol, quote.Name)
			papertrading.PrintQuote(quote)

			// 获取K线
			klines, err := marketClient.GetKLineData(ctx, symbol, "daily", "qfq", 60)
			if err != nil {
				fmt.Printf("⚠️ 获取K线失败: %v\n", err)
			} else {
				// 计算MA
				ma5 := marketClient.CalculateMA(klines, 5)
				ma20 := marketClient.CalculateMA(klines, 20)
				ma60 := marketClient.CalculateMA(klines, 60)
				rsi := marketClient.CalculateRSI(klines, 14)

				fmt.Printf("\n📈 技术指标:\n")
				fmt.Printf("   MA5=¥%.2f | MA20=¥%.2f | MA60=¥%.2f\n", ma5, ma20, ma60)
				fmt.Printf("   RSI(14)=%.2f\n", rsi)

				// 生成信号
				signal := papertrading.GenerateSignal(symbol, quote.Name, quote.Price,
					quote.Amount/100000000, rsi, ma5, ma20, ma60)

				if signal != nil && signal.Score >= 80 {
					fmt.Printf("\n🟢 买入信号! 评分: %.0f\n", signal.Score)
					fmt.Printf("   理由: %s\n", signal.Reason)
				} else if signal != nil {
					fmt.Printf("\n⚪ 观察信号 评分: %.0f\n", signal.Score)
					fmt.Printf("   理由: %s\n", signal.Reason)
				} else {
					fmt.Printf("\n🔴 暂不推荐买入\n")
				}
			}

			return nil
		}

		// 批量扫描
		fmt.Println("\n📊 选股信号扫描")
		fmt.Println("────────────────────────────────────────────────────────────")

		var signals []papertrading.StockSignal
		for _, s := range stocks {
			quote, err := marketClient.GetRealtimeQuote(ctx, s.code)
			if err != nil {
				continue
			}

			klines, _ := marketClient.GetKLineData(ctx, s.code, "daily", "qfq", 60)
			rsi := papertrading.CalcRSIFromKLines(klines, 14)
			ma5 := marketClient.CalculateMA(klines, 5)
			ma20 := marketClient.CalculateMA(klines, 20)
			ma60 := marketClient.CalculateMA(klines, 60)

			signal := papertrading.GenerateSignal(s.code, s.name, quote.Price,
				quote.Amount/100000000, rsi, ma5, ma20, ma60)

			if signal != nil {
				signals = append(signals, *signal)
			}
		}

		// 按评分排序
		validSignals := papertrading.FilterSignals(signals, 5)

		if len(validSignals) > 0 {
			fmt.Println("🟢 买入信号:")
			for _, s := range validSignals {
				fmt.Printf("   %s %s ¥%.2f RSI=%.0f 评分=%.0f\n", s.Code, s.Name, s.Price, s.RSI, s.Score)
				fmt.Printf("      %s\n", s.Reason)
			}
		} else {
			fmt.Println("⚪ 暂无符合条件的买入信号")
		}

		fmt.Println("────────────────────────────────────────────────────────────")
		return nil
	},
}

// ========== 进化命令 ==========

var paperEvolveCmd = &cobra.Command{
	Use:   "evolve",
	Short: "运行自主进化分析",
	Example: `  paper evolve              # 分析并应用优化
  paper evolve --analyze     # 仅分析不应用
  paper evolve --suggest     # 显示优化建议`,
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx := context.Background()
		c := initDB()
		paperDB := papertrading.NewPaperTradingDB(c)
		evolution := papertrading.NewEvolutionSystem(paperDB)

		account, err := paperDB.GetOrCreateAccount(ctx, 1)
		if err != nil {
			return fmt.Errorf("获取账户失败: %w", err)
		}

		analyzeOnly, _ := cmd.Flags().GetBool("analyze")
		suggestOnly, _ := cmd.Flags().GetBool("suggest")

		if suggestOnly {
			// 只显示建议
			suggestions, err := evolution.GetSuggestions(ctx, account.ID)
			if err != nil {
				return fmt.Errorf("生成建议失败: %w", err)
			}
			papertrading.PrintSuggestions(suggestions)
			return nil
		}

		if analyzeOnly {
			// 只分析不更新
			report, err := evolution.AnalyzePerformance(ctx, account.ID)
			if err != nil {
				return fmt.Errorf("分析失败: %w", err)
			}
			papertrading.PrintPerformanceReport(report)
			return nil
		}

		// 完整进化
		fmt.Println("🧬 启动自主进化系统...")
		result, err := evolution.SelfUpdate(ctx, account.ID)
		if err != nil {
			return fmt.Errorf("进化失败: %w", err)
		}

		papertrading.PrintEvolutionResult(result)
		return nil
	},
}

// ========== 报告命令 ==========

var paperReportCmd = &cobra.Command{
	Use:   "report",
	Short: "生成每日/定期报告",
	Example: `  paper report today        # 今日报告
  paper report weekly       # 本周报告
  paper report monthly      # 本月报告`,
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx := context.Background()
		c := initDB()
		paperDB := papertrading.NewPaperTradingDB(c)
		marketClient := papertrading.NewMarketClient()

		account, err := paperDB.GetOrCreateAccount(ctx, 1)
		if err != nil {
			return fmt.Errorf("获取账户失败: %w", err)
		}

		period := "today"
		if len(args) > 0 {
			period = args[0]
		}

		var startDate, endDate string
		now := time.Now()

		switch period {
		case "today":
			startDate = now.Format("2006-01-02")
			endDate = startDate
		case "weekly":
			startDate = now.AddDate(0, 0, -7).Format("2006-01-02")
			endDate = now.Format("2006-01-02")
		case "monthly":
			startDate = now.AddDate(0, -1, 0).Format("2006-01-02")
			endDate = now.Format("2006-01-02")
		default:
			startDate = now.Format("2006-01-02")
			endDate = startDate
		}

		fmt.Printf("\n📊 %s 账户报告 (%s ~ %s)\n", period, startDate, endDate)
		fmt.Println("────────────────────────────────────────────────────────────")

		// 获取统计数据
		stats, err := paperDB.GetDailyStatsRange(ctx, startDate, endDate)
		if err != nil {
			fmt.Printf("⚠️ 获取统计失败: %v\n", err)
		}

		if len(stats) > 0 {
			var totalPnL float64
			var totalTrades int
			for _, s := range stats {
				totalPnL += s.DailyPnl
				totalTrades += s.Trades
			}
			fmt.Printf("累计盈亏: ¥%.2f | 交易次数: %d笔\n", totalPnL, totalTrades)
		}

		// 获取当前持仓
		positions, _ := paperDB.GetPositionsByAccountID(ctx, account.ID)
		if len(positions) > 0 {
			pnls, _ := marketClient.GetPositionPnls(ctx, positions)
			papertrading.PrintPnls(pnls)
		} else {
			fmt.Println("当前无持仓")
		}

		// 获取交易记录
		trades, _ := paperDB.GetTradesByAccountID(ctx, account.ID, 10)
		if len(trades) > 0 {
			fmt.Println("\n📋 最近交易:")
			for _, t := range trades {
				if t.Action == "BUY" {
					fmt.Printf("  🟢 %s 买入 %s ¥%.2f×%d\n", t.TradeDate, t.Symbol, t.Price, t.Shares)
				} else {
					arrow := "+"
					if t.Pnl < 0 {
						arrow = ""
					}
					fmt.Printf("  🔴 %s 卖出 %s ¥%.2f %s¥%.2f(%.1f%%) 持%d天\n",
						t.TradeDate, t.Symbol, t.Price, arrow, t.Pnl, t.PnlPct, t.HoldDays)
				}
			}
		}

		fmt.Println("────────────────────────────────────────────────────────────")
		return nil
	},
}

// ========== 买入命令 ==========

var paperBuyCmd = &cobra.Command{
	Use:   "buy",
	Short: "买入股票",
	Example: `  paper buy 600036 35.50 300 "MA多头+RSI=45"
  paper buy 600036 35.50 300 "MA多头" -n "招商银行" -r 45`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) < 4 {
			return fmt.Errorf("用法: paper buy <代码> <价格> <股数> <理由>")
		}

		code := args[0]
		price, err := strconv.ParseFloat(args[1], 64)
		if err != nil {
			return fmt.Errorf("价格格式错误: %s", args[1])
		}

		shares, err := strconv.Atoi(args[2])
		if err != nil {
			return fmt.Errorf("股数格式错误: %s", args[2])
		}

		reason := args[3]
		name, _ := cmd.Flags().GetString("name")
		if name == "" {
			name = code
		}
		rsi, _ := cmd.Flags().GetFloat64("rsi")

		ctx := context.Background()
		c := initDB()
		paperDB := papertrading.NewPaperTradingDB(c)

		account, err := paperDB.GetOrCreateAccount(ctx, 1)
		if err != nil {
			return fmt.Errorf("获取账户失败: %w", err)
		}

		// 检查持仓数量
		count, _ := paperDB.GetPositionCount(ctx, account.ID)
		if count >= papertrading.MaxPositions {
			return fmt.Errorf("⚠️ 持仓已满 (%d只)", papertrading.MaxPositions)
		}

		// 检查是否已有持仓
		existing, _ := paperDB.GetPositionBySymbol(ctx, account.ID, code)
		if existing != nil {
			return fmt.Errorf("⚠️ %s 已在持仓中", code)
		}

		// 计算最大可买股数
		amount := price * float64(shares)
		maxAmount := account.CurrentCapital - papertrading.CashReserve
		if amount > maxAmount {
			shares = int(maxAmount/price/100) * 100
			amount = price * float64(shares)
		}

		if shares < 100 {
			return fmt.Errorf("⚠️ 资金不足，可用 ¥%.0f", account.CurrentCapital-papertrading.CashReserve)
		}

		// 创建持仓
		today := time.Now().Format("2006-01-02")
		position := &papertrading.PaperPosition{
			AccountID:   account.ID,
			Symbol:      code,
			SymbolName:  name,
			Shares:      shares,
			AvgCost:     price,
			StopLoss:    round(price*(1-papertrading.StopLoss), 2),
			TakeProfit1: round(price*(1+papertrading.TakeProfit1), 2),
			TakeProfit2: round(price*(1+papertrading.TakeProfit2), 2),
			EntryDate:   today,
			Reason:      reason,
			RSI:         rsi,
			StopMoved:   false,
		}

		if err := paperDB.CreatePosition(ctx, position); err != nil {
			return fmt.Errorf("创建持仓失败: %w", err)
		}

		// 记录交易
		trade := &papertrading.PaperTrade{
			AccountID:  account.ID,
			TradeDate:  today,
			Action:     "BUY",
			Symbol:     code,
			SymbolName: name,
			Price:      price,
			Shares:     shares,
			Amount:     amount,
			Reason:     reason,
			CashAfter:  account.CurrentCapital - amount,
		}

		if err := paperDB.CreateTrade(ctx, trade); err != nil {
			fmt.Printf("⚠️ 记录交易失败: %v\n", err)
		}

		// 更新账户
		account.CurrentCapital -= amount
		paperDB.UpdateAccount(ctx, account)

		fmt.Printf("✅ 买入 %s %s ¥%.2f×%d股=¥%.0f\n", code, name, price, shares, amount)
		fmt.Printf("   止损 ¥%.2f | 止盈1 ¥%.2f | 止盈2 ¥%.2f\n", position.StopLoss, position.TakeProfit1, position.TakeProfit2)

		return nil
	},
}

// ========== 卖出命令 ==========

var paperSellCmd = &cobra.Command{
	Use:   "sell",
	Short: "卖出股票",
	Example: `  paper sell 600036 38.50 "止盈"`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) < 2 {
			return fmt.Errorf("用法: paper sell <代码> <价格> [理由]")
		}

		code := args[0]
		price, err := strconv.ParseFloat(args[1], 64)
		if err != nil {
			return fmt.Errorf("价格格式错误: %s", args[1])
		}

		reason := "手动卖出"
		if len(args) > 2 {
			reason = args[2]
		}

		ctx := context.Background()
		c := initDB()
		paperDB := papertrading.NewPaperTradingDB(c)

		account, err := paperDB.GetOrCreateAccount(ctx, 1)
		if err != nil {
			return fmt.Errorf("获取账户失败: %w", err)
		}

		// 获取持仓
		position, err := paperDB.GetPositionBySymbol(ctx, account.ID, code)
		if err != nil {
			return fmt.Errorf("查询持仓失败: %w", err)
		}
		if position == nil {
			return fmt.Errorf("⚠️ %s 不在持仓中", code)
		}

		shares := position.Shares
		avgCost := position.AvgCost
		amount := price * float64(shares)
		pnl := amount - (avgCost * float64(shares))
		pnlPct := (price - avgCost) / avgCost * 100

		// 计算持有天数
		entryDate, _ := time.Parse("2006-01-02", position.EntryDate)
		sellDate := time.Now()
		holdDays := int(sellDate.Sub(entryDate).Hours() / 24)

		// 记录交易
		today := sellDate.Format("2006-01-02")
		trade := &papertrading.PaperTrade{
			AccountID:  account.ID,
			TradeDate:  today,
			Action:     "SELL",
			Symbol:     code,
			SymbolName: position.SymbolName,
			Price:      price,
			Shares:     shares,
			Amount:     amount,
			AvgCost:    avgCost,
			Pnl:        round(pnl, 2),
			PnlPct:     round(pnlPct, 2),
			Reason:     reason,
			HoldDays:   holdDays,
			CashAfter:  account.CurrentCapital + amount,
		}

		if err := paperDB.CreateTrade(ctx, trade); err != nil {
			fmt.Printf("⚠️ 记录交易失败: %v\n", err)
		}

		// 删除持仓
		if err := paperDB.DeletePositionBySymbol(ctx, account.ID, code); err != nil {
			fmt.Printf("⚠️ 删除持仓失败: %v\n", err)
		}

		// 更新账户
		account.CurrentCapital += amount
		paperDB.UpdateAccount(ctx, account)

		emoji := "🟢"
		if pnl < 0 {
			emoji = "🔴"
		}
		fmt.Printf("%s 卖出 %s %s ¥%.2f %s¥%.0f(%.1f%%) 持%d天 [%s]\n",
			emoji, code, position.SymbolName, price, emoji, pnl, pnlPct, holdDays, reason)

		return nil
	},
}

// ========== 交易记录命令 ==========

var paperTradesCmd = &cobra.Command{
	Use:   "trades",
	Short: "查看交易记录",
	Run: func(cmd *cobra.Command, args []string) {
		ctx := context.Background()
		c := initDB()
		paperDB := papertrading.NewPaperTradingDB(c)

		account, err := paperDB.GetOrCreateAccount(ctx, 1)
		if err != nil {
			fmt.Printf("❌ 获取账户失败: %v\n", err)
			return
		}

		limit, _ := cmd.Flags().GetInt("limit")
		trades, err := paperDB.GetTradesByAccountID(ctx, account.ID, limit)
		if err != nil {
			fmt.Printf("❌ 获取交易记录失败: %v\n", err)
			return
		}

		fmt.Println("\n📋 交易记录：")
		fmt.Println("────────────────────────────────────────────────────────────")

		for _, t := range trades {
			if t.Action == "BUY" {
				fmt.Printf("🟢 %s 买入 %s %s ¥%.2f×%d\n", t.TradeDate, t.Symbol, t.SymbolName, t.Price, t.Shares)
			} else {
				emoji := "🟢"
				if t.Pnl < 0 {
					emoji = "🔴"
				}
				fmt.Printf("%s %s 卖出 %s ¥%.2f %s¥%.0f(%.1f%%) 持%d天\n",
					emoji, t.TradeDate, t.Symbol, t.Price, emoji, t.Pnl, t.PnlPct, t.HoldDays)
			}
		}
		fmt.Println("────────────────────────────────────────────────────────────")
		fmt.Printf("共 %d 笔交易\n", len(trades))
	},
}

// ========== 回测命令 ==========

var paperSimulateCmd = &cobra.Command{
	Use:   "simulate",
	Short: "运行历史回测模拟",
	Run: func(cmd *cobra.Command, args []string) {
		papertrading.RunSimulation()
	},
}

// ========== 重置命令 ==========

var paperResetCmd = &cobra.Command{
	Use:   "reset",
	Short: "重置账户",
	Run: func(cmd *cobra.Command, args []string) {
		ctx := context.Background()
		c := initDB()
		paperDB := papertrading.NewPaperTradingDB(c)

		account, err := paperDB.GetOrCreateAccount(ctx, 1)
		if err != nil {
			fmt.Printf("❌ 获取账户失败: %v\n", err)
			return
		}

		// 删除所有持仓
		positions, _ := paperDB.GetPositionsByAccountID(ctx, account.ID)
		for _, p := range positions {
			paperDB.DeletePosition(ctx, p.ID)
		}

		// 重置账户
		account.CurrentCapital = papertrading.InitialCapital - papertrading.CashReserve
		account.TotalValue = papertrading.InitialCapital
		account.TotalPnl = 0
		paperDB.UpdateAccount(ctx, account)

		fmt.Println("✅ 账户已重置")
	},
}

// ========== init ==========

func init() {
	// 注册命令
	rootCmd.AddCommand(paperCmd)
	paperCmd.AddCommand(paperBuyCmd)
	paperCmd.AddCommand(paperSellCmd)
	paperCmd.AddCommand(paperStatusCmd)
	paperCmd.AddCommand(paperTradesCmd)
	paperCmd.AddCommand(paperDailyCmd)
	paperCmd.AddCommand(paperSignalCmd)
	paperCmd.AddCommand(paperEvolveCmd)
	paperCmd.AddCommand(paperReportCmd)
	paperCmd.AddCommand(paperSimulateCmd)
	paperCmd.AddCommand(paperResetCmd)

	// buy 命令参数
	paperBuyCmd.Flags().StringP("name", "n", "", "股票名称")
	paperBuyCmd.Flags().Float64P("rsi", "r", 50, "RSI值")

	// trades 命令参数
	paperTradesCmd.Flags().IntP("limit", "l", 20, "显示最近N条记录")

	// evolve 命令参数
	paperEvolveCmd.Flags().Bool("analyze", false, "仅分析不应用")
	paperEvolveCmd.Flags().Bool("suggest", false, "显示优化建议")
}

// ========== 辅助函数 ==========

func getProjectRoot() string {
	// 优先使用环境变量
	if root := os.Getenv("PROJECT_ROOT"); root != "" {
		return root
	}

	// 向上查找 go.mod 所在目录
	execDir, _ := os.Getwd()
	for {
		if _, err := os.Stat(filepath.Join(execDir, "go.mod")); err == nil {
			return execDir
		}
		parent := filepath.Dir(execDir)
		if parent == execDir {
			// 找不到就返回默认
			return "/Users/tank/Code/QuantOS/quantos"
		}
		execDir = parent
	}
}

func round(val float64, precision int) float64 {
	round := 1.0
	for i := 0; i < precision; i++ {
		round *= 10
	}
	return float64(int(val*round+0.5)) / round
}

// CalcRSIFromKLines 辅助函数
func CalcRSIFromKLines(klines []papertrading.KLineData, period int) float64 {
	if len(klines) < period+1 {
		return 50.0
	}

	var gains, losses float64
	for i := len(klines) - period; i < len(klines); i++ {
		change := klines[i].Close - klines[i-1].Close
		if change > 0 {
			gains += change
		} else {
			losses -= change
		}
	}

	avgGain := gains / float64(period)
	avgLoss := losses / float64(period)

	if avgLoss == 0 {
		return 100.0
	}

	rs := avgGain / avgLoss
	rsi := 100 - (100 / (1 + rs))
	return rsi
}
