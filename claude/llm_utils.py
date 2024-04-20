class Prompt:
    def __init__(self, user_prompt_template, system_prompt_template=""):
        self.system_prompt_template = system_prompt_template
        self.user_prompt_template = user_prompt_template
        self._kwargs = {}

    def set_kwargs(self, **kwargs):
        self._kwargs = kwargs

    def get_system_prompt(self):
        if self._kwargs:
            return self.system_prompt_template.format(**self._kwargs)
        else:
            return self.system_prompt_template

    def get_user_prompt(self):
        if self._kwargs:
            return self.user_prompt_template.format(**self._kwargs)
        else:
            return self.user_prompt_template

    def __str__(self):
        return f"🤖 System Prompt: {self.get_system_prompt()}\n\n👤 User Prompt: {self.get_user_prompt()}\n\n✨ Kwargs: {self._kwargs}"
