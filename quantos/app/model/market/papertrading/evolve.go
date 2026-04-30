package papertrading

import (
	"context"
	"fmt"
	"math"
	"sort"
	"time"
)

// ========== 进化分析数据结构 ==========

// RSIAnalysis RSI区间分析
type RSIAnalysis struct {
	RSIRange    string  `json:"rsi_range"`    // RSI区间
	TradeCount  int     `json:"trade_count"`   // 交易次数
	WinCount    int     `json:"win_count"`    // 盈利次数
	WinRate     float64 `json:"win_rate"`     // 胜率
	AvgWin      float64 `json:"avg_win"`      // 平均盈利
	AvgLoss     float64 `json:"avg_loss"`     // 平均亏损
	ProfitFactor float64 `json:"profit_factor"` // 盈亏比
	TotalPnL    float64 `json:"total_pnl"`    // 总盈亏
}

// PerformanceReport 表现报告
type PerformanceReport struct {
	TotalTrades      int             `json:"total_trades"`       // 总交易数
	WinTrades        int             `json:"win_trades"`        // 盈利交易数
	LoseTrades       int             `json:"lose_trades"`       // 亏损交易数
	WinRate          float64         `json:"win_rate"`          // 胜率
	TotalPnL         float64         `json:"total_pnl"`         // 总盈亏
	AvgWin           float64         `json:"avg_win"`           // 平均盈利
	AvgLoss          float64         `json:"avg_loss"`          // 平均亏损
	ProfitFactor     float64         `json:"profit_factor"`     // 盈亏比
	MaxWin           float64         `json:"max_win"`           // 最大单笔盈利
	MaxLoss          float64         `json:"max_loss"`          // 最大单笔亏损
	AvgHoldDays      float64         `json:"avg_hold_days"`     // 平均持仓天数
	BestTrade        *PaperTrade     `json:"best_trade"`        // 最佳交易
	WorstTrade       *PaperTrade     `json:"worst_trade"`       // 最差交易
	RSIAnalysisList   []*RSIAnalysis  `json:"rsi_analysis"`      // RSI区间分析
	StartDate        string          `json:"start_date"`        // 开始日期
	EndDate          string          `json:"end_date"`          // 结束日期
	Days             int             `json:"days"`              // 交易天数
}

// OptimizationSuggestion 优化建议
type OptimizationSuggestion struct {
	ParamKey   string  `json:"param_key"`   // 参数键
	OldValue   float64 `json:"old_value"`   // 原值
	NewValue   float64 `json:"new_value"`   // 新值
	Reason     string  `json:"reason"`      // 原因
	Confidence float64 `json:"confidence"`  // 置信度
	Priority   int     `json:"priority"`    // 优先级 1-5
}

// EvolutionResult 进化结果
type EvolutionResult struct {
	Timestamp      time.Time                 `json:"timestamp"`
	Improvements  []*OptimizationSuggestion `json:"improvements"`
	Analysis       *PerformanceReport       `json:"analysis"`
	Summary        string                   `json:"summary"`
	StatsUpdated   bool                     `json:"stats_updated"`
}

// ========== 自主进化系统 ==========

// EvolutionSystem 自主进化系统
type EvolutionSystem struct {
	db     *PaperTradingDB
	trades []*PaperTrade
}

// NewEvolutionSystem 创建进化系统
func NewEvolutionSystem(db *PaperTradingDB) *EvolutionSystem {
	return &EvolutionSystem{db: db}
}

// LoadTrades 加载交易数据
func (e *EvolutionSystem) LoadTrades(ctx context.Context, accountID uint64) error {
	var err error
	e.trades, err = e.db.GetClosedTrades(ctx, accountID)
	return err
}

// AnalyzePerformance 分析历史表现
func (e *EvolutionSystem) AnalyzePerformance(ctx context.Context, accountID uint64) (*PerformanceReport, error) {
	if err := e.LoadTrades(ctx, accountID); err != nil {
		return nil, err
	}

	if len(e.trades) == 0 {
		return &PerformanceReport{
			TotalTrades: 0,
			StartDate:   time.Now().Format("2006-01-02"),
			EndDate:     time.Now().Format("2006-01-02"),
		}, nil
	}

	report := &PerformanceReport{
		TotalTrades: len(e.trades),
		RSIAnalysisList: make([]*RSIAnalysis, 0),
	}

	var totalPnL, totalWin, totalLoss float64
	var maxWin, maxLoss float64 = math.Inf(-1), math.Inf(1)
	var totalHoldDays float64
	var winTrades, loseTrades int

	report.StartDate = e.trades[len(e.trades)-1].TradeDate
	report.EndDate = e.trades[0].TradeDate

	// 按RSI区间分组统计
	rsiBuckets := map[string]*RSIAnalysis{
		"30-40": {RSIRange: "30-40"},
		"40-50": {RSIRange: "40-50"},
		"50-60": {RSIRange: "50-60"},
		"60-70": {RSIRange: "60-70"},
		"70+":   {RSIRange: "70+"},
	}

	for _, t := range e.trades {
		report.TotalPnL += t.Pnl

		if t.Pnl > 0 {
			winTrades++
			totalWin += t.Pnl
			if t.Pnl > maxWin {
				maxWin = t.Pnl
				report.BestTrade = t
			}
		} else if t.Pnl < 0 {
			loseTrades++
			totalLoss += math.Abs(t.Pnl)
			if t.Pnl < maxLoss {
				maxLoss = t.Pnl
				report.WorstTrade = t
			}
		}

		totalHoldDays += float64(t.HoldDays)

		// 分配RSI区间
		rsi := t.AvgCost // 这里用成本价暂代，实际应从入场记录获取
		// 根据盈亏反推RSI
		bucket := getRSIBucket(rsi)
		if bucket == "" {
			bucket = "50-60" // 默认
		}
		if _, ok := rsiBuckets[bucket]; ok {
			rsiBuckets[bucket].TradeCount++
			rsiBuckets[bucket].TotalPnL += t.Pnl
			if t.Pnl > 0 {
				rsiBuckets[bucket].WinCount++
				rsiBuckets[bucket].AvgWin += t.Pnl
			} else {
				rsiBuckets[bucket].AvgLoss += math.Abs(t.Pnl)
			}
		}
	}

	report.WinTrades = winTrades
	report.LoseTrades = loseTrades
	report.TotalPnL = totalPnL
	report.MaxWin = maxWin
	report.MaxLoss = maxLoss
	report.AvgHoldDays = totalHoldDays / float64(len(e.trades))

	if winTrades > 0 {
		report.WinRate = float64(winTrades) / float64(len(e.trades)) * 100
		report.AvgWin = totalWin / float64(winTrades)
	}
	if loseTrades > 0 {
		report.AvgLoss = totalLoss / float64(loseTrades)
	}
	if report.AvgLoss > 0 {
		report.ProfitFactor = report.AvgWin / report.AvgLoss
	}

	// 计算RSI区间统计
	for _, bucket := range rsiBuckets {
		if bucket.TradeCount > 0 {
			if bucket.WinCount > 0 {
				bucket.AvgWin /= float64(bucket.WinCount)
				bucket.WinRate = float64(bucket.WinCount) / float64(bucket.TradeCount) * 100
			}
			if bucket.TradeCount-bucket.WinCount > 0 {
				bucket.AvgLoss /= float64(bucket.TradeCount - bucket.WinCount)
			}
			if bucket.AvgLoss > 0 {
				bucket.ProfitFactor = bucket.AvgWin / bucket.AvgLoss
			}
			report.RSIAnalysisList = append(report.RSIAnalysisList, bucket)
		}
	}

	// 按胜率排序
	sort.Slice(report.RSIAnalysisList, func(i, j int) bool {
		return report.RSIAnalysisList[i].WinRate > report.RSIAnalysisList[j].WinRate
	})

	// 计算天数
	start, _ := time.Parse("2006-01-02", report.StartDate)
	end, _ := time.Parse("2006-01-02", report.EndDate)
	report.Days = int(end.Sub(start).Hours()/24) + 1

	return report, nil
}

// OptimizeParams 基于分析结果优化参数
func (e *EvolutionSystem) OptimizeParams(ctx context.Context, accountID uint64) ([]*OptimizationSuggestion, error) {
	report, err := e.AnalyzePerformance(ctx, accountID)
	if err != nil {
		return nil, err
	}

	suggestions := make([]*OptimizationSuggestion, 0)

	if len(e.trades) < 5 {
		suggestions = append(suggestions, &OptimizationSuggestion{
			ParamKey:   "rsi_min",
			OldValue:   35,
			NewValue:   35,
			Reason:     "交易样本不足，需要至少5笔交易才能进行有效优化",
			Confidence: 0,
			Priority:   1,
		})
		return suggestions, nil
	}

	// 分析RSI区间，找出最佳区间
	var bestRSIBucket *RSIAnalysis
	for _, bucket := range report.RSIAnalysisList {
		if bucket.TradeCount >= 2 {
			if bestRSIBucket == nil || bucket.WinRate > bestRSIBucket.WinRate {
				bestRSIBucket = bucket
			}
		}
	}

	if bestRSIBucket != nil {
		// RSI下限优化
		switch bestRSIBucket.RSIRange {
		case "30-40":
			suggestions = append(suggestions, &OptimizationSuggestion{
				ParamKey:   "rsi_min",
				OldValue:   35,
				NewValue:   30,
				Reason:     fmt.Sprintf("RSI 30-40 区间胜率 %.1f%% 最高，建议扩大下限到30", bestRSIBucket.WinRate),
				Confidence: 0.7,
				Priority:   2,
			})
		case "40-50":
			suggestions = append(suggestions, &OptimizationSuggestion{
				ParamKey:   "rsi_min",
				OldValue:   35,
				NewValue:   40,
				Reason:     fmt.Sprintf("RSI 40-50 区间胜率 %.1f%% 最高，建议调整下限到40", bestRSIBucket.WinRate),
				Confidence: 0.8,
				Priority:   2,
			})
		case "50-60":
			suggestions = append(suggestions, &OptimizationSuggestion{
				ParamKey:   "rsi_min",
				OldValue:   35,
				NewValue:   50,
				Reason:     fmt.Sprintf("RSI 50-60 区间胜率 %.1f%% 最高，建议调整下限到50", bestRSIBucket.WinRate),
				Confidence: 0.85,
				Priority:   1,
			})
		case "60-70", "70+":
			suggestions = append(suggestions, &OptimizationSuggestion{
				ParamKey:   "rsi_min",
				OldValue:   35,
				NewValue:   55,
				Reason:     fmt.Sprintf("高RSI区间(>%d)胜率 %.1f%% 最高，建议提高选股RSI下限", 60, bestRSIBucket.WinRate),
				Confidence: 0.75,
				Priority:   2,
			})
		}
	}

	// 盈亏比分析
	if report.ProfitFactor > 0 && report.ProfitFactor < 1.5 {
		suggestions = append(suggestions, &OptimizationSuggestion{
			ParamKey:   "stop_loss",
			OldValue:   StopLoss,
			NewValue:   StopLoss * 0.8,
			Reason:     fmt.Sprintf("盈亏比 %.2f 偏低，建议收紧止损到 %.1f%%", report.ProfitFactor, StopLoss*0.8*100),
			Confidence: 0.6,
			Priority:   3,
		})
	} else if report.ProfitFactor > 2.0 {
		suggestions = append(suggestions, &OptimizationSuggestion{
			ParamKey:   "take_profit1",
			OldValue:   TakeProfit1,
			NewValue:   TakeProfit1 * 1.2,
			Reason:     fmt.Sprintf("盈亏比 %.2f 优秀，建议提高止盈目标到 %.1f%%", report.ProfitFactor, TakeProfit1*1.2*100),
			Confidence: 0.7,
			Priority:   3,
		})
	}

	// 持仓天数分析
	if report.AvgHoldDays < 5 {
		suggestions = append(suggestions, &OptimizationSuggestion{
			ParamKey:   "max_hold_days",
			OldValue:   0,
			NewValue:   10,
			Reason:     fmt.Sprintf("平均持仓仅 %.1f 天，可能过于激进，建议设定最大持仓天数限制", report.AvgHoldDays),
			Confidence: 0.5,
			Priority:   4,
		})
	}

	// 胜率分析
	if report.WinRate < 40 {
		suggestions = append(suggestions, &OptimizationSuggestion{
			ParamKey:   "rsi_max",
			OldValue:   65,
			NewValue:   60,
			Reason:     fmt.Sprintf("胜率 %.1f%% 偏低，建议降低RSI上限到60避免追高", report.WinRate),
			Confidence: 0.65,
			Priority:   2,
		})
	} else if report.WinRate > 60 {
		suggestions = append(suggestions, &OptimizationSuggestion{
			ParamKey:   "position_size",
			OldValue:   MaxPosition,
			NewValue:   MaxPosition * 1.2,
			Reason:     fmt.Sprintf("胜率 %.1f%% 优秀，可适当增加仓位", report.WinRate),
			Confidence: 0.6,
			Priority:   4,
		})
	}

	return suggestions, nil
}

// SelfUpdate 执行自主更新
func (e *EvolutionSystem) SelfUpdate(ctx context.Context, accountID uint64) (*EvolutionResult, error) {
	result := &EvolutionResult{
		Timestamp:     time.Now(),
		Improvements:  make([]*OptimizationSuggestion, 0),
	}

	// 1. 分析表现
	report, err := e.AnalyzePerformance(ctx, accountID)
	if err != nil {
		return nil, fmt.Errorf("分析失败: %w", err)
	}
	result.Analysis = report

	// 2. 生成优化建议
	suggestions, err := e.OptimizeParams(ctx, accountID)
	if err != nil {
		return nil, fmt.Errorf("优化失败: %w", err)
	}
	result.Improvements = suggestions

	// 3. 更新策略参数到数据库
	for _, s := range suggestions {
		if s.Confidence >= 0.7 {
			// 高置信度建议自动应用
			oldParams, _ := e.db.GetStrategyParams(ctx, s.ParamKey)
			oldValue := s.OldValue
			if oldParams != nil {
				oldValue = oldParams.ParamValue
			}

			// 记录进化历史
			evolutionLog := &EvolutionLog{
				ParamKey:   s.ParamKey,
				OldValue:   oldValue,
				NewValue:   s.NewValue,
				Reason:     s.Reason,
				OldWinRate: report.WinRate,
				NewWinRate: report.WinRate, // 预测值相同
			}
			e.db.CreateEvolutionLog(ctx, evolutionLog)

			// 更新参数
			e.db.UpdateStrategyParams(ctx, s.ParamKey, s.NewValue, report.WinRate, report.AvgWin, report.AvgLoss, report.TotalTrades)
			result.StatsUpdated = true

			// 修改成功标记
			s.OldValue = oldValue
		}
	}

	// 4. 生成总结
	result.Summary = e.generateSummary(report, suggestions)

	return result, nil
}

// GetSuggestions 获取优化建议（不执行更新）
func (e *EvolutionSystem) GetSuggestions(ctx context.Context, accountID uint64) ([]*OptimizationSuggestion, error) {
	return e.OptimizeParams(ctx, accountID)
}

// ========== 辅助函数 ==========

// getRSIBucket 根据RSI值确定区间
func getRSIBucket(rsi float64) string {
	switch {
	case rsi < 30:
		return "30-40" // 暂用30-40代表超卖
	case rsi < 40:
		return "30-40"
	case rsi < 50:
		return "40-50"
	case rsi < 60:
		return "50-60"
	case rsi < 70:
		return "60-70"
	default:
		return "70+"
	}
}

// generateSummary 生成进化总结
func (e *EvolutionSystem) generateSummary(report *PerformanceReport, suggestions []*OptimizationSuggestion) string {
	summary := fmt.Sprintf("\n📊 进化分析报告 (%s ~ %s)\n", report.StartDate, report.EndDate)
	summary += fmt.Sprintf("───────────────────────────────────────────────\n")
	summary += fmt.Sprintf("总交易: %d笔 | 胜率: %.1f%% | 盈亏比: %.2f\n", report.TotalTrades, report.WinRate, report.ProfitFactor)
	summary += fmt.Sprintf("总盈亏: ¥%.2f | 均盈: ¥%.2f | 均亏: ¥%.2f\n", report.TotalPnL, report.AvgWin, report.AvgLoss)
	summary += fmt.Sprintf("───────────────────────────────────────────────\n")

	if len(report.RSIAnalysisList) > 0 {
		summary += "📈 RSI区间分析:\n"
		for _, rsi := range report.RSIAnalysisList {
			if rsi.TradeCount > 0 {
				summary += fmt.Sprintf("  RSI %s: %d笔 | 胜率%.1f%% | 盈亏比%.2f\n",
					rsi.RSIRange, rsi.TradeCount, rsi.WinRate, rsi.ProfitFactor)
			}
		}
		summary += "\n"
	}

	if len(suggestions) > 0 {
		summary += "🔧 优化建议:\n"
		for i, s := range suggestions {
			summary += fmt.Sprintf("  %d. [%s] %s: %.2f → %.2f\n     %s\n     置信度: %.0f%%\n",
				i+1, s.ParamKey, s.Reason, s.OldValue, s.NewValue, s.Reason, s.Confidence*100)
		}
	} else {
		summary += "✅ 策略表现良好，暂无需优化\n"
	}

	return summary
}

// PrintEvolutionResult 打印进化结果
func PrintEvolutionResult(result *EvolutionResult) {
	fmt.Println(result.Summary)

	if result.StatsUpdated {
		fmt.Println("\n✅ 策略参数已自动更新到数据库")
	} else {
		fmt.Println("\n📝 可选: 使用 paper evolve -apply 应用优化建议")
	}
}

// PrintPerformanceReport 打印表现报告
func PrintPerformanceReport(report *PerformanceReport) {
	fmt.Println("\n📊 交易表现报告")
	fmt.Println("───────────────────────────────────────────────")
	fmt.Printf("统计周期: %s ~ %s (共%d天)\n", report.StartDate, report.EndDate, report.Days)
	fmt.Printf("总交易: %d笔 | 盈利: %d笔 | 亏损: %d笔\n", report.TotalTrades, report.WinTrades, report.LoseTrades)
	fmt.Printf("胜率: %.1f%% | 盈亏比: %.2f\n", report.WinRate, report.ProfitFactor)
	fmt.Printf("总盈亏: ¥%.2f | 均盈: ¥%.2f | 均亏: ¥%.2f\n", report.TotalPnL, report.AvgWin, report.AvgLoss)
	fmt.Printf("最大单笔盈利: ¥%.2f | 最大单笔亏损: ¥%.2f\n", report.MaxWin, report.MaxLoss)
	fmt.Printf("平均持仓天数: %.1f天\n", report.AvgHoldDays)

	if report.BestTrade != nil {
		fmt.Printf("\n🏆 最佳交易: %s %s 盈利¥%.2f(%.1f%%)\n",
			report.BestTrade.Symbol, report.BestTrade.SymbolName, report.BestTrade.Pnl, report.BestTrade.PnlPct)
	}
	if report.WorstTrade != nil {
		fmt.Printf("💔 最差交易: %s %s 亏损¥%.2f(%.1f%%)\n",
			report.WorstTrade.Symbol, report.WorstTrade.SymbolName, report.WorstTrade.Pnl, report.WorstTrade.PnlPct)
	}

	if len(report.RSIAnalysisList) > 0 {
		fmt.Println("\n📈 RSI区间分析:")
		fmt.Println("───────────────────────────────────────────────")
		fmt.Printf("%-10s %-8s %-8s %-10s %-10s %-10s\n", "RSI区间", "交易数", "胜率", "均盈", "均亏", "盈亏比")
		for _, rsi := range report.RSIAnalysisList {
			if rsi.TradeCount > 0 {
				fmt.Printf("%-10s %-8d %-8.1f%% %-10.2f %-10.2f %-10.2f\n",
					rsi.RSIRange, rsi.TradeCount, rsi.WinRate, rsi.AvgWin, rsi.AvgLoss, rsi.ProfitFactor)
			}
		}
	}
	fmt.Println("───────────────────────────────────────────────")
}

// PrintSuggestions 打印优化建议
func PrintSuggestions(suggestions []*OptimizationSuggestion) {
	if len(suggestions) == 0 {
		fmt.Println("✅ 暂无优化建议，策略表现良好！")
		return
	}

	fmt.Println("\n🔧 优化建议:")
	fmt.Println("───────────────────────────────────────────────")
	for i, s := range suggestions {
		priority := ""
		switch s.Priority {
		case 1:
			priority = "🔴 高"
		case 2:
			priority = "🟡 中"
		case 3:
			priority = "🟢 低"
		default:
			priority = "⚪ 建议"
		}

		arrow := "→"
		if s.NewValue > s.OldValue {
			arrow = "↑"
		} else if s.NewValue < s.OldValue {
			arrow = "↓"
		}

		fmt.Printf("%d. [%s] %s\n", i+1, priority, s.ParamKey)
		fmt.Printf("   值: %.4f %s %.4f\n", s.OldValue, arrow, s.NewValue)
		fmt.Printf("   原因: %s\n", s.Reason)
		fmt.Printf("   置信度: %.0f%%\n", s.Confidence*100)
	}
	fmt.Println("───────────────────────────────────────────────")
}
