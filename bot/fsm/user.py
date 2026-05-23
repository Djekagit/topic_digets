from aiogram.fsm.state import State, StatesGroup


class GroupWizard(StatesGroup):
    name = State()
    channels = State()
    interval = State()
    interval_custom = State()
    prompt_choice = State()
    custom_prompt = State()


class GroupEdit(StatesGroup):
    add_channels = State()
    interval_custom = State()
    custom_prompt = State()
