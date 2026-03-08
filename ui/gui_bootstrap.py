"""
ui/gui_bootstrap.py
===================
GUI 版起動時に必要な依存関係を束ねるブートストラップ層。
UI ウィジェットの生成や表示は行わない。
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class GuiRuntimeContext:
    """GUI 実行時の共有コンテキスト。"""

    resolve: Any
    settings: dict[str, Any]
    project_root: str


class GuiBootstrapper:
    """GUI 実行前の初期化を担当する。"""

    def __init__(self, app: Any, resolve: Any, settings_manager: Any, project_root: str) -> None:
        self.app = app
        self.resolve = resolve
        self.settings_manager = settings_manager
        self.project_root = project_root
        self.runtime_context: GuiRuntimeContext | None = None

    def prepare(self) -> GuiRuntimeContext:
        """
        UI 非依存の初期化を実施し、共有コンテキストを作る。
        """
        self.runtime_context = GuiRuntimeContext(
            resolve=self.resolve,
            settings=self.settings_manager.all_settings,
            project_root=self.project_root,
        )
        return self.runtime_context
