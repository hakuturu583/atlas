"""UI state management service."""

import asyncio
from typing import Optional, Callable, Awaitable
from app.models.ui_state import UIState, ViewType, ViewTransition


class UIStateManager:
    """Manages the UI state and notifies subscribers of changes."""

    def __init__(self):
        self._state = UIState()
        self._subscribers: list[Callable[[UIState], Awaitable[None]]] = []
        self._lock = asyncio.Lock()

    @property
    def current_state(self) -> UIState:
        """Get the current UI state."""
        return self._state.model_copy()

    async def transition_to_view(self, transition: ViewTransition) -> UIState:
        """Transition to a new view."""
        async with self._lock:
            self._state.current_view = transition.target_view

            if transition.scenario_id:
                self._state.selected_scenario_id = transition.scenario_id

            if transition.rerun_file:
                self._state.rerun_file_path = transition.rerun_file

            # 購読者に通知
            await self._notify_subscribers()

            return self._state.model_copy()

    async def update_state(self, **kwargs) -> UIState:
        """Update specific state fields."""
        async with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)

            await self._notify_subscribers()
            return self._state.model_copy()

    def subscribe(self, callback: Callable[[UIState], Awaitable[None]]):
        """Subscribe to state changes."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[UIState], Awaitable[None]]):
        """Unsubscribe from state changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def _notify_subscribers(self):
        """Notify all subscribers of state changes."""
        state_copy = self._state.model_copy()
        await asyncio.gather(
            *[subscriber(state_copy) for subscriber in self._subscribers],
            return_exceptions=True
        )


# グローバルインスタンス
ui_state_manager = UIStateManager()
