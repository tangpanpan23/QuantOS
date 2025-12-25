package common

import (
	"fmt"
	"quantos/app/model/market"
	"quantos/app/model/user"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

type Common struct {
	DB      *gorm.DB
	UserRepo    *UserRepository
	MarketRepo  *MarketRepository
}

func NewCommon(host string, port int, user, password, database string) *Common {
	// 构建数据库连接字符串
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		user, password, host, port, database)

	// 连接数据库
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
	})
	if err != nil {
		panic(fmt.Sprintf("连接数据库失败: %v", err))
	}

	// 自动迁移表结构
	err = db.AutoMigrate(
		&user.User{},
		&user.Strategy{},
		&user.Portfolio{},
		&user.Position{},
		&market.MarketData{},
		&market.NewsData{},
		&market.PolicyData{},
		&market.FactorData{},
		&market.IndexData{},
	)
	if err != nil {
		panic(fmt.Sprintf("数据库迁移失败: %v", err))
	}

	return &Common{
		DB:         db,
		UserRepo:   NewUserRepository(db),
		MarketRepo: NewMarketRepository(db),
	}
}
