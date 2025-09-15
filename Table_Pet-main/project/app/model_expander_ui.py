# app/model_expander_ui.py
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QLineEdit, QPushButton, QListWidget, QPushButton, QLineEdit, QMessageBox, QComboBox, QFileDialog
)

from .llm_api import run_inference
from model_expander.hf_search import search_models_simple, search_models_with_retry
from model_expander.model_loader import load_model, ensure_local_copy, register_transformers, load_model_by_task
from model_expander.ollama_function import classify_prompt, translate_to_english
from model_expander.expander_registry import list_installed, models_dir, register_model, get_adapter, get_modality

class SearchWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, predicted, en):
        super().__init__()
        self.predicted = predicted
        self.en = en

    def run(self):
        try:
            results = search_models_with_retry(
                self.predicted, self.en, limit=10, max_retries=10,
                on_progress=lambda a, t: self.progress.emit(a, t)
            )
            self.finished.emit(results)
        except Exception as e:
            self.failed.emit(str(e))

class ModelExpanderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("擴充/切換模型")
        self.resize(820, 600)
        self._backend = "openrouter"
        self._payload = None

        layout = QVBoxLayout()

        # === 搜尋列 ===
        top = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("輸入任務描述（例如：小說生成 / 情感分析）")
        self.search_btn = QPushButton("搜尋")
        self.search_btn.clicked.connect(self._on_search)
        top.addWidget(self.task_input)
        top.addWidget(self.search_btn)
        layout.addLayout(top)

        hint = QLabel("說明：此視窗只用來『下載/登記擴充模型』，不會影響與桌寵對話所用的主模型。")
        layout.addWidget(hint)

        # 狀態列
        self.status = QLabel("")
        layout.addWidget(self.status)

        # === 上半：搜尋結果 ===
        layout.addWidget(QLabel("搜尋結果（依下載數排序）："))
        self.result_list = QListWidget()
        layout.addWidget(self.result_list)

        self.apply_btn = QPushButton("套用所選模型（上方搜尋結果）")
        self.apply_btn.clicked.connect(self._on_apply_from_search)
        layout.addWidget(self.apply_btn)

        self.add_ollama_btn = QPushButton("➕ 登記 Ollama 模型")
        self.add_ollama_btn.clicked.connect(self._on_add_ollama)
        layout.addWidget(self.add_ollama_btn)

        self.installed_title = QLabel("使用擴充的模型（本工具下載/登記）")
        layout.addWidget(self.installed_title)

        self.installed_list = QListWidget()
        layout.addWidget(self.installed_list)

        row = QHBoxLayout()
        self.delete_installed_btn = QPushButton("🗑 刪除所選")
        self.delete_installed_btn.clicked.connect(self._delete_installed)
        row.addWidget(self.delete_installed_btn)
        self.refresh_installed_btn = QPushButton("重新整理")
        self.refresh_installed_btn.clicked.connect(self._refresh_installed)
        self.use_installed_btn = QPushButton("使用所選")
        self.use_installed_btn.clicked.connect(self._use_installed)
        self.open_folder_btn = QPushButton("開啟資料夾")
        self.open_folder_btn.clicked.connect(self._open_installed_folder)
        row.addWidget(self.refresh_installed_btn)
        row.addWidget(self.use_installed_btn)
        row.addWidget(self.open_folder_btn)
        row.addStretch()
        layout.addLayout(row)

        self._refresh_installed()  # 啟動先載一次

        self.setLayout(layout)

        self._models = []
        self._refresh_installed()  # 啟動時就載一次

    def _on_search(self):
        text = self.task_input.text().strip()
        if not text:
            QMessageBox.warning(self, "提示", "請先輸入任務描述")
            return
        predicted = classify_prompt(text)
        en = translate_to_english(text)

        self.search_btn.setEnabled(False)
        self.status.setText("開始搜尋…")

        self.thread = QThread(self)
        self.worker = SearchWorker(predicted, en)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(lambda a,t: self.status.setText(f"[ 正在嘗試搜尋...（第 {a}/{t} 次）]"))
        self.worker.finished.connect(self._on_search_done)
        self.worker.failed.connect(self._on_search_failed)
        # 清理
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.failed.connect(self.thread.quit)
        self.worker.failed.connect(self.worker.deleteLater)

        self.thread.start()

    def _on_search_done(self, models):
        self.search_btn.setEnabled(True)
        self.result_list.clear()
        self._models = models or []
        if not self._models:
            self.status.setText("查無結果")
            QMessageBox.information(self, "結果", "沒有找到模型，請換個描述再試")
            return
        self.status.setText(f"[ 找到 {len(self._models)} 筆結果 ]")
        for m in self._models:
            self.result_list.addItem(f"{m['id']}  |  {m.get('size_mb','N/A')}  |  👍{m.get('likes','?')}  ⬇️{m.get('downloads','?')}")

    def _on_search_failed(self, msg):
        self.search_btn.setEnabled(True)
        self.status.setText("搜尋失敗")
        QMessageBox.critical(self, "錯誤", msg)

    def _on_apply_from_search(self):
        row = self.result_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "請先在『搜尋結果』選一個模型")
            return

        model_id = self._models[row]['id']

        if not isinstance(model_id, str):  # ✅ 防呆
            QMessageBox.critical(self, "錯誤", f"無效的模型 ID：{model_id}")
            return

        # 1) 嘗試載入（驗證可用）
        model, tok = load_model(model_id)
        if model is None:
            QMessageBox.critical(self, "失敗", "載入失敗，請換一個模型")
            return

        # 2) 下載到本地資料夾（供多模態使用）
        try:
            local_dir = ensure_local_copy(model_id)
        except Exception as e:
            local_dir = ""
            print(f"ensure_local_copy 失敗：{e}")

        # 3) 寫入 registry（記錄為 transformers 類型）
        task = self._models[row].get("task") or ""
        register_transformers(model_id, task, str(local_dir))

        QMessageBox.information(self, "完成", f"已下載並登記：{model_id}\n（多模態工具可使用）")

    def _on_add_ollama(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "登記 Ollama 模型", "請輸入本地 Ollama 模型名稱（例如：qwen2-vl:latest）")
        if not ok or not name.strip():
            return
        # 任務可以先留空，或讓使用者自行輸入；也可之後在多模態窗指定任務
        register_model(repo_id=name.strip(), backend="ollama", task="", local_path=f"ollama:{name.strip()}", notes="")
        QMessageBox.information(self, "完成", f"已登記 Ollama 模型：{name.strip()}")
        self._refresh_installed()

    def get_selection(self):
        return self._backend, self._payload

    def _refresh_installed(self):
        self.installed_list.clear()
        items = list_installed()
        if not items:
            self.installed_list.addItem("（尚無安裝/登記的模型）")
            self.installed_list.setEnabled(False)
            return
        self.installed_list.setEnabled(True)
        for it in items:
            backend = it.get("backend", "?")
            repo = it.get("repo_id", "?")
            task = it.get("task", "")
            path = it.get("local_path", "")
            self.installed_list.addItem(f"[{backend}] {repo} | task={task} | {path}")

    # 3) 下方清單：使用所選
    def _use_installed(self):
        row = self.installed_list.currentRow()
        items = list_installed()
        if row < 0 or not items or row >= len(items):
            QMessageBox.information(self, "提示", "請先選擇一個已安裝的模型")
            return
        it = items[row]
        backend = it.get("backend", "transformers")
        repo_id = it.get("repo_id", "")
        if backend == "openrouter":
            self._backend = "openrouter"
            self._payload = None
            self.accept()
            return
        if backend == "ollama":
            self._backend = "ollama"
            self._payload = repo_id  # repo_id 存成 ollama 的模型名
            self.accept()
            return
        # transformers
        model, tok = load_model(repo_id)
        if model is None:
            QMessageBox.critical(self, "失敗", "載入失敗（可能不支援或檔案缺失）")
            return
        self._backend = "transformers"
        self._payload = (model, tok)
        self.accept()

    # 4) 下方清單：開啟資料夾
    def _open_installed_folder(self):
        p = str(models_dir())  # project/expanded_models
        # Windows 最省事：
        import os, platform, subprocess
        if platform.system() == "Windows":
            os.startfile(p)  # type: ignore
        elif platform.system() == "Darwin":
            subprocess.run(["open", p])
        else:
            subprocess.run(["xdg-open", p])

    def _delete_installed(self):
        from pathlib import Path
        import shutil, os

        row = self.installed_list.currentRow()
        items = list_installed()
        if row < 0 or not items or row >= len(items):
            QMessageBox.information(self, "提示", "請先選擇一個已安裝的模型")
            return

        it = items[row]
        backend = it.get("backend", "")
        repo_id = it.get("repo_id", "")
        local_path = it.get("local_path", "")
        if not repo_id or not backend:
            QMessageBox.warning(self, "提示", "選取資料不完整，無法刪除")
            return

        # 二次確認
        if QMessageBox.question(
            self, "確認刪除",
            f"確定要刪除這個擴充模型？\n\n[{backend}] {repo_id}\n\n"
            + ("※ 將同時刪除本機資料夾：\n" + local_path if (backend=="transformers" and local_path) else "（僅刪除註冊項目）"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return

        # 1) 先從 registry.json 移除
        from model_expander.expander_registry import remove_model, models_dir
        removed = remove_model(repo_id, backend)  # True/False
        # 2) 若是 transformers，嘗試刪除本地資料夾（限制在 expanded_models/ 之下）
        if backend == "transformers" and local_path:
            try:
                root = Path(models_dir()).resolve()        # app/expanded_models
                target = Path(local_path).resolve()
                # 保護：只允許刪 root 之下的資料夾，避免誤刪
                if os.path.commonpath([str(root), str(target)]) == str(root) and target.exists():
                    shutil.rmtree(target, ignore_errors=True)
            except Exception as e:
                print(f"⚠️ 刪除本地資料夾失敗：{e}")

        # 更新 UI
        self._refresh_installed()
        if removed:
            QMessageBox.information(self, "完成", f"已刪除：[{backend}] {repo_id}")
        else:
            QMessageBox.warning(self, "提示", "清單更新失敗，請稍後重試")


class MultiModalWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("多模態擴充工作窗")
        self.resize(900, 600)

        self.setWindowFlag(Qt.Window, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_QuitOnClose, False)

        # === 左右分欄 ===
        root = QtWidgets.QHBoxLayout(self)
        splitter = QtWidgets.QSplitter(self)
        splitter.setOrientation(Qt.Horizontal)
        root.addWidget(splitter)

        # 左欄：任務 + 本地模型清單 + 輸入區 + 操作列
        left = QtWidgets.QWidget()
        lyt_left = QtWidgets.QVBoxLayout(left)

        # 任務下拉
        self.taskBox = QtWidgets.QComboBox()
        self.taskBox.addItems([
            "image-to-text",
            "text-to-image",
            "automatic-speech-recognition",
        ])
        self.taskBox.currentIndexChanged.connect(self._on_task_changed)
        lyt_left.addWidget(QtWidgets.QLabel("任務"))
        lyt_left.addWidget(self.taskBox)

        # 本地可用模型清單
        self.localList = QtWidgets.QListWidget()
        lyt_left.addWidget(QtWidgets.QLabel("本地可用模型（已下載/登記）"))
        lyt_left.addWidget(self.localList)

        # 輸入區（依任務切換可見）
        self.textEdit = QtWidgets.QTextEdit()
        self.textEdit.setPlaceholderText("輸入文字（用於 text / text-to-image）")
        self.imageBtn = QtWidgets.QPushButton("選擇圖片")
        self.audioBtn = QtWidgets.QPushButton("選擇音檔")
        self.status = QtWidgets.QLabel()

        # 檔案選擇回呼
        self.image_path, self.audio_path = None, None
        self.imageBtn.clicked.connect(self._pick_image)
        self.audioBtn.clicked.connect(self._pick_audio)

        lyt_left.addWidget(QtWidgets.QLabel("輸入"))
        lyt_left.addWidget(self.textEdit)
        lyt_left.addWidget(self.imageBtn)
        lyt_left.addWidget(self.audioBtn)

        # 操作列：搜尋（雲端）、執行
        row = QtWidgets.QHBoxLayout()
        self.searchBtn = QtWidgets.QPushButton("🔎 搜尋可用模型（雲端）")
        self.runBtn = QtWidgets.QPushButton("▶ 執行")
        self.searchBtn.clicked.connect(self._search_models_for_task)
        self.runBtn.clicked.connect(self._run_infer)
        row.addWidget(self.searchBtn); row.addWidget(self.runBtn); row.addStretch()
        lyt_left.addLayout(row)
        lyt_left.addWidget(self.status)

        # 右欄：輸出結果
        right = QtWidgets.QWidget()
        lyt_right = QtWidgets.QVBoxLayout(right)
        self.resultLabel = QtWidgets.QLabel("輸出結果預覽")
        self.resultLabel.setAlignment(Qt.AlignCenter)
        self.resultLabel.setMinimumHeight(320)
        self.resultLabel.setStyleSheet("border:1px dashed #aaa;")
        lyt_right.addWidget(self.resultLabel)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # 狀態
        self.models = []  # 搜尋結果（雲）
        self._refresh_local_models()
        self._on_task_changed()  # 初始化一次

    # --- UI 事件與輔助 ---
    def _on_task_changed(self):
        """根據任務切換輸入元件可見性，並重載本地模型清單"""
        task = self.taskBox.currentText()
        modality = get_modality(task)  # "text" / "image" / "audio" / "multi"
        # 切換可見
        self.textEdit.setVisible(modality in ("text",) or task == "text-to-image")
        self.imageBtn.setVisible(modality in ("image", "multi"))
        self.audioBtn.setVisible(modality == "audio")
        # 重載本地模型清單
        self._refresh_local_models()

    def _refresh_local_models(self):
        """列出 registry.json 中符合當前 task 的本地模型"""
        task = self.taskBox.currentText()
        items = list_installed()  # [{'repo_id','backend','task','local_path',...}, ...]
        self.localList.clear()
        count = 0
        for it in items:
            # 規則：task 完全相等；若 registry 未標 task（例如 ollama），則也列出以便測試
            if it.get("task") == task or not it.get("task"):
                backend = it.get("backend","?")
                rid = it.get("repo_id","?")
                self.localList.addItem(f"[{backend}] {rid}  | task={it.get('task','')}")
                count += 1
        if count == 0:
            self.localList.addItem("（此任務尚無本地模型，請先於『擴充/切換模型』下載/登記）")

    def _pick_image(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "選擇圖片", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path: self.image_path = path; self.status.setText(f"已選圖片：{path}")

    def _pick_audio(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "選擇音檔", "", "Audio (*.wav *.mp3 *.m4a *.flac)")
        if path: self.audio_path = path; self.status.setText(f"已選音檔：{path}")

    def _search_models_for_task(self):
        """雲端搜尋若需要（可選）；不會改動本地清單"""
        task = self.taskBox.currentText()
        self.models = search_models_simple(task=task, limit=10)
        self.status.setText("雲端搜尋完成" if self.models else "查無雲端結果")

    def _get_selected_local_model(self):
        row = self.localList.currentRow()
        if row < 0: return None
        text = self.localList.item(row).text()
        # 解析 "[backend] repo_id ..." → 回傳 (backend, repo_id)
        try:
            bracket_end = text.index("]")
            backend = text[1:bracket_end].strip()
            rest = text[bracket_end+1:].strip()
            repo_id = rest.split("|",1)[0].strip()
            return backend, repo_id
        except Exception:
            return None

    def _run_infer(self):
        task = self.taskBox.currentText()
        adapter = get_adapter(task)
        if not adapter:
            self.status.setText(f"未支援的任務：{task}")
            return

        # 1) 先看是否選了本地模型
        sel = self._get_selected_local_model()
        model_id = None
        if sel:
            backend, repo_id = sel
            # 對於 transformers：repo_id 直接用；對於 ollama：repo_id 就是模型名（你在登記時這樣存）
            model_id = repo_id

        # 2) 若沒選本地，就 fallback 雲端搜尋結果（保留相容）
        if not model_id and self.models:
            model_id = self.models[0].get("modelId")

        if not model_id:
            self.status.setText("請先選擇本地模型，或執行『雲端搜尋』以使用候選")
            return

        # 3) 載入 & 推論
        try:
            adapter.prepare(model_id, task=task)
            adapter.load(model_id)
        except Exception as e:
            self.status.setText(f"載入失敗：{e}")
            return

        payload = {}
        modality = get_modality(task)
        if modality in ("image","multi") and self.image_path:
            payload["image"] = self.image_path
        if modality == "audio" and self.audio_path:
            payload["audio"] = self.audio_path
        if modality == "text" or task == "text-to-image":
            txt = self.textEdit.toPlainText().strip()
            if txt: payload["text"] = txt
            if task == "text-to-image": payload["prompt"] = txt

        try:
            out = adapter.infer(payload)
        except Exception as e:
            self.status.setText(f"推論失敗：{e}")
            return

        # 右側顯示結果
        if isinstance(out, dict) and "text" in out:
            self.resultLabel.setText(str(out["text"]))
        elif isinstance(out, dict) and "image" in out:
            self.resultLabel.setText(f"已輸出圖片：{out['image']}")
        else:
            self.resultLabel.setText(str(out))

        self.status.setText("完成")