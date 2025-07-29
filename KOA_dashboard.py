import streamlit as st
import pandas as pd
import numpy as np
import warnings
import base64
import io
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
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
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
                'SH': 'サイドホップテスト',  # サイドホップをサイドホップテストに変更
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
        valid_data = valid_data[valid_data[column] != 0]
        
        if valid_data.empty:
            return default
        
        if 'Date' in valid_data.columns:
            latest_valid = valid_data.sort_values('Date', ascending=False).iloc[0]
            value = latest_valid[column]
        else:
            value = valid_data.iloc[-1][column]
        
        if pd.isna(value) or value == '' or value == 0:
            return default
        
        if isinstance(value, (int, float, np.number)):
            if np.isfinite(value):
                return float(value)
        
        return default
        
    except Exception:
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

def generate_personalized_feedback(section_scores, player_data, all_data, player_name):
    """選手の個別フィードバックを生成"""
    try:
        feedback = []
        
        # 各測定項目の定義（身体組成を除く、フィードバック用の正式名称）
        agility_metrics = {
            '10m_Sprint': {'name': '10mスプリント', 'reverse': True},
            '505_Test_Forward': {'name': '505テスト(前方)', 'reverse': True},
            '505_Test_Backward': {'name': '505テスト(後方)', 'reverse': True},
            'CODD': {'name': 'CODD', 'reverse': True}
        }
        
        jumping_metrics = {
            'BJ': {'name': '立ち幅跳び', 'reverse': False},
            'SH': {'name': 'サイドホップ', 'reverse': True},  # サイドホップは小さいほうが良い
            'SJ': {'name': 'スクワットジャンプ', 'reverse': False},
            'CMJ': {'name': 'カウンタームーブメントジャンプ', 'reverse': False},  # 元の表現に戻す
            'RJ': {'name': 'リバウンドジャンプ', 'reverse': False}
        }
        
        # 各項目のスコアを取得
        agility_metric_scores = {}
        jumping_metric_scores = {}
        
        for metric, info in agility_metrics.items():
            score = get_individual_metric_score(player_data, all_data, metric, info['reverse'])
            if score is not None:
                agility_metric_scores[metric] = score
        
        for metric, info in jumping_metrics.items():
            score = get_individual_metric_score(player_data, all_data, metric, info['reverse'])
            if score is not None:
                jumping_metric_scores[metric] = score
        
        # 前回との比較分析
        progress_analysis = analyze_progress(player_data, agility_metrics, jumping_metrics)
        
        # セクションスコア
        agility_score = section_scores.get('俊敏性', 0)
        jumping_score = section_scores.get('跳躍力', 0)
        
        valid_section_scores = {k: v for k, v in section_scores.items() if v > 0}
        if not valid_section_scores:
            return "データが不足しているため、詳細な分析ができません。"
        
        overall_avg = sum(valid_section_scores.values()) / len(valid_section_scores)
        
        # 導入部分（4スコアの項目がある場合は異なる表現に）
        high_score_sections = [k for k, v in valid_section_scores.items() if v >= 4]
        
        if overall_avg >= 4.5:
            intro = "非常に優れた総合フィジカル能力を示しており、競技レベルでの活躍が大いに期待できます。"
        elif overall_avg >= 4:
            intro = "優秀なフィジカル能力を持っており、さらなる専門性向上により一層の成長が期待できます。"
        elif high_score_sections:
            # 4スコアの項目がある場合の新しい表現
            if len(high_score_sections) == 1:
                intro = f"{high_score_sections[0]}の能力が特に秀でており、この強みを活かした競技力向上が期待できます。"
            else:
                intro = f"{high_score_sections[0]}と{high_score_sections[1]}の能力が秀でており、これらの強みを軸とした更なる発展が見込まれます。"
        elif overall_avg >= 3:
            # 3回に1回程度「バランスの取れた」を使用
            import random
            if random.random() < 0.33:  # 33%の確率
                intro = "バランスの取れたフィジカル能力を持っており、今後のトレーニングで更なる向上が見込まれます。"
            else:
                intro = "各分野において安定した基礎能力を有しており、継続的なトレーニングで着実な成長が期待できます。"
        else:
            intro = "豊富な成長ポテンシャルがあり、継続的なトレーニングで確実に向上していきます。"
        
        feedback.append(intro)
        
        # 前回との比較コメント（項目名を正式名称に変更）
        if progress_analysis['has_comparison']:
            if progress_analysis['improved_metrics']:
                improved_names = []
                for m in progress_analysis['improved_metrics']:
                    if m == 'BJ':
                        improved_names.append('立ち幅跳び')
                    elif m == 'SJ':
                        improved_names.append('スクワットジャンプ')
                    elif m == 'CMJ':
                        improved_names.append('垂直跳び')
                    elif m == 'SH':
                        improved_names.append('サイドホップテスト')
                    elif m == 'RJ':
                        improved_names.append('リバウンドジャンプ')
                    else:
                        improved_names.append(agility_metrics.get(m, {}).get('name', m) or jumping_metrics.get(m, {}).get('name', m))
                
                feedback.append(f"前回と比較して、{improved_names[0]}")
                if len(improved_names) > 1:
                    feedback.append(f"や{improved_names[1]}")
                feedback.append("で向上が見られ、継続的な努力の成果が現れています。")
            
            if progress_analysis['declined_metrics']:
                declined_names = []
                for m in progress_analysis['declined_metrics']:
                    if m == 'BJ':
                        declined_names.append('立ち幅跳び')
                    elif m == 'SJ':
                        declined_names.append('スクワットジャンプ')
                    elif m == 'CMJ':
                        declined_names.append('垂直跳び')
                    elif m == 'SH':
                        declined_names.append('サイドホップテスト')
                    elif m == 'RJ':
                        declined_names.append('リバウンドジャンプ')
                    else:
                        declined_names.append(agility_metrics.get(m, {}).get('name', m) or jumping_metrics.get(m, {}).get('name', m))
                
                feedback.append(f"一方で、{declined_names[0]}")
                if len(declined_names) > 1:
                    feedback.append(f"と{declined_names[1]}")
                feedback.append("については前回より数値が下がっていますが、これは測定時のコンディションや成長期における一時的な変化の可能性もあります。")
            
            if progress_analysis['stable_metrics']:
                feedback.append("その他の項目では安定した数値を維持しており、基礎体力の定着が確認できます。")
        
        # 優れている点の詳細分析（略語を正式名称に変更）
        high_agility_metrics = [k for k, v in agility_metric_scores.items() if v >= 4]
        high_jumping_metrics = [k for k, v in jumping_metric_scores.items() if v >= 4]
        
        strengths = []
        if agility_score >= 4:
            if '10m_Sprint' in high_agility_metrics:
                strengths.append("短距離での爆発的な加速力")
            if '505_Test_Forward' in high_agility_metrics:
                strengths.append("前方スプリントでの優れた加速能力")
            if '505_Test_Backward' in high_agility_metrics:
                strengths.append("方向転換時の優れた減速・再加速能力")
            if 'CODD' in high_agility_metrics:
                strengths.append("純粋な切り返し動作の技術")
            if not high_agility_metrics:
                strengths.append("バランスの取れた俊敏性")
        
        if jumping_score >= 4:
            if 'CMJ' in high_jumping_metrics:
                strengths.append("垂直跳びでの反動利用能力")
            if 'SJ' in high_jumping_metrics:
                strengths.append("スクワットジャンプでの下肢パワー")
            if 'BJ' in high_jumping_metrics:
                strengths.append("立ち幅跳びでの水平跳躍力")
            if 'RJ' in high_jumping_metrics:
                strengths.append("リバウンドジャンプでの連続跳躍能力")
            if 'SH' in high_jumping_metrics:
                strengths.append("サイドホップテストでの足関節安定性")
            if not high_jumping_metrics:
                strengths.append("総合的な跳躍能力")
        
        if strengths:
            feedback.append(f"特に{strengths[0]}")
            if len(strengths) > 1:
                feedback.append(f"と{strengths[1]}")
            feedback.append("が優秀で、これらの能力はゲーム中の重要な武器となります。")
        
        # 改善点と具体的なトレーニング提案（略語を正式名称に変更）
        improvement_areas = []
        training_suggestions = []
        
        if agility_score <= 2:
            low_agility_metrics = [k for k, v in agility_metric_scores.items() if v <= 2]
            if '10m_Sprint' in low_agility_metrics:
                improvement_areas.append("初速の向上")
                training_suggestions.append("スタートダッシュ練習（山なりスタート、クラウチングスタート）や股関節のストレッチ・可動域改善")
            if '505_Test_Forward' in low_agility_metrics:
                improvement_areas.append("前方スプリント能力")
                training_suggestions.append("加速技術とストライド調整、前方への推進力強化")
            if '505_Test_Backward' in low_agility_metrics:
                improvement_areas.append("方向転換技術")
                training_suggestions.append("デセレレーション（減速）トレーニング、ストップ&ゴー練習、体幹プランク系エクササイズ")
            if 'CODD' in low_agility_metrics:
                improvement_areas.append("切り返し動作")
                training_suggestions.append("アジリティラダー（ラテラルステップ、インアウト）、コーンドリル（ジグザグラン、Tドリル）")
        elif agility_score == 3:
            improvement_areas.append("俊敏性のさらなる向上")
            training_suggestions.append("フットワーク強化（サイドシャッフル、バックペダル、クロスオーバーステップ）")
        
        if jumping_score <= 2:
            low_jumping_metrics = [k for k, v in jumping_metric_scores.items() if v <= 2]
            if 'CMJ' in low_jumping_metrics:
                improvement_areas.append("垂直跳びの反動利用技術")
                training_suggestions.append("プライオメトリクス（ボックスジャンプ、デプスジャンプ、バウンディング）")
            if 'SJ' in low_jumping_metrics:
                improvement_areas.append("スクワットジャンプでの下肢筋力")
                training_suggestions.append("基礎筋力トレーニング（スクワット、ランジ、カーフレイズ、ヒップスラスト）")
            if 'BJ' in low_jumping_metrics:
                improvement_areas.append("立ち幅跳びでの水平跳躍力")
                training_suggestions.append("ホップ系練習（シングルレッグホップ、バウンドジャンプ）、前方ジャンプトレーニング")
            if 'RJ' in low_jumping_metrics:
                improvement_areas.append("リバウンドジャンプでの連続跳躍能力")
                training_suggestions.append("リアクティブジャンプ（連続ジャンプ、ハードルジャンプ）、ポゴジャンプ")
            if 'SH' in low_jumping_metrics:
                improvement_areas.append("サイドホップテストでの足関節安定性")
                training_suggestions.append("バランストレーニング（片脚立ち、ボスボール）、足関節強化エクササイズ")
        elif jumping_score == 3:
            improvement_areas.append("跳躍力のレベルアップ")
            training_suggestions.append("跳躍の質向上（着地技術、踏み切り強化）と爆発力向上トレーニング")
        
        # 改善点のフィードバック
        if improvement_areas:
            feedback.append(f"今後は{improvement_areas[0]}")
            if len(improvement_areas) > 1:
                feedback.append(f"と{improvement_areas[1]}")
            feedback.append("に重点的に取り組むことで、さらなる競技力向上が期待できます。")
        
        # 具体的なトレーニング提案
        if training_suggestions:
            feedback.append(f"具体的なトレーニングメニューとしては、{training_suggestions[0]}")
            if len(training_suggestions) > 1:
                feedback.append(f"、および{training_suggestions[1]}")
            feedback.append("などを週2-3回、10-15分程度から始めることをお勧めします。")
        
        # 総合的なまとめと励まし
        best_section = max(valid_section_scores, key=valid_section_scores.get) if valid_section_scores else None
        worst_section = min(valid_section_scores, key=valid_section_scores.get) if valid_section_scores else None
        
        if best_section and worst_section and best_section != worst_section:
            if valid_section_scores[best_section] >= 4:
                feedback.append(f"優れた{best_section}を武器として活かしつつ、{worst_section}の底上げにより、より完成度の高い選手への成長が見込めます。")
            else:
                feedback.append(f"{best_section}の伸びを基盤として、{worst_section}も同様に向上させることで、バランスの取れた身体能力を獲得できます。")
        else:
            if overall_avg >= 4:
                feedback.append("現在の高いレベルを維持しながら、細部の技術向上に取り組むことで、さらなる高みを目指せます。")
            else:
                feedback.append("各分野において継続的な向上を積み重ねることで、必ず大きな成長を実現できます。")
        
        # 最終的な励ましのメッセージ
        if overall_avg >= 4:
            closing = "持続的な努力により、競技において更なる活躍が期待されます。"
        elif overall_avg >= 3:
            closing = "今後の取り組み次第で、短期間での大きな飛躍が十分可能です。"
        else:
            closing = "基礎からしっかりと積み上げることで、確実にレベルアップしていきましょう。"
        
        feedback.append(closing)
        
        return "".join(feedback)
        
    except Exception as e:
        return f"フィードバック生成中にエラーが発生しました: {str(e)}"

def analyze_progress(player_data, agility_metrics, jumping_metrics):
    """前回との比較分析を行う"""
    try:
        if len(player_data) < 2:
            return {
                'has_comparison': False,
                'improved_metrics': [],
                'declined_metrics': [],
                'stable_metrics': []
            }
        
        # 日付でソートして最新と前回を取得
        sorted_data = player_data.sort_values('Date', ascending=False)
        
        all_metrics = {**agility_metrics, **jumping_metrics}
        improved_metrics = []
        declined_metrics = []
        stable_metrics = []
        
        for metric in all_metrics.keys():
            if metric not in player_data.columns:
                continue
            
            # 最新と前回の値を取得
            latest_value = None
            previous_value = None
            
            # 最新の有効値を取得
            for idx, row in sorted_data.iterrows():
                if pd.notna(row[metric]) and row[metric] != 0 and row[metric] != '':
                    if latest_value is None:
                        latest_value = float(row[metric])
                    elif previous_value is None:
                        previous_value = float(row[metric])
                        break
            
            if latest_value is not None and previous_value is not None:
                # 改善の判定（reverse_scoringを考慮）
                is_reverse = all_metrics[metric]['reverse']
                improvement_threshold = 0.02  # 2%以上の変化を有意とする
                
                if is_reverse:
                    # 値が小さいほど良い場合（タイム系）
                    change_ratio = (previous_value - latest_value) / previous_value
                else:
                    # 値が大きいほど良い場合（距離・回数系）
                    change_ratio = (latest_value - previous_value) / previous_value
                
                if change_ratio > improvement_threshold:
                    improved_metrics.append(metric)
                elif change_ratio < -improvement_threshold:
                    declined_metrics.append(metric)
                else:
                    stable_metrics.append(metric)
        
        return {
            'has_comparison': len(improved_metrics + declined_metrics + stable_metrics) > 0,
            'improved_metrics': improved_metrics,
            'declined_metrics': declined_metrics,
            'stable_metrics': stable_metrics
        }
        
    except Exception:
        return {
            'has_comparison': False,
            'improved_metrics': [],
            'declined_metrics': [],
            'stable_metrics': []
        }

def safe_get_best_value(data, column, default=None):
    """安全に最高値を取得する関数"""
    try:
        if column not in data.columns or data.empty:
            return default, default
        
        valid_data = data[data[column].notna()]
        valid_data = valid_data[valid_data[column] != '']
        valid_data = valid_data[valid_data[column] != 0]
        
        if valid_data.empty:
            return default, default
        
        numeric_values = pd.to_numeric(valid_data[column], errors='coerce')
        clean_values = numeric_values.dropna()
        
        if clean_values.empty:
            return default, default
        
        max_value = clean_values.max()
        max_idx = clean_values.idxmax()
        
        best_date = "N/A"
        if 'Date' in data.columns and max_idx in data.index:
            date_val = data.loc[max_idx, 'Date']
            if pd.notna(date_val):
                best_date = date_val.strftime('%Y-%m-%d')
        
        return float(max_value), best_date
        
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
        # 俊敏性・跳躍力のみ目標値あり（10mスプリントの目標値を修正）
        '10m_Sprint': {'U15': 1.7, 'U12': 1.9},
        '505_Test_Forward': {'U15': 2.8, 'U12': 3.2},
        '505_Test_Backward': {'U15': 3.0, 'U12': 3.0},
        'CODD': {'U15': 1.0, 'U12': 1.0},
        'BJ': {'U15': 80, 'U12': 60},
        'SH': {'U15': 15.0, 'U12': 15.0},  # %表記の目標値を±15.0%に変更
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
        
        # 日本語フォント対応（フォント設定を改善）
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
        
        # PDF文書の作成（マージンを最小限に、PDF設定を改善）
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            topMargin=0.5*cm,
            bottomMargin=0.5*cm,
            leftMargin=0.6*cm, 
            rightMargin=0.6*cm,
            allowSplitting=1,  # テキスト分割を許可
            title="KOA Physical Report",
            author="KOA Basketball Academy"
        )
        story = []
        
        # スタイル設定（フォント設定を改善）
        title_style = ParagraphStyle(
            'CustomTitle', 
            fontName=japanese_font,  # タイトルも日本語フォントに戻す
            fontSize=13,  # 11から13に戻す
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
            wordWrap='CJK'  # 日本語の改行処理を改善
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal', 
            fontName=japanese_font, 
            fontSize=10,
            spaceAfter=2,
            leading=12,  # 行間を少し広く
            wordWrap='CJK'
        )
        
        # ヘッダー部分（簡潔に）
        story.append(Paragraph("KOA Basketball Academy", title_style))
        story.append(Paragraph("フィジカルパフォーマンスレポート", title_style))
        
        # 氏名のみ（選手名から氏名に変更）
        player_info = f"氏名: {player_name}"
        story.append(Paragraph(player_info, normal_style))
        story.append(Spacer(1, 6))
        
        # フィジカルスコア（カテゴリーとスコアを横並び）
        story.append(Paragraph("フィジカルスコア", heading_style))
        story.append(Spacer(1, 6))
        valid_scores = [s for s in section_scores.values() if s > 0]
        overall_score = round(np.mean(valid_scores)) if valid_scores else 0
        
        # 横並びのスコア表（Overallを総合スコアに変更）
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
            # 中央配置のためのテーブルでラップ（サイズ調整）
            chart_table = Table([[radar_chart]], colWidths=[5.7*cm])  # 6*cmから5.7*cmに調整
            chart_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(chart_table)
            story.append(Spacer(1, -17))  # -12から-17に変更（さらに5ポイント上に移動）
            
            # 測定データ（見出しを「詳細測定データ」から「測定データ」に変更）
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
            story.append(Spacer(1, -17))  # -12から-17に変更（さらに5ポイント上に移動）
            
            # 測定データ（見出しを「詳細測定データ」から「測定データ」に変更）
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
            ('CODD', 'CODD', 'sec'),  # CODD追加
            ('BJ', '立ち幅跳び', 'cm'),
            ('SH', 'サイドホップテスト', '%'),
            ('SJ', 'スクワットジャンプ', 'cm'),  # SJ追加（名前を変更）
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
        body_composition_items = ['Height', 'Weight', 'BMI', 'Maturity']  # 身体組成系項目
        
        for metric_key, metric_name, unit in key_metrics:
            if metric_key not in df.columns:
                continue
                
            player_val = safe_get_value(player_data, metric_key)
            target_val = get_target_value_for_player(player_data, metric_key, target_values)
            
            # 前回値との変化のみ
            prev_val = None
            if len(player_data) >= 2:
                sorted_player_data = player_data.sort_values('Date', ascending=False)
                valid_data = sorted_player_data[sorted_player_data[metric_key].notna()]
                valid_data = valid_data[valid_data[metric_key] != 0]
                if len(valid_data) >= 2:
                    prev_val = float(valid_data.iloc[1][metric_key])
            
            # 変化の表示（データがない場合は「-」を表示）
            change_display = "-"
            if player_val is not None and prev_val is not None:
                difference = player_val - prev_val
                if abs(difference) > 0.01:
                    if difference > 0:
                        change_display = f"+{difference:.2f}"
                    else:
                        change_display = f"{difference:.2f}"
                else:
                    change_display = "→"
            
            # カテゴリー平均（サイドホップテストの場合は-を表示）
            if metric_key == 'SH':
                category_avg_display = "-"
            else:
                category_avg = safe_mean(category_data[metric_key])
                category_avg_display = f"{format_value(category_avg)}{unit}"
            
            # 身体組成系項目は目標値を「-」にする
            if metric_key in body_composition_items:
                target_display = "-"
            else:
                if metric_key == 'SH' and target_val is not None:
                    target_display = f"±{target_val:.1f}{unit}"  # サイドホップテストは±表記
                else:
                    target_display = f"{format_value(target_val)}{unit}" if target_val is not None else "-"
            
            # サイドホップテストの最新値表示（0%の場合も0%と表示）
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
        
        # テーブルスタイル（フォント設定を改善して文字化けを解決）
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), japanese_font),  # 全体を日本語フォントに統一
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
        
        # フィードバック（見出しを「個別フィードバック」から「フィードバック」に変更）
        story.append(Paragraph("フィードバック", heading_style))
        story.append(Spacer(1, 6))
        
        # フィードバックを一つの段落として表示（フォント設定を改善）
        feedback_style = ParagraphStyle(
            'FeedbackStyle', 
            fontName=japanese_font, 
            fontSize=8,
            spaceAfter=3,
            leading=11,  # 行間を適切に設定
            alignment=TA_LEFT,
            wordWrap='CJK'  # 日本語の改行処理
        )
        
        try:
            story.append(Paragraph(feedback_text, feedback_style))
        except:
            story.append(Paragraph("フィードバック内容の表示中にエラーが発生しました。", feedback_style))
        
        story.append(Spacer(1, 12))
        
        # 測定項目説明（修正された文章）
        story.append(Paragraph("測定項目について", heading_style))
        story.append(Spacer(1, 6))
        
        # 導入文
        intro_text = "育成年代（小・中・高校生）は発育発達の時期であり、身体の変化をモニタリングし、それに応じた指導が重要です。各カテゴリーの平均値・目標値は上記表に記載しています。"
        
        explanation_style = ParagraphStyle(
            'ExplanationStyle', 
            fontName=japanese_font, 
            fontSize=6,
            spaceAfter=2,
            leading=8,  # 行間を適切に設定
            alignment=TA_LEFT,
            wordWrap='CJK'
        )
        
        # 中タイトル用スタイル（フォント改善）
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
        
        # 項目説明用スタイル（フォント改善）
        item_style = ParagraphStyle(
            'ItemStyle', 
            fontName=japanese_font, 
            fontSize=6,
            spaceAfter=1,
            leading=8,  # 行間を適切に設定
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
            story.append(Paragraph("* 左右差15%未満 → 問題なし　　　* 左右差15%以上25%未満 → やや問題あり　　　* 左右差25%以上 → 問題あり", item_style))
            story.append(Paragraph("○スクワットジャンプ・垂直跳び：スクワットジャンプは下肢パワーを、垂直跳びはパワーと反動利用能力を評価します。", item_style))
            story.append(Paragraph("○リバウンドジャンプ：30cmボックスから落下後、接地時間を短く高く跳ぶテストで、\"バネの強さ\"を評価します。RSI（滞空時間/接地時間）を指標とします。", item_style))
            
        except:
            # 日本語でエラーが出る場合は英語で
            story.append(Paragraph("Explanation of measurement items (Japanese text)", explanation_style))
        
        # フッター（簡潔に）
        story.append(Spacer(1, 4))
        footer_style = ParagraphStyle(
            'Footer', 
            fontName=english_font,  # フッターは英語フォント
            fontSize=5,
            alignment=TA_CENTER, 
            textColor=colors.grey
        )
        
        story.append(Paragraph("©2025 KOA BASKETBALL ACADEMY ALL RIGHTS RESERVED", footer_style))
        
        # PDF生成
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
        from reportlab.graphics import renderPDF
        from reportlab.lib import colors as rl_colors
        from reportlab.platypus import KeepTogether
        import math
        
        # チャートサイズ（さらに3ポイント小さく）
        chart_width = 5.7*cm  # 6*cmから5.7*cmに変更
        chart_height = 3.3*cm # 3.5*cmから3.3*cmに変更
        
        drawing = Drawing(chart_width, chart_height)
        
        # 三角形の中心点と半径（チャートサイズに合わせてさらに調整）
        center_x = chart_width / 2
        center_y = chart_height / 2 - 0.08*cm  # 0.1*cmから0.08*cmに調整
        radius = 1.3*cm  # 1.4*cmから1.3*cmに調整
        
        # 三角形の頂点を計算（上向き三角形）
        angles = [90, 210, 330]  # 度数（上、左下、右下）
        triangle_points = []
        for angle in angles:
            rad = math.radians(angle)
            x = center_x + radius * math.cos(rad)
            y = center_y + radius * math.sin(rad)
            triangle_points.extend([x, y])
        
        # レーダーチャートの外枠（5段階）
        for level in range(1, 6):
            scale = level / 5.0
            scaled_points = []
            for i in range(0, len(triangle_points), 2):
                base_x = triangle_points[i]
                base_y = triangle_points[i+1]
                scaled_x = center_x + (base_x - center_x) * scale
                scaled_y = center_y + (base_y - center_y) * scale
                scaled_points.extend([scaled_x, scaled_y])
            
            # 三角形の描画
            color = rl_colors.Color(0.8, 0.8, 0.8, alpha=0.3) if level < 5 else rl_colors.Color(0.6, 0.6, 0.6, alpha=0.5)
            triangle = Polygon(scaled_points)
            triangle.fillColor = None
            triangle.strokeColor = color
            triangle.strokeWidth = 1
            drawing.add(triangle)
        
        # データポイントの計算
        scores = [
            section_scores.get('身体組成', 0),  # 上
            section_scores.get('俊敏性', 0),    # 左下
            section_scores.get('跳躍力', 0)     # 右下
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
        
        # データ三角形の描画
        if len(data_points) == 6:
            data_triangle = Polygon(data_points)
            data_triangle.fillColor = rl_colors.Color(0.2, 0.7, 0.3, alpha=0.3)
            data_triangle.strokeColor = rl_colors.Color(0.1, 0.5, 0.2)
            data_triangle.strokeWidth = 2
            drawing.add(data_triangle)
        
        # ラベルの追加（総合スコアも含めて4つのラベルに変更）
        labels = ['身体組成', '俊敏性', '跳躍力', '総合スコア']
        scores_for_labels = [
            section_scores.get('身体組成', 0),  # 上
            section_scores.get('俊敏性', 0),    # 左下
            section_scores.get('跳躍力', 0),    # 右下
            overall_score if overall_score > 0 else 0  # 下部に総合スコア追加
        ]
        label_positions = [
            (center_x, center_y + radius + 0.25*cm),      # 上
            (center_x - radius - 0.5*cm, center_y - radius/2),  # 左下
            (center_x + radius + 0.5*cm, center_y - radius/2),   # 右下
            (center_x, center_y - radius + 0.37*cm)       # 下部に総合スコア追加（-0.05*cmから+0.37*cmに変更、約12ポイント上に移動）
        ]
        
        for i, (label, (x, y)) in enumerate(zip(labels, label_positions)):
            score = scores_for_labels[i]
            text = f"{label} ({score if score > 0 else 'N/A'})"
            label_text = String(x, y, text)
            # 日本語フォントを試行、エラー時はHelveticaにフォールバック
            try:
                label_text.fontName = 'HeiseiKakuGo-W5'
            except:
                label_text.fontName = 'Helvetica'
            label_text.fontSize = 5  # フォントサイズを統一
            label_text.textAnchor = 'middle'
            label_text.fillColor = rl_colors.Color(0.2, 0.2, 0.2)
            drawing.add(label_text)
        
        return drawing
        
    except Exception as e:
        # レーダーチャート作成に失敗した場合はNoneを返す
        return None

def generate_all_pdf_reports(df, config):
    """全選手のPDFレポートを生成してZIPファイルに格納"""
    try:
        import zipfile
        from io import BytesIO
        
        # ZIPファイルのメモリバッファ
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 全選手のリストを取得
            all_players = df['Name'].dropna().unique()
            
            for player_name in all_players:
                try:
                    # 各選手のデータを取得
                    player_data = df[df['Name'] == player_name]
                    
                    if player_data.empty:
                        continue
                    
                    # 各セクションのスコアを計算
                    section_scores = {}
                    for category, category_config in config.items():
                        reverse_scoring = category_config.get('reverse_scoring', False)
                        score, detail = calculate_section_score(player_data, df, category_config['score_metrics'], reverse_scoring)
                        section_scores[category_config['name']] = score if score is not None else 0
                    
                    # フィードバック生成（編集されたものがあれば使用）
                    feedback_key = f"feedback_{player_name}"
                    if feedback_key in st.session_state:
                        feedback_text = st.session_state[feedback_key]
                    else:
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
                        # スペースを削除してファイル名を作成
                        clean_name = player_name.replace(" ", "").replace("　", "")  # 半角・全角スペース削除
                        # ファイル名を安全にする（特殊文字を除去）
                        safe_name = "".join(c for c in clean_name if c.isalnum() or c in ('-', '_')).rstrip()
                        filename = f"{safe_name} フィジカルフィードバックシート_2025.8.pdf"  # 半角スペース使用
                        
                        # ZIPファイルに追加
                        zip_file.writestr(filename, pdf_bytes)
                        
                except Exception as e:
                    # 個別の選手でエラーが発生しても処理を続行
                    print(f"選手 {player_name} のPDF生成でエラー: {str(e)}")
                    continue
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
        
    except Exception as e:
        print(f"全員分PDF生成エラー: {str(e)}")
        return None

def create_zip_download_link(zip_bytes, filename):
    """ZIPファイルダウンロードリンクを作成"""
    b64_zip = base64.b64encode(zip_bytes).decode()
    href = f'<a href="data:application/zip;base64,{b64_zip}" download="{filename}" style="text-decoration: none;">'
    href += '<div style="background: linear-gradient(135deg, #1565C0 0%, #1976D2 100%); '
    href += 'color: white; padding: 12px 24px; border-radius: 8px; text-align: center; '
    href += 'font-weight: bold; margin: 10px 0; display: inline-block; '
    href += 'box-shadow: 0 4px 12px rgba(21, 101, 192, 0.3);">'
    href += '📁 全員分PDFレポート（ZIP）をダウンロード</div></a>'
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
            height=200,
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
        font-size: 1.1rem;
    ">
        {feedback_text}
    </div>
    """, unsafe_allow_html=True)
    
    # PDF出力ボタン
    if PDF_AVAILABLE:
        st.markdown("### PDFレポート出力")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        # 個人レポート生成
        with col1:
            if st.button("📄 個人PDFレポート生成", type="primary"):
                with st.spinner('PDFレポートを生成中...'):
                    # 編集されたフィードバックを取得
                    current_feedback = st.session_state.get(f"feedback_{selected_name}", feedback_text)
                    
                    pdf_bytes = generate_pdf_report(
                        selected_name, 
                        section_scores, 
                        current_feedback,  # 編集されたフィードバックを使用
                        player_data, 
                        df, 
                        config
                    )
                    
                    if pdf_bytes:
                        # スペースを削除してファイル名を作成
                        clean_name = selected_name.replace(" ", "").replace("　", "")  # 半角・全角スペース削除
                        filename = f"{clean_name} フィジカルフィードバックシート_2025.8.pdf"  # 半角スペース使用
                        download_link = create_download_link(pdf_bytes, filename)
                        st.markdown(download_link, unsafe_allow_html=True)
                        st.success("PDFレポートが生成されました！")
                    else:
                        st.error("PDFレポートの生成に失敗しました。")
        
        # 全員分レポート生成
        with col2:
            if st.button("📁 全員分PDFレポート生成", type="secondary"):
                with st.spinner('全員分のPDFレポートを生成中...'):
                    all_pdf_bytes = generate_all_pdf_reports(df, config)
                    
                    if all_pdf_bytes:
                        filename = f"KOA フィジカルフィードバックシート_2025.8_全員分.zip"  # 半角スペース使用
                        download_link = create_zip_download_link(all_pdf_bytes, filename)
                        st.markdown(download_link, unsafe_allow_html=True)
                        st.success(f"全{len(available_names)}名分のPDFレポートが生成されました！")
                    else:
                        st.error("全員分PDFレポートの生成に失敗しました。")
        
        with col3:
            st.info("個人レポート：選択した選手のみ｜全員分レポート：全選手のPDFをZIPファイルでダウンロード")
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