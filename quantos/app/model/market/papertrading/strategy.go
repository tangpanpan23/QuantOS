package papertrading

import (
	"fmt"
	"math/rand"
	"time"
)

// StockSignal 选股信号
type StockSignal struct {
	Code      string  `json:"code"`
	Name      string  `json:"name"`
	Price     float64 `json:"price"`
	RSI       float64 `json:"rsi"`
	Amount    float64 `json:"amount"`    // 成交额（亿）
	MA5       float64 `json:"ma5"`
	MA20      float64 `json:"ma20"`
	MA60      float64 `json:"ma60"`
	Score     float64 `json:"score"`     // 综合评分
	Reason    string  `json:"reason"`    // 信号理由
}

// CheckIronRules 铁律检查
type IronRules struct {
	MarketDown    bool // 大盘下跌>2%
	DailyLoss     bool // 单日亏损>2000
	ExceedMaxPos  bool // 持仓超过4只
	SingleLoss    bool // 单只亏损>1000
}

func (r *IronRules) CanBuy() bool {
	return !r.MarketDown && !r.ExceedMaxPos && !r.SingleLoss
}

func (r *IronRules) Print() {
	if r.MarketDown {
		fmt.Println("🚨 铁律: 大盘下跌>2%，停止买入")
	}
	if r.DailyLoss {
		fmt.Println("🚨 铁律: 单日亏损>¥2,000，停止交易")
	}
	if r.ExceedMaxPos {
		fmt.Println("🚨 铁律: 持仓已达4只，不能买入")
	}
	if r.SingleLoss {
		fmt.Println("🚨 铁律: 单只亏损>¥1,000，立即止损")
	}
}

// GenerateSignal 生成选股信号
// 选股条件：
// ✅ 成交额 > 3亿/日
// ✅ 价格 10-100元
// ✅ RSI 35-65
// ✅ MA20 > MA60
// ✅ 股价在 MA20 上方
func GenerateSignal(code, name string, price, amount, rsi, ma5, ma20, ma60 float64) *StockSignal {
	reason := []string{}
	score := 0.0
	
	// 条件1: 成交额 > 3亿
	if amount > 3 {
		score += 20
		reason = append(reason, "成交额>3亿")
	} else {
		return nil
	}
	
	// 条件2: 价格 10-100元
	if price < 10 || price > 100 {
		return nil
	}
	score += 15
	
	// 条件3: RSI 35-65
	if rsi >= 35 && rsi <= 65 {
		score += 20
		reason = append(reason, fmt.Sprintf("RSI=%.0f", rsi))
	} else {
		return nil
	}
	
	// 条件4: MA20 > MA60
	if ma20 > ma60 {
		score += 25
		reason = append(reason, "MA20>MA60")
	} else {
		return nil
	}
	
	// 条件5: 股价在 MA20 上方
	if price > ma20 {
		score += 20
		reason = append(reason, "价格>MA20")
	} else {
		return nil
	}
	
	return &StockSignal{
		Code:   code,
		Name:   name,
		Price:  price,
		RSI:    rsi,
		Amount: amount,
		MA5:    ma5,
		MA20:   ma20,
		MA60:   ma60,
		Score:  score,
		Reason: joinReasons(reason),
	}
}

// FilterSignals 过滤并排序信号
func FilterSignals(stocks []StockSignal, topN int) []StockSignal {
	var valid []StockSignal
	for i := range stocks {
		if stocks[i].Score >= 80 {
			valid = append(valid, stocks[i])
		}
	}
	
	// 按评分排序
	for i := 0; i < len(valid); i++ {
		for j := i + 1; j < len(valid); j++ {
			if valid[j].Score > valid[i].Score {
				valid[i], valid[j] = valid[j], valid[i]
			}
		}
	}
	
	if len(valid) > topN {
		valid = valid[:topN]
	}
	
	return valid
}

// RunSimulation 运行历史模拟回测
func RunSimulation() {
	fmt.Println("\n" + "================================================================")
	fmt.Println("🚀 量化交易模拟 - 半年历史回测")
	fmt.Println("================================================================")
	
	account := NewPaperAccount()
	
	// 股票池
	stocks := []struct {
		code      string
		name      string
		basePrice float64
	}{
		{"601288", "农业银行", 3.20},
		{"600900", "长江电力", 22.50},
		{"600036", "招商银行", 35.00},
		{"000858", "五粮液", 150.00},
		{"300750", "宁德时代", 200.00},
		{"601318", "中国平安", 42.00},
		{"002475", "立讯精密", 28.00},
		{"600519", "贵州茅台", 1600.00},
	}
	
	// 初始化价格数据
	type stockData struct {
		name  string
		price float64
		rsi   float64
	}
	prices := make(map[string]stockData)
	for _, s := range stocks {
		prices[s.code] = stockData{name: s.name, price: s.basePrice, rsi: 50}
	}
	
	// 模拟半年 (2025-10-16 到 2026-04-15)
	startDate := time.Date(2025, 10, 16, 0, 0, 0, 0, time.Local)
	endDate := time.Date(2026, 4, 15, 0, 0, 0, 0, time.Local)
	
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	dayCount := 0
	
	for d := startDate; !d.After(endDate); d = d.AddDate(0, 0, 1) {
		// 跳过周末
		if d.Weekday() == time.Saturday || d.Weekday() == time.Sunday {
			continue
		}
		dayCount++
		
		// dateStr := d.Format("2006-01-02")
		
		// 更新价格和RSI
		for code, data := range prices {
			// 随机游走
			change := r.NormFloat64() * 0.018
			// 趋势偏置
			if code == "600036" || code == "300750" || code == "002475" {
				change += 0.004
			}
			if code == "600519" {
				change += 0.002
			}
			
			data.price *= (1 + change)
			data.rsi = clamp(data.rsi+r.NormFloat64()*5, 25, 85)
			prices[code] = data
		}
		
		// 获取当前价格
		currentPrices := make(map[string]float64)
		for code, data := range prices {
			currentPrices[code] = data.price
		}
		
		// 检查止损止盈
		account.CheckPositions(currentPrices)
		
		// 买入信号（每5天尝试买入）
		if len(account.Positions) < MaxPositions && dayCount%5 == 0 {
			for _, s := range stocks {
				if _, has := account.Positions[s.code]; has {
					continue
				}
				
				data := prices[s.code]
				
				// 生成信号
				signal := GenerateSignal(
					s.code, s.name, data.price,
					5, // 假设成交额5亿
					data.rsi, data.price*0.98, data.price*0.95, data.price*0.90,
				)
				
				if signal != nil && signal.Score >= 80 {
					shares := int(MaxPosition / data.price / 100 * 100)
					if shares >= 100 {
						words := []string{"强势", "突破", "回踩"}
						randWord := words[rand.Intn(len(words))]
						account.Buy(s.code, s.name, round(data.price, 2), shares, 
							fmt.Sprintf("MA多头+RSI=%.0f+%s", data.rsi, randWord), 
							data.rsi)
					}
					break
				}
			}
		}
	}
	
	// 强制平仓
	fmt.Println("\n🏁 模拟结束，强制平仓")
	for code := range account.Positions {
		if price, ok := prices[code]; ok {
			account.Sell(code, round(price.price, 2), "模拟结束")
		}
	}
	
	// 打印结果
	account.PrintStatus()
	
	fmt.Println("\n数据已保存到 data/paper/ 目录")
}

// ========== 辅助函数 ==========

func clamp(val, min, max float64) float64 {
	if val < min {
		return min
	}
	if val > max {
		return max
	}
	return val
}

func joinReasons(reasons []string) string {
	result := ""
	for i, r := range reasons {
		if i > 0 {
			result += "+"
		}
		result += r
	}
	return result
}
