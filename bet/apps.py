# -*- coding: utf-8 -*-
#  bet/apps.py

from django.apps import AppConfig

class BetConfig(AppConfig):
    name = 'bet'
    verbose_name = "Bet"

    def ready(self):
        import bet.signals
