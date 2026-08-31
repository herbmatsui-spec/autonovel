"""
AutoNovel 事業計画シミュレーションモデル (3カ年 P/L & シナリオ感度分析)
複合ハイブリッドモデル:
  Line 1: 自社IP出版 (Kindle / DLsite / FANBOX)
  Line 2: ツール販売 (BOOTH買い切り + DLC)
  Line 3: B2C SaaS (月額サブスク)
  Line 4: B2B受託 & 教育スクール
"""

from dataclasses import dataclass


@dataclass
class HybridScenario:
    name: str

    # Line 1: 自社出版
    kdp_monthly_books: int
    kdp_kenpc_reads_per_book: int
    dlsite_monthly_sales_per_book: int

    # Line 2: 買い切りツール (BOOTH/DLsite)
    standalone_units_monthly_y1: int
    standalone_units_monthly_y2: int
    standalone_units_monthly_y3: int
    standalone_price: int

    # Line 3: B2C SaaS
    saas_paid_users_m6: int
    saas_paid_users_m12: int
    saas_paid_users_m24: int
    saas_paid_users_m36: int
    saas_arpu: int
    saas_churn_rate: float

    # Line 4: B2B受託 & スクール
    b2b_projects_annual_y1: int
    b2b_projects_annual_y2: int
    b2b_projects_annual_y3: int
    b2b_avg_price: int

    school_students_annual_y1: int
    school_students_annual_y2: int
    school_students_annual_y3: int
    school_tuition: int

def simulate_year(year: int, sc: HybridScenario) -> dict[str, float]:
    # 1. 自社出版 (年間累積効果)
    # 累積作品数（陳腐化減衰率を考慮: 年間30%減衰）
    books_cumulative = sc.kdp_monthly_books * 12 * (1 if year == 1 else (1.7 if year == 2 else 2.2))
    kenpc_rev = books_cumulative * sc.kdp_kenpc_reads_per_book * 140 * 0.5 * 12
    dlsite_rev = books_cumulative * sc.dlsite_monthly_sales_per_book * 600 * 0.4 * 12
    line1_rev = kenpc_rev + dlsite_rev
    line1_cost = sc.kdp_monthly_books * 12 * 360  # 1冊あたりAPI代360円

    # 2. 買い切りツール
    units = (
        sc.standalone_units_monthly_y1 if year == 1
        else (sc.standalone_units_monthly_y2 if year == 2 else sc.standalone_units_monthly_y3)
    ) * 12
    line2_rev = units * sc.standalone_price
    line2_cost = line2_rev * 0.05  # 手数料・サポート

    # 3. B2C SaaS (期末平均アクティブ課金数で試算)
    users = (
        (sc.saas_paid_users_m6 + sc.saas_paid_users_m12) / 2 if year == 1
        else (sc.saas_paid_users_m24 if year == 2 else sc.saas_paid_users_m36)
    )
    line3_rev = users * sc.saas_arpu * 12
    line3_cost = users * 12 * (sc.saas_arpu * 0.15 + 300)  # LLM原価(15%) + サーバーインフラ等

    # 4. B2B & スクール
    b2b_proj = sc.b2b_projects_annual_y1 if year == 1 else (sc.b2b_projects_annual_y2 if year == 2 else sc.b2b_projects_annual_y3)
    school_st = sc.school_students_annual_y1 if year == 1 else (sc.school_students_annual_y2 if year == 2 else sc.school_students_annual_y3)
    line4_rev = (b2b_proj * sc.b2b_avg_price) + (school_st * sc.school_tuition)
    line4_cost = line4_rev * 0.10  # 制作原価・教材更新

    total_rev = line1_rev + line2_rev + line3_rev + line4_rev
    total_cogs = line1_cost + line2_cost + line3_cost + line4_cost
    gross_profit = total_rev - total_cogs

    # 販管費 (SGA: 広告宣伝費、ツール代、外注費等)
    sga = 300_000 if year == 1 else (1_200_000 if year == 2 else 2_400_000)
    operating_profit = gross_profit - sga
    op_margin = (operating_profit / total_rev * 100) if total_rev > 0 else 0

    return {
        "year": year,
        "line1_rev": line1_rev,
        "line2_rev": line2_rev,
        "line3_rev": line3_rev,
        "line4_rev": line4_rev,
        "total_revenue": total_rev,
        "cogs": total_cogs,
        "gross_profit": gross_profit,
        "sga": sga,
        "operating_profit": operating_profit,
        "operating_margin_pct": op_margin,
    }

def run():
    scenarios = [
        HybridScenario(
            name="保守的 / 堅実シナリオ (Pessimistic-Realistic)",
            kdp_monthly_books=4,
            kdp_kenpc_reads_per_book=5,
            dlsite_monthly_sales_per_book=1,
            standalone_units_monthly_y1=10,
            standalone_units_monthly_y2=15,
            standalone_units_monthly_y3=15,
            standalone_price=9800,
            saas_paid_users_m6=20,
            saas_paid_users_m12=50,
            saas_paid_users_m24=120,
            saas_paid_users_m36=250,
            saas_arpu=2980,
            saas_churn_rate=0.08,
            b2b_projects_annual_y1=1,
            b2b_projects_annual_y2=3,
            b2b_projects_annual_y3=5,
            b2b_avg_price=400000,
            school_students_annual_y1=10,
            school_students_annual_y2=25,
            school_students_annual_y3=40,
            school_tuition=98000,
        ),
        HybridScenario(
            name="標準 / 目標シナリオ (Standard-Realistic)",
            kdp_monthly_books=8,
            kdp_kenpc_reads_per_book=15,
            dlsite_monthly_sales_per_book=4,
            standalone_units_monthly_y1=25,
            standalone_units_monthly_y2=40,
            standalone_units_monthly_y3=40,
            standalone_price=14800,
            saas_paid_users_m6=50,
            saas_paid_users_m12=150,
            saas_paid_users_m24=400,
            saas_paid_users_m36=800,
            saas_arpu=3480,
            saas_churn_rate=0.05,
            b2b_projects_annual_y1=2,
            b2b_projects_annual_y2=6,
            b2b_projects_annual_y3=12,
            b2b_avg_price=600000,
            school_students_annual_y1=25,
            school_students_annual_y2=60,
            school_students_annual_y3=100,
            school_tuition=148000,
        ),
        HybridScenario(
            name="成長 / 楽観シナリオ (Aggressive-Growth)",
            kdp_monthly_books=12,
            kdp_kenpc_reads_per_book=35,
            dlsite_monthly_sales_per_book=10,
            standalone_units_monthly_y1=50,
            standalone_units_monthly_y2=80,
            standalone_units_monthly_y3=80,
            standalone_price=19800,
            saas_paid_users_m6=120,
            saas_paid_users_m12=400,
            saas_paid_users_m24=1200,
            saas_paid_users_m36=2500,
            saas_arpu=3980,
            saas_churn_rate=0.035,
            b2b_projects_annual_y1=4,
            b2b_projects_annual_y2=12,
            b2b_projects_annual_y3=24,
            b2b_avg_price=800000,
            school_students_annual_y1=50,
            school_students_annual_y2=120,
            school_students_annual_y3=200,
            school_tuition=198000,
        ),
    ]

    for sc in scenarios:
        print("=" * 80)
        print(f"【シナリオ: {sc.name}】")
        print("=" * 80)
        print(f"{'項目':<18} | {'1年目 (Year 1)':<16} | {'2年目 (Year 2)':<16} | {'3年目 (Year 3)':<16}")
        print("-" * 80)

        y1 = simulate_year(1, sc)
        y2 = simulate_year(2, sc)
        y3 = simulate_year(3, sc)

        print(f"{'自社出版(KDP/DLsite)':<16} | ¥{y1['line1_rev']:>14,.0f} | ¥{y2['line1_rev']:>14,.0f} | ¥{y3['line1_rev']:>14,.0f}")
        print(f"{'買い切りツール(BOOTH)':<16} | ¥{y1['line2_rev']:>14,.0f} | ¥{y2['line2_rev']:>14,.0f} | ¥{y3['line2_rev']:>14,.0f}")
        print(f"{'B2C SaaS (月額)':<18} | ¥{y1['line3_rev']:>14,.0f} | ¥{y2['line3_rev']:>14,.0f} | ¥{y3['line3_rev']:>14,.0f}")
        print(f"{'B2B受託・スクール':<17} | ¥{y1['line4_rev']:>14,.0f} | ¥{y2['line4_rev']:>14,.0f} | ¥{y3['line4_rev']:>14,.0f}")
        print("-" * 80)
        print(f"{'【売上高合計】':<17} | ¥{y1['total_revenue']:>14,.0f} | ¥{y2['total_revenue']:>14,.0f} | ¥{y3['total_revenue']:>14,.0f}")
        print(f"{'売上原価 (COGS)':<17} | ¥{y1['cogs']:>14,.0f} | ¥{y2['cogs']:>14,.0f} | ¥{y3['cogs']:>14,.0f}")
        print(f"{'売上総利益 (粗利)':<16} | ¥{y1['gross_profit']:>14,.0f} | ¥{y2['gross_profit']:>14,.0f} | ¥{y3['gross_profit']:>14,.0f}")
        print(f"{'販管費 (SGA)':<19} | ¥{y1['sga']:>14,.0f} | ¥{y2['sga']:>14,.0f} | ¥{y3['sga']:>14,.0f}")
        print(f"{'【営業利益】':<18} | ¥{y1['operating_profit']:>14,.0f} | ¥{y2['operating_profit']:>14,.0f} | ¥{y3['operating_profit']:>14,.0f}")
        print(f"{'営業利益率 (%)':<17} | {y1['operating_margin_pct']:>13.1f}% | {y2['operating_margin_pct']:>13.1f}% | {y3['operating_margin_pct']:>13.1f}%")
        print("\n")

if __name__ == "__main__":
    run()
