import streamlit as st
import pandas as pd
import numpy as np
import warnings
import base64
import io
import zipfile
from datetime import datetime
warnings.filterwarnings('ignore')

# Plotlyが利用可能かチェック
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.io as pio
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("Plotly library not found. Graph functionality will be disabled.")

# PDFライブラリの確認
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ページ設定
st.set_page_config(
    page_title="KOA Basketball Academy - Physical Test Dashboard",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%);
        padding: 2.5rem;
        border-radius: 0px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        font-weight: 700;
        font-size: 2.8rem;
        box-shadow: 0 8px 32px rgba(27, 94, 32, 0.3);
        border-left: 6px solid #1B5E20;
    }
    
    .academy-logo {
        font-size: 1.2rem;
        font-weight: 500;
        margin-top: 0.5rem;
        color: #C8E6C9;
        letter-spacing: 2px;
    }
    
    .section-header {
        background: linear-gradient(135deg, #2E7D32 0%, #388E3C 100%);
        padding: 1.2rem 2rem;
        border-radius: 0px;
        color: white;
        font-weight: 600;
        margin: 2rem 0 1.5rem 0;
        font-size: 1.4rem;
        box-shadow: 0 4px 16px rgba(46, 125, 50, 0.2);
        border-left: 4px solid #1B5E20;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        padding: 2rem;
        border-radius: 8px;
        margin: 0.75rem;
        color: white;
        text-align: center;
        box-shadow: 0 8px 24px rgba(76, 175, 80, 0.15);
        transition: all 0.3s ease;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .highlight-metric {
        font-size: 2.4rem;
        font-weight: 700;
        margin: 0.8rem 0;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .metric-label {
        font-size: 1.2rem;
        margin-bottom: 0.8rem;
        opacity: 0.95;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .comparison-text {
        font-size: 1rem;
        opacity: 0.85;
        margin-top: 0.8rem;
        font-weight: 400;
    }
    
    .player-title {
        color: #1B5E20;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 1rem;
        padding: 1rem 0;
        border-bottom: 3px solid #4CAF50;
    }
    
    .date-info {
        background: linear-gradient(135deg, #E8F5E8 0%, #C8E6C9 100%);
        padding: 1rem;
        border-radius: 8px;
        color: #1B5E20;
        font-weight: 500;
        text-align: center;
        border: 1px solid #A5D6A7;
    }
</style>
""", unsafe_allow_html=True)

# データ読み込み関数
@st.cache_data
def load_data_from_file(uploaded_file):
    """アップロードされたファイルからデータを読み込む関数"""
    try:
        if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            df = pd.read_excel(uploaded_file, header=0)
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=0)
        else:
            st.error("対応していないファイル形式です。Excel (.xlsx, .xls) または CSV ファイルをアップロードしてください。")
            return pd.DataFrame()
        
        # 列名をマッピング
        column_mapping = {
            'カテゴリー': 'Category',
            '氏名': 'Name', 
            'date': 'Date',
            '身長': 'Height',
            '体重': 'Weight',
            'BMI': 'BMI',
            '成熟度': 'Maturity',
            '10mスプリント': '10m_Sprint',
            '505テスト(前方スプリント)': '505_Test_Forward',
            '505テスト(バックペダル)': '505_Test_Backward',
            '505テスト': '505_Test_Backward',  # 従来の505テストは後方として扱う
            'CODD': 'CODD',
            'BJ（実測値）': 'BJ_Raw',
            'BJ': 'BJ',
            'SH(R)': 'SH_R',
            'SH(L)': 'SH_L',
            'SH': 'SH',
            'SJ': 'SJ',
            'CMJ': 'CMJ',
            'RJ': 'RJ',
            'Coment': 'Comment'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 不要な列を削除
        columns_to_drop = ['BJ_Raw', 'SH_R', 'SH_L', 'Comment']
        existing_drop_columns = [col for col in columns_to_drop if col in df.columns]
        if existing_drop_columns:
            df = df.drop(columns=existing_drop_columns)
        
        # データ型の変換
        if 'Date' in df.columns:
            df['Date'] = df['Date'].apply(lambda x: convert_date_format(x))
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # 数値列の変換
        numeric_columns = ['Height', 'Weight', 'BMI', 'Maturity', '10m_Sprint', '505_Test_Forward', '505_Test_Backward', 'CODD', 'BJ', 'SH', 'SJ', 'CMJ', 'RJ']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # SHの値を100倍にして%表記に変換
        if 'SH' in df.columns:
            df['SH'] = df['SH'] * 100
        
        # 空行を削除
        df = df.dropna(how='all')
        
        # Name列がNaNまたは空の行を削除
        if 'Name' in df.columns:
            df = df.dropna(subset=['Name'])
            df = df[df['Name'].str.strip() != '']
        
        return df
        
    except Exception as e:
        st.error(f"データ読み込みエラー: {str(e)}")
        return pd.DataFrame()

def convert_date_format(date_str):
    """日付文字列を標準形式に変換"""
    if pd.isna(date_str) or date_str == '':
        return None
    
    try:
        if isinstance(date_str, str):
            if '.' in date_str:
                parts = date_str.split('.')
                if len(parts) == 2:
                    month_str, day_str = parts
                    month_map = {
                        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                    }
                    if month_str in month_map:
                        year = 2024
                        month = month_map[month_str]
                        day = int(day_str)
                        return f"{year}-{month:02d}-{day:02d}"
        
        return date_str
        
    except:
        return date_str

def get_test_config():
    """テスト設定"""
    return {
        'Body Composition': {
            'name': '身体組成',
            'score_metrics': ['Height', 'Weight'],
            'display_metrics': ['Height', 'Weight', 'BMI', 'Maturity'],
            'units': {
                'Height': 'cm',
                'Weight': 'kg',
                'BMI': '',
                'Maturity': ''
            },
            'highlight': ['Height', 'Weight', 'BMI'],
            'japanese_names': {
                'Height': '身長',
                'Weight': '体重',
                'BMI': 'BMI',
                'Maturity': '成熟度'
            },
            'reverse_scoring': False
        },
        'Agility': {
            'name': '俊敏性',
            'score_metrics': ['10m_Sprint', '505_Test_Forward', '505_Test_Backward'],
            'display_metrics': ['10m_Sprint', '505_Test_Forward', '505_Test_Backward', 'CODD'],
            'units': {
                '10m_Sprint': 'sec',
                '505_Test_Forward': 'sec',
                '505_Test_Backward': 'sec',
                'CODD': 'sec'
            },
            'highlight': ['10m_Sprint', '505_Test_Forward', '505_Test_Backward'],
            'japanese_names': {
                '10m_Sprint': '10mスプリント',
                '505_Test_Forward': '505テスト(前方)',
                '505_Test_Backward': '505テスト(後方)',
                'CODD': 'CODD'
            },
            'reverse_scoring': True
        },
        'Jumping': {
            'name': '跳躍力',
            'score_metrics': ['BJ', 'SJ', 'CMJ', 'RJ'],
            'display_metrics': ['BJ', 'SH', 'SJ', 'CMJ', 'RJ'],
            'units': {
                'BJ': 'cm',
                'SH': '%',
                'SJ': 'cm',
                'CMJ': 'cm',
                'RJ': 'index'
            },
            'highlight': ['BJ', 'CMJ', 'RJ'],
            'japanese_names': {
                'BJ': 'BJ',
                'SH': 'サイドホップテスト',
                'SJ': 'SJ',
                'CMJ': 'CMJ',
                'RJ': 'RJ'
            },
            'reverse_scoring': False
        }
    }

def calculate_individual_score(value, category_values, reverse_scoring=False):
    """個別項目のスコアを計算（1-5のスケール）"""
    try:
        if len(category_values) < 2:
            return 3
        
        category_mean = np.mean(category_values)
        category_std = np.std(category_values)
        
        if category_std == 0:
            return 3
        
        z_score = (value - category_mean) / category_std
        
        if reverse_scoring:
            if z_score < -1.5:
                score = 5
            elif z_score < -1.0:
                score = 4
            elif z_score <= 1.0:
                score = 3
            elif z_score <= 1.5:
                score = 2
            else:
                score = 1
        else:
            if z_score < -1.5:
                score = 1
            elif z_score < -1.0:
                score = 2
            elif z_score <= 1.0:
                score = 3
            elif z_score <= 1.5:
                score = 4
            else:
                score = 5
        
        return score
        
    except Exception:
        return 3

def calculate_section_score(player_data, all_data, score_metrics, reverse_scoring=False):
    """セクションのスコアを計算"""
    try:
        player_category = None
        if 'Category' in player_data.columns and not player_data['Category'].isna().all():
            valid_categories = player_data['Category'].dropna()
            if not valid_categories.empty:
                player_category = valid_categories.iloc[0]
        
        if player_category is None:
            category_data = all_data
            category_label = "全体"
        else:
            category_data = all_data[all_data['Category'] == player_category]
            category_label = str(player_category)
        
        if category_data.empty:
            return None, f"カテゴリー '{category_label}' のデータなし"
        
        item_scores = []
        
        for metric in score_metrics:
            player_value = safe_get_value(player_data, metric)
            if player_value is None:
                continue
            
            category_values = []
            for name, category_player_row in category_data.groupby('Name'):
                latest_value = safe_get_value(category_player_row, metric)
                if latest_value is not None:
                    category_values.append(latest_value)
            
            if len(category_values) < 2:
                continue
            
            item_score = calculate_individual_score(player_value, category_values, reverse_scoring)
            item_scores.append(item_score)
        
        if not item_scores:
            return None, "有効な測定項目なし"
        
        section_score = round(np.mean(item_scores))
        
        return section_score, f"カテゴリー: {category_label}"
        
    except Exception as e:
        return None, f"計算エラー: {str(e)}"

def calculate_overall_score(section_scores):
    """総合スコアを計算"""
    try:
        valid_scores = [score for score in section_scores.values() if score is not None and score > 0]
        
        if not valid_scores:
            return None, "有効なセクションスコアなし"
        
        overall_score = round(np.mean(valid_scores))
        return overall_score, f"セクション平均: {np.mean(valid_scores):.1f}"
        
    except Exception as e:
        return None, f"総合計算エラー: {str(e)}"

def safe_get_value(data, column, default=None):
    """安全に最新値を取得する関数"""
    try:
        if column not in data.columns or data.empty:
            return default
        
        valid_data = data[data[column].notna()]
        valid_data = valid_data[valid_data[column] != '']
        # SH列の場合は0も有効な値として扱う
        if column != 'SH':
            valid_data = valid_data[valid_data[column] != 0]
        
        if valid_data.empty:
            return default
        
        if 'Date' in valid_data.columns:
            # 日付でソートして最新の値を取得
            latest_valid = valid_data.sort_values('Date', ascending=False).iloc[0]
            value = latest_valid[column]
        else:
            value = valid_data.iloc[-1][column]
        
        if pd.isna(value) or value == '':
            return default
        
        # SH列の場合は0も有効な値として返す
        if column == 'SH' and value == 0:
            return 0.0
        
        if isinstance(value, (int, float, np.number)):
            if np.isfinite(value):
                return float(value)
        
        return default
        
    except Exception as e:
        return default

def create_radar_chart(scores, section_names):
    """レーダーチャートを作成"""
    if not PLOTLY_AVAILABLE:
        return None
    
    fig = go.Figure()
    
    categories = section_names + [section_names[0]]
    values = list(scores.values()) + [list(scores.values())[0]]
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(76, 175, 80, 0.3)',
        line=dict(color='#2E7D32', width=3),
        marker=dict(
            size=12,
            color='#1B5E20',
            line=dict(width=2, color='white')
        ),
        name='総合スコア'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[1, 5],
                tickvals=[1, 2, 3, 4, 5],
                ticktext=['1', '2', '3', '4', '5'],
                gridcolor='rgba(76, 175, 80, 0.2)',
                linecolor='rgba(76, 175, 80, 0.3)'
            ),
            angularaxis=dict(
                gridcolor='rgba(76, 175, 80, 0.2)',
                linecolor='rgba(76, 175, 80, 0.3)'
            ),
            bgcolor='rgba(248, 250, 252, 0.8)'
        ),
        showlegend=False,
        title=dict(
            text="<b>総合フィジカルスコア</b>",
            x=0.5,
            font=dict(size=18, color='#1B5E20')
        ),
        height=400,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig

def get_individual_metric_score(player_data, all_data, metric, reverse_scoring=False):
    """個別の測定項目のスコアを取得"""
    try:
        player_category = None
        if 'Category' in player_data.columns and not player_data['Category'].isna().all():
            valid_categories = player_data['Category'].dropna()
            if not valid_categories.empty:
                player_category = valid_categories.iloc[0]
        
        if player_category is None:
            category_data = all_data
        else:
            category_data = all_data[all_data['Category'] == player_category]
        
        player_value = safe_get_value(player_data, metric)
        if player_value is None:
            return None
        
        category_values = []
        for name, category_player_row in category_data.groupby('Name'):
            latest_value = safe_get_value(category_player_row, metric)
            if latest_value is not None:
                category_values.append(latest_value)
        
        if len(category_values) < 2:
            return None
        
        score = calculate_individual_score(player_value, category_values, reverse_scoring)
        return score
        
    except:
        return None

def analyze_progress_with_values(player_data, metrics_info):
    """前回との詳細な数値比較分析を行う"""
    try:
        if len(player_data) < 2:
            return None
        
        # 日付でソートして最新と前回を取得
        sorted_data = player_data.sort_values('Date', ascending=False)
        
        comparison_results = []
        
        for metric, info in metrics_info.items():
            if metric not in player_data.columns:
                continue
                
            # 最新の有効値と、それ以前の有効値を探す
            values = []
            for idx, row in sorted_data.iterrows():
                val = row[metric]
                # SHは0も有効、他は0を除外
                if pd.notna(val) and val != '':
                    if metric == 'SH' or val != 0:
                        values.append(float(val))
                        if len(values) >= 2:
                            break
            
            if len(values) >= 2:
                latest = values[0]
                prev = values[1]
                
                is_reverse = info['reverse']
                diff = latest - prev
                
                # 改善判定
                improved = False
                if is_reverse: # タイム系：小さい方が良い
                    if diff < 0: improved = True
                else: # 距離系：大きい方が良い
                    if diff > 0: improved = True
                    
                # 変化なし（非常に小さい変化）
                unchanged = abs(diff) < 0.001
                
                comparison_results.append({
                    'metric': metric,
                    'name': info['name'],
                    'latest': latest,
                    'prev': prev,
                    'diff': diff,
                    'improved': improved and not unchanged,
                    'unchanged': unchanged,
                    'unit': info.get('unit', '')
                })
                
        return comparison_results
    except Exception as e:
        return None

def generate_personalized_feedback(section_scores, player_data, all_data, player_name):
    """
    選手の個別フィードバックを生成
    前回値との比較数値を具体的に含めるように改修
    """
    try:
        feedback = []
        
        # 測定項目の定義（単位含む）
        agility_metrics = {
            '10m_Sprint': {'name': '10mスプリント', 'reverse': True, 'unit': '秒'},
            '505_Test_Forward': {'name': '505テスト(前方)', 'reverse': True, 'unit': '秒'},
            '505_Test_Backward': {'name': '505テスト(後方)', 'reverse': True, 'unit': '秒'},
            'CODD': {'name': 'CODD', 'reverse': True, 'unit': '秒'}
        }
        
        jumping_metrics = {
            'BJ': {'name': '立ち幅跳び', 'reverse': False, 'unit': 'cm'},
            'SH': {'name': 'サイドホップ', 'reverse': True, 'unit': '%'}, 
            'SJ': {'name': 'スクワットジャンプ', 'reverse': False, 'unit': 'cm'},
            'CMJ': {'name': '垂直跳び', 'reverse': False, 'unit': 'cm'},
            'RJ': {'name': 'リバウンドジャンプ', 'reverse': False, 'unit': ''}
        }
        
        all_metrics_info = {**agility_metrics, **jumping_metrics}
        
        # セクションスコア
        valid_section_scores = {k: v for k, v in section_scores.items() if v > 0}
        if not valid_section_scores:
            return "データが不足しているため、詳細な分析ができません。"
        
        overall_avg = sum(valid_section_scores.values()) / len(valid_section_scores)
        
        # --- 1. 導入（総合評価） ---
        if overall_avg >= 4.5:
            intro = "非常に優れた総合フィジカル能力を示しており、各項目で高いパフォーマンスを発揮しています。"
        elif overall_avg >= 4:
            intro = "全体的に高いレベルのフィジカル能力を有しており、日頃のトレーニングの成果が表れています。"
        elif overall_avg >= 3:
            intro = "バランスの取れたフィジカル能力を持っています。強みを伸ばしつつ、課題に取り組むことで更なる成長が期待できます。"
        else:
            intro = "伸びしろが非常に大きく、これからのトレーニング次第で飛躍的に数値を向上させるポテンシャルを秘めています。"
        
        feedback.append(intro)
        
        # --- 2. 前回比較（数値を含む詳細分析） ---
        comparison_results = analyze_progress_with_values(player_data, all_metrics_info)
        
        if comparison_results:
            improved_items = [item for item in comparison_results if item['improved']]
            declined_items = [item for item in comparison_results if not item['improved'] and not item['unchanged']]
            
            # 測定日の取得（最新と前回）
            dates = player_data['Date'].dropna().sort_values(ascending=False)
            prev_date_str = ""
            if len(dates) >= 2:
                prev_date_str = f"（前回:{dates.iloc[1].strftime('%Y/%m/%d')}）"
            
            if improved_items:
                feedback.append(f"\n\n【前回{prev_date_str}からの向上】")
                feedback.append("前回の測定と比較して、以下の項目で具体的な向上が確認できました。")
                
                lines = []
                for item in improved_items:
                    unit = item['unit']
                    # 少数点以下の処理
                    if unit in ['cm', '%']:
                        fmt_prev = f"{item['prev']:.1f}"
                        fmt_curr = f"{item['latest']:.1f}"
                        fmt_diff = f"{abs(item['diff']):.1f}"
                    else: # 秒など
                        fmt_prev = f"{item['prev']:.2f}"
                        fmt_curr = f"{item['latest']:.2f}"
                        fmt_diff = f"{abs(item['diff']):.2f}"
                        
                    lines.append(f"・{item['name']}：{fmt_prev}{unit} → {fmt_curr}{unit} ({fmt_diff}{unit}向上)")
                
                feedback.append("\n".join(lines))
                feedback.append("継続的な努力が数値として表れています。")

            if declined_items:
                # 3つ以上ある場合は絞るか、表現を柔らかくする
                display_declined = declined_items[:3]
                
                feedback.append(f"\n\n【今後の課題】")
                feedback.append("以下の項目では数値の変化が見られました。コンディションの影響も考えられますが、次回の目標として意識してみましょう。")
                
                lines = []
                for item in display_declined:
                    unit = item['unit']
                    if unit in ['cm', '%']:
                        fmt_prev = f"{item['prev']:.1f}"
                        fmt_curr = f"{item['latest']:.1f}"
                    else:
                        fmt_prev = f"{item['prev']:.2f}"
                        fmt_curr = f"{item['latest']:.2f}"
                    
                    lines.append(f"・{item['name']}：{fmt_prev}{unit} → {fmt_curr}{unit}")
                
                feedback.append("\n".join(lines))
        else:
            feedback.append("\n\n※比較対象となる過去のデータが十分にないため、今回は現在の数値に基づいた評価となります。次回以降、成長の推移を確認できます。")

        # --- 3. 強みと推奨トレーニング ---
        # スコアが高い項目、低い項目を抽出
        agility_score = section_scores.get('俊敏性', 0)
        jumping_score = section_scores.get('跳躍力', 0)
        
        high_metric_names = []
        low_metric_names = []
        
        for metric, info in all_metrics_info.items():
            score = get_individual_metric_score(player_data, all_data, metric, info['reverse'])
            if score:
                if score >= 4:
                    high_metric_names.append(info['name'])
                elif score <= 2:
                    low_metric_names.append(info['name'])
        
        # 強みのコメント
        if high_metric_names:
            feedback.append(f"\n\n【強み】\n特に「{'、'.join(high_metric_names[:3])}」のスコアが優秀です。")
            feedback.append("これらの能力は試合中の大きな武器になります。自信を持ってプレーに活かしてください。")
            
        # トレーニングアドバイス
        feedback.append("\n\n【アドバイス】")
        suggestions = []
        
        # 俊敏性が課題の場合
        if agility_score <= 3 or any(m in low_metric_names for m in ['10mスプリント', 'CODD']):
            suggestions.append("俊敏性を高めるために、アジリティラダーを使った細かいステップ練習や、短い距離でのダッシュ（スタートの反応）を練習に取り入れましょう。")
            
        # 跳躍力が課題の場合
        if jumping_score <= 3 or any(m in low_metric_names for m in ['立ち幅跳び', '垂直跳び']):
            suggestions.append("跳躍力を向上させるために、正しいスクワットフォームでの筋力強化や、ボックスジャンプなどのプライオメトリクストレーニングが効果的です。")
            
        # サイドホップ（バランス）が課題
        if any('サイドホップ' in m for m in low_metric_names):
             suggestions.append("サイドホップの数値からは、足首の安定性やバランス能力の向上が見込めます。片足立ちでのバランス練習や体幹トレーニングを意識しましょう。")

        if not suggestions:
            suggestions.append("現在の良好なコンディションを維持するために、ストレッチやケアを十分に行い、怪我の予防に努めてください。")
            
        feedback.append("\n".join(suggestions))
        
        # --- 4. 結び ---
        feedback.append("\n\n次回の測定でも自己ベスト更新を目指して頑張りましょう。")
        
        return "".join(feedback)
        
    except Exception as e:
        return f"フィードバック生成中にエラーが発生しました: {str(e)}"

def safe_get_best_value(data, column, default=None):
    """安全に最高値（またはタイム系は最小値）を取得する関数"""
    try:
        if column not in data.columns or data.empty:
            return default, default
        
        valid_data = data[data[column].notna()]
        valid_data = valid_data[valid_data[column] != '']
        # SH列の場合は0も有効な値として扱う
        if column != 'SH':
            valid_data = valid_data[valid_data[column] != 0]
        
        if valid_data.empty:
            return default, default
        
        numeric_values = pd.to_numeric(valid_data[column], errors='coerce')
        clean_values = numeric_values.dropna()
        
        if clean_values.empty:
            return default, default
        
        # タイム系の測定項目（小さい方が良い）は最小値を取得
        time_based_metrics = ['10m_Sprint', '505_Test_Forward', '505_Test_Backward', 'CODD']
        
        if column in time_based_metrics:
            best_value = clean_values.min()
            best_idx = clean_values.idxmin()
        else:
            best_value = clean_values.max()
            best_idx = clean_values.idxmax()
        
        best_date = "N/A"
        if 'Date' in data.columns and best_idx in data.index:
            date_val = data.loc[best_idx, 'Date']
            if pd.notna(date_val):
                best_date = date_val.strftime('%Y-%m-%d')
        
        return float(best_value), best_date
        
    except Exception:
        return default, default

def safe_mean(series):
    """安全に平均値を計算"""
    if series.empty:
        return None
    numeric_series = pd.to_numeric(series, errors='coerce')
    clean_series = numeric_series.dropna()
    clean_series = clean_series[clean_series != 0]
    return clean_series.mean() if len(clean_series) > 0 else None

def format_value(value, unit=""):
    """値の安全なフォーマット"""
    if value is None or pd.isna(value):
        return "N/A"
    try:
        formatted_val = f"{float(value):.2f}"
        return f"{formatted_val}{unit}" if unit else formatted_val
    except:
        return "N/A"

def get_target_values():
    """エクセルファイルの目標値を定義"""
    return {
        # 身体組成系は目標値なし
        'Height': None,
        'Weight': None, 
        'BMI': None,
        'Maturity': None,
        # 俊敏性・跳躍力のみ目標値あり
        '10m_Sprint': {'U15': 1.7, 'U12': 1.9},
        '505_Test_Forward': {'U15': 2.8, 'U12': 3.2},
        '505_Test_Backward': {'U15': 3.0, 'U12': 3.0},
        'CODD': {'U15': 1.0, 'U12': 1.0},
        'BJ': {'U15': 80, 'U12': 60},
        'SH': {'U15': 15.0, 'U12': 15.0},
        'SJ': {'U15': 40, 'U12': 35},
        'CMJ': {'U15': 50, 'U12': 45},
        'RJ': {'U15': 2.0, 'U12': 1.8}
    }

def get_target_value_for_player(player_data, metric, target_values):
    """選手のカテゴリーに応じた目標値を取得"""
    try:
        # 身体組成系は目標値なし
        if target_values.get(metric) is None:
            return None
            
        # 選手のカテゴリーを取得
        player_category = "U15"  # デフォルト
        if 'Category' in player_data.columns and not player_data['Category'].isna().all():
            valid_categories = player_data['Category'].dropna()
            if not valid_categories.empty:
                category_str = str(valid_categories.iloc[0])
                if 'U12' in category_str or '12' in category_str:
                    player_category = "U12"
                elif 'U15' in category_str or '15' in category_str:
                    player_category = "U15"
        
        if metric in target_values and target_values[metric] is not None and player_category in target_values[metric]:
            return target_values[metric][player_category]
        return None
    except:
        return None

def create_comparison_table(player_data, all_data, metrics, category, config):
    """比較表の作成"""
    table_data = []
    target_values = get_target_values()
    
    japanese_names = config[category].get('japanese_names', {})
    
    for metric in metrics:
        player_val = safe_get_value(player_data, metric)
        best_val, best_date = safe_get_best_value(player_data, metric)
        avg_val = safe_mean(all_data[metric])
        target_val = get_target_value_for_player(player_data, metric, target_values)
        
        measurement_date = "N/A"
        if player_val is not None:
            valid_data = player_data.dropna(subset=[metric])
            valid_data = valid_data[valid_data[metric] != 0]
            if not valid_data.empty and 'Date' in valid_data.columns:
                latest_valid = valid_data.sort_values('Date', ascending=False).iloc[0]
                measurement_date = latest_valid['Date'].strftime('%Y-%m-%d') if pd.notna(latest_valid['Date']) else "N/A"
        
        best_value_text = "N/A"
        if best_val is not None:
            best_value_text = f"{best_val:.2f}"
            if best_date != "N/A":
                best_value_text += f" ({best_date})"
        
        display_name = japanese_names.get(metric, metric)
        
        table_data.append({
            '項目': display_name,
            '最新値': format_value(player_val),
            '測定日': measurement_date,
            '自己ベスト': best_value_text,
            'カテゴリー平均': format_value(avg_val),
            '目標値': format_value(target_val) if target_val is not None else "N/A"
        })
    
    return pd.DataFrame(table_data)

def create_trend_chart(player_data, metrics, title, units, japanese_names):
    """トレンドチャートの作成"""
    if not PLOTLY_AVAILABLE:
        return None
        
    if len(player_data) < 2:
        return None
    
    player_data = player_data.sort_values('Date')
    
    available_metrics = []
    for metric in metrics:
        if metric in player_data.columns:
            data_with_values = player_data.dropna(subset=[metric])
            data_with_values = data_with_values[data_with_values[metric] != 0]
            if len(data_with_values) >= 2:
                available_metrics.append(metric)
    
    if not available_metrics:
        return None
    
    rows = (len(available_metrics) + 1) // 2
    cols = min(2, len(available_metrics))
    
    subplot_titles = []
    for metric in available_metrics:
        display_name = japanese_names.get(metric, metric)
        subplot_titles.append(f"<b>{display_name}</b>")
    
    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=subplot_titles,
        vertical_spacing=0.18,
        horizontal_spacing=0.15
    )
    
    colors = ['#1B5E20', '#2E7D32', '#388E3C', '#4CAF50', '#66BB6A', '#81C784']
    
    for i, metric in enumerate(available_metrics):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        data_with_values = player_data.dropna(subset=[metric])
        data_with_values = data_with_values[data_with_values[metric] != 0]
        
        if len(data_with_values) >= 2:
            fig.add_trace(
                go.Scatter(
                    x=data_with_values['Date'],
                    y=data_with_values[metric],
                    mode='lines+markers',
                    name=japanese_names.get(metric, metric),
                    line=dict(
                        color=colors[i % len(colors)], 
                        width=4,
                        shape='spline',
                        smoothing=0.3
                    ),
                    marker=dict(
                        size=10, 
                        line=dict(width=3, color='white'),
                        symbol='circle'
                    ),
                    showlegend=False,
                    hovertemplate='<b>%{fullData.name}</b><br>日付: %{x}<br>値: %{y:.2f}<extra></extra>'
                ),
                row=row, col=col
            )
            
            unit = units.get(metric, '')
            fig.update_yaxes(
                title_text=f"{unit}" if unit else "値",
                row=row, col=col,
                gridcolor='rgba(76, 175, 80, 0.1)',
                linecolor='rgba(76, 175, 80, 0.3)',
                title_font=dict(size=12, color='#1B5E20'),
                tickfont=dict(size=10)
            )
    
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            font=dict(size=20, color='#1B5E20', family='Arial Black')
        ),
        height=400 * rows,
        showlegend=False,
        plot_bgcolor='rgba(232, 245, 232, 0.3)',
        paper_bgcolor='white',
        margin=dict(l=50, r=50, t=80, b=50),
        font=dict(family="Arial")
    )
    
    return fig

def generate_pdf_report(player_name, section_scores, feedback_text, player_data, df, config):
    """個人レポートのPDF生成（A4 1枚に収める）"""
    if not PDF_AVAILABLE:
        return None
    
    try:
        buffer = io.BytesIO()
        
        # 日本語フォント対応
        try:
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            from reportlab.pdfbase.ttfonts import TTFont
            # 日本語フォントを登録
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
            japanese_font = 'HeiseiKakuGo-W5'
            # アルファベット用のフォントも登録
            english_font = 'Helvetica'
        except:
            japanese_font = 'Helvetica'
            english_font = 'Helvetica'
        
        # PDF文書の作成（マージンを最小限に）
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            topMargin=0.5*cm,
            bottomMargin=0.5*cm,
            leftMargin=0.6*cm, 
            rightMargin=0.6*cm,
            allowSplitting=1,
            title="KOA Physical Report",
            author="KOA Basketball Academy"
        )
        story = []
        
        # スタイル設定
        title_style = ParagraphStyle(
            'CustomTitle', 
            fontName=japanese_font, 
            fontSize=13, 
            spaceAfter=4,
            alignment=TA_CENTER, 
            textColor=colors.Color(0.1, 0.5, 0.2)
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading', 
            fontName=japanese_font, 
            fontSize=10,
            spaceAfter=3,
            spaceBefore=4,
            textColor=colors.Color(0.3, 0.3, 0.3),
            wordWrap='CJK'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal', 
            fontName=japanese_font, 
            fontSize=10,
            spaceAfter=2,
            leading=12,
            wordWrap='CJK'
        )
        
        # ヘッダー部分
        story.append(Paragraph("KOA Basketball Academy", title_style))
        story.append(Paragraph("フィジカルパフォーマンスレポート", title_style))
        
        # 氏名
        player_info = f"氏名: {player_name}"
        story.append(Paragraph(player_info, normal_style))
        story.append(Spacer(1, 6))
        
        # フィジカルスコア
        story.append(Paragraph("フィジカルスコア", heading_style))
        story.append(Spacer(1, 6))
        valid_scores = [s for s in section_scores.values() if s > 0]
        overall_score = round(np.mean(valid_scores)) if valid_scores else 0
        
        # 横並びのスコア表
        score_data = []
        score_row = []
        for section_name in ['身体組成', '俊敏性', '跳躍力']:
            score = section_scores.get(section_name, 0)
            score_row.extend([section_name, str(score) if score > 0 else 'N/A'])
        score_row.extend(['総合スコア', str(overall_score)])
        score_data.append(score_row)
        
        score_table = Table([score_data[0]], colWidths=[2*cm, 1.2*cm, 2*cm, 1.2*cm, 2*cm, 1.2*cm, 2*cm, 1.2*cm])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), japanese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 8))
        
        # フィジカルバランス（三角形レーダーチャート）
        radar_chart = create_triangle_radar_chart(section_scores, overall_score)
        if radar_chart:
            # 中央配置のためのテーブルでラップ
            chart_table = Table([[radar_chart]], colWidths=[5.7*cm])
            chart_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(chart_table)
            story.append(Spacer(1, -17))
            
            # 測定データ
            story.append(Paragraph("測定データ", heading_style))
        else:
            # フォールバック：テキスト表示
            radar_visual_data = [['項目', 'スコア', '視覚的表示 (1-5スケール)']]
            
            for section_name in ['身体組成', '俊敏性', '跳躍力']:
                score = section_scores.get(section_name, 0)
                if score > 0:
                    visual_display = '★' * score + '☆' * (5 - score)
                    score_text = str(score)
                else:
                    visual_display = '☆☆☆☆☆'
                    score_text = 'N/A'
                
                radar_visual_data.append([section_name, score_text, visual_display])
            
            radar_visual_table = Table(radar_visual_data, colWidths=[3.5*cm, 2*cm, 6*cm])
            radar_visual_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), japanese_font),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(radar_visual_table)
            story.append(Spacer(1, -17))
            
            story.append(Paragraph("測定データ", heading_style))
        
        # 測定データにSJとCODDを追加
        key_metrics = [
            ('Height', '身長', 'cm'),
            ('Weight', '体重', 'kg'),
            ('BMI', 'BMI', ''),
            ('Maturity', '成熟度', 'year'),
            ('10m_Sprint', '10mスプリント', 'sec'),
            ('505_Test_Forward', '505テスト(前方)', 'sec'),
            ('505_Test_Backward', '505テスト(後方)', 'sec'),
            ('CODD', 'CODD', 'sec'), 
            ('BJ', '立ち幅跳び', 'cm'),
            ('SH', 'サイドホップテスト', '%'),
            ('SJ', 'スクワットジャンプ', 'cm'),
            ('CMJ', '垂直跳び（反動あり）', 'cm'),
            ('RJ', 'リバウンドジャンプ', 'index')
        ]
        
        # カテゴリー平均のためのデータ
        player_category = "未分類"
        if 'Category' in player_data.columns and not player_data['Category'].isna().all():
            valid_categories = player_data['Category'].dropna()
            if not valid_categories.empty:
                player_category = valid_categories.iloc[0]
        
        category_data = df
        if player_category != "未分類":
            category_data = df[df['Category'] == player_category]
        
        detail_data = [['測定項目', '最新値', '変化', 'カテゴリー平均', '目標値']]
        
        target_values = get_target_values()
        body_composition_items = ['Height', 'Weight', 'BMI', 'Maturity']
        
        for metric_key, metric_name, unit in key_metrics:
            if metric_key not in df.columns:
                continue
                
            player_val = safe_get_value(player_data, metric_key)
            target_val = get_target_value_for_player(player_data, metric_key, target_values)
            
            # 前回値との変化
            prev_val = None
            if len(player_data) >= 2:
                sorted_player_data = player_data.sort_values('Date', ascending=False)
                valid_data = sorted_player_data[sorted_player_data[metric_key].notna()]
                valid_data = valid_data[valid_data[metric_key] != '']
                if metric_key != 'SH':
                    valid_data = valid_data[valid_data[metric_key] != 0]
                if len(valid_data) >= 2:
                    prev_val = float(valid_data.iloc[1][metric_key])
            
            # 変化の表示
            change_display = "-"
            if player_val is not None and prev_val is not None:
                difference = player_val - prev_val
                
                if metric_key == 'SH':
                    if difference > 0:
                        change_display = f"+{difference:.1f}%"
                    elif difference < 0:
                        change_display = f"{difference:.1f}%"
                    else:
                        change_display = "0.0%"
                else:
                    if difference > 0:
                        change_display = f"+{difference:.2f}"
                    elif difference < 0:
                        change_display = f"{difference:.2f}"
                    else:
                        change_display = "0.00"
            
            # カテゴリー平均
            if metric_key == 'SH':
                category_avg_display = "-"
            else:
                category_avg = safe_mean(category_data[metric_key])
                category_avg_display = f"{format_value(category_avg)}{unit}"
            
            # 目標値表示
            if metric_key in body_composition_items:
                target_display = "-"
            else:
                if metric_key == 'SH' and target_val is not None:
                    target_display = f"±{target_val:.1f}{unit}"
                else:
                    target_display = f"{format_value(target_val)}{unit}" if target_val is not None else "-"
            
            # プレイヤー値表示
            if metric_key == 'SH':
                if player_val is not None:
                    if player_val == 0:
                        player_val_display = f"0{unit}"
                    else:
                        player_val_display = f"{player_val:.2f}{unit}"
                else:
                    player_val_display = "N/A"
            else:
                player_val_display = f"{format_value(player_val)}{unit}"
            
            detail_data.append([
                metric_name,
                player_val_display,
                change_display,
                category_avg_display,
                target_display
            ])
        
        detail_table = Table(detail_data, colWidths=[3.5*cm, 2.5*cm, 2*cm, 2.5*cm, 2.5*cm])
        
        # テーブルスタイル
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), japanese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ]
        
        detail_table.setStyle(TableStyle(table_style))
        story.append(detail_table)
        story.append(Spacer(1, 11))
        
        # フィードバック
        story.append(Paragraph("フィードバック", heading_style))
        story.append(Spacer(1, 6))
        
        feedback_style = ParagraphStyle(
            'FeedbackStyle', 
            fontName=japanese_font, 
            fontSize=8,
            spaceAfter=3,
            leading=11,
            alignment=TA_LEFT,
            wordWrap='CJK'
        )
        
        try:
            # 改行コードをHTMLの<br/>タグまたはParagraphの分割で処理
            for line in feedback_text.split('\n'):
                if line.strip():
                    story.append(Paragraph(line, feedback_style))
        except:
            story.append(Paragraph("フィードバック内容の表示中にエラーが発生しました。", feedback_style))
        
        story.append(Spacer(1, 12))
        
        # 測定項目説明
        story.append(Paragraph("測定項目について", heading_style))
        story.append(Spacer(1, 6))
        
        # 導入文
        intro_text = "育成年代（小・中・高校生）は発育発達の時期であり、身体の変化をモニタリングし、それに応じた指導が重要です。各カテゴリーの平均値・目標値は上記表に記載しています。"
        
        explanation_style = ParagraphStyle(
            'ExplanationStyle', 
            fontName=japanese_font, 
            fontSize=6,
            spaceAfter=2,
            leading=8,
            alignment=TA_LEFT,
            wordWrap='CJK'
        )
        
        subtitle_style = ParagraphStyle(
            'SubtitleStyle', 
            fontName=japanese_font, 
            fontSize=7,
            spaceAfter=1,
            spaceBefore=3,
            alignment=TA_LEFT,
            textColor=colors.Color(0.2, 0.2, 0.2),
            wordWrap='CJK'
        )
        
        item_style = ParagraphStyle(
            'ItemStyle', 
            fontName=japanese_font, 
            fontSize=6,
            spaceAfter=1,
            leading=8,
            alignment=TA_LEFT,
            leftIndent=0.5*cm,
            wordWrap='CJK'
        )
        
        try:
            story.append(Paragraph(intro_text, explanation_style))
            story.append(Spacer(1, 4))
            
            # 身体組成セクション
            story.append(Paragraph("<身体組成>", subtitle_style))
            story.append(Paragraph("○BMI：身長あたりの体重を示します。U12・U15年代は筋肉がつきづらく低値になりやすいですが、高校生以上は25.0〜26.0kg/m²を目指します。", item_style))
            story.append(Paragraph("○成熟度：身長の伸び率が最大になる時期をPHV（ピーク身長成長速度）と呼び、PHV前後で取り組むべきトレーニングが異なるとされています。成熟度は、身長・体重・脚長から推定されるPHVからの年数で表します。", item_style))
            
            # 俊敏性セクション
            story.append(Paragraph("<俊敏性>", subtitle_style))
            story.append(Paragraph("○10mスプリント：バスケットボールは28m以内のコートで行うため、トップスピードよりも速く加速する能力が重要です。", item_style))
            story.append(Paragraph("○505テスト（前方）：5m直線スプリント後に方向転換するテストで、前方スプリント時の減速と再加速の能力を評価します。", item_style))
            story.append(Paragraph("○505テスト(後方)：5m直線スプリント後にバックペダルで折り返すテストで、後方移動を含む多方向への移動能力を評価します。", item_style))
            story.append(Paragraph("○CODD：505テスト(後方)タイムから10mスプリントタイムを引き、純粋な切り返し能力を評価します。", item_style))
            
            # 跳躍力セクション
            story.append(Paragraph("<跳躍力>", subtitle_style))
            story.append(Paragraph("○立ち幅跳び：瞬発力を評価します。身長の影響を考慮し、ジャンプ距離（cm）から身長（cm）を引いた値を用います。", item_style))
            story.append(Paragraph("○サイドホップテスト：片脚で10秒間に左右に何回ホップできるかを評価し、左右差から足関節の機能の非対称性を判断します。【(右-左)/右×100】", item_style))
            story.append(Paragraph("例：+10%→右は左より10%優れている　　-10%→右は左より10%劣っている", item_style))
            story.append(Paragraph("* 左右差15%未満 → 問題なし　* 左右差15%以上25%未満 → やや問題あり　* 左右差25%以上 → 問題あり", item_style))
            story.append(Paragraph("○スクワットジャンプ・垂直跳び：スクワットジャンプは下肢パワーを、垂直跳びはパワーと反動利用能力を評価します。", item_style))
            story.append(Paragraph("○リバウンドジャンプ：30cmボックスから落下後、接地時間を短く高く跳ぶテストで、\"バネの強さ\"を評価します。RSI（滞空時間/接地時間）を指標とします。", item_style))
            
        except:
            story.append(Paragraph("Explanation of measurement items (Japanese text)", explanation_style))
        
        # フッター
        story.append(Spacer(1, 4))
        footer_style = ParagraphStyle(
            'Footer', 
            fontName=english_font,
            fontSize=5,
            alignment=TA_CENTER, 
            textColor=colors.grey
        )
        
        story.append(Paragraph("©2025 KOA BASKETBALL ACADEMY ALL RIGHTS RESERVED", footer_style))
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        st.error(f"PDF生成エラー: {str(e)}")
        return None

def create_triangle_radar_chart(section_scores, overall_score):
    """三角形レーダーチャートを作成"""
    try:
        from reportlab.graphics.shapes import Drawing, Polygon, String
        from reportlab.lib import colors as rl_colors
        import math
        
        # チャートサイズ
        chart_width = 5.7*cm
        chart_height = 3.3*cm
        
        drawing = Drawing(chart_width, chart_height)
        
        # 三角形の中心点と半径
        center_x = chart_width / 2
        center_y = chart_height / 2 - 0.08*cm
        radius = 1.3*cm
        
        # 三角形の頂点を計算
        angles = [90, 210, 330]
        triangle_points = []
        for angle in angles:
            rad = math.radians(angle)
            x = center_x + radius * math.cos(rad)
            y = center_y + radius * math.sin(rad)
            triangle_points.extend([x, y])
        
        # レーダーチャートの外枠
        for level in range(1, 6):
            scale = level / 5.0
            scaled_points = []
            for i in range(0, len(triangle_points), 2):
                base_x = triangle_points[i]
                base_y = triangle_points[i+1]
                scaled_x = center_x + (base_x - center_x) * scale
                scaled_y = center_y + (base_y - center_y) * scale
                scaled_points.extend([scaled_x, scaled_y])
            
            color = rl_colors.Color(0.8, 0.8, 0.8, alpha=0.3) if level < 5 else rl_colors.Color(0.6, 0.6, 0.6, alpha=0.5)
            triangle = Polygon(scaled_points)
            triangle.fillColor = None
            triangle.strokeColor = color
            triangle.strokeWidth = 1
            drawing.add(triangle)
        
        # データポイント
        scores = [
            section_scores.get('身体組成', 0),
            section_scores.get('俊敏性', 0),
            section_scores.get('跳躍力', 0)
        ]
        
        data_points = []
        for i, score in enumerate(scores):
            if score > 0:
                scale = score / 5.0
                angle_rad = math.radians(angles[i])
                x = center_x + radius * scale * math.cos(angle_rad)
                y = center_y + radius * scale * math.sin(angle_rad)
                data_points.extend([x, y])
            else:
                data_points.extend([center_x, center_y])
        
        # データ三角形
        if len(data_points) == 6:
            data_triangle = Polygon(data_points)
            data_triangle.fillColor = rl_colors.Color(0.2, 0.7, 0.3, alpha=0.3)
            data_triangle.strokeColor = rl_colors.Color(0.1, 0.5, 0.2)
            data_triangle.strokeWidth = 2
            drawing.add(data_triangle)
        
        # ラベル
        labels = ['身体組成', '俊敏性', '跳躍力', '総合スコア']
        scores_for_labels = [
            section_scores.get('身体組成', 0),
            section_scores.get('俊敏性', 0),
            section_scores.get('跳躍力', 0),
            overall_score if overall_score > 0 else 0
        ]
        label_positions = [
            (center_x, center_y + radius + 0.25*cm),
            (center_x - radius - 0.5*cm, center_y - radius/2),
            (center_x + radius + 0.5*cm, center_y - radius/2),
            (center_x, center_y - radius + 0.37*cm)
        ]
        
        for i, (label, (x, y)) in enumerate(zip(labels, label_positions)):
            score = scores_for_labels[i]
            text = f"{label} ({score if score > 0 else 'N/A'})"
            label_text = String(x, y, text)
            try:
                label_text.fontName = 'HeiseiKakuGo-W5'
            except:
                label_text.fontName = 'Helvetica'
            label_text.fontSize = 5
            label_text.textAnchor = 'middle'
            label_text.fillColor = rl_colors.Color(0.2, 0.2, 0.2)
            drawing.add(label_text)
        
        return drawing
        
    except Exception as e:
        return None

def generate_batch_pdf_reports(df, config, category_filter=None):
    """
    指定されたカテゴリー（U12 または U15/U18）のPDFレポートを一括生成する
    category_filter: 'U12' または 'U15_U18'
    """
    try:
        # ZIPファイルのメモリバッファ
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 全選手のリストを取得
            all_players = df['Name'].dropna().unique()
            
            count = 0
            
            for player_name in all_players:
                try:
                    # 各選手のデータを取得
                    player_data = df[df['Name'] == player_name]
                    if player_data.empty:
                        continue
                    
                    # カテゴリー判定ロジック
                    player_cat_series = player_data['Category'].dropna()
                    if player_cat_series.empty:
                        continue
                        
                    player_cat = str(player_cat_series.iloc[0])
                    
                    # フィルタリング
                    if category_filter == 'U12':
                        if not ('U12' in player_cat or '12' in player_cat):
                            continue
                    elif category_filter == 'U15_U18':
                        # U15またはU18を含む、あるいはU12を含まない場合を対象とするなど
                        # ここではU15または15, U18または18が含まれる場合とする
                        if not (
                            'U15' in player_cat or '15' in player_cat or 
                            'U18' in player_cat or '18' in player_cat
                        ):
                            continue
                    
                    # 対象選手であれば生成処理
                    count += 1
                    
                    # 各セクションのスコアを計算
                    section_scores = {}
                    for category, category_config in config.items():
                        reverse_scoring = category_config.get('reverse_scoring', False)
                        score, detail = calculate_section_score(player_data, df, category_config['score_metrics'], reverse_scoring)
                        section_scores[category_config['name']] = score if score is not None else 0
                    
                    # フィードバック生成（常に最新ロジックで自動生成）
                    feedback_text = generate_personalized_feedback(section_scores, player_data, df, player_name)
                    
                    # PDFレポート生成
                    pdf_bytes = generate_pdf_report(
                        player_name, 
                        section_scores, 
                        feedback_text, 
                        player_data, 
                        df, 
                        config
                    )
                    
                    if pdf_bytes:
                        clean_name = player_name.replace(" ", "").replace("　", "")
                        safe_name = "".join(c for c in clean_name if c.isalnum() or c in ('-', '_')).rstrip()
                        filename = f"{safe_name} フィジカルフィードバックシート_2025.8.pdf"
                        zip_file.writestr(filename, pdf_bytes)
                        
                except Exception as e:
                    print(f"選手 {player_name} のPDF生成でエラー: {str(e)}")
                    continue
        
        if count == 0:
            return None, 0
            
        zip_buffer.seek(0)
        return zip_buffer.getvalue(), count
        
    except Exception as e:
        print(f"一括生成エラー: {str(e)}")
        return None, 0

def create_zip_download_link(zip_bytes, filename, label):
    """ZIPファイルダウンロードリンクを作成"""
    b64_zip = base64.b64encode(zip_bytes).decode()
    href = f'<a href="data:application/zip;base64,{b64_zip}" download="{filename}" style="text-decoration: none;">'
    href += '<div style="background: linear-gradient(135deg, #1565C0 0%, #1976D2 100%); '
    href += 'color: white; padding: 12px 24px; border-radius: 8px; text-align: center; '
    href += 'font-weight: bold; margin: 10px 0; display: inline-block; '
    href += 'box-shadow: 0 4px 12px rgba(21, 101, 192, 0.3);">'
    href += f'{label}</div></a>'
    return href

def create_download_link(pdf_bytes, filename):
    """PDFダウンロードリンクを作成"""
    b64_pdf = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{filename}" style="text-decoration: none;">'
    href += '<div style="background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%); '
    href += 'color: white; padding: 12px 24px; border-radius: 8px; text-align: center; '
    href += 'font-weight: bold; margin: 10px 0; display: inline-block; '
    href += 'box-shadow: 0 4px 12px rgba(46, 125, 50, 0.3);">'
    href += '📄 PDFレポートをダウンロード</div></a>'
    return href

def main():
    # ヘッダー
    st.markdown("""
    <div class="main-header">
        KOA Basketball Academy
        <div class="academy-logo">Physical Performance Dashboard</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ファイルアップロード
    uploaded_file = st.file_uploader(
        "測定データファイルをアップロードしてください",
        type=['xlsx', 'xls', 'csv']
    )
    
    if uploaded_file is None:
        st.info("データファイルをアップロードして分析を開始してください。")
        st.stop()
    
    # データ読み込み
    df = load_data_from_file(uploaded_file)
    if df.empty:
        st.error("データの読み込みに失敗しました。")
        st.stop()
    
    # テスト設定
    config = get_test_config()
    
    # サイドバー
    st.sidebar.header("選手選択")
    
    # 選手名の選択
    available_names = df['Name'].dropna().unique()
    if len(available_names) == 0:
        st.error("選手データが見つかりません。")
        st.stop()
    
    selected_name = st.sidebar.selectbox("選手を選択", available_names)
    
    # 選択された選手のデータを取得
    player_data = df[df['Name'] == selected_name]
    
    if player_data.empty:
        st.error(f"選手 '{selected_name}' のデータが見つかりません。")
        return
    
    # 選手情報の表示
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f'<div class="player-title">{selected_name}</div>', unsafe_allow_html=True)
    with col2:
        all_dates = player_data['Date'].dropna().sort_values(ascending=False)
        if not all_dates.empty:
            latest_date = all_dates.iloc[0].strftime('%Y-%m-%d')
            oldest_date = all_dates.iloc[-1].strftime('%Y-%m-%d')
            st.markdown(f'<div class="date-info">測定期間: {oldest_date} ~ {latest_date}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="date-info">測定日: N/A</div>', unsafe_allow_html=True)
    
    # 総合スコアの計算と表示
    st.markdown('<div class="section-header">総合フィジカルスコア</div>', unsafe_allow_html=True)
    
    # 各セクションのスコアを計算
    section_scores = {}
    
    for category, category_config in config.items():
        reverse_scoring = category_config.get('reverse_scoring', False)
        score, detail = calculate_section_score(player_data, df, category_config['score_metrics'], reverse_scoring)
        section_scores[category_config['name']] = score if score is not None else 0
    
    # 総合スコアを計算
    overall_score, overall_detail = calculate_overall_score(section_scores)
    
    # スコア表示
    score_cols = st.columns(4)
    
    # 各セクションスコア
    section_names = list(section_scores.keys())
    for i, (section_name, score) in enumerate(section_scores.items()):
        with score_cols[i]:
            if score <= 1:
                color = "#F44336"
            elif score <= 2:
                color = "#FF9800"
            elif score <= 3:
                color = "#FFC107"
            elif score <= 4:
                color = "#4CAF50"
            else:
                color = "#2E7D32"
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, {color} 0%, {color}CC 100%);
                padding: 1.5rem;
                border-radius: 8px;
                color: white;
                text-align: center;
                margin: 0.5rem 0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            ">
                <div style="font-size: 0.9rem; margin-bottom: 0.5rem; opacity: 0.9;">{section_name}</div>
                <div style="font-size: 2rem; font-weight: 700;">{score if score > 0 else 'N/A'}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # 総合スコア
    with score_cols[3]:
        total_color = "#1B5E20" if overall_score and overall_score > 0 else "#757575"
        total_score_text = str(overall_score) if overall_score and overall_score > 0 else "N/A"
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {total_color} 0%, {total_color}CC 100%);
            padding: 1.5rem;
            border-radius: 8px;
            color: white;
            text-align: center;
            margin: 0.5rem 0;
            box-shadow: 0 6px 16px rgba(0,0,0,0.2);
            border: 2px solid white;
        ">
            <div style="font-size: 0.9rem; margin-bottom: 0.5rem; opacity: 0.9;">総合スコア</div>
            <div style="font-size: 2rem; font-weight: 700;">{total_score_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # レーダーチャート
    if all(score > 0 for score in section_scores.values()):
        radar_chart = create_radar_chart(section_scores, section_names)
        if radar_chart:
            st.plotly_chart(radar_chart, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("レーダーチャートの表示には全セクションのデータが必要です。")
    
    # 個別フィードバック
    st.markdown('<div class="section-header">個別フィードバック</div>', unsafe_allow_html=True)
    
    # 自動生成されたフィードバックを取得
    auto_feedback_text = generate_personalized_feedback(section_scores, player_data, df, selected_name)
    
    # セッション状態でフィードバックを管理
    feedback_key = f"feedback_{selected_name}"
    if feedback_key not in st.session_state:
        st.session_state[feedback_key] = auto_feedback_text
    
    # フィードバック編集UI
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("🔄 自動生成に戻す", help="AIが生成したフィードバックに戻します"):
            st.session_state[feedback_key] = auto_feedback_text
            st.rerun()
        
        if st.button("💾 編集内容を保存", help="編集したフィードバックを保存します"):
            st.success("フィードバックが保存されました！")
    
    with col2:
        # 編集可能なテキストエリア
        feedback_text = st.text_area(
            "フィードバック内容（編集可能）",
            value=st.session_state[feedback_key],
            height=250,
            key=f"feedback_editor_{selected_name}",
            help="このテキストを直接編集できます。PDF出力時にはここの内容が使用されます。"
        )
        
        # セッション状態を更新
        st.session_state[feedback_key] = feedback_text
    
    # 編集されたフィードバックを表示
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
        padding: 2rem;
        border-radius: 12px;
        border-left: 5px solid #4CAF50;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        line-height: 1.6;
        color: #2D3748;
        font-size: 1.0rem;
        white-space: pre-wrap;
    ">
        {feedback_text}
    </div>
    """, unsafe_allow_html=True)
    
    # PDF出力ボタン
    if PDF_AVAILABLE:
        st.markdown("### PDFレポート出力")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        # 個人レポート生成
        with col1:
            if st.button("📄 個人PDFレポート生成", type="primary"):
                with st.spinner('PDFレポートを生成中...'):
                    # 編集されたフィードバックを取得
                    current_feedback = st.session_state.get(f"feedback_{selected_name}", feedback_text)
                    
                    pdf_bytes = generate_pdf_report(
                        selected_name, 
                        section_scores, 
                        current_feedback, 
                        player_data, 
                        df, 
                        config
                    )
                    
                    if pdf_bytes:
                        clean_name = selected_name.replace(" ", "").replace("　", "")
                        filename = f"{clean_name} フィジカルフィードバックシート_2025.8.pdf"
                        download_link = create_download_link(pdf_bytes, filename)
                        st.markdown(download_link, unsafe_allow_html=True)
                        st.success("PDFレポートが生成されました！")
                    else:
                        st.error("PDFレポートの生成に失敗しました。")
        
        # U12 一括生成
        with col2:
            if st.button("📁 U12選手のみ一括生成"):
                with st.spinner('U12選手のPDFを生成中...'):
                    zip_bytes, count = generate_batch_pdf_reports(df, config, category_filter='U12')
                    
                    if zip_bytes and count > 0:
                        filename = f"KOA_U12_フィジカルレポート_2025.8.zip"
                        download_link = create_zip_download_link(zip_bytes, filename, f"📁 U12レポート({count}名)をダウンロード")
                        st.markdown(download_link, unsafe_allow_html=True)
                        st.success(f"U12カテゴリーの選手 {count}名分のPDFを生成しました！")
                    else:
                        st.warning("U12カテゴリーの選手が見つからないか、生成に失敗しました。")
        
        # U15/U18 一括生成
        with col3:
            if st.button("📁 U15/U18選手のみ一括生成"):
                with st.spinner('U15/U18選手のPDFを生成中...'):
                    zip_bytes, count = generate_batch_pdf_reports(df, config, category_filter='U15_U18')
                    
                    if zip_bytes and count > 0:
                        filename = f"KOA_U15_U18_フィジカルレポート_2025.8.zip"
                        download_link = create_zip_download_link(zip_bytes, filename, f"📁 U15/U18レポート({count}名)をダウンロード")
                        st.markdown(download_link, unsafe_allow_html=True)
                        st.success(f"U15/U18カテゴリーの選手 {count}名分のPDFを生成しました！")
                    else:
                        st.warning("U15/U18カテゴリーの選手が見つからないか、生成に失敗しました。")
    else:
        st.warning("PDF出力機能を使用するには reportlab ライブラリが必要です。")
    
    # 各カテゴリの処理
    for category, category_config in config.items():
        if player_data.empty:
            continue
        
        st.markdown(f'<div class="section-header">{category_config["name"]}</div>', unsafe_allow_html=True)
        
        # 主要指標
        if category_config['highlight']:
            st.markdown("### 主要指標")
            highlight_cols = st.columns(len(category_config['highlight']))
            
            for i, metric in enumerate(category_config['highlight']):
                with highlight_cols[i]:
                    player_val = safe_get_value(player_data, metric)
                    best_val, best_date = safe_get_best_value(player_data, metric)
                    avg_val = safe_mean(df[metric])
                    unit = category_config['units'].get(metric, '')
                    
                    japanese_name = category_config['japanese_names'].get(metric, metric)
                    
                    best_text = ""
                    if best_val is not None:
                        best_text = f"<br>自己ベスト: {best_val:.2f}{unit}"
                        if best_date != "N/A":
                            best_text += f" ({best_date})"
                    
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">{japanese_name}</div>
                        <div class="highlight-metric">{format_value(player_val, unit)}</div>
                        <div class="comparison-text">
                            チーム平均: {format_value(avg_val, unit)}{best_text}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # 詳細データ表
        st.markdown("### 詳細データ")
        available_metrics = [m for m in category_config['display_metrics'] if m in df.columns]
        
        if available_metrics:
            comparison_df = create_comparison_table(
                player_data, df, available_metrics, category, config
            )
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            
            # トレンドグラフ
            trend_fig = create_trend_chart(
                player_data, 
                available_metrics, 
                f"{category_config['name']} 推移", 
                category_config['units'],
                category_config['japanese_names']
            )
            
            if trend_fig:
                st.markdown("### 推移グラフ")
                st.plotly_chart(trend_fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("推移グラフには2回以上の測定データが必要です。")
        else:
            st.info(f"{category_config['name']}のデータがありません。")

if __name__ == "__main__":
    main()