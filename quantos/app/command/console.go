package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"quantos/app/command/internal"
)

var rootCmd = &cobra.Command{
	Use:   "console",
	Short: "QuantSaaS 命令行工具",
	Long:  "QuantSaaS 平台的命令行管理工具",
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func init() {
	rootCmd.AddCommand(paperCmd)
	rootCmd.AddCommand(internal.MigrateCmd)
}