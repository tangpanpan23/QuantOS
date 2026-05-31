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
	existingUser, err := l.svcCtx.Common.UserRepo.FindByUsername(l.ctx, req.Username)
	if err == nil && existingUser != nil {
		return &types.CommonResp{Code: 400, Message: "用户名已存在"}, nil
	}
	existingUser, err = l.svcCtx.Common.UserRepo.FindByEmail(l.ctx, req.Email)
	if err == nil && existingUser != nil {
		return &types.CommonResp{Code: 400, Message: "邮箱已存在"}, nil
	}
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		return &types.CommonResp{Code: 500, Message: "系统错误"}, nil
	}
	newUser := &user.User{
		Username:     req.Username,
		Email:       req.Email,
		Password:    string(hashedPassword),
		Phone:       req.Phone,
		Status:      1,
		Role:        4,
		Subscription: 1,
		RiskTolerance: 0.5,
		TimeHorizon: 2,
	}
	err = l.svcCtx.Common.UserRepo.Create(l.ctx, newUser)
	if err != nil {
		return &types.CommonResp{Code: 500, Message: "注册失败"}, nil
	}
	return &types.CommonResp{Code: 200, Message: "注册成功", Data: map[string]interface{}{"user_id": newUser.ID}}, nil
}

type UserLoginLogic struct {
	logx.Logger
	ctx    context.Context
	svcCtx *svc.ServiceContext
}

func NewUserLoginLogic(ctx context.Context, svcCtx *svc.ServiceContext) *UserLoginLogic {
	return &UserLoginLogic{Logger: logx.WithContext(ctx), ctx: ctx, svcCtx: svcCtx}
}

func (l *UserLoginLogic) UserLogin(req *types.UserLoginReq) (resp *types.UserLoginResp, err error) {
	userData, err := l.svcCtx.Common.UserRepo.FindByUsername(l.ctx, req.Username)
	if err != nil || userData == nil {
		return nil, &types.ErrorResponse{Code: 401, Message: "用户名或密码错误"}
	}
	err = bcrypt.CompareHashAndPassword([]byte(userData.Password), []byte(req.Password))
	if err != nil {
		return nil, &types.ErrorResponse{Code: 401, Message: "用户名或密码错误"}
	}
	if userData.Status != 1 {
		return nil, &types.ErrorResponse{Code: 403, Message: "账号已被禁用"}
	}
	now := time.Now()
	token, err := l.generateToken(userData.ID, now, l.svcCtx.Config.JwtAuth.AccessExpire)
	if err != nil {
		return nil, &types.ErrorResponse{Code: 500, Message: "登录失败"}
	}
	ts := now.Format("2006-01-02 15:04:05")
	userData.LastLoginAt = &ts
	l.svcCtx.Common.UserRepo.Update(l.ctx, userData)
	createdAtStr := ""
	if !userData.CreatedAt.IsZero() {
		createdAtStr = userData.CreatedAt.Format("2006-01-02 15:04:05")
	}
	return &types.UserLoginResp{
		AccessToken:  token,
		AccessExpire: now.Add(time.Duration(l.svcCtx.Config.JwtAuth.AccessExpire) * time.Second).Unix(),
		User: &types.User{
			ID: userData.ID, Username: userData.Username, Email: userData.Email,
			Phone: userData.Phone, Avatar: userData.Avatar, Nickname: userData.Nickname,
			Status: userData.Status, Role: userData.Role, Subscription: userData.Subscription,
			RiskTolerance: userData.RiskTolerance, TimeHorizon: userData.TimeHorizon,
			TotalAssets: userData.TotalAssets, TotalReturns: userData.TotalReturns,
			WinRate: userData.WinRate, CreatedAt: &createdAtStr,
		},
	}, nil
}

func (l *UserLoginLogic) generateToken(userID uint64, now time.Time, expire int64) (string, error) {
	claims := jwt.MapClaims{"user_id": userID, "iat": now.Unix(), "exp": now.Add(time.Duration(expire) * time.Second).Unix(), "iss": "quantos"}
	return jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString([]byte(l.svcCtx.Config.JwtAuth.AccessSecret))
}

type GetUserLogic struct {
	logx.Logger
	ctx    context.Context
	svcCtx *svc.ServiceContext
}

func NewGetUserLogic(ctx context.Context, svcCtx *svc.ServiceContext) *GetUserLogic {
	return &GetUserLogic{Logger: logx.WithContext(ctx), ctx: ctx, svcCtx: svcCtx}
}

func (l *GetUserLogic) GetUser(req *types.GetUserReq) (resp *types.User, err error) {
	userData, err := l.svcCtx.Common.UserRepo.FindByID(l.ctx, req.UserID)
	if err != nil || userData == nil {
		return nil, &types.ErrorResponse{Code: 404, Message: "用户不存在"}
	}
	createdAtStr := ""
	if !userData.CreatedAt.IsZero() {
		createdAtStr = userData.CreatedAt.Format("2006-01-02 15:04:05")
	}
	return &types.User{
		ID: userData.ID, Username: userData.Username, Email: userData.Email,
		Phone: userData.Phone, Avatar: userData.Avatar, Nickname: userData.Nickname,
		Status: userData.Status, Role: userData.Role, Subscription: userData.Subscription,
		RiskTolerance: userData.RiskTolerance, TimeHorizon: userData.TimeHorizon,
		TotalAssets: userData.TotalAssets, TotalReturns: userData.TotalReturns,
		WinRate: userData.WinRate, CreatedAt: &createdAtStr,
	}, nil
}

type UpdateUserLogic struct {
	logx.Logger
	ctx    context.Context
	svcCtx *svc.ServiceContext
}

func NewUpdateUserLogic(ctx context.Context, svcCtx *svc.ServiceContext) *UpdateUserLogic {
	return &UpdateUserLogic{Logger: logx.WithContext(ctx), ctx: ctx, svcCtx: svcCtx}
}

func (l *UpdateUserLogic) UpdateUser(req *types.UpdateUserReq) (resp *types.CommonResp, err error) {
	userData, err := l.svcCtx.Common.UserRepo.FindByID(l.ctx, req.UserID)
	if err != nil || userData == nil {
		return &types.CommonResp{Code: 404, Message: "用户不存在"}, nil
	}
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
		return &types.CommonResp{Code: 500, Message: "更新失败"}, nil
	}
	return &types.CommonResp{Code: 200, Message: "更新成功"}, nil
}
