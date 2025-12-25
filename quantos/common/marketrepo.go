package common

import (
	"context"
	"quantos/app/model/market"

	"gorm.io/gorm"
)

type MarketRepository struct {
	db *gorm.DB
}

func NewMarketRepository(db *gorm.DB) *MarketRepository {
	return &MarketRepository{db: db}
}

// CreateMarketData 创建市场数据
func (r *MarketRepository) CreateMarketData(ctx context.Context, data *market.MarketData) error {
	return r.db.WithContext(ctx).Create(data).Error
}

// FindMarketDataBySymbol 获取股票的历史数据
func (r *MarketRepository) FindMarketDataBySymbol(ctx context.Context, symbol string, limit int) ([]*market.MarketData, error) {
	var data []*market.MarketData
	err := r.db.WithContext(ctx).Where("symbol = ?", symbol).
		Order("trade_date DESC, trade_time DESC").
		Limit(limit).Find(&data).Error
	return data, err
}

// FindMarketDataByDateRange 获取指定日期范围内的市场数据
func (r *MarketRepository) FindMarketDataByDateRange(ctx context.Context, symbol, startDate, endDate string) ([]*market.MarketData, error) {
	var data []*market.MarketData
	err := r.db.WithContext(ctx).Where("symbol = ? AND trade_date BETWEEN ? AND ?", symbol, startDate, endDate).
		Order("trade_date ASC, trade_time ASC").Find(&data).Error
	return data, err
}

// CreateNewsData 创建新闻数据
func (r *MarketRepository) CreateNewsData(ctx context.Context, news *market.NewsData) error {
	return r.db.WithContext(ctx).Create(news).Error
}

// FindNewsByPage 分页获取新闻数据
func (r *MarketRepository) FindNewsByPage(ctx context.Context, category string, page, pageSize int) ([]*market.NewsData, int64, error) {
	var news []*market.NewsData
	var total int64

	query := r.db.WithContext(ctx).Model(&market.NewsData{})

	if category != "" {
		query = query.Where("category = ?", category)
	}

	// 获取总数
	err := query.Count(&total).Error
	if err != nil {
		return nil, 0, err
	}

	// 分页查询
	offset := (page - 1) * pageSize
	err = query.Order("publish_time DESC").
		Offset(offset).Limit(pageSize).Find(&news).Error

	return news, total, err
}

// CreatePolicyData 创建政策数据
func (r *MarketRepository) CreatePolicyData(ctx context.Context, policy *market.PolicyData) error {
	return r.db.WithContext(ctx).Create(policy).Error
}

// FindPolicyByPage 分页获取政策数据
func (r *MarketRepository) FindPolicyByPage(ctx context.Context, category string, page, pageSize int) ([]*market.PolicyData, int64, error) {
	var policies []*market.PolicyData
	var total int64

	query := r.db.WithContext(ctx).Model(&market.PolicyData{})

	if category != "" {
		query = query.Where("category = ?", category)
	}

	// 获取总数
	err := query.Count(&total).Error
	if err != nil {
		return nil, 0, err
	}

	// 分页查询
	offset := (page - 1) * pageSize
	err = query.Order("publish_time DESC").
		Offset(offset).Limit(pageSize).Find(&policies).Error

	return policies, total, err
}

// CreateFactorData 创建因子数据
func (r *MarketRepository) CreateFactorData(ctx context.Context, factor *market.FactorData) error {
	return r.db.WithContext(ctx).Create(factor).Error
}

// FindFactorsByCode 获取因子历史数据
func (r *MarketRepository) FindFactorsByCode(ctx context.Context, factorCode string, limit int) ([]*market.FactorData, error) {
	var factors []*market.FactorData
	err := r.db.WithContext(ctx).Where("factor_code = ?", factorCode).
		Order("date DESC, time DESC").
		Limit(limit).Find(&factors).Error
	return factors, err
}

// FindFactorsBySymbol 获取特定股票的因子数据
func (r *MarketRepository) FindFactorsBySymbol(ctx context.Context, symbol, factorCode string, limit int) ([]*market.FactorData, error) {
	var factors []*market.FactorData
	query := r.db.WithContext(ctx).Where("symbol = ?", symbol)

	if factorCode != "" {
		query = query.Where("factor_code = ?", factorCode)
	}

	err := query.Order("date DESC, time DESC").
		Limit(limit).Find(&factors).Error
	return factors, err
}

// CreateIndexData 创建指数数据
func (r *MarketRepository) CreateIndexData(ctx context.Context, index *market.IndexData) error {
	return r.db.WithContext(ctx).Create(index).Error
}

// FindIndexDataByCode 获取指数历史数据
func (r *MarketRepository) FindIndexDataByCode(ctx context.Context, indexCode string, limit int) ([]*market.IndexData, error) {
	var data []*market.IndexData
	err := r.db.WithContext(ctx).Where("index_code = ?", indexCode).
		Order("trade_date DESC").
		Limit(limit).Find(&data).Error
	return data, err
}
