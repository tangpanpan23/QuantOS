package internal

import (
	"fmt"
	"io/ioutil"
	"path/filepath"
	"sort"
	"strings"

	"github.com/spf13/cobra"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

var migrateCmd = &cobra.Command{
	Use:   "migrate",
	Short: "数据库迁移管理",
	Long:  "管理数据库结构迁移",
}

var migrateUpCmd = &cobra.Command{
	Use:   "up",
	Short: "执行迁移",
	Long:  "执行所有待迁移的文件",
	Run: func(cmd *cobra.Command, args []string) {
		if err := runMigrations("up"); err != nil {
			fmt.Printf("迁移失败: %v\n", err)
			return
		}
		fmt.Println("迁移完成")
	},
}

var migrateDownCmd = &cobra.Command{
	Use:   "down",
	Short: "回滚迁移",
	Long:  "回滚最后一次迁移",
	Run: func(cmd *cobra.Command, args []string) {
		if err := runMigrations("down"); err != nil {
			fmt.Printf("回滚失败: %v\n", err)
			return
		}
		fmt.Println("回滚完成")
	},
}

var migrateStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "查看迁移状态",
	Long:  "显示所有迁移文件的状态",
	Run: func(cmd *cobra.Command, args []string) {
		if err := showMigrationStatus(); err != nil {
			fmt.Printf("查看状态失败: %v\n", err)
			return
		}
	},
}

func init() {
	migrateCmd.AddCommand(migrateUpCmd)
	migrateCmd.AddCommand(migrateDownCmd)
	migrateCmd.AddCommand(migrateStatusCmd)
}

func runMigrations(direction string) error {
	db, err := connectDB()
	if err != nil {
		return fmt.Errorf("连接数据库失败: %v", err)
	}

	// 创建migrations表（如果不存在）
	if err := createMigrationsTable(db); err != nil {
		return fmt.Errorf("创建迁移表失败: %v", err)
	}

	files, err := getMigrationFiles(direction)
	if err != nil {
		return err
	}

	for _, file := range files {
		if err := executeMigration(db, file, direction); err != nil {
			return fmt.Errorf("执行迁移失败 %s: %v", file, err)
		}
		fmt.Printf("✓ 执行迁移: %s\n", file)
	}

	return nil
}

func showMigrationStatus() error {
	db, err := connectDB()
	if err != nil {
		return fmt.Errorf("连接数据库失败: %v", err)
	}

	// 获取所有迁移文件
	upFiles, err := getMigrationFiles("up")
	if err != nil {
		return err
	}

	fmt.Println("迁移状态:")
	fmt.Println("==========")

	for _, upFile := range upFiles {
		version := extractVersion(upFile)
		executed, err := isMigrationExecuted(db, version)
		if err != nil {
			return err
		}

		status := "待执行"
		if executed {
			status = "已执行"
		}
		fmt.Printf("%s: %s\n", version, status)
	}

	return nil
}

func connectDB() (*gorm.DB, error) {
	// 这里应该从配置文件读取数据库连接信息
	// 暂时使用硬编码的配置
	dsn := "quantos:quantos123@tcp(localhost:3306)/quantos?charset=utf8mb4&parseTime=True&loc=Local"
	return gorm.Open(mysql.Open(dsn), &gorm.Config{})
}

func createMigrationsTable(db *gorm.DB) error {
	return db.Exec(`
		CREATE TABLE IF NOT EXISTS schema_migrations (
			version VARCHAR(255) NOT NULL PRIMARY KEY,
			executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	`).Error
}

func getMigrationFiles(direction string) ([]string, error) {
	files, err := filepath.Glob("database/migrations/*." + direction + ".sql")
	if err != nil {
		return nil, err
	}
	sort.Strings(files)
	return files, nil
}

func executeMigration(db *gorm.DB, file, direction string) error {
	content, err := ioutil.ReadFile(file)
	if err != nil {
		return err
	}

	version := extractVersion(file)

	// 检查是否已经执行过
	if direction == "up" {
		executed, err := isMigrationExecuted(db, version)
		if err != nil {
			return err
		}
		if executed {
			return nil // 已经执行过，跳过
		}
	}

	// 在事务中执行迁移
	tx := db.Begin()
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()

	if err := tx.Exec(string(content)).Error; err != nil {
		tx.Rollback()
		return err
	}

	// 记录迁移执行情况
	if direction == "up" {
		if err := tx.Exec("INSERT INTO schema_migrations (version) VALUES (?)", version).Error; err != nil {
			tx.Rollback()
			return err
		}
	} else {
		if err := tx.Exec("DELETE FROM schema_migrations WHERE version = ?", version).Error; err != nil {
			tx.Rollback()
			return err
		}
	}

	return tx.Commit().Error
}

func extractVersion(filename string) string {
	// 从文件名中提取版本号，例如 "000001_create_initial_tables.up.sql" -> "000001"
	base := filepath.Base(filename)
	return strings.Split(base, "_")[0]
}

func isMigrationExecuted(db *gorm.DB, version string) (bool, error) {
	var count int64
	err := db.Model(&MigrationRecord{}).Where("version = ?", version).Count(&count).Error
	return count > 0, err
}

type MigrationRecord struct {
	Version    string `gorm:"column:version"`
	ExecutedAt string `gorm:"column:executed_at"`
}

func (MigrationRecord) TableName() string {
	return "schema_migrations"
}
