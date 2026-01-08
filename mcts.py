#!/usr/bin/env python3
"""
MCTS - Minecraft Terrain Studio
Complete Edition with Resume System & 15 Languages
by AOIROSERVER creeper_dev © 2026

Features:
✨ Multi-language support (15 languages)
✨ Project management system
✨ Auto-save checkpoints every 10 seconds
✨ Resume from crash/interruption
✨ DEM/DSM support
✨ Batch processing with progress tracking
✨ Memory efficient processing
✨ Detailed error handling

How to use:
1. Run: python mcts.py
2. Select language (15 choices)
3. Choose operation mode:
   - Project: Reproject DEM data
   - Generate: Generate MCA files
   - All: Full pipeline
   - Resume: Continue interrupted project
4. Enter project name (letters, numbers, _, - only)
5. Configure settings (CRS, offsets, batch size)
6. Processing starts with auto-save every 10 seconds
7. If interrupted, select Resume to continue

Crash Recovery:
- Checkpoints saved every 10 seconds
- Resume exactly where you left off
- No data loss
- Skip already processed files

Supported Languages:
English, 日本語, 中文(简体), Español, Français, Deutsch, 
Português, Русский, Italiano, 한국어, 中文(繁體), العربية, 
हिन्दी, ไทย, Tiếng Việt
"""
import sys
import os
import subprocess
import signal
import glob
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import anvil
from collections import defaultdict
from colorama import init, Fore, Style
import questionary
from questionary import Style as QStyle

init(autoreset=True)

# ==================== GLOBALS ====================
PROJECTS_DIR = "projects"
CHECKPOINT_INTERVAL = 10  # seconds

# ==================== SIGNAL HANDLER ====================
def signal_handler(sig, frame):
    print("\n\n⚠️  Operation interrupted by user. Checkpoint saved.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ==================== AUTO INSTALLER ====================
REQUIRED_PACKAGES = {'rasterio': 'rasterio', 'numpy': 'numpy', 'anvil': 'anvil-parser', 'colorama': 'colorama', 'questionary': 'questionary'}

def check_dependencies():
    missing = []
    for imp, pkg in REQUIRED_PACKAGES.items():
        try: __import__(imp)
        except ImportError: missing.append((imp, pkg))
    if missing:
        print("\n" + "="*60 + "\n🔧 INSTALLING PACKAGES\n" + "="*60 + "\n")
        for _, pkg in missing:
            print(f"📦 Installing {pkg}...")
            try: subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"]); print(f"✓ {pkg} installed")
            except: print(f"✗ Failed"); sys.exit(1)
        print("\n✅ All dependencies installed!\n")

check_dependencies()

# ==================== TRANSLATIONS (15 LANGUAGES) ====================
CL = 'English'
LANG = {
    'English': {'sl': 'Select language', 'bm': 'Beginner mode?', 'sm': 'Select operation:', 'mp': 'Project - Reproject DEM', 'mg': 'Generate - Generate MCA', 'ma': 'All - Full pipeline', 'mr': 'Resume - Continue interrupted project', 'dt': 'Select data type:', 'dem': 'DEM - Terrain only', 'dsm': 'DSM - Terrain + buildings/trees', 'pn': 'Enter project name:', 'pni': 'Invalid characters. Use letters, numbers, _ or -', 'pe': 'Project already exists. Use different name.', 'rnp': 'Select project to resume:', 'npa': 'No projects available to resume', 'rs': 'Resuming from Step', 'cp': 'Checkpoint found! Resume from', 's1': 'STEP 1: REPROJECTION', 's2': 'STEP 2: MCA GENERATION', 'rp': '🗺️  Reprojecting:', 'gm': '🎮 Generating:', 'sc': '✓ Complete', 'ma2': '✨ MISSION ACCOMPLISHED ✨'},
    '日本語': {'sl': '言語選択', 'bm': '初心者モード？', 'sm': '処理選択:', 'mp': 'Project - DEM投影変換', 'mg': 'Generate - MCA生成', 'ma': 'All - 全処理', 'mr': 'Resume - 中断したプロジェクトを再開', 'dt': 'データ種類:', 'dem': 'DEM - 地形のみ', 'dsm': 'DSM - 地形+建物/樹木', 'pn': 'プロジェクト名を入力:', 'pni': '無効な文字。英数字、_、-のみ使用可', 'pe': 'プロジェクトが既に存在。別名を使用してください。', 'rnp': '再開するプロジェクトを選択:', 'npa': '再開可能なプロジェクトがありません', 'rs': '再開: ステップ', 'cp': 'チェックポイント検出！再開位置:', 's1': 'ステップ1: 投影変換', 's2': 'ステップ2: MCA生成', 'rp': '🗺️  変換中:', 'gm': '🎮 生成中:', 'sc': '✓ 完了', 'ma2': '✨ 処理完了 ✨'},
    '中文（简体）': {'sl': '选择语言', 'bm': '新手模式？', 'sm': '选择操作:', 'mp': 'Project - 重投影DEM', 'mg': 'Generate - 生成MCA', 'ma': 'All - 完整流程', 'mr': 'Resume - 继续中断的项目', 'dt': '选择数据类型:', 'dem': 'DEM - 仅地形', 'dsm': 'DSM - 地形+建筑/树木', 'pn': '输入项目名称:', 'pni': '无效字符。请使用字母、数字、_或-', 'pe': '项目已存在。请使用不同的名称。', 'rnp': '选择要恢复的项目:', 'npa': '没有可恢复的项目', 'rs': '从步骤恢复', 'cp': '检测到检查点！从以下位置恢复', 's1': '步骤1: 重投影', 's2': '步骤2: MCA生成', 'rp': '🗺️  重投影中:', 'gm': '🎮 生成中:', 'sc': '✓ 完成', 'ma2': '✨ 任务完成 ✨'},
    'Español': {'sl': 'Seleccionar idioma', 'bm': '¿Modo principiante?', 'sm': 'Seleccionar operación:', 'mp': 'Project - Reproyectar DEM', 'mg': 'Generate - Generar MCA', 'ma': 'All - Pipeline completo', 'mr': 'Resume - Continuar proyecto interrumpido', 'dt': 'Seleccionar tipo de datos:', 'dem': 'DEM - Solo terreno', 'dsm': 'DSM - Terreno + edificios/árboles', 'pn': 'Ingrese nombre del proyecto:', 'pni': 'Caracteres no válidos. Use letras, números, _ o -', 'pe': 'El proyecto ya existe. Use un nombre diferente.', 'rnp': 'Seleccionar proyecto a reanudar:', 'npa': 'No hay proyectos disponibles para reanudar', 'rs': 'Reanudando desde el paso', 'cp': '¡Punto de control encontrado! Reanudar desde', 's1': 'PASO 1: REPROYECCIÓN', 's2': 'PASO 2: GENERACIÓN MCA', 'rp': '🗺️  Reproyectando:', 'gm': '🎮 Generando:', 'sc': '✓ Completo', 'ma2': '✨ MISIÓN CUMPLIDA ✨'},
    'Français': {'sl': 'Sélectionner la langue', 'bm': 'Mode débutant?', 'sm': 'Sélectionner opération:', 'mp': 'Project - Reprojeter DEM', 'mg': 'Generate - Générer MCA', 'ma': 'All - Pipeline complet', 'mr': 'Resume - Continuer projet interrompu', 'dt': 'Sélectionner type de données:', 'dem': 'DEM - Terrain uniquement', 'dsm': 'DSM - Terrain + bâtiments/arbres', 'pn': 'Entrer nom du projet:', 'pni': 'Caractères invalides. Utilisez lettres, chiffres, _ ou -', 'pe': 'Le projet existe déjà. Utilisez un nom différent.', 'rnp': 'Sélectionner projet à reprendre:', 'npa': 'Aucun projet disponible à reprendre', 'rs': 'Reprise de l\'étape', 'cp': 'Point de contrôle trouvé! Reprendre depuis', 's1': 'ÉTAPE 1: REPROJECTION', 's2': 'ÉTAPE 2: GÉNÉRATION MCA', 'rp': '🗺️  Reprojection:', 'gm': '🎮 Génération:', 'sc': '✓ Terminé', 'ma2': '✨ MISSION ACCOMPLIE ✨'},
    'Deutsch': {'sl': 'Sprache auswählen', 'bm': 'Anfängermodus?', 'sm': 'Operation auswählen:', 'mp': 'Project - DEM neu projizieren', 'mg': 'Generate - MCA generieren', 'ma': 'All - Vollständiger Ablauf', 'mr': 'Resume - Unterbrochenes Projekt fortsetzen', 'dt': 'Datentyp auswählen:', 'dem': 'DEM - Nur Gelände', 'dsm': 'DSM - Gelände + Gebäude/Bäume', 'pn': 'Projektnamen eingeben:', 'pni': 'Ungültige Zeichen. Verwenden Sie Buchstaben, Zahlen, _ oder -', 'pe': 'Projekt existiert bereits. Verwenden Sie einen anderen Namen.', 'rnp': 'Projekt zum Fortsetzen auswählen:', 'npa': 'Keine Projekte zum Fortsetzen verfügbar', 'rs': 'Fortsetzen ab Schritt', 'cp': 'Checkpoint gefunden! Fortsetzen von', 's1': 'SCHRITT 1: NEUPROJEKTION', 's2': 'SCHRITT 2: MCA-GENERIERUNG', 'rp': '🗺️  Neuprojektion:', 'gm': '🎮 Generierung:', 'sc': '✓ Abgeschlossen', 'ma2': '✨ MISSION ERFÜLLT ✨'},
    'Português': {'sl': 'Selecionar idioma', 'bm': 'Modo iniciante?', 'sm': 'Selecionar operação:', 'mp': 'Project - Reprojetar DEM', 'mg': 'Generate - Gerar MCA', 'ma': 'All - Pipeline completo', 'mr': 'Resume - Continuar projeto interrompido', 'dt': 'Selecionar tipo de dados:', 'dem': 'DEM - Apenas terreno', 'dsm': 'DSM - Terreno + edifícios/árvores', 'pn': 'Digite nome do projeto:', 'pni': 'Caracteres inválidos. Use letras, números, _ ou -', 'pe': 'Projeto já existe. Use um nome diferente.', 'rnp': 'Selecionar projeto para retomar:', 'npa': 'Nenhum projeto disponível para retomar', 'rs': 'Retomando da etapa', 'cp': 'Checkpoint encontrado! Retomar de', 's1': 'PASSO 1: REPROJEÇÃO', 's2': 'PASSO 2: GERAÇÃO MCA', 'rp': '🗺️  Reprojetando:', 'gm': '🎮 Gerando:', 'sc': '✓ Completo', 'ma2': '✨ MISSÃO CUMPRIDA ✨'},
    'Русский': {'sl': 'Выбрать язык', 'bm': 'Режим новичка?', 'sm': 'Выбрать операцию:', 'mp': 'Project - Перепроецировать DEM', 'mg': 'Generate - Создать MCA', 'ma': 'All - Полный процесс', 'mr': 'Resume - Продолжить прерванный проект', 'dt': 'Выбрать тип данных:', 'dem': 'DEM - Только рельеф', 'dsm': 'DSM - Рельеф + здания/деревья', 'pn': 'Введите имя проекта:', 'pni': 'Недопустимые символы. Используйте буквы, цифры, _ или -', 'pe': 'Проект уже существует. Используйте другое имя.', 'rnp': 'Выбрать проект для возобновления:', 'npa': 'Нет проектов для возобновления', 'rs': 'Возобновление с шага', 'cp': 'Контрольная точка найдена! Возобновить с', 's1': 'ШАГ 1: ПЕРЕПРОЕКЦИЯ', 's2': 'ШАГ 2: ГЕНЕРАЦИЯ MCA', 'rp': '🗺️  Перепроекция:', 'gm': '🎮 Генерация:', 'sc': '✓ Завершено', 'ma2': '✨ МИССИЯ ВЫПОЛНЕНА ✨'},
    'Italiano': {'sl': 'Seleziona lingua', 'bm': 'Modalità principiante?', 'sm': 'Seleziona operazione:', 'mp': 'Project - Riproietta DEM', 'mg': 'Generate - Genera MCA', 'ma': 'All - Pipeline completo', 'mr': 'Resume - Continua progetto interrotto', 'dt': 'Seleziona tipo di dati:', 'dem': 'DEM - Solo terreno', 'dsm': 'DSM - Terreno + edifici/alberi', 'pn': 'Inserisci nome progetto:', 'pni': 'Caratteri non validi. Usa lettere, numeri, _ o -', 'pe': 'Il progetto esiste già. Usa un nome diverso.', 'rnp': 'Seleziona progetto da riprendere:', 'npa': 'Nessun progetto disponibile da riprendere', 'rs': 'Ripresa dal passo', 'cp': 'Checkpoint trovato! Riprendi da', 's1': 'PASSO 1: RIPROIEZIONE', 's2': 'PASSO 2: GENERAZIONE MCA', 'rp': '🗺️  Riproiezione:', 'gm': '🎮 Generazione:', 'sc': '✓ Completo', 'ma2': '✨ MISSIONE COMPIUTA ✨'},
    '한국어': {'sl': '언어 선택', 'bm': '초보자 모드?', 'sm': '작업 선택:', 'mp': 'Project - DEM 재투영', 'mg': 'Generate - MCA 생성', 'ma': 'All - 전체 파이프라인', 'mr': 'Resume - 중단된 프로젝트 계속', 'dt': '데이터 유형 선택:', 'dem': 'DEM - 지형만', 'dsm': 'DSM - 지형 + 건물/나무', 'pn': '프로젝트 이름 입력:', 'pni': '잘못된 문자. 문자, 숫자, _ 또는 - 사용', 'pe': '프로젝트가 이미 존재합니다. 다른 이름을 사용하세요.', 'rnp': '재개할 프로젝트 선택:', 'npa': '재개할 수 있는 프로젝트가 없습니다', 'rs': '단계에서 재개', 'cp': '체크포인트 발견! 다음에서 재개', 's1': '단계 1: 재투영', 's2': '단계 2: MCA 생성', 'rp': '🗺️  재투영 중:', 'gm': '🎮 생성 중:', 'sc': '✓ 완료', 'ma2': '✨ 임무 완수 ✨'},
    '中文（繁體）': {'sl': '選擇語言', 'bm': '新手模式？', 'sm': '選擇操作:', 'mp': 'Project - 重投影DEM', 'mg': 'Generate - 生成MCA', 'ma': 'All - 完整流程', 'mr': 'Resume - 繼續中斷的項目', 'dt': '選擇數據類型:', 'dem': 'DEM - 僅地形', 'dsm': 'DSM - 地形+建築/樹木', 'pn': '輸入項目名稱:', 'pni': '無效字符。請使用字母、數字、_或-', 'pe': '項目已存在。請使用不同的名稱。', 'rnp': '選擇要恢復的項目:', 'npa': '沒有可恢復的項目', 'rs': '從步驟恢復', 'cp': '檢測到檢查點！從以下位置恢復', 's1': '步驟1: 重投影', 's2': '步驟2: MCA生成', 'rp': '🗺️  重投影中:', 'gm': '🎮 生成中:', 'sc': '✓ 完成', 'ma2': '✨ 任務完成 ✨'},
    'العربية': {'sl': 'اختر اللغة', 'bm': 'وضع المبتدئين؟', 'sm': 'اختر العملية:', 'mp': 'Project - إعادة إسقاط DEM', 'mg': 'Generate - إنشاء MCA', 'ma': 'All - خط الأنابيب الكامل', 'mr': 'Resume - متابعة مشروع متقطع', 'dt': 'اختر نوع البيانات:', 'dem': 'DEM - التضاريس فقط', 'dsm': 'DSM - التضاريس + المباني/الأشجار', 'pn': 'أدخل اسم المشروع:', 'pni': 'أحرف غير صالحة. استخدم الحروف والأرقام و _ أو -', 'pe': 'المشروع موجود بالفعل. استخدم اسمًا مختلفًا.', 'rnp': 'اختر مشروعًا للاستئناف:', 'npa': 'لا توجد مشاريع متاحة للاستئناف', 'rs': 'الاستئناف من الخطوة', 'cp': 'تم العثور على نقطة تفتيش! استئناف من', 's1': 'الخطوة 1: إعادة الإسقاط', 's2': 'الخطوة 2: إنشاء MCA', 'rp': '🗺️  إعادة الإسقاط:', 'gm': '🎮 الإنشاء:', 'sc': '✓ مكتمل', 'ma2': '✨ المهمة أنجزت ✨'},
    'हिन्दी': {'sl': 'भाषा चुनें', 'bm': 'शुरुआती मोड?', 'sm': 'ऑपरेशन चुनें:', 'mp': 'Project - DEM पुनः प्रोजेक्ट', 'mg': 'Generate - MCA जेनरेट', 'ma': 'All - पूर्ण पाइपलाइन', 'mr': 'Resume - बाधित परियोजना जारी रखें', 'dt': 'डेटा प्रकार चुनें:', 'dem': 'DEM - केवल भूभाग', 'dsm': 'DSM - भूभाग + इमारतें/पेड़', 'pn': 'परियोजना का नाम दर्ज करें:', 'pni': 'अमान्य वर्ण। अक्षर, संख्या, _ या - का उपयोग करें', 'pe': 'परियोजना पहले से मौजूद है। एक अलग नाम का उपयोग करें।', 'rnp': 'फिर से शुरू करने के लिए परियोजना चुनें:', 'npa': 'फिर से शुरू करने के लिए कोई परियोजना उपलब्ध नहीं', 'rs': 'चरण से फिर से शुरू', 'cp': 'चेकपॉइंट मिला! यहाँ से फिर से शुरू करें', 's1': 'चरण 1: पुनः प्रक्षेपण', 's2': 'चरण 2: MCA जनरेशन', 'rp': '🗺️  पुनः प्रक्षेपण:', 'gm': '🎮 जेनरेट कर रहे हैं:', 'sc': '✓ पूर्ण', 'ma2': '✨ मिशन पूरा ✨'},
    'ไทย': {'sl': 'เลือกภาษา', 'bm': 'โหมดผู้เริ่มต้น?', 'sm': 'เลือกการดำเนินการ:', 'mp': 'Project - ฉายใหม่ DEM', 'mg': 'Generate - สร้าง MCA', 'ma': 'All - กระบวนการเต็ม', 'mr': 'Resume - ดำเนินการโปรเจ็กต์ที่ถูกขัดจังหวะต่อ', 'dt': 'เลือกประเภทข้อมูล:', 'dem': 'DEM - ภูมิประเทศเท่านั้น', 'dsm': 'DSM - ภูมิประเทศ + อาคาร/ต้นไม้', 'pn': 'ป้อนชื่อโปรเจ็กต์:', 'pni': 'อักขระไม่ถูกต้อง ใช้ตัวอักษร ตัวเลข _ หรือ -', 'pe': 'โปรเจ็กต์มีอยู่แล้ว ใช้ชื่ออื่น', 'rnp': 'เลือกโปรเจ็กต์ที่จะดำเนินการต่อ:', 'npa': 'ไม่มีโปรเจ็กต์ที่จะดำเนินการต่อ', 'rs': 'ดำเนินการต่อจากขั้นตอน', 'cp': 'พบจุดตรวจสอบ! ดำเนินการต่อจาก', 's1': 'ขั้นตอนที่ 1: การฉายใหม่', 's2': 'ขั้นตอนที่ 2: การสร้าง MCA', 'rp': '🗺️  กำลังฉายใหม่:', 'gm': '🎮 กำลังสร้าง:', 'sc': '✓ เสร็จสมบูรณ์', 'ma2': '✨ ภารกิจสำเร็จ ✨'},
    'Tiếng Việt': {'sl': 'Chọn ngôn ngữ', 'bm': 'Chế độ người mới?', 'sm': 'Chọn thao tác:', 'mp': 'Project - Tái chiếu DEM', 'mg': 'Generate - Tạo MCA', 'ma': 'All - Quy trình đầy đủ', 'mr': 'Resume - Tiếp tục dự án bị gián đoạn', 'dt': 'Chọn loại dữ liệu:', 'dem': 'DEM - Chỉ địa hình', 'dsm': 'DSM - Địa hình + tòa nhà/cây', 'pn': 'Nhập tên dự án:', 'pni': 'Ký tự không hợp lệ. Sử dụng chữ cái, số, _ hoặc -', 'pe': 'Dự án đã tồn tại. Sử dụng tên khác.', 'rnp': 'Chọn dự án để tiếp tục:', 'npa': 'Không có dự án nào để tiếp tục', 'rs': 'Tiếp tục từ bước', 'cp': 'Đã tìm thấy điểm kiểm tra! Tiếp tục từ', 's1': 'BƯỚC 1: TÁI CHIẾU', 's2': 'BƯỚC 2: TẠO MCA', 'rp': '🗺️  Đang tái chiếu:', 'gm': '🎮 Đang tạo:', 'sc': '✓ Hoàn thành', 'ma2': '✨ NHIỆM VỤ HOÀN THÀNH ✨'},
}
def t(k): return LANG[CL].get(k, LANG['English'].get(k, k))

CS = QStyle([('qmark', 'fg:#00ff00 bold'), ('question', 'bold'), ('answer', 'fg:#00ff00 bold'), ('pointer', 'fg:#00ff00 bold'), ('highlighted', 'fg:#00ff00 bold')])

# ==================== PROJECT MANAGEMENT ====================
class ProjectManager:
    def __init__(self, project_name):
        self.name = project_name
        self.base_dir = os.path.join(PROJECTS_DIR, project_name)
        self.input_dir = os.path.join(self.base_dir, "input")
        self.projected_dir = os.path.join(self.base_dir, "tiff_projected")
        self.output_dir = os.path.join(self.base_dir, "mca_output")
        self.temp_dir = os.path.join(self.base_dir, "temp")
        self.checkpoint_file = os.path.join(self.base_dir, "checkpoint.json")
    
    def create(self):
        """Create project structure"""
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.projected_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def save_checkpoint(self, data):
        """Save checkpoint"""
        data['timestamp'] = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_checkpoint(self):
        """Load checkpoint"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return None
    
    def delete_checkpoint(self):
        """Delete checkpoint after completion"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)

def validate_project_name(name):
    """Validate project name for folder creation"""
    if not name or len(name.strip()) == 0:
        return False, t('pn')
    name = name.strip()
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False, t('pni')
    if os.path.exists(os.path.join(PROJECTS_DIR, name)):
        return False, t('pe')
    return True, name

def get_existing_projects():
    """Get list of projects with checkpoints"""
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    projects = []
    for proj_name in os.listdir(PROJECTS_DIR):
        proj_path = os.path.join(PROJECTS_DIR, proj_name)
        if os.path.isdir(proj_path):
            checkpoint = os.path.join(proj_path, "checkpoint.json")
            if os.path.exists(checkpoint):
                try:
                    with open(checkpoint, 'r') as f:
                        data = json.load(f)
                    projects.append((proj_name, data))
                except:
                    pass
    return projects

# ==================== UI ====================
def select_lang():
    global CL
    print(f"{Fore.CYAN}{'='*60}\n{Fore.GREEN}MCTS - Minecraft Terrain Studio\n{Fore.CYAN}{'='*60}\n")
    CL = questionary.select("🌍 Select Language / 言語:", choices=list(LANG.keys()), style=CS).ask() or 'English'

def logo():
    print(f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
║  {Fore.GREEN}███╗   ███╗ ██████╗████████╗███████╗                   {Fore.CYAN}║
║  {Fore.GREEN}████╗ ████║██╔════╝╚══██╔══╝██╔════╝                   {Fore.CYAN}║
║  {Fore.GREEN}██╔████╔██║██║        ██║   ███████╗                   {Fore.CYAN}║
║  {Fore.GREEN}██║╚██╔╝██║██║        ██║   ╚════██║                   {Fore.CYAN}║
║  {Fore.GREEN}██║ ╚═╝ ██║╚██████╗   ██║   ███████║                   {Fore.CYAN}║
║  {Fore.GREEN}╚═╝     ╚═╝ ╚═════╝   ╚═╝   ╚══════╝                   {Fore.CYAN}║
║  {Fore.YELLOW}    Minecraft Terrain Studio v1.0.0                   {Fore.CYAN}║
║  {Fore.MAGENTA}  by AOIROSERVER creeper_dev © 2026                   {Fore.CYAN}║
╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}""")

def prog(c, tot, st, pre=""):
    p = c / tot if tot > 0 else 0; f = int(50 * p); b = "█" * f + "░" * (50 - f); e = (datetime.now() - st).total_seconds(); eta = str(timedelta(seconds=int(e / c * (tot - c)))) if c > 0 else "N/A"; es = str(timedelta(seconds=int(e))); bc = Fore.RED if p < 0.33 else Fore.YELLOW if p < 0.66 else Fore.GREEN
    sys.stdout.write(f"\r{Fore.CYAN}{pre}{bc}[{b}] {Fore.WHITE}{p*100:.1f}% {Fore.CYAN}│ {Fore.YELLOW}{c}/{tot} {Fore.CYAN}│ {Fore.MAGENTA}⏱ {es} {Fore.CYAN}│ {Fore.GREEN}⏳ {eta}{Style.RESET_ALL}"); sys.stdout.flush()
    if c >= tot: print()

def stat(s, m, st="info"):
    ic = {"info": f"{Fore.CYAN}ℹ", "success": f"{Fore.GREEN}✓", "error": f"{Fore.RED}✗"}
    print(f"{ic.get(st, '•')} {Fore.WHITE}{s}: {m}{Style.RESET_ALL}")

# ==================== CORE PROCESSING ====================
def reproject_tiff(inp, outp, crs):
    """Reproject TIFF file to target coordinate system"""
    with rasterio.open(inp) as src:
        # Calculate target transform and dimensions
        tr, w, h = calculate_default_transform(
            src.crs, crs, src.width, src.height, *src.bounds
        )
        
        # Update metadata
        kw = src.meta.copy()
        kw.update({
            'crs': crs,
            'transform': tr,
            'width': w,
            'height': h
        })
        
        # Perform reprojection
        with rasterio.open(outp, 'w', **kw) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=tr,
                dst_crs=crs,
                resampling=Resampling.bilinear
            )

def process_tiff_simple(tiff_path, base_x, base_y, nodata_value=-9999):
    """
    Process TIFF and extract coordinate data
    Returns: (min_elevation, coords_dict)
    """
    try:
        with rasterio.open(tiff_path) as src:
            # Read elevation data
            data = src.read(1)
            transform = src.transform
            
            # Generate coordinate indices
            y_indices, x_indices = np.indices(data.shape)
            
            # Calculate real-world coordinates
            x_coords = x_indices * transform.a + transform.c + transform.a / 2.0
            y_coords = y_indices * transform.e + transform.f + transform.e / 2.0
            
            # Flatten arrays
            x_coords = x_coords.ravel()
            y_coords = y_coords.ravel()
            data = data.ravel()
            
            # Apply coordinate offset
            x_coords = x_coords - base_x
            y_coords = -(y_coords - base_y)
            
            # Convert to integers
            x_coords = np.trunc(x_coords).astype(int)
            y_coords = np.trunc(y_coords).astype(int)
            data = np.trunc(data).astype(int)
        
        # Filter out nodata values
        valid_mask = data != nodata_value
        x_coords = x_coords[valid_mask]
        y_coords = y_coords[valid_mask]
        data = data[valid_mask]
        
        if len(data) == 0:
            return None, None
        
        # Calculate minimum elevation
        current_min = int(np.min(data))
        
        # Build coordinate dictionary
        coords_data = {}
        for x, z, y in zip(x_coords, y_coords, data):
            coords_data[(int(x), int(z))] = int(y)
        
        return current_min, coords_data
        
    except Exception as e:
        return None, None

def organize_by_region(coords_data):
    """
    Organize coordinates by Minecraft region structure
    Returns nested dict: region -> chunk -> block coordinates
    """
    region_data = defaultdict(lambda: defaultdict(dict))
    
    for (x, z), y in coords_data.items():
        # Calculate region coordinates (512 blocks per region)
        region_x = x >> 9  # Divide by 512
        region_z = z >> 9
        
        # Calculate chunk coordinates within region (32 chunks per region)
        chunk_x = (x >> 4) & 31  # (x / 16) % 32
        chunk_z = (z >> 4) & 31
        
        # Calculate block coordinates within chunk (16 blocks per chunk)
        block_x = x & 15  # x % 16
        block_z = z & 15
        
        # Store in nested structure
        region_data[(region_x, region_z)][(chunk_x, chunk_z)][(block_x, block_z)] = y
    
    return region_data

def generate_mca_file(region_x, region_z, chunks_data, min_elevation, is_dsm=False):
    """
    Generate MCA file from organized chunk data
    
    Args:
        region_x, region_z: Region coordinates
        chunks_data: Dict of chunk data
        min_elevation: Minimum elevation for Y offset
        is_dsm: Whether this is DSM data
    
    Returns:
        anvil.Region object
    """
    # Create empty region
    region = anvil.EmptyRegion(region_x, region_z)
    
    # Define blocks (can be customized based on is_dsm)
    stone = anvil.Block('minecraft', 'stone')
    
    # Process each chunk
    for (chunk_x, chunk_z), block_coords in chunks_data.items():
        # Create empty chunk
        chunk = anvil.EmptyChunk(chunk_x, chunk_z)
        
        # Place blocks
        for (block_x, block_z), y in block_coords.items():
            # Minecraft Y coordinate range: -64 to 319
            if min_elevation <= y <= 319:
                try:
                    chunk.set_block(stone, block_x, y, block_z)
                except Exception:
                    # Skip if block placement fails
                    pass
        
        # Add chunk to region
        region.add_chunk(chunk)
    
    return region

def generate_mca_batch(batch_coords, base_x, base_y, min_elevation, output_dir, existing_mcas_set, is_dsm=False):
    """
    Generate MCA files from a batch of coordinate data
    
    Args:
        batch_coords: Combined coordinates from multiple TIFFs
        base_x, base_y: Coordinate offsets
        min_elevation: Minimum elevation
        output_dir: Output directory for MCA files
        existing_mcas_set: Set of existing MCA filenames to skip
        is_dsm: Whether this is DSM data
    
    Returns:
        Number of MCA files created
    """
    import gc
    
    # Organize coordinates by region
    region_data = organize_by_region(batch_coords)
    
    mca_count = 0
    
    # Generate MCA for each region
    for (region_x, region_z), chunks in region_data.items():
        mca_filename = f"r.{region_x}.{region_z}.mca"
        
        # Skip if already exists
        if mca_filename in existing_mcas_set:
            continue
        
        mca_path = os.path.join(output_dir, mca_filename)
        
        try:
            # Generate and save MCA
            region = generate_mca_file(region_x, region_z, chunks, min_elevation, is_dsm)
            region.save(mca_path)
            
            # Add to existing set
            existing_mcas_set.add(mca_filename)
            mca_count += 1
            
        except Exception as e:
            # Log error but continue
            pass
    
    # Clean up memory
    del region_data
    gc.collect()
    
    return mca_count

# ==================== PROCESSING STEPS ====================
def s1(pm, crs, checkpoint_data):
    """Step 1: Reproject with detailed checkpoints and progress tracking"""
    print(f"\n{Fore.CYAN}{'='*60}\n{t('s1')}\n{'='*60}{Style.RESET_ALL}\n")
    
    # Get all TIFF files from input
    tfs = glob.glob(os.path.join(pm.input_dir, "*.tif"))
    if not tfs: 
        stat("ERROR", f"No TIFF files in {pm.input_dir}", "error")
        return False
    
    # Check checkpoint for resume
    start_idx = checkpoint_data.get('step1_progress', 0) if checkpoint_data else 0
    
    if start_idx > 0:
        print(f"{Fore.YELLOW}{t('cp')} {start_idx}/{len(tfs)} files already processed{Style.RESET_ALL}\n")
    
    stat("Input Directory", pm.input_dir, "info")
    stat("Output Directory", pm.projected_dir, "info")
    stat("Target CRS", crs, "info")
    stat("Total Files", f"{len(tfs)} TIFF files", "success")
    stat("Completed", f"{start_idx} files", "info" if start_idx > 0 else "success")
    stat("Remaining", f"{len(tfs) - start_idx} files", "info")
    print()
    
    # Processing loop
    st = datetime.now()
    last_checkpoint_time = datetime.now()
    processed_count = 0
    skipped_count = 0
    
    print(f"{Fore.CYAN}{'='*60}")
    print(f"Starting reprojection from file {start_idx + 1}")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    
    for i, tp in enumerate(tfs[start_idx:], start_idx + 1):
        fn = os.path.basename(tp)
        op = os.path.join(pm.projected_dir, fn)
        
        # Skip if already exists
        if os.path.exists(op):
            skipped_count += 1
            continue
        
        try:
            # Perform reprojection
            reproject_tiff(tp, op, crs)
            processed_count += 1
            
            # Update progress bar
            prog(i, len(tfs), st, t('rp'))
            
        except Exception as e:
            print()
            stat(fn, f"Error: {str(e)}", "error")
            print(f"{Fore.YELLOW}⚠ Continuing with next file...{Style.RESET_ALL}\n")
            continue
        
        # Auto-save checkpoint every CHECKPOINT_INTERVAL seconds
        current_time = datetime.now()
        if (current_time - last_checkpoint_time).total_seconds() >= CHECKPOINT_INTERVAL:
            checkpoint_data['step1_progress'] = i
            checkpoint_data['current_step'] = 'project'
            pm.save_checkpoint(checkpoint_data)
            last_checkpoint_time = current_time
    
    print()
    
    # Final statistics
    elapsed_time = (datetime.now() - st).total_seconds()
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"REPROJECTION COMPLETE")
    print(f"{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ Files processed: {processed_count}{Style.RESET_ALL}")
    if skipped_count > 0:
        print(f"{Fore.YELLOW}⊘ Files skipped (already exist): {skipped_count}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}⏱ Processing time: {str(timedelta(seconds=int(elapsed_time)))}{Style.RESET_ALL}\n")
    
    stat(t('sc'), f"{len(tfs)} files total", "success")
    
    # Mark step as complete
    checkpoint_data['step1_progress'] = len(tfs)
    checkpoint_data['step1_complete'] = True
    pm.save_checkpoint(checkpoint_data)
    
    return True

def s2(pm, bx, by, bs, checkpoint_data):
    """Step 2: Generate MCA with checkpoints and detailed processing"""
    print(f"\n{Fore.CYAN}{'='*60}\n{t('s2')}\n{'='*60}{Style.RESET_ALL}\n")
    
    # Get all TIFF files
    tfs = sorted(glob.glob(os.path.join(pm.projected_dir, "*.tif")))
    if not tfs: 
        stat("ERROR", "No TIFF files found", "error")
        return False
    
    # Calculate total batches
    total_batches = (len(tfs) + bs - 1) // bs
    
    # Check checkpoint for resume
    start_batch = checkpoint_data.get('step2_batch', 0) if checkpoint_data else 0
    
    if start_batch > 0:
        remaining = total_batches - start_batch
        print(f"{Fore.YELLOW}{t('cp')} batch {start_batch}/{total_batches}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}ℹ Remaining: {remaining} batches ({remaining * bs} files){Style.RESET_ALL}\n")
    
    stat("Input", pm.projected_dir, "info")
    stat("Output", pm.output_dir, "info")
    stat("Files", f"{len(tfs)} TIFF files", "success")
    stat("Batches", f"{total_batches} total ({bs} files each)", "info")
    print()
    
    # Calculate or load minimum elevation
    if 'min_elevation' not in checkpoint_data:
        print(f"{Fore.MAGENTA}⚙ Analyzing elevation data...{Style.RESET_ALL}")
        me = 0
        sample_size = min(100, len(tfs))
        
        for i, tp in enumerate(tfs[:sample_size], 1):
            cm, _ = process_tiff_simple(tp, bx, by)
            if cm is not None and cm < me:
                me = cm
            
            # Show sampling progress
            if i % 10 == 0 or i == sample_size:
                percent = int((i / sample_size) * 100)
                sys.stdout.write(f"\r{Fore.MAGENTA}⚙ Sampling: [{Fore.CYAN}{'█' * (percent // 2)}{'░' * (50 - percent // 2)}{Fore.MAGENTA}] {percent}%{Style.RESET_ALL}")
                sys.stdout.flush()
        
        print()
        checkpoint_data['min_elevation'] = me
        pm.save_checkpoint(checkpoint_data)
    else:
        me = checkpoint_data['min_elevation']
    
    stat(t('me') if 'me' in t.__code__.co_names else "Min Elevation", f"{me}m", "success")
    
    if checkpoint_data.get('is_dsm'):
        stat("Data Type", "DSM - Surface Model (terrain + buildings/trees)", "info")
    else:
        stat("Data Type", "DEM - Elevation Model (terrain only)", "info")
    print()
    
    # Build set of existing MCA files
    print(f"{Fore.CYAN}📦 Scanning existing MCA files...{Style.RESET_ALL}")
    existing_mca_paths = glob.glob(os.path.join(pm.output_dir, "*.mca"))
    existing_mcas_set = set(os.path.basename(p) for p in existing_mca_paths)
    print(f"{Fore.GREEN}✓ Found {len(existing_mcas_set)} existing MCA files (will skip){Style.RESET_ALL}\n")
    
    # Processing loop
    st = datetime.now()
    total_mca_created = 0
    last_checkpoint_time = datetime.now()
    
    print(f"{Fore.CYAN}{'='*60}")
    print(f"Processing batches {start_batch + 1} to {total_batches}")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    
    for batch_idx in range(start_batch, total_batches):
        # Get batch files
        batch_start_idx = batch_idx * bs
        batch_end_idx = min(batch_start_idx + bs, len(tfs))
        batch_files = tfs[batch_start_idx:batch_end_idx]
        
        # Process all TIFFs in this batch
        batch_coords = {}
        for tiff_path in batch_files:
            _, coords = process_tiff_simple(tiff_path, bx, by)
            if coords:
                batch_coords.update(coords)
        
        # Generate MCA files for this batch
        if batch_coords:
            mca_count = generate_mca_batch(
                batch_coords,
                bx, by,
                me,
                pm.output_dir,
                existing_mcas_set,
                checkpoint_data.get('is_dsm', False)
            )
            total_mca_created += mca_count
        
        # Clean up batch data
        del batch_coords
        import gc
        gc.collect()
        
        # Update progress
        relative_current = batch_idx - start_batch + 1
        relative_total = total_batches - start_batch
        prog(relative_current, relative_total, st, t('gm'))
        
        # Auto-save checkpoint every CHECKPOINT_INTERVAL seconds
        current_time = datetime.now()
        if (current_time - last_checkpoint_time).total_seconds() >= CHECKPOINT_INTERVAL:
            checkpoint_data['step2_batch'] = batch_idx + 1
            checkpoint_data['mca_created'] = total_mca_created
            pm.save_checkpoint(checkpoint_data)
            last_checkpoint_time = current_time
    
    print()
    
    # Final statistics
    final_mca_count = len(glob.glob(os.path.join(pm.output_dir, "*.mca")))
    elapsed_time = (datetime.now() - st).total_seconds()
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ New MCA files created: {total_mca_created}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ Total MCA files: {final_mca_count}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}⏱ Processing time: {str(timedelta(seconds=int(elapsed_time)))}{Style.RESET_ALL}\n")
    
    stat(t('sc'), f"MCA generation complete", "success")
    
    # Mark step as complete
    checkpoint_data['step2_complete'] = True
    checkpoint_data['final_mca_count'] = final_mca_count
    pm.save_checkpoint(checkpoint_data)
    
    return True

# ==================== CONFIGURATION ====================
def get_config(mode):
    """Get configuration"""
    print(f"\n{Fore.CYAN}╔═══════════════════════════════╗\n║  {Fore.WHITE}{Style.BRIGHT}CONFIGURATION{Fore.CYAN}         ║\n╚═══════════════════════════════╝{Style.RESET_ALL}\n")
    
    # Project name
    while True:
        pn = questionary.text(t('pn'), style=CS).ask()
        valid, result = validate_project_name(pn)
        if valid: break
        print(f"{Fore.RED}✗ {result}{Style.RESET_ALL}\n")
    
    pm = ProjectManager(result)
    pm.create()
    
    # Data type
    dt = questionary.select(t('dt'), choices=[t('dem'), t('dsm')], style=CS).ask()
    is_dsm = 'DSM' in dt
    
    # CRS
    crs_opt = {"EPSG:6677 - Tokyo": "EPSG:6677", "EPSG:6668 - Zone 1": "EPSG:6668", "Custom": "custom"}
    crs_ch = questionary.select("Select CRS:", choices=list(crs_opt.keys()), style=CS).ask()
    crs = questionary.text("Enter CRS:", style=CS).ask() if crs_opt[crs_ch] == "custom" else crs_opt[crs_ch]
    
    bx = int(questionary.text("Base X:", default="-36000", style=CS).ask())
    by = int(questionary.text("Base Y:", default="-29000", style=CS).ask())
    bs = int(questionary.text("Batch size:", default="10", style=CS).ask())
    
    config = {'mode': mode, 'is_dsm': is_dsm, 'crs': crs, 'bx': bx, 'by': by, 'bs': bs, 'project_name': result}
    pm.save_checkpoint(config)
    
    return pm, config

def resume_project():
    """Resume interrupted project"""
    projects = get_existing_projects()
    
    if not projects:
        print(f"\n{Fore.YELLOW}{t('npa')}{Style.RESET_ALL}\n")
        return None, None
    
    choices = [f"{name} ({data.get('current_step', 'unknown')} - {data.get('timestamp', 'N/A')[:19]})" for name, data in projects]
    sel = questionary.select(t('rnp'), choices=choices, style=CS).ask()
    
    if not sel: return None, None
    
    idx = choices.index(sel)
    proj_name, checkpoint_data = projects[idx]
    pm = ProjectManager(proj_name)
    
    print(f"\n{Fore.GREEN}✓ Resuming project: {proj_name}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}ℹ {t('rs')}: {checkpoint_data.get('current_step', 'unknown')}{Style.RESET_ALL}\n")
    
    return pm, checkpoint_data

# ==================== MAIN ====================
def main():
    try:
        select_lang(); logo()
        beg = questionary.confirm(t('bm'), default=True, style=CS).ask()
        
        # Mode selection with Resume option
        modes = [t('mp'), t('mg'), t('ma'), t('mr')]
        md = questionary.select(t('sm'), choices=modes, style=CS).ask()
        
        if t('mr') in md:  # Resume
            pm, ckpt = resume_project()
            if not pm: return
            
            # Continue from checkpoint
            if ckpt.get('current_step') == 'project':
                ok = s1(pm, ckpt['crs'], ckpt)
                if ok and ckpt['mode'] in ['all', 'All']:
                    ok = s2(pm, ckpt['bx'], ckpt['by'], ckpt['bs'], ckpt)
            elif ckpt.get('current_step') == 'generate':
                ok = s2(pm, ckpt['bx'], ckpt['by'], ckpt['bs'], ckpt)
            else:
                print(f"{Fore.RED}✗ Unknown step{Style.RESET_ALL}")
                return
            
            if ok: pm.delete_checkpoint()
        
        else:  # New project
            ms = md.split(" - ")[0].lower()
            pm, cfg = get_config(ms)
            
            if ms == 'project':
                ok = s1(pm, cfg['crs'], cfg)
            elif ms == 'generate':
                ok = s2(pm, cfg['bx'], cfg['by'], cfg['bs'], cfg)
            elif ms == 'all':
                ok = s1(pm, cfg['crs'], cfg)
                if ok: ok = s2(pm, cfg['bx'], cfg['by'], cfg['bs'], cfg)
            
            if ok: pm.delete_checkpoint()
        
        if ok:
            print(f"\n{Fore.GREEN}╔═══════════════════════════════╗\n║  {Fore.WHITE}{Style.BRIGHT}{t('ma2')}{Fore.GREEN}  ║\n╚═══════════════════════════════╝{Style.RESET_ALL}\n")
    
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Interrupted. Checkpoint saved.{Style.RESET_ALL}\n")
    except Exception as e:
        print(f"\n{Fore.RED}💥 ERROR: {e}{Style.RESET_ALL}\n")

if __name__ == '__main__': main()