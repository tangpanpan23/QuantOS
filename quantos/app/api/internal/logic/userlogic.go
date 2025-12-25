package logic

import (
	"context"
	"time"

	"quantos/app/api/internal/svc"
	"quantos/app/api/internal/types"
	"quantos/app/model/user"

	"github.com/golang-jwt/jwt/v4"
	"github.com/zeromicro/go-zero/core/logx"
	"golang.org/x/crypto/bcrypt"
)

type UserRegisterLogic struct {
	logx.Logger
	ctx    context.Context
	svcCtx *svc.ServiceContext
}

func NewUserRegisterLogic(ctx context.Context, svcCtx *svc.ServiceContext) *UserRegisterLogic {
	return &UserRegisterLogic{
		Logger: logx.WithContext(ctx),
		ctx:    ctx,
		svcCtx: svcCtx,
	}
}

func (l *UserRegisterLogic) UserRegister(req *types.UserRegisterReq) (resp *types.CommonResp, err error) {
	// 检查用户名是否已存在
	existingUser, err := l.svcCtx.Common.UserRepo.FindByUsername(l.ctx, req.Username)
	if err == nil && existingUser != nil {
		return &types.CommonResp{
			Code:    400,
			Message: "用户名已存在",
		}, nil
	}

	// 检查邮箱是否已存在
	existingUser, err = l.svcCtx.Common.UserRepo.FindByEmail(l.ctx, req.Email)
	if err == nil && existingUser != nil {
		return &types.CommonResp{
			Code:    400,
			Message: "邮箱已存在",
		}, nil
	}

	// 密码加密
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		l.Errorf("密码加密失败: %v", err)
		return &types.CommonResp{
			Code:    500,
			Message: "系统错误",
		}, nil
	}

	// 创建用户
	newUser := &user.User{
		Username:     req.Username,
		Email:        req.Email,
		Password:     string(hashedPassword),
		Phone:        req.Phone,
		Status:       1, // 默认正常状态
		Role:         4, // 默认投资者角色
		Subscription: 1, // 默认免费版
		RiskTolerance: 0.5, // 默认风险容忍度
		TimeHorizon:  2,    // 默认中期投资
	}

	err = l.svcCtx.Common.UserRepo.Create(l.ctx, newUser)
	if err != nil {
		l.Errorf("创建用户失败: %v", err)
		return &types.CommonResp{
			Code:    500,
			Message: "注册失败",
		}, nil
	}

	return &types.CommonResp{
		Code:    200,
		Message: "注册成功",
		Data: map[string]interface{}{
			"user_id": newUser.ID,
		},
	}, nil
}

type UserLoginLogic struct {
	logx.Logger
	ctx    context.Context
	svcCtx *svc.ServiceContext
}

func NewUserLoginLogic(ctx context.Context, svcCtx *svc.ServiceContext) *UserLoginLogic {
	return &UserLoginLogic{
		Logger: logx.WithContext(ctx),
		ctx:    ctx,
		svcCtx: svcCtx,
	}
}

func (l *UserLoginLogic) UserLogin(req *types.UserLoginReq) (resp *types.UserLoginResp, err error) {
	// 根据用户名查找用户
	userData, err := l.svcCtx.Common.UserRepo.FindByUsername(l.ctx, req.Username)
	if err != nil || userData == nil {
		return nil, &types.ErrorResponse{
			Code:    401,
			Message: "用户名或密码错误",
		}
	}

	// 验证密码
	err = bcrypt.CompareHashAndPassword([]byte(userData.Password), []byte(req.Password))
	if err != nil {
		return nil, &types.ErrorResponse{
			Code:    401,
			Message: "用户名或密码错误",
		}
	}

	// 检查用户状态
	if userData.Status != 1 {
		return nil, &types.ErrorResponse{
			Code:    403,
			Message: "账号已被禁用",
		}
	}

	// 生成JWT token
	now := time.Now()
	accessExpire := l.svcCtx.Config.JwtAuth.AccessExpire
	token, err := l.generateToken(userData.ID, now, accessExpire)
	if err != nil {
		l.Errorf("生成token失败: %v", err)
		return nil, &types.ErrorResponse{
			Code:    500,
			Message: "登录失败",
		}
	}

	// 更新最后登录时间
	userData.LastLoginAt = &now.Format("2006-01-02 15:04:05")
	l.svcCtx.Common.UserRepo.Update(l.ctx, userData)

	// 构建用户信息
	userInfo := &types.User{
		ID:           userData.ID,
		Username:     userData.Username,
		Email:        userData.Email,
		Phone:        userData.Phone,
		Avatar:       userData.Avatar,
		Nickname:     userData.Nickname,
		Status:       userData.Status,
		Role:         userData.Role,
		Subscription: userData.Subscription,
		RiskTolerance: userData.RiskTolerance,
		TimeHorizon:  userData.TimeHorizon,
		TotalAssets:  userData.TotalAssets,
		TotalReturns: userData.TotalReturns,
		WinRate:      userData.WinRate,
		CreatedAt:    userData.CreatedAt.Format("2006-01-02 15:04:05"),
	}

	return &types.UserLoginResp{
		AccessToken:  token,
		AccessExpire: now.Add(time.Duration(accessExpire) * time.Second).Unix(),
		User:         userInfo,
	}, nil
}

func (l *UserLoginLogic) generateToken(userID uint64, now time.Time, expire int64) (string, error) {
	claims := jwt.MapClaims{
		"user_id": userID,
		"iat":     now.Unix(),
		"exp":     now.Add(time.Duration(expire) * time.Second).Unix(),
		"iss":     "quantos",
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(l.svcCtx.Config.JwtAuth.AccessSecret))
}

type GetUserLogic struct {
	logx.Logger
	ctx    context.Context
	svcCtx *svc.ServiceContext
}

func NewGetUserLogic(ctx context.Context, svcCtx *svc.ServiceContext) *GetUserLogic {
	return &GetUserLogic{
		Logger: logx.WithContext(ctx),
		ctx:    ctx,
		svcCtx: svcCtx,
	}
}

func (l *GetUserLogic) GetUser(req *types.GetUserReq) (resp *types.User, err error) {
	userData, err := l.svcCtx.Common.UserRepo.FindByID(l.ctx, req.UserID)
	if err != nil || userData == nil {
		return nil, &types.ErrorResponse{
			Code:    404,
			Message: "用户不存在",
		}
	}

	return &types.User{
		ID:           userData.ID,
		Username:     userData.Username,
		Email:        userData.Email,
		Phone:        userData.Phone,
		Avatar:       userData.Avatar,
		Nickname:     userData.Nickname,
		Status:       userData.Status,
		Role:         userData.Role,
		Subscription: userData.Subscription,
		RiskTolerance: userData.RiskTolerance,
		TimeHorizon:  userData.TimeHorizon,
		TotalAssets:  userData.TotalAssets,
		TotalReturns: userData.TotalReturns,
		WinRate:      userData.WinRate,
		CreatedAt:    userData.CreatedAt.Format("2006-01-02 15:04:05"),
	}, nil
}

type UpdateUserLogic struct {
	logx.Logger
	ctx    context.Context
	svcCtx *svc.ServiceContext
}

func NewUpdateUserLogic(ctx context.Context, svcCtx *svc.ServiceContext) *UpdateUserLogic {
	return &UpdateUserLogic{
		Logger: logx.WithContext(ctx),
		ctx:    ctx,
		svcCtx: svcCtx,
	}
}

func (l *UpdateUserLogic) UpdateUser(req *types.UpdateUserReq) (resp *types.CommonResp, err error) {
	userData, err := l.svcCtx.Common.UserRepo.FindByID(l.ctx, req.UserID)
	if err != nil || userData == nil {
		return &types.CommonResp{
			Code:    404,
			Message: "用户不存在",
		}, nil
	}

	// 更新字段
	if req.Phone != nil {
		userData.Phone = *req.Phone
	}
	if req.Avatar != nil {
		userData.Avatar = *req.Avatar
	}
	if req.Nickname != nil {
		userData.Nickname = *req.Nickname
	}
	if req.RiskTolerance != nil {
		userData.RiskTolerance = *req.RiskTolerance
	}
	if req.TimeHorizon != nil {
		userData.TimeHorizon = *req.TimeHorizon
	}

	err = l.svcCtx.Common.UserRepo.Update(l.ctx, userData)
	if err != nil {
		l.Errorf("更新用户失败: %v", err)
		return &types.CommonResp{
			Code:    500,
			Message: "更新失败",
		}, nil
	}

	return &types.CommonResp{
		Code:    200,
		Message: "更新成功",
	}, nil
}
