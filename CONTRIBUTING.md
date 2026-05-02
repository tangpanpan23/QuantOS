# 贡献指南

感谢你关注 QuantSaaS 项目！🎉

本文档将帮助你了解如何为项目做出贡献。

---

## 开发流程

### 1. Fork & Clone

```bash
# Fork 项目后
git clone https://github.com/YOUR_USERNAME/quantos.git
cd quantos
```

### 2. 创建特性分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 3. 开发

```bash
# 启动开发环境
make dev

# 运行代码格式化
make fmt

# 运行代码检查
make lint

# 本地测试
make test
```

### 4. 提交

```bash
# 提交（遵循 Conventional Commits）
git commit -m "feat: add new strategy template system"
git commit -m "fix: resolve market data fetch timeout"
git commit -m "docs: update API documentation"
git commit -m "refactor: improve trade execution logic"
```

**提交类型：**

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构 |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具/辅助 |

### 5. Push & PR

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上发起 Pull Request。

---

## 代码规范

### Go 代码

- 遵循 Go 官方 [Effective Go](https://go.dev/doc/effective_go)
- 命名：包名简短（全小写），变量/函数用驼峰
- 错误处理：使用 `fmt.Errorf("doing something: %w", err)` 包装
- Context：每个入口函数传递 `context.Context`
- 日志：使用 `logx`（go-zero 内置）

**示例：**

```go
// ✅ 正确
func GetStockData(ctx context.Context, symbol string) (*StockData, error) {
    data, err := fetchFromAPI(ctx, symbol)
    if err != nil {
        return nil, fmt.Errorf("fetch stock data: %w", err)
    }
    return data, nil
}

// ❌ 错误
func GetStockData(symbol string) (*StockData, error) {
    data, err := fetchFromAPI(symbol) // 缺少 context，错误包装随意
    return data, err
}
```

### 文件结构

```
handler/    # HTTP 层，只做参数解析和响应封装
logic/      # 业务逻辑，核心处理
model/      # 数据模型和数据库操作
types/      # 请求/响应 DTO
```

### Handler 命名

| 操作 | 命名 |
|------|------|
| 创建 | `createXXXHandler` |
| 获取单个 | `getXXXHandler` |
| 获取列表 | `getXXXsHandler` |
| 更新 | `updateXXXHandler` |
| 删除 | `deleteXXXHandler` |
| 自定义 | `doSomethingHandler` |

---

## API 文档规范

新增或修改 API 端点时，必须同步更新 `docs/API.md`：

```markdown
### GET /api/v1/strategies

获取策略列表。

**查询参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| user_id | uint64 | - | 按用户筛选 |

**响应示例：**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [...],
    "total": 100
  }
}
```
```

---

## 测试规范

### 单元测试

```bash
# 运行当前包测试
go test ./app/model/... -v

# 带覆盖率
go test ./... -coverprofile=coverage.out
```

### 测试文件命名

```
userlogic_test.go    # 对应 userlogic.go
```

### 测试函数命名

```go
func TestGetUserHandler(t *testing.T) { ... }
func TestGetUserHandler_NameTooLong(t *testing.T) { ... }
```

---

## PR 审核清单

提交 PR 前请确认：

- [ ] `make fmt` 已运行
- [ ] `make lint` 无错误
- [ ] `make test` 通过
- [ ] 新功能有对应测试
- [ ] API 变更已更新 `docs/API.md`
- [ ] 重大变更已更新 `docs/CHANGELOG.md`

---

## 重大决策

对于以下变更，需要先开 Issue 讨论：

- 改变核心数据模型
- 修改 API 接口签名
- 引入新的外部依赖
- 大规模重构

---

## 提问？

- 开 [GitHub Issue](https://github.com/tangpanpan23/quantos/issues)
- 发送邮件：tangpan23@126.com

---

再次感谢你的贡献！ 💪
