from aiogram.fsm.state import State, StatesGroup


class AdminSettings(StatesGroup):
    model = State()
    default_prompt = State()
