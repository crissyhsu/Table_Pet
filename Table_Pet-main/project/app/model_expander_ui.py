# app/model_expander_ui.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
                             QLineEdit, QPushButton, QListWidget, QMessageBox, QComboBox, QFileDialog)
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from model_expander.hf_search import search_models, search_models_with_retry
from model_expander.model_loader import load_model, ensure_local_copy, register_transformers
from model_expander.ollama_function import classify_prompt, translate_to_english
from model_expander.expander_registry import list_installed, models_dir, register_model

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

        # 後端選擇
        backend_row = QHBoxLayout()
        backend_row.addWidget(QLabel("推論後端："))
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["openrouter", "transformers", "ollama"])
        backend_row.addWidget(self.backend_combo)
        backend_row.addStretch()
        layout.addLayout(backend_row)

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

        self.installed_title = QLabel("使用擴充的模型（本工具下載/登記）")
        layout.addWidget(self.installed_title)

        self.installed_list = QListWidget()
        layout.addWidget(self.installed_list)

        row = QHBoxLayout()
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
        backend = self.backend_combo.currentText()
        if backend == "openrouter":
            self._backend = "openrouter"
            self._payload = None
            self.accept()
            return

        row = self.result_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "請先在上面『搜尋結果』選一個模型")
            return
        model_id = self._models[row]['id']

        if backend == "transformers":
            # 1) 載入（推論用）
            model, tok = load_model(model_id)
            if model is None:
                QMessageBox.critical(self, "失敗", "載入失敗，請換一個模型或改用其他後端")
                return

            # 2) 下載完整檔案到專屬資料夾（供『已安裝清單』用）
            try:
                local_dir = ensure_local_copy(model_id)
            except Exception as e:
                local_dir = ""
                print(f"ensure_local_copy 失敗：{e}")

            # 3) 寫入 registry
            task = self._models[row].get("task") or ""
            register_transformers(model_id, task, local_dir)

            # 4) 回傳給 Main
            self._backend = "transformers"
            self._payload = (model, tok)
            self.accept()

        elif backend == "ollama":
            from PyQt5.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "Ollama 模型名", "請輸入本地 Ollama 模型名稱（如 qwen2.5:7b）")
            if not ok or not name.strip():
                return
            # 登記（以 "ollama:<name>" 做標示）
            register_model(repo_id=name.strip(), backend="ollama", task="", local_path=f"ollama:{name.strip()}", notes="")
            self._backend = "ollama"
            self._payload = name.strip()
            self.accept()
            return

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
