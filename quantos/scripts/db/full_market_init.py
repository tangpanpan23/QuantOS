# -*- coding: utf-8 -*-
"""
全市场A股股票池初始化脚本
一次性将A股全市场股票基本信息写入 q_stock_pool 表，
并补充行业分类信息。

数据源：
1. stock_info_a_code_name  — 全市场股票基本信息（代码+名称）
2. stock_board_industry_name_ths — 同花顺90个行业分类
3. stock_board_industry_cons_ths — 各行业成分股（通过股票代码匹配行业）

用法：
    cd /Users/tank/Code/QuantOS/quantos/scripts
    python3 -m db.full_market_init
"""
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 清除代理
for _k in list(os.environ.keys()):
    if "proxy" in _k.lower():
        del os.environ[_k]

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("full_market")


def _infer_market(symbol: str) -> str:
    if symbol.startswith(("6", "9", "5", "7")):
        return "SH"
    return "SZ"


def _infer_sector(symbol: str) -> str:
    """根据代码区间推断大类板块"""
    s = symbol.zfill(6)
    prefix = s[:3]

    # 主板上海
    if s[0] == "6":
        if s[:3] in ("600", "601", "603"):
            return "主板"
        elif s[:3] in ("688",):
            return "科创板"
    # 主板深圳
    elif s[0] in ("0", "3"):
        if s[:3] in ("000", "001"):
            return "主板"
        elif s[:3] == "002":
            return "中小板"
        elif s[:3] == "003":
            return "主板"
        elif s[:3] in ("300",):
            return "创业板"
    return "主板"


def _industry_desc(industry: str) -> str:
    """各行业中文说明"""
    DESC = {
        "银行": "金融业，提供存贷款、支付结算等核心银行服务",
        "证券": "金融业，资本市场中介服务（经纪/投行/资管）",
        "保险": "金融业，人身险/财产险/再保险业务",
        "白酒": "消费行业，高端白酒制造与销售",
        "医药": "医疗健康，创新药/仿制药/医疗器械",
        "半导体": "科技行业，集成电路/芯片设计与制造",
        "软件服务": "科技行业，应用软件/SaaS/IT服务",
        "互联网": "科技行业，电商/社交/搜索/云计算平台",
        "通信设备": "科技行业，运营商网络设备/光通信",
        "电力": "公用事业，发电/输配电/新能源发电",
        "煤炭": "能源行业，煤炭开采与洗选",
        "石油": "能源行业，石油开采/炼化/销售",
        "钢铁": "周期行业，钢铁冶炼与加工",
        "房地产": "周期行业，房地产开发与物业管理",
        "建筑": "周期行业，工程承包/园林绿化/装饰",
        "化学制品": "化工行业，精细化工/新材料",
        "化学制药": "医疗健康，化学原料药与制剂",
        "中药": "医疗健康，中成药/中药饮片",
        "医疗器械": "医疗健康，医疗设备与耗材",
        "食品加工": "消费行业，食品制造与加工",
        "饮料制造": "消费行业，软饮/乳制品/功能性饮料",
        "纺织服装": "消费行业，品牌服饰/代工制造",
        "家电": "消费行业，白电/黑电/小家电制造",
        "汽车整车": "制造业，整车制造与销售",
        "汽车零部件": "制造业，零部件供应与售后",
        "通用设备": "制造业，机床/泵阀/减速机等",
        "专用设备": "制造业，工程机械/医疗设备/光伏设备",
        "电气设备": "制造业，发电/输配电/电机/储能",
        "电子元件": "科技行业，PCB/连接器/被动元件",
        "光学光电子": "科技行业，LED/面板/光学镜头",
        "计算机设备": "科技行业，服务器/存储/外设",
        "环保": "公用事业，水处理/固废处理/大气治理",
        "公路铁路": "公用事业，收费公路/铁路运营",
        "港口航运": "交运物流，港口装卸/船运/物流",
        "航空机场": "交运物流，航空运输/机场运营",
        "物流": "交运物流，快递/跨境物流/仓储",
        "农业": "农林牧渔，种植/养殖/农产品加工",
        "军工": "国防军工，航空航天/舰船/陆装/信息化",
        "环保设备": "制造业，除尘/水处理/监测设备",
        "造纸": "轻工业，纸浆/纸张/包装纸",
        "包装印刷": "轻工业，包装材料/印刷服务",
        "化学纤维": "化工行业，化纤/氨纶/碳纤维",
        "橡胶": "化工行业，轮胎/橡胶制品",
        "金属非金属": "周期行业，建材/玻璃/水泥",
        "装修装饰": "周期行业，家庭装修/公装",
        "景点": "消费服务，景区门票/旅游综合",
        "酒店餐饮": "消费服务，酒店运营/餐饮连锁",
        "传媒": "消费服务，内容制作/院线/广告",
        "零售": "消费服务，零售连锁/电商代运营",
        "教育": "消费服务，K12/职教/培训",
        "医疗器械": "医疗健康，医疗设备与耗材",
        "生物制品": "医疗健康，疫苗/血制品/抗体药",
        "其他医疗": "医疗健康，CRO/CMO/医药商业",
        "电力设备": "制造业，储能/光伏/特高压",
        "军工": "国防军工，航空航天/舰船/信息化",
        "化学原料": "化工行业，大宗化工原料",
        "传媒": "消费服务，游戏/影视/广告",
        "计算机应用": "科技行业，IT解决方案/外包",
        "通信服务": "科技行业，电信运营/IDC/CDN",
        "光学光电子": "科技行业，面板/MiniLED/光学元件",
        "仪器仪表": "制造业，工业检测/科学仪器",
        "电机": "制造业，电机/微特电机",
        "其他电子": "科技行业，电子制造服务(EMS)",
        "种植业": "农林牧渔，农作物种植",
        "渔业": "农林牧渔，水产养殖与捕捞",
        "饲料": "农林牧渔，畜禽饲料生产",
        "畜禽养殖": "农林牧渔，生猪/禽类养殖",
        "动物保健": "农林牧渔，兽药与疫苗",
        "林业": "农林牧渔，造林/木材加工",
        "农业综合": "农林牧渔，农业服务与综合",
        "综合": "综合类，多元化集团",
        "公交": "交运物流，公共交通运营",
        "机场航运": "交运物流，航空与机场",
    }
    return DESC.get(industry, "")


def step1_fetch_all_stocks():
    """步骤1：从 AkShare 拉全市场股票基本信息"""
    import akshare as ak

    logger.info("=" * 50)
    logger.info("步骤1：拉取全市场股票基本信息...")
    logger.info("=" * 50)

    df = ak.stock_info_a_code_name()
    stocks = []
    for _, row in df.iterrows():
        sym = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        if not sym or len(sym) < 6:
            continue
        stocks.append({
            "symbol": sym.zfill(6),
            "name": name,
            "market": _infer_market(sym),
            "sector": _infer_sector(sym),
        })

    logger.info(f"全市场股票共 {len(stocks)} 只")
    # 按沪/深/创/科创统计
    markets = {}
    for s in stocks:
        m = s["market"]
        markets[m] = markets.get(m, 0) + 1
    for m, c in sorted(markets.items()):
        logger.info(f"  {m}: {c} 只")
    return stocks


def step2_fetch_industry_mapping():
    """步骤2：从同花顺获取行业分类，返回 {symbol: industry} 映射"""
    import akshare as ak

    logger.info("=" * 50)
    logger.info("步骤2：拉取同花顺行业分类...")
    logger.info("=" * 50)

    # 先获取所有行业列表
    ind_df = ak.stock_board_industry_name_ths()
    industries = ind_df["name"].tolist()
    logger.info(f"共 {len(industries)} 个行业: {industries[:10]}...")

    # 由于行业成分接口需要一个个拉，太慢，改用 Sina 批量查询
    # 这里用代码区间做粗分类 + 股票名称关键词匹配
    return {}


def _guess_industry_by_code(symbol: str, name: str) -> str:
    """根据代码区间和名称关键词推断行业"""
    s = symbol.zfill(6)
    n = name.replace(" ", "")

    # 代码区间规则（粗分）
    # 科创板 688xxx
    if s.startswith("688"):
        if "半导体" in n or "微" in n or "芯" in n or "电" in n:
            return "半导体"
        return "科创板"

    # 医药类 002/300 开头的医药股
    if s.startswith("002") or s.startswith("300"):
        kw_industry = [
            ("药", "医药"),
            ("医", "医疗器械"),
            ("生", "生物制品"),
            ("康", "医疗器械"),
            ("芯", "半导体"),
            ("光", "光学光电子"),
            ("电", "电子元件"),
            ("网", "互联网"),
            ("智", "软件服务"),
            ("机", "通用设备"),
            ("能", "电气设备"),
        ]
        for kw, ind in kw_industry:
            if kw in n:
                return ind

    # 上海主板 6xxxxx
    if s.startswith("6"):
        kw_industry = [
            ("银", "银行"), ("保", "保险"), ("证", "证券"),
            ("酒", "白酒"), ("电", "电力"), ("石", "石油"),
            ("煤", "煤炭"), ("钢", "钢铁"), ("建", "建筑"),
            ("房", "房地产"), ("汽", "汽车整车"),
            ("机", "通用设备"), ("化", "化学制品"),
            ("药", "化学制药"), ("中", "中药"),
            ("光", "光学光电子"), ("芯", "半导体"),
            ("网", "互联网"), ("云", "软件服务"),
            ("数", "计算机设备"), ("通", "通信设备"),
        ]
        for kw, ind in kw_industry:
            if kw in n:
                return ind

    # 深圳 0xxxxx / 3xxxxx
    kw_industry = [
        ("银", "银行"),
        ("酒", "白酒"), ("食", "食品加工"),
        ("药", "化学制药"), ("医", "医疗器械"),
        ("芯", "半导体"), ("光", "光学光电子"),
        ("电", "电子元件"), ("网", "互联网"),
        ("智", "软件服务"), ("机", "通用设备"),
        ("电", "电气设备"), ("汽", "汽车零部件"),
        ("养", "畜禽养殖"), ("饲", "饲料"),
        ("木", "林业"), ("渔", "渔业"),
    ]
    for kw, ind in kw_industry:
        if kw in n:
            return ind

    return "综合"


def step3_save_to_db(all_stocks: list):
    """步骤3：写入数据库"""
    from .db_client import get_session
    from .models import StockPoolDB
    from sqlalchemy.exc import IntegrityError

    logger.info("=" * 50)
    logger.info("步骤3：写入数据库...")
    logger.info("=" * 50)

    # 查重：已有的 symbol
    with get_session() as db:
        existing = {r.symbol for r in db.query(StockPoolDB.symbol).all()}
    logger.info(f"  已有 {len(existing)} 只，跳过")

    inserted = 0
    skipped = 0
    batch = []

    for stock in all_stocks:
        sym = stock["symbol"]
        if sym in existing:
            skipped += 1
            continue

        # 推断行业
        industry = _guess_industry_by_code(sym, stock["name"])
        notes = _industry_desc(industry)

        batch.append(StockPoolDB(
            symbol=sym,
            name=stock["name"],
            market=stock["market"],
            sector=stock["sector"],
            industry=industry,
            status=1,
            is_watched=0,
            is_paper_simulated=0,
            notes=notes,
        ))

        # 每500条写入一次
        if len(batch) >= 500:
            with get_session() as db:
                for obj in batch:
                    try:
                        db.add(obj)
                        inserted += 1
                    except IntegrityError:
                        db.rollback()
                        skipped += 1
                db.commit()
            logger.info(f"  已写入 {inserted} 只 (本次 {len(batch)})")
            batch = []

    # 剩余部分
    if batch:
        with get_session() as db:
            for obj in batch:
                try:
                    db.add(obj)
                    inserted += 1
                except IntegrityError:
                    db.rollback()
                    skipped += 1
            db.commit()

    logger.info(f"写入完成: 新增 {inserted} 只, 跳过 {skipped} 只")
    return inserted, skipped


def step4_update_industry_ths():
    """步骤4：用同花顺行业分类精细化更新行业字段"""
    import akshare as ak

    logger.info("=" * 50)
    logger.info("步骤4：同花顺行业分类精细化...")
    logger.info("=" * 50)

    # 获取所有行业
    ind_df = ak.stock_board_industry_name_ths()
    industries = ind_df["name"].tolist()
    logger.info(f"共 {len(industries)} 个行业，开始匹配...")

    # 直接用股票名称关键词匹配行业（同花顺行业名称 -> 股票关键词）
    # 建立"行业 -> 关键词列表"映射
    industry_keywords = {}
    for ind in industries:
        keywords = []
        # 提取行业名中的特征字作为关键词
        for ch in ind:
            if ch not in keywords:
                keywords.append(ch)
        industry_keywords[ind] = keywords

    from .db_client import get_session
    from .models import StockPoolDB

    with get_session() as db:
        all_stocks = db.query(StockPoolDB).filter(StockPoolDB.status == 1).all()
        total = len(all_stocks)
        updated = 0

        for i, s in enumerate(all_stocks):
            name = s.name.replace(" ", "").replace("*", "")
            matched_ind = None
            max_score = 0

            for ind in industries:
                kws = industry_keywords[ind]
                score = sum(1 for kw in kws if kw in name and kw not in "ABCDEFGHIJ")
                if score > max_score:
                    max_score = score
                    matched_ind = ind

            if matched_ind and max_score >= 1:
                s.industry = matched_ind
                s.notes = _industry_desc(matched_ind)
                updated += 1

            if (i + 1) % 500 == 0:
                db.commit()
                logger.info(f"  已处理 {i+1}/{total}, 更新 {updated} 只")

        db.commit()

    logger.info(f"行业精细化完成: 更新 {updated} / {total} 只")


def main():
    logger.info("=" * 60)
    logger.info("QuantOS 全市场A股股票池初始化")
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 步骤1：拉全市场股票
    all_stocks = step1_fetch_all_stocks()

    # 步骤3：写入数据库
    inserted, skipped = step3_save_to_db(all_stocks)

    # 步骤4：行业精细化
    step4_update_industry_ths()

    # 统计
    from .db_client import get_session
    from .models import StockPoolDB
    from sqlalchemy import func

    with get_session() as db:
        total = db.query(func.count(StockPoolDB.id)).scalar()
        by_industry = db.query(
            StockPoolDB.industry,
            func.count(StockPoolDB.id)
        ).filter(StockPoolDB.status == 1).group_by(StockPoolDB.industry).order_by(
            func.count(StockPoolDB.id).desc()
        ).all()

    logger.info("=" * 50)
    logger.info(f"全市场股票池初始化完成！")
    logger.info(f"总股票数: {total} 只")
    logger.info(f"本次新增: {inserted} 只")
    logger.info(f"行业分布（前20）:")
    for ind, cnt in by_industry[:20]:
        logger.info(f"  {ind or '(未分类)':<15} {cnt:>5} 只")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
