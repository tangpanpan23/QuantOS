package main

import (
	"fmt"
	"os"
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

func main() {
	migrateCmd.AddCommand(migrateUpCmd, migrateDownCmd, migrateStatusCmd)
	migrateCmd.SetArgs(os.Args[1:])
	if err := migrateCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func runMigrations(direction string) error {
	db, err := connectDB()
	if err != nil {
		return fmt.Errorf("连接数据库失败: %v", err)
	}
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
		fmt.Printf("✓ 执行迁移: %s\n", filepath.Base(file))
	}
	return nil
}

func showMigrationStatus() error {
	db, err := connectDB()
	if err != nil {
		return fmt.Errorf("连接数据库失败: %v", err)
	}
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
	dsn := "root:quantos2024@tcp(127.0.0.1:3306)/quantos?charset=utf8mb4&parseTime=True&loc=Local"
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
	content, err := os.ReadFile(file)
	if err != nil {
		return err
	}
	version := extractVersion(file)
	if direction == "up" {
		executed, err := isMigrationExecuted(db, version)
		if err != nil {
			return err
		}
		if executed {
			return nil
		}
	}

	tx := db.Begin()
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()

	// 分割多条 SQL 语句逐条执行
	lines := strings.Split(string(content), ";")
	for _, raw := range lines {
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "--") {
			continue
		}
		// 移除行内注释
		if idx := strings.Index(line, "--"); idx >= 0 {
			line = strings.TrimSpace(line[:idx])
		}
		if line == "" {
			continue
		}
		if err := tx.Exec(line).Error; err != nil {
			tx.Rollback()
			preview := line
			if len(preview) > 80 {
				preview = preview[:80] + "..."
			}
			return fmt.Errorf("SQL 错误 [%s]: %v", preview, err)
		}
	}

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
