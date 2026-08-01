#!/usr/bin/env python3
"""种子数据 — 预置示例岗位，测试看板用"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.db import FinanceJobDB
from scraper.platforms.company_careers import CompanyCareerScraper
from datetime import datetime

db = FinanceJobDB()

# 清空旧数据并重新初始化
db.conn.execute("DELETE FROM jobs")
db.conn.execute("DELETE FROM company_db")

# 先导入120家企业库
scraper = CompanyCareerScraper(db)
scraper.seed_companies()

# 插入示例岗位数据
SAMPLE_JOBS = [
    {"platform":"官网-中信证券","source_type":"company_careers","title":"行研实习生-新能源组","company":"中信证券","company_type":"券商","industry":"证券研究","location":"深圳","is_remote":False,"salary_raw":"150-200/天","salary_monthly_est":3850,"recruiter_email":"hr@citics.com","apply_url":"https://www.citics.com/careers","jd_raw":"【岗位职责】1、协助研究员完成行业数据收集与整理；2、撰写行业日报/周报；3、参与上市公司调研并撰写纪要；4、协助构建财务估值模型(DCF/可比公司法)。【要求】金融/经济相关专业硕士在读，CFA/CPA优先，熟练使用Wind/同花顺。"},
    {"platform":"猎聘","source_type":"platform","title":"投行部实习生","company":"中金公司","company_type":"券商","industry":"投资银行IBD","location":"北京","is_remote":False,"salary_raw":"200-300/天","salary_monthly_est":5500,"recruiter_email":"","apply_url":"https://www.liepin.com/job/xxx","jd_raw":"CICC投行部招聘实习生，参与IPO/再融资/并购项目执行，财务核查、招股书撰写、尽职调查。"},
    {"platform":"官网-腾讯","source_type":"company_careers","title":"战略投资分析实习生","company":"腾讯","company_type":"互联网战投","industry":"战略投资/战投","location":"深圳","is_remote":False,"salary_raw":"200-250/天","salary_monthly_est":4950,"recruiter_email":"talent@tencent.com","apply_url":"https://careers.tencent.com","jd_raw":"【岗位描述】1、对互联网/科技行业进行深度研究；2、协助投资团队进行项目sourcing和尽职调查；3、撰写投资备忘录和行业分析报告；4、跟踪portfolio公司运营数据。【要求】顶尖院校硕士/MBA在读，有PE/VC/投行实习经验优先。"},
    {"platform":"Boss直聘","source_type":"platform","title":"远程行研实习生-消费组","company":"华泰证券","company_type":"券商","industry":"证券研究","location":"远程","is_remote":True,"salary_raw":"120-180/天","salary_monthly_est":3300,"recruiter_email":"","apply_url":"https://www.zhipin.com/job/xxx","jd_raw":"远程行研实习生，覆盖消费行业。要求：能独立完成深度报告，有行研实习经验，每周至少3天。"},
    {"platform":"官网-高瓴资本","source_type":"company_careers","title":"投资实习生-科技方向","company":"高瓴资本","company_type":"PE/VC","industry":"PE/VC","location":"北京","is_remote":False,"salary_raw":"面议","salary_monthly_est":None,"recruiter_email":"careers@hillhousecap.com","apply_url":"https://www.hillhousecap.com/careers","jd_raw":"Hillhouse Capital is seeking intern for our technology investment team. Responsibilities include industry research, due diligence, financial modeling, and investment memo preparation."},
    {"platform":"51job","source_type":"platform","title":"量化研究实习生","company":"幻方量化","company_type":"量化私募","industry":"量化交易","location":"杭州","is_remote":False,"salary_raw":"300-500/天","salary_monthly_est":8800,"recruiter_email":"hr@high-flyer.cn","apply_url":"https://www.51job.com/job/xxx","jd_raw":"【岗位职责】1、研究股票/期货市场微观结构；2、开发与优化量化交易策略；3、进行因子挖掘与回测分析；4、维护交易系统与数据库。【要求】数学/物理/计算机/金融工程背景，精通Python，有竞赛经历优先。"},
    {"platform":"官网-易方达基金","source_type":"company_careers","title":"行业研究员实习生","company":"易方达基金","company_type":"公募基金","industry":"证券研究/行研","location":"广州","is_remote":False,"salary_raw":"面议","salary_monthly_est":None,"recruiter_email":"careers@efunds.com.cn","apply_url":"https://www.efunds.com.cn/careers","jd_raw":"易方达基金研究部招聘行业研究实习生，覆盖TMT/消费/医药/新能源等方向。"},
    {"platform":"官网-红杉中国","source_type":"company_careers","title":"投资实习生-Seed Stage","company":"红杉中国","company_type":"PE/VC","industry":"PE/VC","location":"上海","is_remote":False,"salary_raw":"面议","salary_monthly_est":None,"recruiter_email":"","apply_url":"https://www.sequoiacap.com/china/careers","jd_raw":"Sequoia Capital China is seeking seed stage investment intern based in Shanghai. Work directly with investment team on deal sourcing, market research and due diligence."},
    {"platform":"应届生求职网","source_type":"platform","title":"金融工程实习生","company":"东方财富","company_type":"评级/数据","industry":"金融科技","location":"上海","is_remote":False,"salary_raw":"150/天","salary_monthly_est":3300,"recruiter_email":"hr@eastmoney.com","apply_url":"https://www.yingjiesheng.com/job/xxx","jd_raw":"东方财富金融工程团队招聘实习生，参与金融数据产品开发、量化模型构建、数据可视化。"},
    {"platform":"官网-招商银行","source_type":"company_careers","title":"总行金融市场部实习生","company":"招商银行","company_type":"银行","industry":"银行总行管培","location":"深圳","is_remote":False,"salary_raw":"面议","salary_monthly_est":None,"recruiter_email":"","apply_url":"https://career.cmbchina.com","jd_raw":"招商银行总行金融市场部招聘实习生，学习利率/汇率/信用衍生品知识，协助市场分析报告撰写。"},
]

for job in SAMPLE_JOBS:
    job["scraped_at"] = datetime.now().isoformat()
    job["status"] = "new"
    db.insert_job(job)

print(f"✅ 已导入 {len(SAMPLE_JOBS)} 个示例岗位")
print(f"   公司库: {len(db.get_active_companies())} 家企业")
print(f"   现在运行评分: python3 -m scoring_engine.pipeline --dry")
db.close()
