package papertrading

import (
	"context"
	"fmt"
	"time"

	"quantos/common"

	"gorm.io/gorm"
)

// ========== 数据库模型 ==========

// PaperAccount 模拟账户（数据库模型）
type PaperAccountDB struct {
	ID             uint64    `gorm:"primaryKey;autoIncrement" json:"id"`
	UserID         uint64    `gorm:"column:user_id;not null;default:1" json:"user_id"`
	InitialCapital float64   `gorm:"column:initial_capital;type:decimal(20,2);not null;default:100000" json:"initial_capital"`
	CurrentCapital float64   `gorm:"column:current_capital;type:decimal(20,2);not null;default:60000" json:"current_capital"`
	TotalValue     float64   `gorm:"column:total_value;type:decimal(20,2);not null;default:100000" json:"total_value"`
	TotalPnl       float64   `gorm:"column:total_pnl;type:decimal(20,2);default:0" json:"total_pnl"`
	CreatedAt      time.Time `gorm:"column:created_at" json:"created_at"`
	UpdatedAt      time.Time `gorm:"column:updated_at" json:"updated_at"`
}

func (PaperAccountDB) TableName() string {
	return "q_paper_account"
}

// PaperPosition 持仓（数据库模型）
type PaperPosition struct {
	ID           uint64    `gorm:"primaryKey;autoIncrement" json:"id"`
	AccountID    uint64    `gorm:"column:account_id;not null" json:"account_id"`
	Symbol       string    `gorm:"column:symbol;type:varchar(20);not null" json:"symbol"`
	SymbolName   string    `gorm:"column:symbol_name;type:varchar(100)" json:"symbol_name"`
	Shares       int       `gorm:"column:shares;not null" json:"shares"`
	AvgCost      float64   `gorm:"column:avg_cost;type:decimal(10,4);not null" json:"avg_cost"`
	StopLoss     float64   `gorm:"column:stop_loss;type:decimal(10,4)" json:"stop_loss"`
	TakeProfit1  float64   `gorm:"column:take_profit1;type:decimal(10,4)" json:"take_profit1"`
	TakeProfit2  float64   `gorm:"column:take_profit2;type:decimal(10,4)" json:"take_profit2"`
	EntryDate    string    `gorm:"column:entry_date;type:date;not null" json:"entry_date"`
	Reason       string    `gorm:"column:reason;type:varchar(500)" json:"reason"`
	RSI          float64   `gorm:"column:rsi;type:decimal(7,4)" json:"rsi"`
	StopMoved    bool      `gorm:"column:stop_moved;type:tinyint(1);default:0" json:"stop_moved"`
	CreatedAt    time.Time `gorm:"column:created_at" json:"created_at"`
	UpdatedAt    time.Time `gorm:"column:updated_at" json:"updated_at"`
}

func (PaperPosition) TableName() string {
	return "q_paper_position"
}

// PaperTrade 交易记录（数据库模型）
type PaperTrade struct {
	ID          uint64    `gorm:"primaryKey;autoIncrement" json:"id"`
	AccountID   uint64    `gorm:"column:account_id;not null" json:"account_id"`
	TradeDate   string    `gorm:"column:trade_date;type:date;not null" json:"trade_date"`
	Action      string    `gorm:"column:action;type:varchar(10);not null" json:"action"`
	Symbol      string    `gorm:"column:symbol;type:varchar(20);not null" json:"symbol"`
	SymbolName  string    `gorm:"column:symbol_name;type:varchar(100)" json:"symbol_name"`
	Price       float64   `gorm:"column:price;type:decimal(10,4);not null" json:"price"`
	Shares      int       `gorm:"column:shares;not null" json:"shares"`
	Amount      float64   `gorm:"column:amount;type:decimal(20,2);not null" json:"amount"`
	AvgCost     float64   `gorm:"column:avg_cost;type:decimal(10,4)" json:"avg_cost"`
	Pnl         float64   `gorm:"column:pnl;type:decimal(20,2)" json:"pnl"`
	PnlPct      float64   `gorm:"column:pnl_pct;type:decimal(10,4)" json:"pnl_pct"`
	Reason      string    `gorm:"column:reason;type:varchar(500)" json:"reason"`
	HoldDays    int       `gorm:"column:hold_days" json:"hold_days"`
	CashAfter   float64   `gorm:"column:cash_after;type:decimal(20,2)" json:"cash_after"`
	CreatedAt   time.Time `gorm:"column:created_at" json:"created_at"`
}

func (PaperTrade) TableName() string {
	return "q_paper_trade"
}

// StrategyParams 策略参数（数据库模型）
type StrategyParams struct {
	ID         uint64    `gorm:"primaryKey;autoIncrement" json:"id"`
	ParamKey   string    `gorm:"column:param_key;type:varchar(100);not null;uniqueIndex" json:"param_key"`
	ParamValue float64   `gorm:"column:param_value;type:decimal(20,4);not null" json:"param_value"`
	WinRate    float64   `gorm:"column:win_rate;type:decimal(5,2)" json:"win_rate"`
	AvgWin     float64   `gorm:"column:avg_win;type:decimal(10,2)" json:"avg_win"`
	AvgLoss    float64   `gorm:"column:avg_loss;type:decimal(10,2)" json:"avg_loss"`
	TradeCount int       `gorm:"column:trade_count;default:0" json:"trade_count"`
	UpdatedAt  time.Time `gorm:"column:updated_at" json:"updated_at"`
}

func (StrategyParams) TableName() string {
	return "q_strategy_params"
}

// DailyStats 每日统计（数据库模型）
type DailyStats struct {
	ID             uint64    `gorm:"primaryKey;autoIncrement" json:"id"`
	StatDate       string    `gorm:"column:stat_date;type:date;not null;uniqueIndex" json:"stat_date"`
	InitialCapital float64   `gorm:"column:initial_capital;type:decimal(20,2)" json:"initial_capital"`
	TotalValue     float64   `gorm:"column:total_value;type:decimal(20,2)" json:"total_value"`
	PositionsValue float64   `gorm:"column:positions_value;type:decimal(20,2)" json:"positions_value"`
	Cash           float64   `gorm:"column:cash;type:decimal(20,2)" json:"cash"`
	DailyPnl       float64   `gorm:"column:daily_pnl;type:decimal(20,2)" json:"daily_pnl"`
	DailyPnlPct    float64   `gorm:"column:daily_pnl_pct;type:decimal(10,4)" json:"daily_pnl_pct"`
	TotalPnl       float64   `gorm:"column:total_pnl;type:decimal(20,2)" json:"total_pnl"`
	Positions      int       `gorm:"column:positions" json:"positions"`
	Trades         int       `gorm:"column:trades" json:"trades"`
	CreatedAt      time.Time `gorm:"column:created_at" json:"created_at"`
}

func (DailyStats) TableName() string {
	return "q_daily_stats"
}

// EvolutionLog 进化历史记录（数据库模型）
type EvolutionLog struct {
	ID         uint64    `gorm:"primaryKey;autoIncrement" json:"id"`
	ParamKey   string    `gorm:"column:param_key;type:varchar(100);not null" json:"param_key"`
	OldValue   float64   `gorm:"column:old_value;type:decimal(20,4)" json:"old_value"`
	NewValue   float64   `gorm:"column:new_value;type:decimal(20,4)" json:"new_value"`
	Reason     string    `gorm:"column:reason;type:varchar(500)" json:"reason"`
	OldWinRate float64   `gorm:"column:old_win_rate;type:decimal(5,2)" json:"old_win_rate"`
	NewWinRate float64   `gorm:"column:new_win_rate;type:decimal(5,2)" json:"new_win_rate"`
	CreatedAt  time.Time `gorm:"column:created_at" json:"created_at"`
}

func (EvolutionLog) TableName() string {
	return "q_evolution_log"
}

// ========== 数据库操作层 ==========

// PaperTradingDB 模拟盘数据库操作
type PaperTradingDB struct {
	db *gorm.DB
}

// NewPaperTradingDB 创建数据库操作实例
func NewPaperTradingDB(common *common.Common) *PaperTradingDB {
	// 自动迁移表结构
	common.DB.AutoMigrate(
		&PaperAccountDB{},
		&PaperPosition{},
		&PaperTrade{},
		&StrategyParams{},
		&DailyStats{},
		&EvolutionLog{},
	)

	return &PaperTradingDB{db: common.DB}
}

// ========== 账户操作 ==========

// GetOrCreateAccount 获取或创建账户
func (p *PaperTradingDB) GetOrCreateAccount(ctx context.Context, userID uint64) (*PaperAccountDB, error) {
	var account PaperAccountDB
	result := p.db.WithContext(ctx).Where("user_id = ?", userID).First(&account)
	if result.Error == gorm.ErrRecordNotFound {
		account = PaperAccountDB{
			UserID:         userID,
			InitialCapital: InitialCapital,
			CurrentCapital: InitialCapital - CashReserve,
			TotalValue:     InitialCapital,
			TotalPnl:       0,
		}
		if err := p.db.WithContext(ctx).Create(&account).Error; err != nil {
			return nil, fmt.Errorf("创建账户失败: %w", err)
		}
		return &account, nil
	}
	if result.Error != nil {
		return nil, fmt.Errorf("查询账户失败: %w", result.Error)
	}
	return &account, nil
}

// UpdateAccount 更新账户
func (p *PaperTradingDB) UpdateAccount(ctx context.Context, account *PaperAccountDB) error {
	return p.db.WithContext(ctx).Save(account).Error
}

// GetAccountByUserID 根据用户ID获取账户
func (p *PaperTradingDB) GetAccountByUserID(ctx context.Context, userID uint64) (*PaperAccountDB, error) {
	var account PaperAccountDB
	result := p.db.WithContext(ctx).Where("user_id = ?", userID).First(&account)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil, nil
		}
		return nil, result.Error
	}
	return &account, nil
}

// ========== 持仓操作 ==========

// CreatePosition 创建持仓
func (p *PaperTradingDB) CreatePosition(ctx context.Context, position *PaperPosition) error {
	return p.db.WithContext(ctx).Create(position).Error
}

// GetPositionsByAccountID 获取账户所有持仓
func (p *PaperTradingDB) GetPositionsByAccountID(ctx context.Context, accountID uint64) ([]*PaperPosition, error) {
	var positions []*PaperPosition
	err := p.db.WithContext(ctx).Where("account_id = ?", accountID).Find(&positions).Error
	return positions, err
}

// GetPositionBySymbol 获取指定持仓
func (p *PaperTradingDB) GetPositionBySymbol(ctx context.Context, accountID uint64, symbol string) (*PaperPosition, error) {
	var position PaperPosition
	result := p.db.WithContext(ctx).Where("account_id = ? AND symbol = ?", accountID, symbol).First(&position)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil, nil
		}
		return nil, result.Error
	}
	return &position, nil
}

// UpdatePosition 更新持仓
func (p *PaperTradingDB) UpdatePosition(ctx context.Context, position *PaperPosition) error {
	return p.db.WithContext(ctx).Save(position).Error
}

// DeletePosition 删除持仓
func (p *PaperTradingDB) DeletePosition(ctx context.Context, id uint64) error {
	return p.db.WithContext(ctx).Delete(&PaperPosition{}, id).Error
}

// DeletePositionBySymbol 删除指定持仓
func (p *PaperTradingDB) DeletePositionBySymbol(ctx context.Context, accountID uint64, symbol string) error {
	return p.db.WithContext(ctx).Where("account_id = ? AND symbol = ?", accountID, symbol).Delete(&PaperPosition{}).Error
}

// GetPositionCount 获取持仓数量
func (p *PaperTradingDB) GetPositionCount(ctx context.Context, accountID uint64) (int64, error) {
	var count int64
	err := p.db.WithContext(ctx).Model(&PaperPosition{}).Where("account_id = ?", accountID).Count(&count).Error
	return count, err
}

// ========== 交易记录操作 ==========

// CreateTrade 创建交易记录
func (p *PaperTradingDB) CreateTrade(ctx context.Context, trade *PaperTrade) error {
	return p.db.WithContext(ctx).Create(trade).Error
}

// GetTradesByAccountID 获取账户所有交易记录
func (p *PaperTradingDB) GetTradesByAccountID(ctx context.Context, accountID uint64, limit int) ([]*PaperTrade, error) {
	var trades []*PaperTrade
	query := p.db.WithContext(ctx).Where("account_id = ?", accountID).Order("created_at DESC")
	if limit > 0 {
		query = query.Limit(limit)
	}
	err := query.Find(&trades).Error
	return trades, err
}

// GetTradesBySymbol 获取指定股票的交易记录
func (p *PaperTradingDB) GetTradesBySymbol(ctx context.Context, accountID uint64, symbol string) ([]*PaperTrade, error) {
	var trades []*PaperTrade
	err := p.db.WithContext(ctx).Where("account_id = ? AND symbol = ?", accountID, symbol).Order("created_at DESC").Find(&trades).Error
	return trades, err
}

// GetClosedTrades 获取已平仓交易（用于分析）
func (p *PaperTradingDB) GetClosedTrades(ctx context.Context, accountID uint64) ([]*PaperTrade, error) {
	var trades []*PaperTrade
	err := p.db.WithContext(ctx).Where("account_id = ? AND action = ?", accountID, "SELL").
		Where("pnl IS NOT NULL AND pnl != 0").Order("trade_date DESC").Find(&trades).Error
	return trades, err
}

// GetTodayTrades 获取今日交易记录
func (p *PaperTradingDB) GetTodayTrades(ctx context.Context, accountID uint64) ([]*PaperTrade, error) {
	var trades []*PaperTrade
	today := time.Now().Format("2006-01-02")
	err := p.db.WithContext(ctx).Where("account_id = ? AND trade_date = ?", accountID, today).Find(&trades).Error
	return trades, err
}

// ========== 策略参数操作 ==========

// GetStrategyParams 获取策略参数
func (p *PaperTradingDB) GetStrategyParams(ctx context.Context, paramKey string) (*StrategyParams, error) {
	var params StrategyParams
	result := p.db.WithContext(ctx).Where("param_key = ?", paramKey).First(&params)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil, nil
		}
		return nil, result.Error
	}
	return &params, nil
}

// GetAllStrategyParams 获取所有策略参数
func (p *PaperTradingDB) GetAllStrategyParams(ctx context.Context) ([]*StrategyParams, error) {
	var params []*StrategyParams
	err := p.db.WithContext(ctx).Find(&params).Error
	return params, err
}

// UpsertStrategyParams 创建或更新策略参数
func (p *PaperTradingDB) UpsertStrategyParams(ctx context.Context, paramKey string, value float64) error {
	params := StrategyParams{
		ParamKey:   paramKey,
		ParamValue: value,
	}
	return p.db.WithContext(ctx).Where("param_key = ?", paramKey).Assign(params).FirstOrCreate(&params).Error
}

// UpdateStrategyParams 更新策略参数及其统计
func (p *PaperTradingDB) UpdateStrategyParams(ctx context.Context, paramKey string, value, winRate, avgWin, avgLoss float64, tradeCount int) error {
	params := StrategyParams{
		ParamValue: value,
		WinRate:    winRate,
		AvgWin:     avgWin,
		AvgLoss:    avgLoss,
		TradeCount: tradeCount,
	}
	return p.db.WithContext(ctx).Where("param_key = ?", paramKey).Assign(params).FirstOrCreate(&params).Error
}

// ========== 每日统计操作 ==========

// CreateDailyStats 创建每日统计
func (p *PaperTradingDB) CreateDailyStats(ctx context.Context, stats *DailyStats) error {
	return p.db.WithContext(ctx).Create(stats).Error
}

// GetDailyStats 获取指定日期的统计
func (p *PaperTradingDB) GetDailyStats(ctx context.Context, date string) (*DailyStats, error) {
	var stats DailyStats
	result := p.db.WithContext(ctx).Where("stat_date = ?", date).First(&stats)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil, nil
		}
		return nil, result.Error
	}
	return &stats, nil
}

// GetDailyStatsRange 获取日期范围内的统计
func (p *PaperTradingDB) GetDailyStatsRange(ctx context.Context, startDate, endDate string) ([]*DailyStats, error) {
	var stats []*DailyStats
	err := p.db.WithContext(ctx).Where("stat_date BETWEEN ? AND ?", startDate, endDate).Order("stat_date ASC").Find(&stats).Error
	return stats, err
}

// GetLatestDailyStats 获取最近一次统计
func (p *PaperTradingDB) GetLatestDailyStats(ctx context.Context) (*DailyStats, error) {
	var stats DailyStats
	result := p.db.WithContext(ctx).Order("stat_date DESC").First(&stats)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil, nil
		}
		return nil, result.Error
	}
	return &stats, nil
}

// UpsertDailyStats 创建或更新每日统计
func (p *PaperTradingDB) UpsertDailyStats(ctx context.Context, stats *DailyStats) error {
	return p.db.WithContext(ctx).Where("stat_date = ?", stats.StatDate).Assign(stats).FirstOrCreate(stats).Error
}

// ========== 进化历史操作 ==========

// CreateEvolutionLog 创建进化记录
func (p *PaperTradingDB) CreateEvolutionLog(ctx context.Context, log *EvolutionLog) error {
	return p.db.WithContext(ctx).Create(log).Error
}

// GetEvolutionLogs 获取进化历史
func (p *PaperTradingDB) GetEvolutionLogs(ctx context.Context, paramKey string, limit int) ([]*EvolutionLog, error) {
	var logs []*EvolutionLog
	query := p.db.WithContext(ctx)
	if paramKey != "" {
		query = query.Where("param_key = ?", paramKey)
	}
	if limit > 0 {
		query = query.Limit(limit)
	}
	err := query.Order("created_at DESC").Find(&logs).Error
	return logs, err
}

// GetRecentEvolutionLogs 获取最近的进化记录
func (p *PaperTradingDB) GetRecentEvolutionLogs(ctx context.Context, limit int) ([]*EvolutionLog, error) {
	var logs []*EvolutionLog
	err := p.db.WithContext(ctx).Order("created_at DESC").Limit(limit).Find(&logs).Error
	return logs, err
}
