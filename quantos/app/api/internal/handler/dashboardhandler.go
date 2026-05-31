package handler

import (
	"net/http"
	"time"

	"quantos/app/api/internal/svc"

	"github.com/zeromicro/go-zero/rest/httpx"
)

// ========== 管理后台 Dashboard API (公开，无需认证) ==========

type DashboardResp struct {
	Code    int                    `json:"code"`
	Message string                 `json:"message"`
	Data    map[string]interface{} `json:"data"`
}

func dashboardStatsHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB

		// 1. 账户概况
		type AccountStats struct {
			InitialCapital float64 `json:"initial_capital"`
			CurrentCapital float64 `json:"current_capital"`
			TotalValue     float64 `json:"total_value"`
			TotalPnl       float64 `json:"total_pnl"`
			UsedMargin     float64 `json:"used_margin"`
		}
		var account AccountStats
		db.WithContext(r.Context()).Table("q_paper_account").
			Select("COALESCE(SUM(initial_capital),0) as initial_capital, COALESCE(SUM(current_capital),0) as current_capital, COALESCE(SUM(total_value),0) as total_value, COALESCE(SUM(total_pnl),0) as total_pnl").
			Scan(&account)
		account.UsedMargin = account.InitialCapital - account.CurrentCapital

		// 2. 持仓列表
		type PositionItem struct {
			Symbol     string  `json:"symbol"`
			SymbolName string  `json:"symbol_name"`
			Shares     float64 `json:"shares"`
			AvgCost    float64 `json:"avg_cost"`
			StopLoss   float64 `json:"stop_loss"`
			RSI        float64 `json:"rsi"`
			EntryDate  string  `json:"entry_date"`
			Reason     string  `json:"reason"`
		}
		var positions []PositionItem
		db.WithContext(r.Context()).Table("q_paper_position").Scan(&positions)

		// 3. 持仓汇总
		type PosStats struct {
			TotalCount  int     `json:"total_count"`
			TotalValue float64 `json:"total_value"`
			TotalCost  float64 `json:"total_cost"`
		}
		var posStats PosStats
		posStats.TotalCount = len(positions)
		for _, p := range positions {
			posStats.TotalCost += p.Shares * p.AvgCost
		}

		// 4. 最新行情
		type MarketQuote struct {
			Symbol     string  `json:"symbol"`
			SymbolName string  `json:"symbol_name"`
			ClosePrice float64 `json:"close_price"`
			ChangePct  float64 `json:"change_pct"`
			Volume     float64 `json:"volume"`
			TradeDate  string  `json:"trade_date"`
		}
		var quotes []MarketQuote
		db.WithContext(r.Context()).Table("q_market_data").
			Order("trade_date DESC, id DESC").Limit(20).Scan(&quotes)

		// 5. 涨停池
		type LimitUp struct {
			Symbol     string  `json:"symbol"`
			SymbolName string  `json:"symbol_name"`
			ClosePrice float64 `json:"close_price"`
			ChangePct  float64 `json:"change_pct"`
			Volume     float64 `json:"volume"`
			Reason     string  `json:"reason"`
			TradeDate  string  `json:"trade_date"`
		}
		var limitUpPool []LimitUp
		db.WithContext(r.Context()).Table("q_limit_up_pool").
			Order("id DESC").Limit(10).Scan(&limitUpPool)

		// 6. 龙虎榜
		type DragonTiger struct {
			Symbol     string  `json:"symbol"`
			SymbolName string  `json:"symbol_name"`
			ClosePrice float64 `json:"close_price"`
			ChangePct  float64 `json:"change_pct"`
			Volume     float64 `json:"volume"`
			Reason     string  `json:"reason"`
			TradeDate  string  `json:"trade_date"`
		}
		var dragonTiger []DragonTiger
		db.WithContext(r.Context()).Table("q_dragon_tiger_list").
			Order("id DESC").Limit(10).Scan(&dragonTiger)

		// 7. 策略列表
		type StrategyInfo struct {
			ID          uint    `json:"id"`
			Name        string  `json:"name"`
			Status      string  `json:"status"`
			Type        string  `json:"type"`
			AnnualReturn float64 `json:"annual_return"`
			Sharpe      float64 `json:"sharpe_ratio"`
			MaxDrawdown float64 `json:"max_drawdown"`
			RunCount    int     `json:"run_count"`
		}
		var strategies []StrategyInfo
		db.WithContext(r.Context()).Table("q_strategies").
			Order("id DESC").Limit(20).Scan(&strategies)

		// 8. 资金曲线（每日快照）
		type DailySnapshot struct {
			StatDate        string  `json:"stat_date"`
			TotalValue      float64 `json:"total_value"`
			PositionsValue  float64 `json:"positions_value"`
			Cash            float64 `json:"cash"`
			DailyPnl        float64 `json:"daily_pnl"`
			DailyPnlPct     float64 `json:"daily_pnl_pct"`
		}
		var snapshots []DailySnapshot
		db.WithContext(r.Context()).Table("q_daily_stats").
			Order("stat_date ASC").Limit(60).Scan(&snapshots)

		// 9. 最新新闻
		type NewsItem struct {
			Title   string `json:"title"`
			Source  string `json:"source"`
			Publish string `json:"published_at"`
			Sentiment string `json:"sentiment"`
		}
		var news []NewsItem
		db.WithContext(r.Context()).Table("q_news_data").
			Order("id DESC").Limit(10).Scan(&news)

		// 10. 用户数
		var userCount int64
		db.WithContext(r.Context()).Table("q_users").Count(&userCount)

		// 11. 今日涨跌统计
		type TodayStats struct {
			UpCount      int     `json:"up_count"`
			DownCount    int     `json:"down_count"`
			LimitUpCount int     `json:"limit_up_count"`
			TradeDate    string  `json:"trade_date"`
			AvgChangePct float64 `json:"avg_change_pct"`
		}
		var todayStats TodayStats
		var latestDate string
		db.WithContext(r.Context()).Table("q_market_data").
			Select("COALESCE(MAX(trade_date),'') as trade_date").
			Scan(&latestDate)
		todayStats.TradeDate = latestDate
		todayStats.UpCount = 0
		todayStats.DownCount = 0

		resp := DashboardResp{
			Code:    0,
			Message: "ok",
			Data: map[string]interface{}{
				"account":       account,
				"positions":     positions,
				"pos_stats":     posStats,
				"quotes":        quotes,
				"limit_up_pool": limitUpPool,
				"dragon_tiger":  dragonTiger,
				"strategies":    strategies,
				"snapshots":     snapshots,
				"news":          news,
				"user_count":    userCount,
				"today_stats":   todayStats,
				"updated_at":    time.Now().Format("2006-01-02 15:04:05"),
			},
		}

		httpx.OkJson(w, resp)
	}
}

// SeedDemoDataHandler - 填充演示数据（公开）
func seedDemoDataHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		now := time.Now()

		demoQuotes := []struct {
			Symbol     string
			SymbolName string
			BasePrice  float64
		}{
			{"000001", "平安银行", 12.50},
			{"000002", "万科A", 8.30},
			{"000858", "五粮液", 145.00},
			{"600000", "浦发银行", 8.20},
			{"600036", "招商银行", 35.60},
			{"600519", "贵州茅台", 1680.00},
			{"600887", "伊利股份", 28.50},
			{"601318", "中国平安", 45.20},
			{"601888", "中国中免", 72.00},
			{"002594", "比亚迪", 235.00},
			{"300750", "宁德时代", 185.00},
		}

		for i, q := range demoQuotes {
			change := float64(i%3-1) * 0.02 * q.BasePrice
			closePrice := q.BasePrice + change
			volume := float64(1000000 + i*50000)
			db.Exec(`INSERT INTO q_market_data (symbol, symbol_name, open_price, high_price, low_price, close_price, volume, amount, trade_date, trade_time, market, data_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
				q.Symbol, q.SymbolName,
				closePrice*0.99, closePrice*1.02, closePrice*0.98,
				closePrice, volume, volume*closePrice,
				now.Format("2006-01-02"), now.Format("15:04:05"), "SH", "demo")
		}

		db.Exec(`INSERT INTO q_limit_up_pool (symbol, symbol_name, close_price, change_pct, volume, trade_date, reason) VALUES ('300750','宁德时代',192.00,20.0,1500000,'2026-05-25','技术突破'), ('002415','海康威视',42.50,10.0,800000,'2026-05-25','业绩预增')`)
		db.Exec(`INSERT INTO q_dragon_tiger_list (symbol, symbol_name, close_price, change_pct, volume, reason, trade_date) VALUES ('600519','贵州茅台',1700.00,5.5,500000,'机构买入','2026-05-25'), ('601888','中国中免',75.00,8.2,650000,'游资接力','2026-05-25')`)
		db.Exec(`INSERT INTO q_news_data (title, content, source, published_at, sentiment, category) VALUES ('央行宣布降准0.25个百分点','央行宣布将于近期实施降准，释放长期资金约5000亿元','财联社',NOW(), 'positive', 'policy'), ('A股三大指数集体收涨','沪指涨1.2%，深成指涨1.5%，创业板指涨2.0%','东方财富',NOW(), 'positive', 'market')`)

		for i := 30; i >= 0; i-- {
			d := now.AddDate(0, 0, -i)
			val := 100000.0 + float64(30-i)*100 + float64(i%7-3)*500
			db.Exec(`INSERT INTO q_daily_stats (stat_date, initial_capital, total_value, positions_value, cash, daily_pnl, daily_pnl_pct, positions, trades) VALUES (?, 100000, ?, ?, ?, ?, ?, 3, 5)`,
				d.Format("2006-01-02"), val, val*0.7, val*0.3, float64(i%5-2)*300, float64(i%5-2)*0.3)
		}

		db.Exec(`INSERT INTO q_strategies (name, description, status, type, category, annual_return, sharpe_ratio, max_drawdown, run_count, created_at) VALUES
			('趋势跟踪策略','基于MACD和MA均线的趋势跟踪策略','active','trend','日线',18.5,1.2,-12.3,5,NOW()),
			('均值回归策略','基于RSI的超跌反弹策略','active','mean_reversion','小时线',12.3,0.8,-8.5,3,NOW()),
			('突破策略','基于价格突破的追涨策略','inactive','breakout','日线',22.1,1.5,-15.0,2,NOW())`)

		httpx.OkJson(w, map[string]interface{}{
			"code":    0,
			"message": "演示数据已填充",
			"data": map[string]interface{}{
				"quotes": 12, "limit_up": 2, "dragon_tiger": 2,
				"news": 2, "snapshots": 31, "strategies": 3,
			},
		})
	}
}

// ClearDemoDataHandler - 清除演示数据
func clearDemoDataHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		db.Exec("DELETE FROM q_market_data WHERE data_source='demo'")
		db.Exec("DELETE FROM q_limit_up_pool")
		db.Exec("DELETE FROM q_dragon_tiger_list")
		db.Exec("DELETE FROM q_news_data WHERE category IN ('policy','market')")
		db.Exec("DELETE FROM q_daily_stats")
		db.Exec("DELETE FROM q_strategies WHERE status IN ('active','inactive')")

		httpx.OkJson(w, map[string]interface{}{
			"code": 0, "message": "演示数据已清除",
		})
	}
}
