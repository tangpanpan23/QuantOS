package handler

import (
	"io"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"quantos/app/api/internal/svc"
	"quantos/app/api/internal/types"

	"github.com/zeromicro/go-zero/rest/httpx"
)

// GET /api/v1/portfolio/refresh - 热刷新行情（查持仓前调用，保证最新价）
func refreshQuotesHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB

		// 收集所有需要刷新价格的股票
		var symbols []string
		rows, _ := db.WithContext(r.Context()).Raw(`
			SELECT DISTINCT symbol FROM (
				SELECT symbol FROM q_positions WHERE portfolio_id=1 AND quantity>0
				UNION ALL SELECT symbol FROM q_paper_position WHERE account_id=1
				UNION ALL SELECT symbol FROM q_stock_pool WHERE is_watched=1
			) t
		`).Rows()
		if rows != nil {
			defer rows.Close()
			for rows.Next() {
				var s string
				if rows.Scan(&s) == nil && s != "" {
					symbols = append(symbols, s)
				}
			}
		}

		quotes := make(map[string]map[string]float64)

		if len(symbols) > 0 {
			batch := []string{}
			for _, sym := range symbols {
				if strings.HasPrefix(sym, "6") || strings.HasPrefix(sym, "9") {
					batch = append(batch, "sh"+sym)
				} else {
					batch = append(batch, "sz"+sym)
				}
			}

			for i := 0; i < len(batch); i += 50 {
				end := i + 50
				if end > len(batch) {
					end = len(batch)
				}
				url := "https://hq.sinajs.cn/list=" + strings.Join(batch[i:end], ",")
				req, _ := http.NewRequestWithContext(r.Context(), "GET", url, nil)
				req.Header.Set("Referer", "https://finance.sina.com.cn/")
				req.Header.Set("User-Agent", "Mozilla/5.0")

				client := &http.Client{Timeout: 5 * time.Second}
				resp, err := client.Do(req)
				if err != nil {
					continue
				}
				defer resp.Body.Close()

				body, _ := io.ReadAll(resp.Body)

				re := regexp.MustCompile(`hq_str_[a-z]+(\d+)="([^"]+)"`)
				for _, m := range re.FindAllSubmatch(body, -1) {
					sym := string(m[1])
					fields := strings.Split(string(m[2]), ",")
					if len(fields) < 10 {
						continue
					}
					prev, _ := strconv.ParseFloat(fields[2], 64)
					close, _ := strconv.ParseFloat(fields[3], 64)
					pct := float64(0)
					if prev > 0 {
						pct = (close - prev) / prev * 100
					}
					high, _ := strconv.ParseFloat(fields[4], 64)
					low, _ := strconv.ParseFloat(fields[5], 64)
					open, _ := strconv.ParseFloat(fields[1], 64)
					vol, _ := strconv.ParseFloat(fields[8], 64)
					amount, _ := strconv.ParseFloat(fields[9], 64)

					quotes[sym] = map[string]float64{
						"close_price": close,
						"change_pct":  pct,
						"high_price":  high,
						"low_price":  low,
						"open_price": open,
						"volume":     vol,
						"amount":     amount,
					}
				}
				time.Sleep(200 * time.Millisecond)
			}
		}

		// 写入 q_market_data
		today := time.Now().Format("2006-01-02")
		updated := 0
		for sym, q := range quotes {
			if q["close_price"] <= 0 {
				continue
			}
			db.WithContext(r.Context()).Exec(`
				INSERT INTO q_market_data (symbol, trade_date, open_price, high_price, low_price, close_price, volume, amount, change_pct)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
				ON DUPLICATE KEY UPDATE
				open_price=VALUES(open_price), high_price=VALUES(high_price),
				low_price=VALUES(low_price), close_price=VALUES(close_price),
				volume=VALUES(volume), amount=VALUES(amount), change_pct=VALUES(change_pct)`,
				sym, today, q["open_price"], q["high_price"], q["low_price"],
				q["close_price"], q["volume"], q["amount"], q["change_pct"])
			updated++
		}

		httpx.OkJson(w, map[string]interface{}{
			"code":    0,
			"message": "ok",
			"data": map[string]interface{}{
				"symbols_updated": updated,
				"symbols_total":  len(symbols),
				"refreshed_at":   time.Now().Format("15:04:05"),
			},
		})
	}
}

// ========== 投资组合 API ==========

// GET /api/v1/portfolio/watchlist - 关注列表
func getWatchListHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		var result []map[string]interface{}

		rows, err := db.WithContext(r.Context()).Raw(`
			SELECT w.id, w.symbol, b.name, b.industry, b.market,
			       COALESCE(m.close_price, 0) as close_price,
			       COALESCE(m.change_pct, 0) as change_pct,
			       COALESCE(m.high_price, 0) as high_price,
			       COALESCE(m.low_price, 0) as low_price,
			       COALESCE(m.volume, 0) as volume,
			       w.notes, w.created_at, w.tags
			FROM q_stock_pool w
			LEFT JOIN q_stock_basic b ON w.symbol = b.symbol
			LEFT JOIN q_market_data m ON w.symbol = m.symbol AND m.trade_date = CURDATE()
			WHERE w.is_watched = 1
			ORDER BY w.created_at DESC
		`).Rows()
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var id uint
			var symbol, name, industry, market, notes, tags string
			var closePrice, changePct, highPrice, lowPrice, volume float64
			var createdAt []uint8
			rows.Scan(&id, &symbol, &name, &industry, &market, &closePrice, &changePct,
				&highPrice, &lowPrice, &volume, &notes, &createdAt, &tags)
			result = append(result, map[string]interface{}{
				"id":           id,
				"symbol":       symbol,
				"name":         name,
				"industry":     industry,
				"market":       market,
				"close_price":  closePrice,
				"change_pct":   changePct,
				"high_price":   highPrice,
				"low_price":    lowPrice,
				"volume":       volume,
				"notes":        notes,
				"tags":         tags,
				"created_at":   string(createdAt),
			})
			}
		}
		if result == nil {
			result = []map[string]interface{}{}
		}
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": result})
	}
}

// POST /api/v1/portfolio/watch/add - 添加关注
func addWatchHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		symbol := r.URL.Query().Get("symbol")
		if symbol == "" {
			httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "股票代码不能为空"})
			return
		}
		note := r.URL.Query().Get("note")
		tags := r.URL.Query().Get("tags")
		db.WithContext(r.Context()).Exec(
			"INSERT IGNORE INTO q_stock_pool (symbol, is_watched, notes, tags, created_at) VALUES (?, 1, ?, ?, NOW())",
			symbol, note, tags,
		)
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]string{"symbol": symbol, "status": "added"}})
	}
}

// DELETE /api/v1/portfolio/watch/remove - 取消关注
func removeWatchHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		symbol := r.PathValue("symbol")
		if symbol == "" {
			httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "股票代码不能为空"})
			return
		}
		db.WithContext(r.Context()).Exec("UPDATE q_stock_pool SET is_watched=0 WHERE symbol=?", symbol)
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]string{"symbol": symbol, "status": "removed"}})
	}
}

// GET /api/v1/portfolio/paper/account - 模拟账户概况
func getPaperAccountHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		var id, userID int64
		var initCap, totalVal float64
		var createdAt []uint8

		row := db.WithContext(r.Context()).Raw(`
			SELECT id, user_id, initial_capital, total_value, created_at
			FROM q_paper_account WHERE id = 1
		`).Row()
		row.Scan(&id, &userID, &initCap, &totalVal, &createdAt)

		// 持仓统计
		var posCount int64
		db.WithContext(r.Context()).Raw("SELECT COUNT(*) FROM q_paper_position WHERE account_id=1").Scan(&posCount)

		// 今日涨跌（未实现盈亏）
		rows, _ := db.WithContext(r.Context()).Raw(`
			SELECT SUM((COALESCE(m.close_price, p.avg_cost) - p.avg_cost) * p.shares)
			FROM q_paper_position p
			LEFT JOIN q_market_data m ON p.symbol = m.symbol AND m.trade_date = CURDATE()
			WHERE p.account_id = 1
		`).Rows()
		var todayPnl float64
		if rows.Next() {
			rows.Scan(&todayPnl)
		}
		rows.Close()

		// 累计盈亏
		var totalPnl float64
		db.WithContext(r.Context()).Raw("SELECT COALESCE(total_pnl, 0) FROM q_paper_account WHERE id=1").Scan(&totalPnl)

		// 收益率（防除零）
		profitRate := 0.0
		if initCap > 0 {
			profitRate = (totalVal - initCap) / initCap * 100
		}

		data := map[string]interface{}{
			"account_id":      1,
			"initial_capital": initCap,
			"total_value":     totalVal,
			"total_pnl":       totalPnl,
			"profit_rate":     profitRate,
			"position_count":  posCount,
			"created_at":      string(createdAt),
		}
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": data})
	}
}

// GET /api/v1/portfolio/paper/positions - 模拟持仓
func getPaperPositionsHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		var result []map[string]interface{}

		// 先查今日行情
		todayQuotes := make(map[string]struct{ Price, ChangePct float64 })
		db.Raw(`SELECT symbol, close_price, change_pct FROM q_market_data WHERE trade_date = CURDATE()`).Scan(&todayQuotes)
		// 再查最近交易日行情（备用）
		var lastQuotes []struct {
			Symbol     string
			Price      float64
			ChangePct  float64
		}
		db.Raw(`SELECT m.symbol, m.close_price as price, m.change_pct FROM q_paper_position p JOIN q_market_data m ON p.symbol = m.symbol AND m.trade_date = (SELECT MAX(trade_date) FROM q_market_data WHERE symbol = p.symbol AND trade_date < CURDATE()) WHERE p.account_id = 1`).Scan(&lastQuotes)
		lastMap := make(map[string]struct{ Price, ChangePct float64 })
		for _, lq := range lastQuotes {
			lastMap[lq.Symbol] = struct{ Price, ChangePct float64 }{lq.Price, lq.ChangePct}
		}

		rows, err := db.Raw(`
			SELECT p.id, p.symbol, COALESCE(b.name,'') as name, COALESCE(b.industry,'') as industry, COALESCE(b.market,'') as market,
			       p.shares, p.avg_cost, p.shares * p.avg_cost as total_cost,
			       p.entry_date as opened_at
			FROM q_paper_position p
			LEFT JOIN q_stock_basic b ON p.symbol = b.symbol
			WHERE p.account_id = 1
			ORDER BY p.id DESC
		`).Rows()
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var id int64
				var symbol, name, industry, market, openedAt string
				var shares, avgCost, totalCost float64
				rows.Scan(&id, &symbol, &name, &industry, &market, &shares, &avgCost, &totalCost, &openedAt)
				// 注入实时行情：优先今日，否则最近交易日
				curPrice, changePct := avgCost, 0.0
				if q, ok := todayQuotes[symbol]; ok {
					curPrice, changePct = q.Price, q.ChangePct
				} else if q, ok := lastMap[symbol]; ok {
					curPrice, changePct = q.Price, q.ChangePct
				}
				profit := (curPrice - avgCost) * shares
				profitRate := 0.0
				if avgCost > 0 && curPrice > 0 {
					profitRate = (curPrice - avgCost) / avgCost * 100
				}
				result = append(result, map[string]interface{}{
					"id":            id,
					"symbol":        symbol,
					"name":          name,
					"industry":      industry,
					"market":        market,
					"shares":        shares,
					"avg_cost":      avgCost,
					"total_cost":    totalCost,
					"current_price": curPrice,
					"change_pct":    changePct,
					"high_price":    curPrice,
					"low_price":     curPrice,
					"volume":        0.0,
					"profit":        profit,
					"profit_rate":   profitRate,
					"opened_at":     openedAt,
				})
			}
		}
		if result == nil {
			result = []map[string]interface{}{}
		}
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": result})
	}
}

// GET /api/v1/portfolio/paper/trades - 模拟交易记录
func getPaperTradesHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		page, _ := strconv.ParseInt(r.URL.Query().Get("page"), 10, 64)
		pageSize, _ := strconv.ParseInt(r.URL.Query().Get("page_size"), 10, 64)
		if page < 1 {
			page = 1
		}
		if pageSize < 1 || pageSize > 50 {
			pageSize = 20
		}
		offset := (page - 1) * pageSize

		var result []map[string]interface{}
		var total int64

		db.WithContext(r.Context()).Raw("SELECT COUNT(*) FROM q_paper_trade WHERE account_id=1").Scan(&total)

		rows, err := db.WithContext(r.Context()).Raw(`
			SELECT t.id, t.symbol, b.name, t.action, t.price, t.shares,
			       t.amount, t.pnl, t.trade_date, t.action_type
			FROM q_paper_trade t
			LEFT JOIN q_stock_basic b ON t.symbol = b.symbol
			WHERE t.account_id = 1
			ORDER BY t.trade_date DESC, t.id DESC
			LIMIT ? OFFSET ?
		`, pageSize, offset).Rows()
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var id int64
				var symbol, name, action, tradedAt, actionType string
				var price, shares, amount, pnl float64
				rows.Scan(&id, &symbol, &name, &action, &price, &shares, &amount, &pnl, &tradedAt, &actionType)
				result = append(result, map[string]interface{}{
					"id":          id,
					"symbol":      symbol,
					"name":        name,
					"action":      action,
					"price":      price,
					"shares":     shares,
					"amount":     amount,
					"pnl":        pnl,
					"trade_date": tradedAt,
					"action_type": actionType,
				})
			}
		}
		if result == nil {
			result = []map[string]interface{}{}
		}
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]interface{}{
			"list":  result,
			"total": total,
			"page":  page,
			"page_size": pageSize,
		}})
	}
}

// POST /api/v1/portfolio/paper/trade - 模拟交易（买入/卖出）
func paperTradeHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		symbol := r.URL.Query().Get("symbol")
		action := r.URL.Query().Get("action")
		shares, _ := strconv.ParseFloat(r.URL.Query().Get("shares"), 64)
		price, _ := strconv.ParseFloat(r.URL.Query().Get("price"), 64)

		if symbol == "" || action == "" || shares <= 0 || price <= 0 {
			httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "参数不完整"})
			return
		}
		action = strings.ToUpper(action)
		if action != "BUY" && action != "SELL" {
			httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "action 必须是 BUY 或 SELL"})
			return
		}

		accountID := int64(1)
		fee := shares * price * 0.0003
		amount := shares * price

		// 买入：检查账户余额
		if action == "BUY" {
			var totalValue float64
			db.WithContext(r.Context()).Raw("SELECT total_value FROM q_paper_account WHERE id=?", accountID).Scan(&totalValue)
			if amount+fee > totalValue {
				httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "余额不足"})
				return
			}
			// 更新持仓
			var existingShares float64
			db.WithContext(r.Context()).Raw(
				"SELECT shares FROM q_paper_position WHERE account_id=? AND symbol=?", accountID, symbol,
			).Scan(&existingShares)
			if existingShares > 0 {
				newAvgCost := (existingShares*price + amount) / (existingShares + shares)
				newShares := existingShares + shares
				db.WithContext(r.Context()).Exec(
					"UPDATE q_paper_position SET shares=?, avg_cost=? WHERE account_id=? AND symbol=?",
					newShares, newAvgCost, accountID, symbol,
				)
			} else {
				db.WithContext(r.Context()).Exec(
					"INSERT INTO q_paper_position (account_id, symbol, shares, avg_cost, entry_date) VALUES (?,?,?,?,CURDATE())",
					accountID, symbol, shares, price,
				)
			}
		}

		// 卖出：检查持仓
		if action == "SELL" {
			var existingShares float64
			db.WithContext(r.Context()).Raw(
				"SELECT shares FROM q_paper_position WHERE account_id=? AND symbol=?", accountID, symbol,
			).Scan(&existingShares)
			if shares > existingShares {
				httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "持仓不足"})
				return
			}
			newShares := existingShares - shares
			if newShares > 0 {
				db.WithContext(r.Context()).Exec(
					"UPDATE q_paper_position SET shares=? WHERE account_id=? AND symbol=?",
					newShares, accountID, symbol,
				)
			} else {
				db.WithContext(r.Context()).Exec(
					"DELETE FROM q_paper_position WHERE account_id=? AND symbol=?", accountID, symbol,
				)
			}
		}

		// 记录交易
		db.WithContext(r.Context()).Exec(
			"INSERT INTO q_paper_trade (account_id, trade_date, action, symbol, price, shares, amount, commission) VALUES (?, CURDATE(), ?, ?, ?, ?, ?, 0)",
			accountID, action, symbol, price, shares, amount,
		)

		// 更新账户
		if action == "BUY" {
			db.WithContext(r.Context()).Exec(
				"UPDATE q_paper_account SET total_value = total_value - ? WHERE id=?",
				amount+fee, accountID,
			)
		} else {
			db.WithContext(r.Context()).Exec(
				"UPDATE q_paper_account SET total_value = total_value + ? - ? WHERE id=?",
				amount, fee, accountID,
			)
		}

		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]string{
			"symbol": symbol, "action": action, "status": "FILLED",
		}})
	}
}

// GET /api/v1/portfolio/paper/snapshots - 模拟盘每日净值
func getPaperSnapshotsHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		days, _ := strconv.ParseInt(r.URL.Query().Get("days"), 10, 64)
		if days <= 0 || days > 90 {
			days = 30
		}

		var result []map[string]interface{}
		rows, err := db.WithContext(r.Context()).Raw(`
			SELECT id, snapshot_date, total_value, daily_pnl, daily_pnl_pct,
			       total_pnl, return_pct, positions_value, cash
			FROM q_daily_snapshot
			WHERE account_id = 1
			ORDER BY snapshot_date DESC
			LIMIT ?
		`, days).Rows()
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var id int64
				var snapshotDate string
				var totalVal, dailyPnl, dailyPnlPct, totalPnl, returnPct, posVal, cash float64
				rows.Scan(&id, &snapshotDate, &totalVal, &dailyPnl, &dailyPnlPct, &totalPnl, &returnPct, &posVal, &cash)
				result = append(result, map[string]interface{}{
					"id":                id,
					"snapshot_date":     snapshotDate,
					"total_value":       totalVal,
					"daily_pnl":         dailyPnl,
					"daily_pnl_pct":     dailyPnlPct,
					"total_pnl":         totalPnl,
					"return_pct":        returnPct,
					"positions_value":   posVal,
					"cash":              cash,
				})
			}
		}
		if result == nil {
			result = []map[string]interface{}{}
		}
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": result})
	}
}

// GET /api/v1/portfolio/real/positions - 实盘持仓
func getRealPositionsHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		var result []map[string]interface{}

		// 查今日行情
		var todayQuotes map[string]struct{ Price, ChangePct float64 }
		rows, _ := db.WithContext(r.Context()).Raw(`
			SELECT symbol, close_price, change_pct FROM q_market_data WHERE trade_date = CURDATE()
		`).Rows()
		todayQuotes = make(map[string]struct{ Price, ChangePct float64 })
		if rows != nil {
			defer rows.Close()
			for rows.Next() {
				var sym string
				var price, pct float64
				if rows.Scan(&sym, &price, &pct) == nil {
					todayQuotes[sym] = struct{ Price, ChangePct float64 }{price, pct}
				}
			}
		}

		// 查最近交易日（非今日）
		var lastQuotes map[string]struct{ Price, ChangePct float64 }
		lrows, _ := db.WithContext(r.Context()).Raw(`
			SELECT symbol, close_price, change_pct FROM q_market_data
			WHERE trade_date = (SELECT MAX(trade_date) FROM q_market_data WHERE trade_date < CURDATE())
		`).Rows()
		lastQuotes = make(map[string]struct{ Price, ChangePct float64 })
		if lrows != nil {
			defer lrows.Close()
			for lrows.Next() {
				var sym string
				var price, pct float64
				if lrows.Scan(&sym, &price, &pct) == nil {
					lastQuotes[sym] = struct{ Price, ChangePct float64 }{price, pct}
				}
			}
		}

		// 查持仓
		rows2, err := db.WithContext(r.Context()).Raw(`
			SELECT p.id, p.symbol, b.name, b.industry, b.market,
			       p.quantity, p.avg_cost, p.quantity * p.avg_cost as total_cost, p.opened_at
			FROM q_positions p
			LEFT JOIN q_stock_basic b ON p.symbol = b.symbol
			WHERE p.portfolio_id = 1
			ORDER BY (COALESCE(?, p.avg_cost) - p.avg_cost) * p.quantity DESC
		`, 0.0).Rows()
		if err == nil {
			defer rows2.Close()
			for rows2.Next() {
				var id int64
				var symbol, name, industry, market, openedAt string
				var quantity, avgCost, totalCost float64
				rows2.Scan(&id, &symbol, &name, &industry, &market, &quantity, &avgCost, &totalCost, &openedAt)
				curPrice := avgCost
				curPct := 0.0
				if q, ok := todayQuotes[symbol]; ok {
					curPrice = q.Price
					curPct = q.ChangePct
				} else if q, ok := lastQuotes[symbol]; ok {
					curPrice = q.Price
					curPct = q.ChangePct
				}
				profit := (curPrice - avgCost) * quantity
				profitRate := 0.0
				if avgCost > 0 && curPrice > 0 {
					profitRate = (curPrice - avgCost) / avgCost * 100
				}
				result = append(result, map[string]interface{}{
					"id":            id,
					"symbol":        symbol,
					"name":          name,
					"industry":      industry,
					"market":        market,
					"shares":        quantity,
					"avg_cost":      avgCost,
					"total_cost":    totalCost,
					"current_price": curPrice,
					"change_pct":    curPct,
					"profit":        profit,
					"profit_rate":   profitRate,
					"opened_at":     openedAt,
				})
			}
		}
		if result == nil {
			result = []map[string]interface{}{}
		}
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": result})
	}
}

// GET /api/v1/portfolio/real/trades - 实盘交易记录
func getRealTradesHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		page, _ := strconv.ParseInt(r.URL.Query().Get("page"), 10, 64)
		pageSize, _ := strconv.ParseInt(r.URL.Query().Get("page_size"), 10, 64)
		if page < 1 {
			page = 1
		}
		if pageSize < 1 || pageSize > 50 {
			pageSize = 20
		}
		offset := (page - 1) * pageSize

		var total int64
		db.WithContext(r.Context()).Raw("SELECT COUNT(*) FROM q_trade_log WHERE account_id=1").Scan(&total)

		var result []map[string]interface{}
		rows, err := db.WithContext(r.Context()).Raw(`
			SELECT t.id, t.symbol, b.name, t.action, t.price, t.shares,
			       t.amount, t.pnl, t.trade_date, t.note
			FROM q_trade_log t
			LEFT JOIN q_stock_basic b ON t.symbol = b.symbol
			WHERE t.account_id = 1
			ORDER BY t.trade_date DESC, t.id DESC
			LIMIT ? OFFSET ?
		`, pageSize, offset).Rows()
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var id int64
				var symbol, name, action, tradedAt, note string
				var price, shares, amount, pnl float64
				rows.Scan(&id, &symbol, &name, &action, &price, &shares, &amount, &pnl, &tradedAt, &note)
				result = append(result, map[string]interface{}{
					"id":          id,
					"symbol":      symbol,
					"name":        name,
					"action":      action,
					"price":      price,
					"shares":     shares,
					"amount":     amount,
					"pnl":        pnl,
					"trade_date": tradedAt,
					"note":       note,
				})
			}
		}
		if result == nil {
			result = []map[string]interface{}{}
		}
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]interface{}{
			"list":  result,
			"total": total,
			"page":  page,
			"page_size": pageSize,
		}})
	}
}

// POST /api/v1/portfolio/real/trade - 实盘交易
func realTradeHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		symbol := r.URL.Query().Get("symbol")
		action := r.URL.Query().Get("action")
		shares, _ := strconv.ParseFloat(r.URL.Query().Get("shares"), 64)
		price, _ := strconv.ParseFloat(r.URL.Query().Get("price"), 64)
		note := r.URL.Query().Get("note")

		if symbol == "" || action == "" || shares <= 0 || price <= 0 {
			httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "参数不完整"})
			return
		}
		action = strings.ToUpper(action)
		if action != "BUY" && action != "SELL" {
			httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "action 必须是 BUY 或 SELL"})
			return
		}

		userID := int64(1)
		fee := shares * price * 0.0003
		amount := shares * price
		_ = userID
		_ = fee

		if action == "SELL" {
			var existingShares float64
			db.WithContext(r.Context()).Raw(
				"SELECT COALESCE(SUM(quantity),0) FROM q_positions WHERE portfolio_id=1 AND symbol=? AND quantity>0", symbol,
			).Scan(&existingShares)
			if shares > existingShares {
				httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "持仓不足"})
				return
			}
		}

		// 更新持仓
		var existingShares float64
		db.WithContext(r.Context()).Raw(
			"SELECT COALESCE(SUM(quantity),0) FROM q_positions WHERE portfolio_id=1 AND symbol=?", symbol,
		).Scan(&existingShares)

		var newShares, newAvgCost, newTotalCost float64
		if action == "BUY" {
			newShares = existingShares + shares
			if existingShares > 0 {
				type costRow struct {
					AvgCost   float64
					TotalCost float64
				}
				var cr costRow
				db.WithContext(r.Context()).Raw(
					"SELECT avg_cost, quantity * avg_cost FROM q_positions WHERE portfolio_id=1 AND symbol=?", symbol,
				).Scan(&cr)
				newAvgCost = (cr.TotalCost + amount) / newShares
			} else {
				newAvgCost = price
			}
			newTotalCost = newShares * newAvgCost
		} else {
			newShares = existingShares - shares
			var avgCost float64
			db.WithContext(r.Context()).Raw(
				"SELECT avg_cost FROM q_positions WHERE portfolio_id=1 AND symbol=?", symbol,
			).Scan(&avgCost)
			newAvgCost = avgCost
			newTotalCost = newShares * newAvgCost
		}

		if existingShares > 0 {
			if newShares > 0 {
				db.WithContext(r.Context()).Exec(
					"UPDATE q_positions SET quantity=?, avg_cost=?, quantity*avg_cost=? WHERE portfolio_id=1 AND symbol=?",
					newShares, newAvgCost, newTotalCost, symbol,
				)
			} else {
				db.WithContext(r.Context()).Exec(
					"DELETE FROM q_positions WHERE portfolio_id=1 AND symbol=?", symbol,
				)
			}
		} else {
			db.WithContext(r.Context()).Exec(
				"INSERT INTO q_positions (portfolio_id, account_id, symbol, quantity, avg_cost, quantity*avg_cost, entry_date) VALUES (1, 1, ?, ?, ?, ?, CURDATE())",
				symbol, newShares, newAvgCost, newTotalCost,
			)
		}

		// 记录交易
		db.WithContext(r.Context()).Exec(
			"INSERT INTO q_trade_log (account_id, trade_no, symbol, action, price, shares, amount, note, trade_date, trade_time, action_type, cash_before, cash_after) VALUES (1, CONCAT(DATE_FORMAT(CURDATE(),'%Y%m%d'),'-',LPAD(COALESCE((SELECT MAX(id)+1 FROM q_trade_log),0),4,'0')), ?, ?, ?, ?, ?, ?, CURDATE(), CURTIME(), 'MANUAL', 0, 0)",
			symbol, action, price, shares, amount, note,
		)

		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]string{
			"symbol": symbol, "action": action, "status": "FILLED",
		}})
	}
}

// GET /api/v1/portfolio/real/summary - 实盘收益汇总
func getRealSummaryHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB

		// 账户总览
		var totalInvested, totalValue, totalProfit, totalProfitRate, posCount float64
		db.WithContext(r.Context()).Raw("SELECT COUNT(*) FROM q_positions WHERE portfolio_id=1 AND quantity>0").Scan(&posCount)
		posRows, _ := db.WithContext(r.Context()).Raw(`
			SELECT COALESCE(SUM(quantity * avg_cost), 0) FROM q_positions WHERE portfolio_id=1 AND quantity > 0
		`).Rows()
		if posRows != nil {
			posRows.Scan(&totalInvested)
			posRows.Close()
		}

		// 今日行情
		var todayQuotes map[string]struct{ Price, ChangePct float64 }
		tRows, _ := db.WithContext(r.Context()).Raw(`
			SELECT symbol, close_price, change_pct FROM q_market_data WHERE trade_date = CURDATE()
		`).Rows()
		todayQuotes = make(map[string]struct{ Price, ChangePct float64 })
		if tRows != nil {
			defer tRows.Close()
			for tRows.Next() {
				var sym string
				var price, pct float64
				if tRows.Scan(&sym, &price, &pct) == nil {
					todayQuotes[sym] = struct{ Price, ChangePct float64 }{price, pct}
				}
			}
		}
		// 最近交易日
		var lastQuotes map[string]struct{ Price, ChangePct float64 }
		lRows, _ := db.WithContext(r.Context()).Raw(`
			SELECT symbol, close_price, change_pct FROM q_market_data
			WHERE trade_date = (SELECT MAX(trade_date) FROM q_market_data WHERE trade_date < CURDATE())
		`).Rows()
		lastQuotes = make(map[string]struct{ Price, ChangePct float64 })
		if lRows != nil {
			defer lRows.Close()
			for lRows.Next() {
				var sym string
				var price, pct float64
				if lRows.Scan(&sym, &price, &pct) == nil {
					lastQuotes[sym] = struct{ Price, ChangePct float64 }{price, pct}
				}
			}
		}
		// 用持仓数据计算总市值
		pRows2, _ := db.WithContext(r.Context()).Raw(`
			SELECT symbol, quantity, avg_cost FROM q_positions WHERE portfolio_id=1 AND quantity > 0
		`).Rows()
		if pRows2 != nil {
			defer pRows2.Close()
			for pRows2.Next() {
				var sym string
				var qty, cost float64
				if pRows2.Scan(&sym, &qty, &cost) != nil {
					continue
				}
				price := cost
				if q, ok := todayQuotes[sym]; ok {
					price = q.Price
				} else if q, ok := lastQuotes[sym]; ok {
					price = q.Price
				}
				totalValue += price * qty
			}
		}
		totalProfit = totalValue - totalInvested
		if totalInvested > 0 {
			totalProfitRate = totalProfit / totalInvested * 100
		}

		// 年度盈亏（按月统计）
		var monthly []map[string]interface{}
		mRows, _ := db.WithContext(r.Context()).Raw(`
			SELECT DATE_FORMAT(trade_date, '%Y-%m') as month,
			       SUM(CASE WHEN action='BUY' THEN -amount - COALESCE(commission,0)
			                WHEN action='SELL' THEN amount - COALESCE(commission,0) END) as pnl,
			       COUNT(*) as trade_count
			FROM q_trade_log WHERE account_id=1
			GROUP BY DATE_FORMAT(trade_date, '%Y-%m')
			ORDER BY month DESC LIMIT 12
		`).Rows()
		if mRows != nil {
			for mRows.Next() {
				var month string
				var pnl float64
				var count int64
				mRows.Scan(&month, &pnl, &count)
				monthly = append(monthly, map[string]interface{}{
					"month":       month,
					"pnl":         pnl,
					"trade_count": count,
				})
			}
			mRows.Close()
		}

		data := map[string]interface{}{
			"total_invested":  totalInvested,
			"total_value":     totalValue,
			"total_profit":   totalProfit,
			"profit_rate":     totalProfitRate,
			"position_count":  posCount,
			"monthly":         monthly,
		}
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": data})
	}
}

// GET /api/v1/portfolio/strategy/list - 交易策略列表
func getStrategyListHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		var result []map[string]interface{}

		rows, err := db.WithContext(r.Context()).Raw(`
			SELECT id, name, type, description, params, is_active, created_at
			FROM q_strategy WHERE is_deleted=0 ORDER BY created_at DESC
		`).Rows()
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var id int64
				var name, strategyType, desc, params string
				var isActive bool
				var createdAt []uint8
				rows.Scan(&id, &name, &strategyType, &desc, &params, &isActive, &createdAt)
				result = append(result, map[string]interface{}{
					"id":          id,
					"name":        name,
					"type":        strategyType,
					"description": desc,
					"params":      params,
					"is_active":   isActive,
					"created_at":  string(createdAt),
				})
			}
		}
		if result == nil {
			result = []map[string]interface{}{}
		}
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": result})
	}
}

// POST /api/v1/portfolio/strategy - 创建/更新策略
func saveStrategyHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		name := r.URL.Query().Get("name")
		strategyType := r.URL.Query().Get("type")
		desc := r.URL.Query().Get("description")
		params := r.URL.Query().Get("params")
		idStr := r.URL.Query().Get("id")

		if name == "" || strategyType == "" {
			httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "名称和类型不能为空"})
			return
		}

		if idStr != "" {
			id, _ := strconv.ParseInt(idStr, 10, 64)
			db.WithContext(r.Context()).Exec(
				"UPDATE q_strategy SET name=?, type=?, description=?, params=? WHERE id=?",
				name, strategyType, desc, params, id,
			)
			httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]string{"id": idStr, "status": "updated"}})
		} else {
			db.WithContext(r.Context()).Exec(
				"INSERT INTO q_strategy (name, type, description, params, is_active, created_at) VALUES (?,?,?,?,0,NOW())",
				name, strategyType, desc, params,
			)
			var newID int64
			db.WithContext(r.Context()).Raw("SELECT LAST_INSERT_ID()").Scan(&newID)
			httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]interface{}{"id": newID, "status": "created"}})
		}
	}
}

// POST /api/v1/portfolio/strategy/toggle - 启用/停用策略
func toggleStrategyHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		id, _ := strconv.ParseInt(r.URL.Query().Get("id"), 10, 64)
		active := r.URL.Query().Get("active")
		if id <= 0 {
			httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "无效的策略ID"})
			return
		}
		isActive := 0
		if active == "1" || active == "true" {
			isActive = 1
		}
		db.WithContext(r.Context()).Exec("UPDATE q_strategy SET is_active=? WHERE id=?", isActive, id)
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]string{"id": strconv.FormatInt(id, 10), "is_active": strconv.Itoa(isActive)}})
	}
}

// DELETE /api/v1/portfolio/strategy - 删除策略
func deleteStrategyHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		id, _ := strconv.ParseInt(r.URL.Query().Get("id"), 10, 64)
		if id <= 0 {
			httpx.Error(w, &types.ErrorResponse{Code: 400, Message: "无效的策略ID"})
			return
		}
		db.WithContext(r.Context()).Exec("UPDATE q_strategy SET is_deleted=1 WHERE id=?", id)
		httpx.OkJson(w, map[string]interface{}{"code": 0, "message": "ok", "data": map[string]string{"id": strconv.FormatInt(id, 10), "status": "deleted"}})
	}
}
