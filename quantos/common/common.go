package common

import (
	"fmt"
	"time"
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

func NewCommon(host string, port int, user, password, database string, maxIdleConns, maxOpenConns, connMaxLifetime int) *Common {
	// 构建数据库连接字符串 - 使用参数化查询防止注入
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local&timeout=30s&readTimeout=30s&writeTimeout=30s",
		user, password, host, port, database)

	// 连接数据库
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
		// 禁用自动创建外键约束，提高性能和安全性
		DisableForeignKeyConstraintWhenMigrating: true,
	})
	if err != nil {
		panic(fmt.Sprintf("连接数据库失败: %v", err))
	}

	// 配置数据库连接池
	sqlDB, err := db.DB()
	if err != nil {
		panic(fmt.Sprintf("获取数据库连接失败: %v", err))
	}

	// 设置连接池参数
	sqlDB.SetMaxIdleConns(maxIdleConns)                                    // 最大空闲连接数
	sqlDB.SetMaxOpenConns(maxOpenConns)                                  // 最大打开连接数
	sqlDB.SetConnMaxLifetime(time.Duration(connMaxLifetime) * time.Second) // 连接最大生存时间

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
