package papertrading

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"time"
)

// ========== 常量定义 ==========

const (
	InitialCapital  = 100000.0  // 初始资金 ¥100,000
	CashReserve     = 40000.0   // 保留现金 ¥40,000
	MaxPosition     = 15000.0   // 单只最大持仓 ¥15,000
	MaxPositions    = 4         // 最多持仓 4 只
	StopLoss        = 0.03      // 止损线 3%
	TakeProfit1     = 0.05      // 第一止盈 5%
	TakeProfit2     = 0.08      // 第二止盈 8%
	StopLossMove    = 0.005     // 移动止损补偿 0.5%
)

// ========== 数据模型 ==========

// Position 持仓
type Position struct {
	Code        string  `json:"code"`        // 股票代码
	Name        string  `json:"name"`        // 股票名称
	Shares      int     `json:"shares"`      // 股数
	AvgCost     float64 `json:"avg_cost"`    // 成本价
	StopLoss    float64 `json:"stop_loss"`   // 止损价
	TakeProfit1 float64 `json:"take_profit1"` // 止盈价1
	TakeProfit2 float64 `json:"take_profit2"` // 止盈价2
	EntryDate   string  `json:"entry_date"`  // 入场日期
	Reason      string  `json:"reason"`      // 买入理由
	RSI         float64 `json:"rsi"`         // 入场RSI
	StopMoved   bool    `json:"stop_moved"`  // 止损线是否已移动
}

// TradeRecord 交易记录
type TradeRecord struct {
	ID          int     `json:"id"`          // 交易ID
	Date        string  `json:"date"`        // 交易日期
	Action      string  `json:"action"`      // BUY/SELL
	Code        string  `json:"code"`        // 股票代码
	Name        string  `json:"name"`        // 股票名称
	Price       float64 `json:"price"`       // 成交价
	Shares      int     `json:"shares"`      // 股数
	Amount      float64 `json:"amount"`      // 成交金额
	AvgCost     float64 `json:"avg_cost,omitempty"` // 成本价（卖出时记录）
	PnL         float64 `json:"pnl,omitempty"`      // 盈亏金额（卖出时计算）
	PnLPct      float64 `json:"pnl_pct,omitempty"`  // 盈亏比例
	Reason      string  `json:"reason"`      // 交易理由
	HoldDays    int     `json:"hold_days,omitempty"` // 持有天数
	CashAfter   float64 `json:"cash_after"`  // 交易后现金
}

// AccountStats 账户统计
type AccountStats struct {
	InitialCapital float64 `json:"initial_capital"` // 初始资金
	CurrentCapital float64 `json:"current_capital"` // 当前现金
	TotalValue     float64 `json:"total_value"`     // 总资产
	PositionsValue float64 `json:"positions_value"` // 持仓市值
	TotalPnL       float64 `json:"total_pnl"`       // 总盈亏
	ReturnRate     float64 `json:"return_rate"`     // 收益率
	TotalTrades    int     `json:"total_trades"`    // 总交易次数
	Wins           int     `json:"wins"`            // 盈利次数
	Losses         int     `json:"losses"`          // 亏损次数
	WinRate        float64 `json:"win_rate"`        // 胜率
	AvgWin         float64 `json:"avg_win"`         // 平均盈利
	AvgLoss        float64 `json:"avg_loss"`        // 平均亏损
	CurrentPos     int     `json:"current_positions"` // 当前持仓数
}

// PaperAccount 模拟账户
type PaperAccount struct {
	InitialCapital float64            `json:"initial_capital"`
	Capital        float64            `json:"capital"`
	Positions      map[string]*Position `json:"positions"`
	Trades         []*TradeRecord      `json:"trades"`
	dataDir        string
	tradeFile      string
	positionFile   string
	statsFile      string
}

// ========== 账户管理 ==========

// NewPaperAccount 创建新账户
func NewPaperAccount() *PaperAccount {
	dataDir := filepath.Join(getProjectRoot(), "data", "paper")
	os.MkdirAll(dataDir, 0755)
	
	acc := &PaperAccount{
		InitialCapital: InitialCapital,
		Capital:        InitialCapital - CashReserve, // 可交易资金
		Positions:      make(map[string]*Position),
		Trades:         []*TradeRecord{},
		dataDir:        dataDir,
		tradeFile:      filepath.Join(dataDir, "trades.json"),
		positionFile:   filepath.Join(dataDir, "positions.json"),
		statsFile:      filepath.Join(dataDir, "stats.json"),
	}
	
	acc.Load()
	return acc
}

// Load 加载数据
func (a *PaperAccount) Load() {
	// 加载交易记录
	if data, err := os.ReadFile(a.tradeFile); err == nil {
		json.Unmarshal(data, &a.Trades)
	}
	
	// 加载持仓
	if data, err := os.ReadFile(a.positionFile); err == nil {
		var positions map[string]*Position
		if err := json.Unmarshal(data, &positions); err == nil {
			a.Positions = positions
		}
	}
	
	// 重建现金（从交易记录计算）
	a.Capital = a.InitialCapital - CashReserve
	for _, t := range a.Trades {
		if t.Action == "BUY" {
			a.Capital -= t.Amount
		} else {
			a.Capital += t.Amount
		}
	}
	
	// 清理已平仓的持仓记录
	for _, t := range a.Trades {
		if t.Action == "SELL" {
			delete(a.Positions, t.Code)
		}
	}
}

// Save 保存数据
func (a *PaperAccount) Save() {
	// 保存交易记录
	data, _ := json.MarshalIndent(a.Trades, "", "  ")
	os.WriteFile(a.tradeFile, data, 0644)
	
	// 保存持仓
	data, _ = json.MarshalIndent(a.Positions, "", "  ")
	os.WriteFile(a.positionFile, data, 0644)
	
	// 保存统计
	stats := a.GetStats()
	data, _ = json.MarshalIndent(stats, "", "  ")
	os.WriteFile(a.statsFile, data, 0644)
}

// GetStats 获取账户统计
func (a *PaperAccount) GetStats() *AccountStats {
	stats := &AccountStats{
		InitialCapital: a.InitialCapital,
		CurrentCapital: a.Capital,
		CurrentPos:     len(a.Positions),
	}
	
	// 计算持仓市值
	positionsValue := 0.0
	for _, pos := range a.Positions {
		positionsValue += pos.AvgCost * float64(pos.Shares)
	}
	stats.PositionsValue = positionsValue
	stats.TotalValue = a.Capital + positionsValue
	stats.ReturnRate = (stats.TotalValue - a.InitialCapital) / a.InitialCapital * 100
	
	// 统计已平仓交易
	var wins, losses, totalPnL, totalWin, totalLoss float64
	for _, t := range a.Trades {
		if t.Action == "SELL" && t.PnL != 0 {
			totalPnL += t.PnL
			if t.PnL > 0 {
				wins++
				totalWin += t.PnL
			} else {
				losses++
				totalLoss += math.Abs(t.PnL)
			}
		}
	}
	
	stats.TotalTrades = int(wins + losses)
	stats.Wins = int(wins)
	stats.Losses = int(losses)
	stats.TotalPnL = totalPnL
	if wins+losses > 0 {
		stats.WinRate = wins / (wins + losses) * 100
	}
	if wins > 0 {
		stats.AvgWin = totalWin / wins
	}
	if losses > 0 {
		stats.AvgLoss = totalLoss / losses
	}
	
	return stats
}

// PrintStatus 打印账户状态
func (a *PaperAccount) PrintStatus() {
	stats := a.GetStats()
	
	arrow := "↑"
	if stats.ReturnRate < 0 {
		arrow = "↓"
	}
	
	fmt.Printf(`
╔══════════════════════════════════════════════════════════════╗
║  📊 模拟账户状态                                           ║
╠══════════════════════════════════════════════════════════════╣
║  现金: ¥%.0f | 总资产: ¥%.0f (%s%.1f%%)                  ║
║  交易: %d笔(胜%d/负%d) | 胜率%.0f%%                          ║
║  盈亏: ¥%.0f | 均盈¥%.0f | 均亏¥%.0f                        ║
╠══════════════════════════════════════════════════════════════╣
║  📋 持仓 %d/%d                                              ║`, 
		stats.CurrentCapital, stats.TotalValue, arrow, stats.ReturnRate,
		stats.TotalTrades, stats.Wins, stats.Losses, stats.WinRate,
		stats.TotalPnL, stats.AvgWin, stats.AvgLoss,
		stats.CurrentPos, MaxPositions)
	
	if len(a.Positions) == 0 {
		fmt.Println("║  (空仓)                                                   ║")
	} else {
		for _, pos := range a.Positions {
			fmt.Printf("║  • %s %s: %d股@¥%.2f                                     ║\n", 
				pos.Code, pos.Name, pos.Shares, pos.AvgCost)
		}
	}
	fmt.Println("╚══════════════════════════════════════════════════════════════╝")
}

// ========== 交易操作 ==========

// Buy 买入
func (a *PaperAccount) Buy(code, name string, price float64, shares int, reason string, rsi float64) error {
	date := time.Now().Format("2006-01-02")
	
	// 检查持仓数量限制
	if len(a.Positions) >= MaxPositions {
		return fmt.Errorf("⚠️ 持仓已满 (%d只)", MaxPositions)
	}
	
	// 检查是否已有持仓
	if _, exists := a.Positions[code]; exists {
		return fmt.Errorf("⚠️ %s 已在持仓中", code)
	}
	
	// 计算最大可买股数
	amount := price * float64(shares)
	maxAmount := a.Capital - CashReserve
	if amount > maxAmount {
		shares = int(maxAmount/price/100) * 100
		amount = price * float64(shares)
	}
	
	if shares < 100 {
		return fmt.Errorf("⚠️ 资金不足，可用 ¥%.0f", a.Capital-CashReserve)
	}
	
	// 创建持仓
	pos := &Position{
		Code:        code,
		Name:        name,
		Shares:      shares,
		AvgCost:     price,
		StopLoss:    round(price*(1-StopLoss), 2),
		TakeProfit1: round(price*(1+TakeProfit1), 2),
		TakeProfit2: round(price*(1+TakeProfit2), 2),
		EntryDate:   date,
		Reason:      reason,
		RSI:         rsi,
		StopMoved:   false,
	}
	
	// 记录交易
	trade := &TradeRecord{
		ID:        len(a.Trades) + 1,
		Date:      date,
		Action:    "BUY",
		Code:      code,
		Name:      name,
		Price:     price,
		Shares:    shares,
		Amount:    amount,
		Reason:    reason,
		CashAfter: a.Capital - amount,
	}
	
	a.Capital -= amount
	a.Positions[code] = pos
	a.Trades = append(a.Trades, trade)
	a.Save()
	
	fmt.Printf("✅ 买入 %s %s ¥%.2f×%d股=¥%.0f\n", code, name, price, shares, amount)
	fmt.Printf("   止损 ¥%.2f | 止盈1 ¥%.2f | 止盈2 ¥%.2f\n", pos.StopLoss, pos.TakeProfit1, pos.TakeProfit2)
	
	return nil
}

// Sell 卖出
func (a *PaperAccount) Sell(code string, price float64, reason string) error {
	pos, exists := a.Positions[code]
	if !exists {
		return fmt.Errorf("⚠️ %s 不在持仓中", code)
	}
	
	date := time.Now().Format("2006-01-02")
	shares := pos.Shares
	avgCost := pos.AvgCost
	amount := price * float64(shares)
	pnl := amount - (avgCost * float64(shares))
	pnlPct := (price - avgCost) / avgCost * 100
	
	// 计算持有天数
	entryDate, _ := time.Parse("2006-01-02", pos.EntryDate)
	sellDate, _ := time.Parse("2006-01-02", date)
	holdDays := int(sellDate.Sub(entryDate).Hours() / 24)
	
	// 记录交易
	trade := &TradeRecord{
		ID:       len(a.Trades) + 1,
		Date:     date,
		Action:   "SELL",
		Code:     code,
		Name:     pos.Name,
		Price:    price,
		Shares:   shares,
		Amount:   amount,
		AvgCost:  avgCost,
		PnL:      round(pnl, 2),
		PnLPct:   round(pnlPct, 2),
		Reason:   reason,
		HoldDays: holdDays,
		CashAfter: a.Capital + amount,
	}
	
	a.Capital += amount
	delete(a.Positions, code)
	a.Trades = append(a.Trades, trade)
	a.Save()
	
	emoji := "🟢"
	if pnl < 0 {
		emoji = "🔴"
	}
	fmt.Printf("%s 卖出 %s %s ¥%.2f %s¥%.0f(%.1f%%) 持%d天 [%s]\n", 
		emoji, code, pos.Name, price, emoji, pnl, pnlPct, holdDays, reason)
	
	return nil
}

// CheckPositions 检查持仓，触发止损止盈
func (a *PaperAccount) CheckPositions(prices map[string]float64) {
	for code, pos := range a.Positions {
		currentPrice, exists := prices[code]
		if !exists {
			continue
		}
		
		pnlPct := (currentPrice - pos.AvgCost) / pos.AvgCost * 100
		
		// 止损检查
		if currentPrice <= pos.StopLoss {
			a.Sell(code, currentPrice, fmt.Sprintf("止损(%.1f%%)", pnlPct))
			continue
		}
		
		// 止盈2检查
		if pnlPct >= TakeProfit2*100 {
			a.Sell(code, currentPrice, fmt.Sprintf("止盈2(%.1f%%)", pnlPct))
			continue
		}
		
		// 止盈1检查（盈利5%以上，概率触发）
		if pnlPct >= TakeProfit1*100 {
			a.Sell(code, currentPrice, fmt.Sprintf("止盈1(%.1f%%)", pnlPct))
			continue
		}
		
		// 移动止损检查（盈利>5%后，止损线移到成本价）
		if pnlPct > TakeProfit1*100 && !pos.StopMoved {
			pos.StopLoss = pos.AvgCost * (1 - StopLossMove)
			pos.StopMoved = true
			a.Save()
			fmt.Printf("📈 %s 移动止损到 ¥%.2f\n", code, pos.StopLoss)
		}
	}
}

// PrintTrades 打印交易记录
func (a *PaperAccount) PrintTrades(limit int) {
	if limit <= 0 {
		limit = 20
	}
	
	fmt.Println("\n📋 交易记录：")
	fmt.Println("────────────────────────────────────────────────────────────")
	
	trades := a.Trades
	if len(trades) > limit {
		trades = trades[len(trades)-limit:]
	}
	
	for _, t := range trades {
		if t.Action == "BUY" {
			fmt.Printf("🟢 %s 买入 %s %s ¥%.2f×%d\n", t.Date, t.Code, t.Name, t.Price, t.Shares)
		} else {
			emoji := "🟢"
			if t.PnL < 0 {
				emoji = "🔴"
			}
			fmt.Printf("%s %s 卖出 %s ¥%.2f %s¥%.0f(%.1f%%) 持%d天\n", 
				emoji, t.Date, t.Code, t.Price, emoji, t.PnL, t.PnLPct, t.HoldDays)
		}
	}
	fmt.Println("────────────────────────────────────────────────────────────")
	fmt.Printf("共 %d 笔交易\n", len(a.Trades))
}

// Reset 重置账户
func (a *PaperAccount) Reset() {
	a.Capital = a.InitialCapital - CashReserve
	a.Positions = make(map[string]*Position)
	a.Trades = []*TradeRecord{}
	a.Save()
	fmt.Println("✅ 账户已重置")
}

// ========== 辅助函数 ==========

func round(val float64, precision int) float64 {
	round := math.Pow(10, float64(precision))
	return math.Round(val*round) / round
}

func getProjectRoot() string {
	// 向上查找 go.mod 所在目录
	dir, _ := os.Getwd()
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return dir
		}
		dir = parent
	}
}