package handler

import (
	"net/http"
	"strconv"
	"strings"

	"quantos/app/api/internal/svc"
	"quantos/app/api/internal/types"

	"github.com/zeromicro/go-zero/rest/httpx"
)

// ========== 股票数据 API ==========

// GET /api/v1/stock/list
func getStockListHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB

		page, _ := strconv.ParseInt(r.URL.Query().Get("page"), 10, 64)
		pageSize, _ := strconv.ParseInt(r.URL.Query().Get("page_size"), 10, 64)
		if page < 1 {
			page = 1
		}
		if pageSize < 1 || pageSize > 100 {
			pageSize = 20
		}
		offset := (page - 1) * pageSize

		keyword := r.URL.Query().Get("keyword")
		market := r.URL.Query().Get("market")

		query := db.WithContext(r.Context()).Table("q_stock_basic")
		if keyword != "" {
			query = query.Where("symbol LIKE ? OR name LIKE ?", "%"+keyword+"%", "%"+keyword+"%")
		}
		if market != "" {
			query = query.Where("market = ?", market)
		}

		var total int64
		query.Count(&total)

		type StockItem struct {
			ID         uint    `json:"id"`
			Symbol     string  `json:"symbol"`
			SymbolName string  `json:"name"`
			Market     string  `json:"market"`
			Industry   string  `json:"industry"`
			Sector     string  `json:"sector"`
			ListDate   string  `json:"list_date"`
			Status     int     `json:"status"`
			TotalShare *string `json:"total_share"`
		}
		var list []StockItem
		query.Order("id DESC").Offset(int(offset)).Limit(int(pageSize)).Scan(&list)

		if list == nil {
			list = []StockItem{}
		}

		httpx.OkJson(w, map[string]interface{}{
			"code":    0,
			"message": "ok",
			"data": map[string]interface{}{
				"list":      list,
				"total":     total,
				"page":      page,
				"page_size": pageSize,
			},
		})
	}
}

// GET /api/v1/stock/quote
func getRealTimeQuoteHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB

		symbols := r.URL.Query().Get("symbols")

		type QuoteItem struct {
			Symbol     string  `json:"symbol"`
			SymbolName string  `json:"symbol_name"`
			OpenPrice  float64 `json:"open_price"`
			HighPrice  float64 `json:"high_price"`
			LowPrice   float64 `json:"low_price"`
			ClosePrice float64 `json:"close_price"`
			Volume     int64   `json:"volume"`
			Amount     float64 `json:"amount"`
			ChangePct  float64 `json:"change_pct"`
			TradeDate  string  `json:"trade_date"`
		}

		var list []QuoteItem
		var err error

		if symbols != "" {
			codes := strings.Split(symbols, ",")
			for i := range codes {
				codes[i] = strings.TrimSpace(codes[i])
			}
			err = db.WithContext(r.Context()).Table("q_market_data").
				Where("symbol IN ?", codes).
				Order("trade_date DESC, id DESC").
				Find(&list).Error
		} else {
			// 去重：每个 symbol 只取最新一条
			err = db.WithContext(r.Context()).Raw(`
				SELECT t1.* FROM q_market_data t1
				INNER JOIN (
					SELECT symbol, MAX(id) as max_id
					FROM q_market_data
					GROUP BY symbol
				) t2 ON t1.id = t2.max_id
				ORDER BY t1.id DESC
				LIMIT 20
			`).Scan(&list).Error
		}

		if err != nil || list == nil {
			list = []QuoteItem{}
		}

		httpx.OkJson(w, map[string]interface{}{
			"code":    0,
			"message": "ok",
			"data":    list,
		})
	}
}

// GET /api/v1/stock/kline
func getKLineDataHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB

		symbol := r.URL.Query().Get("symbol")
		limit, _ := strconv.ParseInt(r.URL.Query().Get("limit"), 10, 64)
		if limit < 1 || limit > 500 {
			limit = 60
		}
		period := r.URL.Query().Get("period") // daily, weekly, monthly

		if symbol == "" {
			httpx.Error(w, &types.ErrorResponse{Code: 1001, Message: "symbol 参数必填"})
			return
		}

		type KlineItem struct {
			Symbol      string  `json:"symbol"`
			TradeDate   string  `json:"trade_date"`
			OpenPrice   float64 `json:"open_price"`
			HighPrice   float64 `json:"high_price"`
			LowPrice    float64 `json:"low_price"`
			ClosePrice  float64 `json:"close_price"`
			Volume      int64   `json:"volume"`
			Amount      float64 `json:"amount"`
			ChangePct   float64 `json:"change_pct"`
			MA5         *float64 `json:"ma5"`
			MA10        *float64 `json:"ma10"`
			MA20        *float64 `json:"ma20"`
			MA60        *float64 `json:"ma60"`
			RSI6        *float64 `json:"rsi6"`
			RSI12       *float64 `json:"rsi12"`
			RSI24       *float64 `json:"rsi24"`
			MACDDif     *float64 `json:"macd_dif"`
			MACDDea     *float64 `json:"macd_dea"`
			MACDHist    *float64 `json:"macd_hist"`
		}

		var list []KlineItem

		if period == "weekly" {
			// 周线：按 week 分组
			db.WithContext(r.Context()).Raw(`
				SELECT symbol, MIN(trade_date) as trade_date,
					CAST(AVG(open_price) AS DECIMAL(10,2)) as open_price,
					CAST(MAX(high_price) AS DECIMAL(10,2)) as high_price,
					CAST(MIN(low_price) AS DECIMAL(10,2)) as low_price,
					CAST(AVG(close_price) AS DECIMAL(10,2)) as close_price,
					SUM(volume) as volume, SUM(amount) as amount,
					CAST(AVG(change_pct) AS DECIMAL(10,2)) as change_pct
				FROM q_daily_kline
				WHERE symbol = ?
				GROUP BY YEARWEEK(trade_date, 1)
				ORDER BY trade_date DESC
				LIMIT ?
			`, symbol, limit).Scan(&list)
		} else if period == "monthly" {
			db.WithContext(r.Context()).Raw(`
				SELECT symbol, MIN(trade_date) as trade_date,
					CAST(AVG(open_price) AS DECIMAL(10,2)) as open_price,
					CAST(MAX(high_price) AS DECIMAL(10,2)) as high_price,
					CAST(MIN(low_price) AS DECIMAL(10,2)) as low_price,
					CAST(AVG(close_price) AS DECIMAL(10,2)) as close_price,
					SUM(volume) as volume, SUM(amount) as amount,
					CAST(AVG(change_pct) AS DECIMAL(10,2)) as change_pct
				FROM q_daily_kline
				WHERE symbol = ?
				GROUP BY DATE_FORMAT(trade_date, '%Y-%m')
				ORDER BY trade_date DESC
				LIMIT ?
			`, symbol, limit).Scan(&list)
		} else {
			// 日线
			db.WithContext(r.Context()).Table("q_daily_kline").
				Where("symbol = ?", symbol).
				Order("trade_date DESC").
				Limit(int(limit)).
				Scan(&list)
		}

		if list == nil {
			list = []KlineItem{}
		}

		httpx.OkJson(w, map[string]interface{}{
			"code":    0,
			"message": "ok",
			"data": map[string]interface{}{
				"symbol": symbol,
				"klines": list,
			},
		})
	}
}

// GET /api/v1/stock/index
func getIndexDataHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB

		defaultIndex := []string{"000001", "399001", "399006", "000688", "000300"}
		symbols := r.URL.Query().Get("symbols")
		var indexList []string
		if symbols != "" {
			for _, s := range strings.Split(symbols, ",") {
				indexList = append(indexList, strings.TrimSpace(s))
			}
		} else {
			indexList = defaultIndex
		}

		type IndexItem struct {
			Symbol     string  `json:"symbol"`
			SymbolName string  `json:"name"`
			ClosePrice float64 `json:"close_price"`
			ChangePct  float64 `json:"change_pct"`
			Volume     int64   `json:"volume"`
			Amount     float64 `json:"amount"`
			TradeDate  string  `json:"trade_date"`
		}

		var list []IndexItem
		// 每个 symbol 取最新一条：用 db.Table().Where().Find()
		// 分开查询避免复杂 JOIN
		for _, sym := range indexList {
			var item IndexItem
			err := db.WithContext(r.Context()).Table("q_market_data").
				Where("symbol = ?", sym).
				Order("id DESC").Limit(1).
				Scan(&item).Error
			if err == nil && item.Symbol != "" {
				list = append(list, item)
			}
		}

		if list == nil {
			list = []IndexItem{}
		}

		httpx.OkJson(w, map[string]interface{}{
			"code":    0,
			"message": "ok",
			"data":    list,
		})
	}
}

// GET /api/v1/stock/search
func getStockSearchHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		db := ctx.Common.DB
		keyword := r.URL.Query().Get("keyword")
		limit, _ := strconv.ParseInt(r.URL.Query().Get("limit"), 10, 64)
		if limit < 1 || limit > 20 {
			limit = 10
		}

		type SearchItem struct {
			Symbol string `json:"symbol"`
			Name   string `json:"name"`
			Market string `json:"market"`
		}

		var list []SearchItem
		if keyword != "" {
			db.WithContext(r.Context()).Table("q_stock_basic").
				Select("symbol, name, market").
				Where("status = 1").
				Where("symbol LIKE ? OR name LIKE ?", "%"+keyword+"%", "%"+keyword+"%").
				Order("FIELD(market, 'SH','SZ') DESC, symbol").
				Limit(int(limit)).
				Scan(&list)
		}

		if list == nil {
			list = []SearchItem{}
		}

		httpx.OkJson(w, map[string]interface{}{
			"code":    0,
			"message": "ok",
			"data":    list,
		})
	}
}


// GET /api/v1/stock/level2
func getLevel2DataHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		httpx.Error(w, &types.ErrorResponse{
			Code:    4001,
			Message: "Level2 数据需要专业版权限",
		})
	}
}
