package papertrading

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

// ========== 市场数据结构 ==========

// RealtimeQuote 实时行情
type RealtimeQuote struct {
	Symbol     string  `json:"symbol"`
	Name       string  `json:"name"`
	Price      float64 `json:"price"`
	ChangePct  float64 `json:"change_pct"`
	Volume     int64   `json:"volume"`
	Amount     float64 `json:"amount"`
	Open       float64 `json:"open"`
	High       float64 `json:"high"`
	Low        float64 `json:"low"`
	PrevClose  float64 `json:"prev_close"`
	RSI        float64 `json:"rsi"`
	MA5        float64 `json:"ma5"`
	MA10       float64 `json:"ma10"`
	MA20       float64 `json:"ma20"`
	Timestamp  int64   `json:"timestamp"`
}

// KLineData K线数据
type KLineData struct {
	Date      string  `json:"日期"`
	Open      float64 `json:"开盘"`
	High      float64 `json:"最高"`
	Low       float64 `json:"最低"`
	Close     float64 `json:"收盘"`
	Volume    int64   `json:"成交量"`
	Amount    float64 `json:"成交额"`
	Turnover  float64 `json:"换手率"` // 百分比
}

// PositionPnl 持仓盈亏
type PositionPnl struct {
	Symbol       string  `json:"symbol"`
	SymbolName   string  `json:"symbol_name"`
	Shares       int     `json:"shares"`
	AvgCost      float64 `json:"avg_cost"`
	CurrentPrice float64 `json:"current_price"`
	MarketValue  float64 `json:"market_value"`
	CostValue    float64 `json:"cost_value"`
	Pnl          float64 `json:"pnl"`
	PnlPct       float64 `json:"pnl_pct"`
	StopLoss     float64 `json:"stop_loss"`
	TakeProfit1  float64 `json:"take_profit1"`
	TakeProfit2  float64 `json:"take_profit2"`
	Action       string  `json:"action"` // STOP_LOSS, TAKE_PROFIT1, TAKE_PROFIT2, NORMAL
}

// ========== 市场数据接口 ==========

// MarketClient 市场数据客户端
type MarketClient struct {
	pythonScript string
}

// NewMarketClient 创建市场数据客户端
func NewMarketClient() *MarketClient {
	return &MarketClient{
		pythonScript: getProjectRoot() + "/scripts/fetch_market_data.py",
	}
}

// GetRealtimeQuote 获取股票实时行情
func (m *MarketClient) GetRealtimeQuote(ctx context.Context, symbol string) (*RealtimeQuote, error) {
	cmd := exec.CommandContext(ctx, "python3", m.pythonScript, "realtime", symbol)
	output, err := cmd.Output()
	if err != nil {
		return m.getMockQuote(symbol)
	}

	var quote RealtimeQuote
	if err := json.Unmarshal(output, &quote); err != nil || quote.Symbol == "" {
		return m.getMockQuote(symbol)
	}

	return &quote, nil
}

// GetRealtimeQuotes 批量获取股票实时行情
func (m *MarketClient) GetRealtimeQuotes(ctx context.Context, symbols []string) (map[string]*RealtimeQuote, error) {
	result := make(map[string]*RealtimeQuote)
	for _, symbol := range symbols {
		quote, err := m.GetRealtimeQuote(ctx, symbol)
		if err == nil && quote != nil {
			result[symbol] = quote
		}
	}
	return result, nil
}

// GetKLineData 获取K线数据
func (m *MarketClient) GetKLineData(ctx context.Context, symbol string, period string, adjust string, limit int) ([]KLineData, error) {
	cmd := exec.CommandContext(ctx, "python3", m.pythonScript, "kline", symbol, period, adjust, strconv.Itoa(limit))
	output, err := cmd.Output()
	if err != nil {
		return m.getMockKLine(symbol, limit)
	}

	var klines []KLineData
	if err := json.Unmarshal(output, &klines); err != nil || len(klines) == 0 {
		return m.getMockKLine(symbol, limit)
	}

	return klines, nil
}

// CalculateRSI 计算RSI指标
func (m *MarketClient) CalculateRSI(klines []KLineData, period int) float64 {
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

// CalculateMA 计算移动平均线
func (m *MarketClient) CalculateMA(klines []KLineData, period int) float64 {
	if len(klines) < period {
		return 0
	}

	var sum float64
	for i := len(klines) - period; i < len(klines); i++ {
		sum += klines[i].Close
	}
	return sum / float64(period)
}

// GetPositionPnls 计算持仓盈亏
func (m *MarketClient) GetPositionPnls(ctx context.Context, positions []*PaperPosition) ([]*PositionPnl, error) {
	result := make([]*PositionPnl, 0, len(positions))

	for _, pos := range positions {
		quote, err := m.GetRealtimeQuote(ctx, pos.Symbol)
		if err != nil {
			quote = &RealtimeQuote{
				Symbol: pos.Symbol,
				Name:   pos.SymbolName,
				Price:  pos.AvgCost,
			}
		}

		currentPrice := quote.Price
		if currentPrice == 0 {
			currentPrice = pos.AvgCost
		}

		marketValue := currentPrice * float64(pos.Shares)
		costValue := pos.AvgCost * float64(pos.Shares)
		pnl := marketValue - costValue
		pnlPct := 0.0
		if costValue > 0 {
			pnlPct = (currentPrice - pos.AvgCost) / pos.AvgCost * 100
		}

		action := "NORMAL"
		if currentPrice <= pos.StopLoss {
			action = "STOP_LOSS"
		} else if pnlPct >= TakeProfit2*100 {
			action = "TAKE_PROFIT2"
		} else if pnlPct >= TakeProfit1*100 {
			action = "TAKE_PROFIT1"
		}

		result = append(result, &PositionPnl{
			Symbol:       pos.Symbol,
			SymbolName:   pos.SymbolName,
			Shares:       pos.Shares,
			AvgCost:      pos.AvgCost,
			CurrentPrice: currentPrice,
			MarketValue:  marketValue,
			CostValue:    costValue,
			Pnl:          pnl,
			PnlPct:       pnlPct,
			StopLoss:     pos.StopLoss,
			TakeProfit1:  pos.TakeProfit1,
			TakeProfit2:  pos.TakeProfit2,
			Action:       action,
		})
	}

	return result, nil
}

// ========== 辅助函数 ==========

// getMockQuote 获取模拟行情数据
func (m *MarketClient) getMockQuote(symbol string) (*RealtimeQuote, error) {
	prices := map[string]float64{
		"600036": 35.50, "600900": 22.50, "601288": 3.20,
		"000858": 150.00, "300750": 200.00, "601318": 42.00,
		"002475": 28.00, "600519": 1600.00,
	}

	nameMap := map[string]string{
		"600036": "招商银行", "600900": "长江电力", "601288": "农业银行",
		"000858": "五粮液", "300750": "宁德时代", "601318": "中国平安",
		"002475": "立讯精密", "600519": "贵州茅台",
	}

	price := prices[symbol]
	if price == 0 {
		price = 20.0
	}

	name := nameMap[symbol]
	if name == "" {
		name = symbol
	}

	return &RealtimeQuote{
		Symbol:    symbol,
		Name:      name,
		Price:     price,
		ChangePct: 0,
		Volume:    1000000,
		Amount:    500000000,
		Open:      price * 0.99,
		High:      price * 1.02,
		Low:       price * 0.98,
		PrevClose: price,
		RSI:       50,
		MA5:       price,
		MA10:      price,
		MA20:      price,
		Timestamp: time.Now().Unix(),
	}, nil
}

// getMockKLine 获取模拟K线数据
func (m *MarketClient) getMockKLine(symbol string, limit int) ([]KLineData, error) {
	basePrices := map[string]float64{
		"600036": 35.0, "600900": 22.0, "601288": 3.2,
	}
	basePrice := basePrices[symbol]
	if basePrice == 0 {
		basePrice = 20.0
	}

	klines := make([]KLineData, 0, limit)
	currentPrice := basePrice

	for i := limit - 1; i >= 0; i-- {
		date := time.Now().AddDate(0, 0, -i)
		if date.Weekday() == time.Saturday || date.Weekday() == time.Sunday {
			continue
		}

		change := (float64(i%10) - 5) / 100
		currentPrice = currentPrice * (1 + change)

		open := currentPrice * 0.995
		high := currentPrice * 1.015
		low := currentPrice * 0.985

		klines = append(klines, KLineData{
			Date:     date.Format("2006-01-02"),
			Open:     roundM(open, 2),
			High:     roundM(high, 2),
			Low:      roundM(low, 2),
			Close:    roundM(currentPrice, 2),
			Volume:   int64(1000000 + i*10000),
			Amount:   currentPrice * 1000000,
			Turnover: 2.5,
		})
	}

	return klines, nil
}

// PrintQuote 打印行情信息
func PrintQuote(quote *RealtimeQuote) {
	arrow := "→"
	color := ""
	if quote.ChangePct > 0 {
		arrow = "↑"
		color = "🟢"
	} else if quote.ChangePct < 0 {
		arrow = "↓"
		color = "🔴"
	}

	fmt.Printf("%s %s %s 最新价 ¥%.2f %s%.2f%%\n", color, quote.Symbol, quote.Name, quote.Price, arrow, quote.ChangePct)
	fmt.Printf("   开盘:¥%.2f 最高:¥%.2f 最低:¥%.2f 昨收:¥%.2f\n", quote.Open, quote.High, quote.Low, quote.PrevClose)
	fmt.Printf("   RSI=%.1f MA5=¥%.2f MA20=¥%.2f\n", quote.RSI, quote.MA5, quote.MA20)
}

// PrintPnls 打印持仓盈亏列表
func PrintPnls(pnls []*PositionPnl) {
	if len(pnls) == 0 {
		fmt.Println("暂无持仓")
		return
	}

	fmt.Println("\n📊 持仓盈亏：")
	fmt.Println("────────────────────────────────────────────────────────────")
	fmt.Printf("%-8s %-10s %-6s %-8s %-8s %-8s %-6s\n", "代码", "名称", "股数", "成本价", "现价", "盈亏", "收益率")
	fmt.Println("────────────────────────────────────────────────────────────")

	for _, p := range pnls {
		arrow := ""
		color := ""
		if p.Pnl > 0 {
			arrow = "+"
			color = "🟢"
		} else if p.Pnl < 0 {
			arrow = ""
			color = "🔴"
		}

		fmt.Printf("%s%-8s %-10s %-6d ¥%-7.2f ¥%-7.2f %s¥%.0f %s%.1f%%\n",
			color, p.Symbol, p.SymbolName, p.Shares, p.AvgCost, p.CurrentPrice,
			arrow, p.Pnl, arrow, p.PnlPct)

		if p.Action == "STOP_LOSS" {
			fmt.Printf("   ⚠️  触发止损 ¥%.2f\n", p.StopLoss)
		} else if p.Action == "TAKE_PROFIT1" {
			fmt.Printf("   💰 触发止盈1 ¥%.2f\n", p.TakeProfit1)
		} else if p.Action == "TAKE_PROFIT2" {
			fmt.Printf("   💰 触发止盈2 ¥%.2f\n", p.TakeProfit2)
		}
	}
	fmt.Println("────────────────────────────────────────────────────────────")
}

// PrintKLine 打印K线数据
func PrintKLine(klines []KLineData) {
	if len(klines) == 0 {
		fmt.Println("暂无K线数据")
		return
	}

	fmt.Println("\n📈 K线数据：")
	fmt.Println("────────────────────────────────────────────────────────────")
	fmt.Printf("%-12s %-8s %-8s %-8s %-8s %-12s\n", "日期", "开盘", "最高", "最低", "收盘", "成交量")
	fmt.Println("────────────────────────────────────────────────────────────")

	show := klines
	if len(show) > 10 {
		show = show[len(show)-10:]
	}

	for _, k := range show {
		color := ""
		if k.Close > k.Open {
			color = "🟢"
		} else if k.Close < k.Open {
			color = "🔴"
		}
		fmt.Printf("%s%-12s %s¥%-7.2f ¥%-7.2f ¥%-7.2f ¥%-7.2f %d万\n",
			color, k.Date, color, k.Open, k.High, k.Low, k.Close, k.Volume/10000)
	}
	fmt.Println("────────────────────────────────────────────────────────────")
}

// ========== 辅助函数 ==========

func roundM(val float64, precision int) float64 {
	round := 1.0
	for i := 0; i < precision; i++ {
		round *= 10
	}
	return float64(int(val*round+0.5)) / round
}

func parseFloat(s string) float64 {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0
	}
	return f
}

// CalcRSIFromKLines 辅助函数，供外部调用
func CalcRSIFromKLines(klines []KLineData, period int) float64 {
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
	return 100 - (100 / (1 + rs))
}
