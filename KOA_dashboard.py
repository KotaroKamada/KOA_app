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
            '505テスト': '505_Test',
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
        numeric_columns = ['Height', 'Weight', 'BMI', 'Maturity', '10m_Sprint', '505_Test', 'CODD', 'BJ', 'SH', 'SJ', 'CMJ', 'RJ']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
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
            'score_metrics': ['10m_Sprint', '505_Test'],
            'display_metrics': ['10m_Sprint', '505_Test', 'CODD'],
            'units': {
                '10m_Sprint': 'sec',
                '505_Test': 'sec',
                'CODD': 'sec'
            },
            'highlight': ['10m_Sprint', '505_Test', 'CODD'],
            'japanese_names': {
                '10m_Sprint': '10mスプリント',
                '505_Test': '505テスト',
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
                'SH': 'cm',
                'SJ': 'cm',
                'CMJ': 'cm',
                'RJ': 'index'
            },
            'highlight': ['BJ', 'CMJ', 'RJ'],
            'japanese_names': {
                'BJ': 'BJ',
                'SH': 'SH',
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
        
        # 各測定項目の定義（身体組成を除く）
        agility_metrics = {
            '10m_Sprint': {'name': '10mスプリント', 'reverse': True},
            '505_Test': {'name': '505テスト', 'reverse': True},
            'CODD': {'name': 'CODD', 'reverse': True}
        }
        
        jumping_metrics = {
            'BJ': {'name': '立ち幅跳び', 'reverse': False},
            'SH': {'name': 'サイドホップ', 'reverse': False},
            'SJ': {'name': 'スクワットジャンプ', 'reverse': False},
            'CMJ': {'name': 'カウンタームーブメントジャンプ', 'reverse': False},
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
        
        # 導入部分
        if overall_avg >= 4.5:
            intro = f"{player_name}選手は非常に優れた総合フィジカル能力を示しており、競技レベルでの活躍が大いに期待できます。"
        elif overall_avg >= 4:
            intro = f"{player_name}選手は優秀なフィジカル能力を持っており、さらなる専門性向上により一層の成長が期待できます。"
        elif overall_avg >= 3:
            intro = f"{player_name}選手は平均的なフィジカル能力を示しており、今後の取り組み次第で大きな成長が見込めます。"
        else:
            intro = f"{player_name}選手には豊富な成長ポテンシャルがあり、継続的なトレーニングで必ず向上していきます。"
        
        feedback.append(intro)
        
        # 前回との比較コメント
        if progress_analysis['has_comparison']:
            if progress_analysis['improved_metrics']:
                improved_names = [agility_metrics.get(m, {}).get('name', m) or jumping_metrics.get(m, {}).get('name', m) for m in progress_analysis['improved_metrics']]
                feedback.append(f"前回と比較して、{improved_names[0]}")
                if len(improved_names) > 1:
                    feedback.append(f"や{improved_names[1]}")
                feedback.append("で向上が見られ、継続的な努力の成果が現れています。")
            
            if progress_analysis['declined_metrics']:
                declined_names = [agility_metrics.get(m, {}).get('name', m) or jumping_metrics.get(m, {}).get('name', m) for m in progress_analysis['declined_metrics']]
                feedback.append(f"一方で、{declined_names[0]}")
                if len(declined_names) > 1:
                    feedback.append(f"と{declined_names[1]}")
                feedback.append("については前回より数値が下がっていますが、これは測定時のコンディションや成長期における一時的な変化の可能性もあります。")
            
            if progress_analysis['stable_metrics']:
                feedback.append("その他の項目では安定した数値を維持しており、基礎体力の定着が確認できます。")
        
        # 優れている点の詳細分析
        high_agility_metrics = [k for k, v in agility_metric_scores.items() if v >= 4]
        high_jumping_metrics = [k for k, v in jumping_metric_scores.items() if v >= 4]
        
        strengths = []
        if agility_score >= 4:
            if '10m_Sprint' in high_agility_metrics:
                strengths.append("短距離での爆発的な加速力")
            if '505_Test' in high_agility_metrics:
                strengths.append("方向転換時の優れた減速・再加速能力")
            if 'CODD' in high_agility_metrics:
                strengths.append("純粋な切り返し動作の技術")
            if not high_agility_metrics:
                strengths.append("バランスの取れた俊敏性")
        
        if jumping_score >= 4:
            if 'CMJ' in high_jumping_metrics:
                strengths.append("反動を活かした効率的な跳躍力")
            if 'SJ' in high_jumping_metrics:
                strengths.append("下肢の純粋なパワー発揮能力")
            if 'BJ' in high_jumping_metrics:
                strengths.append("水平方向への瞬発力")
            if 'RJ' in high_jumping_metrics:
                strengths.append("短時間での連続跳躍能力")
            if not high_jumping_metrics:
                strengths.append("総合的な跳躍能力")
        
        if strengths:
            feedback.append(f"特に{strengths[0]}")
            if len(strengths) > 1:
                feedback.append(f"と{strengths[1]}")
            feedback.append("が優秀で、これらの能力はゲーム中の重要な武器となります。")
        
        # 改善点と具体的なトレーニング提案
        improvement_areas = []
        training_suggestions = []
        
        if agility_score <= 2:
            low_agility_metrics = [k for k, v in agility_metric_scores.items() if v <= 2]
            if '10m_Sprint' in low_agility_metrics:
                improvement_areas.append("初速の向上")
                training_suggestions.append("スタートダッシュ練習（山なりスタート、クラウチングスタート）や股関節のストレッチ・可動域改善")
            if '505_Test' in low_agility_metrics:
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
                improvement_areas.append("反動利用技術")
                training_suggestions.append("プライオメトリクス（ボックスジャンプ、デプスジャンプ、バウンディング）")
            if 'SJ' in low_jumping_metrics:
                improvement_areas.append("下肢筋力")
                training_suggestions.append("基礎筋力トレーニング（スクワット、ランジ、カーフレイズ、ヒップスラスト）")
            if 'BJ' in low_jumping_metrics:
                improvement_areas.append("水平跳躍力")
                training_suggestions.append("ホップ系練習（シングルレッグホップ、バウンドジャンプ）、前方ジャンプトレーニング")
            if 'RJ' in low_jumping_metrics:
                improvement_areas.append("連続跳躍能力")
                training_suggestions.append("リアクティブジャンプ（連続ジャンプ、ハードルジャンプ）、ポゴジャンプ")
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

def create_comparison_table(player_data, all_data, metrics, category, config):
    """比較表の作成"""
    table_data = []
    
    japanese_names = config[category].get('japanese_names', {})
    
    for metric in metrics:
        player_val = safe_get_value(player_data, metric)
        best_val, best_date = safe_get_best_value(player_data, metric)
        avg_val = safe_mean(all_data[metric])
        
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
            'チーム平均': format_value(avg_val)
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
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
            japanese_font = 'HeiseiKakuGo-W5'
        except:
            japanese_font = 'Helvetica'
        
        # PDF文書の作成（マージンを最小限に）
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            topMargin=0.5*cm,
            bottomMargin=0.5*cm,
            leftMargin=0.6*cm, 
            rightMargin=0.6*cm
        )
        story = []
        
        # スタイル設定（全体的に小さく）
        title_style = ParagraphStyle(
            'CustomTitle', 
            fontName=japanese_font, 
            fontSize=17,  # 15から17に変更（+2ポイント）
            spaceAfter=4,
            alignment=TA_CENTER, 
            textColor=colors.Color(0.2, 0.2, 0.2)
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading', 
            fontName=japanese_font, 
            fontSize=10,
            spaceAfter=3,
            spaceBefore=4,
            textColor=colors.Color(0.3, 0.3, 0.3)
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal', 
            fontName=japanese_font, 
            fontSize=10,  # 8から10に変更（+2ポイント）
            spaceAfter=2,
            leading=11
        )
        
        # ヘッダー部分（簡潔に）
        story.append(Paragraph("KOA Basketball Academy", title_style))
        story.append(Paragraph("フィジカルパフォーマンスレポート", title_style))
        
        # 選手名のみ
        player_info = f"選手名: {player_name}"
        story.append(Paragraph(player_info, normal_style))
        story.append(Spacer(1, 6))
        
        # フィジカルスコア（カテゴリーとスコアを横並び）
        story.append(Paragraph("フィジカルスコア", heading_style))
        story.append(Spacer(1, 6))  # 0.5行追加のスペース
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
        
        score_table = Table([score_data[0]], colWidths=[2.5*cm, 1.5*cm, 2.5*cm, 1.5*cm, 2.5*cm, 1.5*cm, 2.5*cm, 1.5*cm])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), japanese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 8))
        
        # フィジカルバランス（三角形レーダーチャート）
        # タイトルなしで直接チャートを表示（中央配置）
        radar_chart = create_triangle_radar_chart(section_scores, overall_score)
        if radar_chart:
            # 中央配置のためのテーブルでラップ
            chart_table = Table([[radar_chart]], colWidths=[8*cm])
            chart_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(chart_table)
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
        story.append(Spacer(1, 8))
        
        # 詳細測定データ（簡略化）
        story.append(Paragraph("詳細測定データ", heading_style))
        
        key_metrics = [
            ('Height', '身長', 'cm'),
            ('Weight', '体重', 'kg'),
            ('BMI', 'BMI', ''),
            ('10m_Sprint', '10mスプリント', 'sec'),
            ('505_Test', '505テスト', 'sec'),
            ('BJ', '立ち幅跳び', 'cm'),
            ('CMJ', 'CMJ', 'cm'),
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
        
        detail_data = [['測定項目', '最新値', '変化', 'カテゴリー平均']]
        
        for metric_key, metric_name, unit in key_metrics:
            if metric_key not in df.columns:
                continue
                
            player_val = safe_get_value(player_data, metric_key)
            
            # 前回値との変化のみ
            prev_val = None
            if len(player_data) >= 2:
                sorted_player_data = player_data.sort_values('Date', ascending=False)
                valid_data = sorted_player_data[sorted_player_data[metric_key].notna()]
                valid_data = valid_data[valid_data[metric_key] != 0]
                if len(valid_data) >= 2:
                    prev_val = float(valid_data.iloc[1][metric_key])
            
            change_display = "→"
            if player_val is not None and prev_val is not None:
                difference = player_val - prev_val
                if abs(difference) > 0.01:
                    if difference > 0:
                        change_display = f"+{difference:.2f}"
                    else:
                        change_display = f"{difference:.2f}"
            
            category_avg = safe_mean(category_data[metric_key])
            
            detail_data.append([
                metric_name,
                f"{format_value(player_val)}{unit}",
                change_display,
                f"{format_value(category_avg)}{unit}"
            ])
        
        detail_table = Table(detail_data, colWidths=[4*cm, 3*cm, 2.5*cm, 3*cm])
        detail_table.setStyle(TableStyle([
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
        ]))
        
        story.append(detail_table)
        story.append(Spacer(1, 12))  # 1行分のスペースを追加
        
        # 個別フィードバック（改行して全文表示）
        story.append(Paragraph("個別フィードバック", heading_style))
        story.append(Spacer(1, 6))  # 0.5行分のスペースを追加
        
        # フィードバックを一つの段落として表示
        feedback_style = ParagraphStyle(
            'FeedbackStyle', 
            fontName=japanese_font, 
            fontSize=8,  # 9から8に変更（-1ポイント）
            spaceAfter=3,
            leading=10,
            alignment=TA_LEFT
        )
        
        try:
            story.append(Paragraph(feedback_text, feedback_style))
        except:
            story.append(Paragraph("フィードバック内容の表示中にエラーが発生しました。", feedback_style))
        
        story.append(Spacer(1, 12))  # 1行分のスペースを追加
        
        # 測定項目説明（指定された全文）
        story.append(Paragraph("測定項目について", heading_style))
        story.append(Spacer(1, 6))  # 0.5行分のスペースを追加
        
        # 導入文
        intro_text = "育成年代（小・中・高校生）は発育発達の時期であり、身体の変化をモニタリングし、それに応じた指導が重要です。各カテゴリーの平均値・目標値は上記表に記載しています。"
        
        explanation_style = ParagraphStyle(
            'ExplanationStyle', 
            fontName=japanese_font, 
            fontSize=7,  # 9から7に変更
            spaceAfter=2,
            leading=8,
            alignment=TA_LEFT
        )
        
        # 中タイトル用スタイル
        subtitle_style = ParagraphStyle(
            'SubtitleStyle', 
            fontName=japanese_font, 
            fontSize=8,  # 10から8に変更
            spaceAfter=1,
            spaceBefore=3,
            alignment=TA_LEFT,
            textColor=colors.Color(0.2, 0.2, 0.2)
        )
        
        # 項目説明用スタイル（○項目）
        item_style = ParagraphStyle(
            'ItemStyle', 
            fontName=japanese_font, 
            fontSize=7,  # 9から7に変更
            spaceAfter=1,
            leading=8,
            alignment=TA_LEFT,
            leftIndent=0.5*cm
        )
        
        try:
            story.append(Paragraph(intro_text, explanation_style))
            story.append(Spacer(1, 4))
            
            # 体組成セクション
            story.append(Paragraph("<体組成>", subtitle_style))
            story.append(Paragraph("○BMI 身長あたりの体重を示します。U12・U15年代は筋肉がつきづらく低値になりやすいですが、高校生以上は25.0〜26.0kg/m²を目指します。", item_style))
            story.append(Paragraph("○成熟度 身長の伸び率が最大になる時期をPHV（ピーク身長成長速度）と呼び、PHV前後で取り組むべきトレーニングが異なるとされています。成熟度は、身長・体重・脚長から推定されるPHVからの年数で表します。", item_style))
            
            # 俊敏性セクション
            story.append(Paragraph("<俊敏性>", subtitle_style))
            story.append(Paragraph("○10mスプリント バスケットボールは28m以内のコートで行うため、トップスピードよりも速く加速する能力が重要です。", item_style))
            story.append(Paragraph("○505テスト 5m直線スプリント後にバックペダルで折り返すテストで、減速と再加速の能力を評価します。", item_style))
            story.append(Paragraph("○CODD 505テストタイムからスプリントタイムを引き、純粋な切り返し能力を評価します。", item_style))
            
            # 跳躍能力セクション
            story.append(Paragraph("<跳躍能力>", subtitle_style))
            story.append(Paragraph("○立ち幅跳び（BJ） 瞬発力を評価します。身長の影響を考慮し、ジャンプ距離（cm）から身長（cm）を引いた値を用います。", item_style))
            story.append(Paragraph("○Side hop test 片脚で10秒間に左右に何回ホップできるかを評価し、左右差から足関節の安定性を判断します。", item_style))
            story.append(Paragraph("* 左右差15%未満 → 問題なし", item_style))
            story.append(Paragraph("* 15%以上25%未満 → やや問題あり", item_style))
            story.append(Paragraph("* 25%以上 → 問題あり", item_style))
            story.append(Paragraph("○スクワットジャンプ・カウンタームーブメントジャンプ（SJ・CMJ） SJは下肢パワーを、CMJはパワーと反動利用能力を評価します。", item_style))
            story.append(Paragraph("○リバウンドジャンプ（RJ） 30cmボックスから落下後、接地時間を短く高く跳ぶテストで、爆発的パワーを評価します。RSI（滞空時間/接地時間）を指標とします。", item_style))
            
        except:
            # 日本語でエラーが出る場合は英語で
            story.append(Paragraph("Explanation of measurement items (Japanese text)", explanation_style))
        
        # フッター（簡潔に）
        story.append(Spacer(1, 4))
        footer_style = ParagraphStyle(
            'Footer', 
            fontName=japanese_font, 
            fontSize=7,
            alignment=TA_CENTER, 
            textColor=colors.grey
        )
        
        story.append(Paragraph("KOA Basketball Academy Physical Performance Dashboard", footer_style))
        
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
        
        # チャートサイズ（さらに小さく）
        chart_width = 8*cm
        chart_height = 5.5*cm
        
        drawing = Drawing(chart_width, chart_height)
        
        # 三角形の中心点と半径（さらに小さく）
        center_x = chart_width / 2
        center_y = chart_height / 2 - 0.3*cm
        radius = 2*cm
        
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
        
        # ラベルの追加（英語に変更）
        labels = ['Body Composition', 'Agility', 'Jumping']
        label_positions = [
            (center_x, center_y + radius + 0.3*cm),      # 上
            (center_x - radius - 0.6*cm, center_y - radius/2),  # 左下
            (center_x + radius + 0.6*cm, center_y - radius/2)   # 右下
        ]
        
        for i, (label, (x, y)) in enumerate(zip(labels, label_positions)):
            score = scores[i]
            text = f"{label} ({score if score > 0 else 'N/A'})"
            label_text = String(x, y, text)
            label_text.fontName = 'Helvetica'
            label_text.fontSize = 7  # 8から7に縮小
            label_text.textAnchor = 'middle'
            label_text.fillColor = rl_colors.Color(0.2, 0.2, 0.2)
            drawing.add(label_text)
        
        # 総合スコアを中央に表示
        total_text = String(center_x, center_y - 1.6*cm, f"Overall: {overall_score if overall_score > 0 else 'N/A'}")
        total_text.fontName = 'Helvetica-Bold'
        total_text.fontSize = 9  # 10から9に縮小
        total_text.textAnchor = 'middle'
        total_text.fillColor = rl_colors.Color(0.1, 0.1, 0.1)
        drawing.add(total_text)
        
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
                        # ファイル名を安全にする（特殊文字を除去）
                        safe_name = "".join(c for c in player_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        filename = f"KOA_Physical_Report_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
                        
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
                        filename = f"KOA_Physical_Report_{selected_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
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
                        filename = f"KOA_All_Physical_Reports_{datetime.now().strftime('%Y%m%d')}.zip"
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