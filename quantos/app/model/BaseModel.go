package model

import (
	"time"

	"gorm.io/gorm"
)

// BaseModel 基础模型，包含通用字段
type BaseModel struct {
	ID        uint64         `gorm:"primaryKey;autoIncrement;comment:主键ID"`
	CreatedAt *time.Time     `gorm:"column:created_at;comment:创建时间"`
	UpdatedAt *time.Time     `gorm:"column:updated_at;comment:更新时间"`
	DeletedAt gorm.DeletedAt `gorm:"index;comment:删除时间"`
}

// BeforeCreate 创建前的钩子
func (b *BaseModel) BeforeCreate(tx *gorm.DB) error {
	now := time.Now()
	if b.CreatedAt == nil {
		b.CreatedAt = &now
	}
	if b.UpdatedAt == nil {
		b.UpdatedAt = &now
	}
	return nil
}

// BeforeUpdate 更新前的钩子
func (b *BaseModel) BeforeUpdate(tx *gorm.DB) error {
	now := time.Now()
	b.UpdatedAt = &now
	return nil
}
