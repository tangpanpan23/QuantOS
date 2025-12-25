package common

import (
	"context"
	"quantos/app/model/user"

	"gorm.io/gorm"
)

type UserRepository struct {
	db *gorm.DB
}

func NewUserRepository(db *gorm.DB) *UserRepository {
	return &UserRepository{db: db}
}

// Create 创建用户
func (r *UserRepository) Create(ctx context.Context, user *user.User) error {
	return r.db.WithContext(ctx).Create(user).Error
}

// FindByID 根据ID查找用户
func (r *UserRepository) FindByID(ctx context.Context, id uint64) (*user.User, error) {
	var u user.User
	err := r.db.WithContext(ctx).First(&u, id).Error
	if err != nil {
		return nil, err
	}
	return &u, nil
}

// FindByUsername 根据用户名查找用户
func (r *UserRepository) FindByUsername(ctx context.Context, username string) (*user.User, error) {
	var u user.User
	err := r.db.WithContext(ctx).Where("username = ?", username).First(&u).Error
	if err != nil {
		return nil, err
	}
	return &u, nil
}

// FindByEmail 根据邮箱查找用户
func (r *UserRepository) FindByEmail(ctx context.Context, email string) (*user.User, error) {
	var u user.User
	err := r.db.WithContext(ctx).Where("email = ?", email).First(&u).Error
	if err != nil {
		return nil, err
	}
	return &u, nil
}

// Update 更新用户
func (r *UserRepository) Update(ctx context.Context, user *user.User) error {
	return r.db.WithContext(ctx).Save(user).Error
}

// Delete 删除用户
func (r *UserRepository) Delete(ctx context.Context, id uint64) error {
	return r.db.WithContext(ctx).Delete(&user.User{}, id).Error
}

// FindStrategiesByUserID 获取用户的策略列表
func (r *UserRepository) FindStrategiesByUserID(ctx context.Context, userID uint64, offset, limit int) ([]*user.Strategy, error) {
	var strategies []*user.Strategy
	err := r.db.WithContext(ctx).Where("user_id = ?", userID).
		Offset(offset).Limit(limit).Find(&strategies).Error
	return strategies, err
}

// FindPortfoliosByUserID 获取用户的投资组合列表
func (r *UserRepository) FindPortfoliosByUserID(ctx context.Context, userID uint64, offset, limit int) ([]*user.Portfolio, error) {
	var portfolios []*user.Portfolio
	err := r.db.WithContext(ctx).Where("user_id = ?", userID).
		Offset(offset).Limit(limit).Find(&portfolios).Error
	return portfolios, err
}

// CreateStrategy 创建策略
func (r *UserRepository) CreateStrategy(ctx context.Context, strategy *user.Strategy) error {
	return r.db.WithContext(ctx).Create(strategy).Error
}

// FindStrategyByID 根据ID查找策略
func (r *UserRepository) FindStrategyByID(ctx context.Context, id uint64) (*user.Strategy, error) {
	var s user.Strategy
	err := r.db.WithContext(ctx).First(&s, id).Error
	if err != nil {
		return nil, err
	}
	return &s, nil
}

// UpdateStrategy 更新策略
func (r *UserRepository) UpdateStrategy(ctx context.Context, strategy *user.Strategy) error {
	return r.db.WithContext(ctx).Save(strategy).Error
}

// DeleteStrategy 删除策略
func (r *UserRepository) DeleteStrategy(ctx context.Context, id uint64) error {
	return r.db.WithContext(ctx).Delete(&user.Strategy{}, id).Error
}

// CreatePortfolio 创建投资组合
func (r *UserRepository) CreatePortfolio(ctx context.Context, portfolio *user.Portfolio) error {
	return r.db.WithContext(ctx).Create(portfolio).Error
}

// FindPortfolioByID 根据ID查找投资组合
func (r *UserRepository) FindPortfolioByID(ctx context.Context, id uint64) (*user.Portfolio, error) {
	var p user.Portfolio
	err := r.db.WithContext(ctx).Preload("Positions").First(&p, id).Error
	if err != nil {
		return nil, err
	}
	return &p, nil
}
